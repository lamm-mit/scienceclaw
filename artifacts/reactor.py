#!/usr/bin/env python3
"""
Artifact Reaction Layer

Enables emergent coordination: agents scan peer artifact stores, run compatible
skills on matching payloads, and produce child artifacts with parent lineage.

Compatibility is determined dynamically:
    skill.input_schema ∩ artifact.payload_schema ≠ ∅

Where:
    skill.input_schema  = CLI parameter names parsed from --help
    artifact.payload_schema = top-level keys of the artifact payload

No hardcoded type→skill mapping.  Adding a new skill or a new payload key
automatically makes it eligible for reactions without touching this file.

Loop prevention:
  1. consumed.txt — each artifact_id written once; never re-reacted
  2. producer_agent != self.agent_name — no self-loops
  3. limit=3 per heartbeat — caps fan-out per cycle

Execution path:
  Reactor → core.skill_executor.SkillExecutor  (same path as deep_investigation)
"""

import json
import logging
import math
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

_log = logging.getLogger(__name__)

from artifacts.artifact import Artifact, ArtifactStore, SKILL_DOMAIN_MAP
from core.skill_registry import get_registry
from core.skill_executor import get_executor


# ---------------------------------------------------------------------------
# Skill input map: skill_name → {param, entity, hint}
# Maps each skill to the primary CLI parameter it expects, the semantic entity
# type the LLM should extract, and an illustrative example value.
# ---------------------------------------------------------------------------

SKILL_INPUT_MAP: Dict[str, Dict[str, str]] = {
    # ── Literature / Search ──────────────────────────────────────────────────
    "pubmed":                  {"param": "query",        "entity": "research topic",                        "hint": "TP53 Y220C small molecule reactivation"},
    "pubmed-database":         {"param": "query",        "entity": "research topic",                        "hint": "p53 reactivation TP53-mutant cancer"},
    "arxiv":                   {"param": "query",        "entity": "research topic",                        "hint": "protein structure prediction transformer"},
    "biorxiv-database":        {"param": "query",        "entity": "research topic",                        "hint": "CRISPR base editing efficiency"},
    "openalex-database":       {"param": "query",        "entity": "research topic",                        "hint": "kinase inhibitor selectivity"},
    "literature-review":       {"param": "topic",        "entity": "research topic",                        "hint": "p53 tumour suppressor reactivation mechanisms"},
    "research-lookup":         {"param": "query",        "entity": "research topic",                        "hint": "APR-246 clinical trials TP53"},
    "perplexity-search":       {"param": "query",        "entity": "research topic",                        "hint": "eprenetapopt mechanism of action"},
    "websearch":               {"param": "query",        "entity": "research topic",                        "hint": "p53 reactivation small molecules"},
    # ── Protein / Sequence ───────────────────────────────────────────────────
    "uniprot":                 {"param": "query",        "entity": "protein name or UniProt accession",     "hint": "TP53, P04637, or KRAS"},
    "uniprot-database":        {"param": "query",        "entity": "protein name or UniProt accession",     "hint": "P53_HUMAN, BRCA1, or P04637"},
    "blast":                   {"param": "query",        "entity": "protein name or gene symbol",           "hint": "TP53 DNA-binding domain"},
    "biopython":               {"param": "sequence",     "entity": "protein or DNA sequence",               "hint": "amino acid or nucleotide sequence string"},
    "sequence":                {"param": "query",        "entity": "sequence or gene name",                 "hint": "TP53 exon 5-8"},
    "gget":                    {"param": "query",        "entity": "gene symbol",                           "hint": "TP53, BRCA1, or KRAS"},
    "esm":                     {"param": "sequence",     "entity": "amino acid sequence",                   "hint": "MEEPQSDPSVEPPLSQETFSDLWKLLPENNVLSPLPSQAMDDLMLSPDDIEQWFTEDP"},
    "adaptyv":                 {"param": "sequence",     "entity": "amino acid sequence",                   "hint": "protein sequence for property prediction"},
    "string-database":         {"param": "query",        "entity": "gene or protein name",                  "hint": "TP53 interaction network"},
    "brenda-database":         {"param": "query",        "entity": "enzyme name or EC number",              "hint": "MDM2 E3 ligase or EC 6.3.2"},
    # ── Structure ────────────────────────────────────────────────────────────
    "pdb":                     {"param": "query",        "entity": "protein name or PDB ID",                "hint": "TP53 Y220C or 2OCJ"},
    "pdb-database":            {"param": "pdb-id",       "entity": "PDB ID",                                "hint": "2OCJ, 4HHB, 6W63"},
    "alphafold-database":      {"param": "query",        "entity": "UniProt accession",                     "hint": "P04637 (TP53_HUMAN)"},
    "diffdock":                {"param": "smiles",       "entity": "SMILES string",                         "hint": "APR-246 SMILES for docking against TP53 structure"},
    "openmm":                  {"param": "structure",    "entity": "PDB file path",                         "hint": "path/to/tp53_y220c.pdb"},
    "rowan":                   {"param": "structure",    "entity": "PDB file path",                         "hint": "path/to/structure.pdb"},
    # ── Chemistry / Compounds ─────────────────────────────────────────────────
    "pubchem":                 {"param": "query",        "entity": "compound name",                         "hint": "APR-246, PRIMA-1, eprenetapopt"},
    "pubchem-database":        {"param": "query",        "entity": "compound name",                         "hint": "APR-246, NSC319726"},
    "chembl":                  {"param": "query",        "entity": "compound name or target",               "hint": "eprenetapopt, APR-246, or TP53"},
    "chembl-database":         {"param": "query",        "entity": "compound name or target",               "hint": "p53 reactivator or MDM2 inhibitor"},
    "cas":                     {"param": "query",        "entity": "compound name or CAS number",           "hint": "APR-246 or 7396-28-3"},
    "nistwebbook":             {"param": "query",        "entity": "compound name",                         "hint": "methylene quinuclidinone"},
    "zinc-database":           {"param": "query",        "entity": "compound name or SMILES",               "hint": "p53 stabilizer scaffold"},
    "drugbank-database":       {"param": "query",        "entity": "drug name",                             "hint": "eprenetapopt, APR-246"},
    "hmdb-database":           {"param": "query",        "entity": "metabolite name",                       "hint": "cysteine, glutathione"},
    # ── Cheminformatics ───────────────────────────────────────────────────────
    "rdkit":                   {"param": "smiles",       "entity": "SMILES string",                         "hint": "O=C1CC[N+]2(CC=C)CCC1CC2 (APR-246)"},
    "datamol":                 {"param": "smiles",       "entity": "SMILES string",                         "hint": "valid SMILES for molecular analysis"},
    "medchem":                 {"param": "smiles",       "entity": "SMILES string",                         "hint": "SMILES for medicinal chemistry filters"},
    "molfeat":                 {"param": "smiles",       "entity": "SMILES string",                         "hint": "SMILES for molecular featurisation"},
    # ── ADMET / Drug Properties ───────────────────────────────────────────────
    "tdc":                     {"param": "smiles",       "entity": "SMILES string",                         "hint": "O=C1CC[N+]2(CC=C)CCC1CC2 (APR-246 SMILES)"},
    "pytdc":                   {"param": "smiles",       "entity": "SMILES string",                         "hint": "valid SMILES for BBB/hERG/solubility prediction"},
    "deepchem":                {"param": "smiles",       "entity": "SMILES string",                         "hint": "SMILES or dataset name (tox21, bbbp)"},
    "torchdrug":               {"param": "smiles",       "entity": "SMILES string",                         "hint": "SMILES for drug-knowledge-graph learning"},
    # ── Pathways / Metabolism ─────────────────────────────────────────────────
    "kegg-database":           {"param": "query",        "entity": "pathway or gene name",                  "hint": "p53 signalling pathway or TP53"},
    "reactome-database":       {"param": "query",        "entity": "pathway or gene name",                  "hint": "TP53 apoptosis pathway"},
    "cobrapy":                 {"param": "model-file",   "entity": "metabolic model file",                  "hint": "path/to/model.json or recon3d"},
    "opentargets-database":    {"param": "query",        "entity": "gene or disease",                       "hint": "TP53, ENSG00000141510, or cancer"},
    # ── Genomics / Variants ───────────────────────────────────────────────────
    "ensembl-database":        {"param": "gene",         "entity": "gene symbol or variant",                "hint": "TP53 or ENSG00000141510"},
    "clinvar-database":        {"param": "query",        "entity": "gene, variant, or disease",             "hint": "TP53 Y220C or rs28934578"},
    "gene-database":           {"param": "query",        "entity": "gene symbol",                           "hint": "TP53, BRCA1, KRAS"},
    "gwas-database":           {"param": "query",        "entity": "SNP ID or trait",                       "hint": "rs28934578 or Li-Fraumeni syndrome"},
    "cosmic-database":         {"param": "query",        "entity": "cancer gene or mutation",               "hint": "TP53 Y220C or KRAS G12D"},
    "ena-database":            {"param": "query",        "entity": "accession or organism",                 "hint": "Homo sapiens TP53 mRNA"},
    # ── Expression / Single-Cell ──────────────────────────────────────────────
    "scanpy":                  {"param": "file",         "entity": "H5AD file path",                        "hint": "path/to/data.h5ad"},
    "scvi-tools":              {"param": "file",         "entity": "H5AD file path",                        "hint": "path/to/single_cell.h5ad"},
    "anndata":                 {"param": "file",         "entity": "H5AD file path",                        "hint": "path/to/anndata.h5ad"},
    "cellxgene-census":        {"param": "gene",         "entity": "gene symbol",                           "hint": "TP53"},
    "pydeseq2":                {"param": "counts-file",  "entity": "count matrix file",                     "hint": "path/to/counts.csv"},
    "geo-database":            {"param": "accession",    "entity": "GEO accession",                         "hint": "GSE12345 or GPL570"},
    # ── Materials Science ─────────────────────────────────────────────────────
    "materials":               {"param": "mp-id",        "entity": "Materials Project ID",                  "hint": "mp-149, mp-1234"},
    "pymatgen":                {"param": "structure-file","entity": "crystal structure file",                "hint": "path/to/POSCAR or structure.cif"},
    "ase":                     {"param": "structure-file","entity": "atomic structure file",                 "hint": "path/to/structure.vasp"},
    # ── Visualisation ─────────────────────────────────────────────────────────
    "datavis":                 {"param": "data",         "entity": "CSV/JSON data or file path",            "hint": "path/to/results.csv or inline JSON"},
    "matplotlib":              {"param": "data",         "entity": "data file path",                        "hint": "path/to/data.csv"},
    "seaborn":                 {"param": "data",         "entity": "data file path",                        "hint": "path/to/data.csv"},
    "plotly":                  {"param": "data",         "entity": "data file path",                        "hint": "path/to/data.json"},
    "scientific-visualization":{"param": "data",         "entity": "data file or description",              "hint": "path/to/results.csv"},
    "scientific-schematics":   {"param": "description",  "entity": "diagram description",                   "hint": "p53-MDM2 interaction schematic"},
    # ── ML / Statistics ───────────────────────────────────────────────────────
    "scikit-learn":            {"param": "data",         "entity": "data file path",                        "hint": "path/to/features.csv"},
    "transformers":            {"param": "text",         "entity": "text or model name",                    "hint": "bert-base-uncased or text to classify"},
    "statistical-analysis":    {"param": "data-file",    "entity": "data file path",                        "hint": "path/to/experimental_data.csv"},
    # ── Peer Review / Synthesis ───────────────────────────────────────────────
    "hypothesis-generation":   {"param": "topic",        "entity": "research topic",                        "hint": "p53 reactivation small molecules TP53-mutant"},
    "scientific-brainstorming":{"param": "prompt",       "entity": "scientific prompt",                     "hint": "novel approaches to restore TP53 function"},
    "peer-review":             {"param": "paper",        "entity": "paper text or file",                    "hint": "manuscript content to review"},
}


def _parse_rich_text_to_results(payload: dict) -> dict:
    """Wrap upstream artifact content for LLM query derivation."""
    text = (
        payload.get("open_questions", "")
        or payload.get("output", "")
        or payload.get("query", "")
        or str(payload)[:600]
    )
    return {
        "papers":    [{"title": text[:400]}] if text else [],
        "proteins":  [],
        "compounds": [],
    }


# ---------------------------------------------------------------------------
# Schema introspection helpers
# ---------------------------------------------------------------------------

# Module-level cache: skill_name -> frozenset of normalised param names
_SKILL_PARAM_CACHE: Dict[str, frozenset] = {}

_SKILL_SCHEMA_CACHE: Dict[str, Optional[dict]] = {}


def _get_skill_schema(skill_name: str, skill_meta: dict) -> Optional[dict]:
    """
    Call `python3 <script> --describe-schema` and return the parsed JSON schema,
    or None if the script doesn't support --describe-schema or crashes.

    Result is cached per skill_name.
    """
    if skill_name in _SKILL_SCHEMA_CACHE:
        return _SKILL_SCHEMA_CACHE[skill_name]

    executables = skill_meta.get("executables", [])
    result = None

    if executables:
        script = executables[0]
        try:
            proc = subprocess.run(
                [sys.executable, script, "--describe-schema"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            output = proc.stdout.strip()
            if output:
                result = json.loads(output)
        except Exception as exc:
            _log.debug("_get_skill_schema(%s): %s", skill_name, exc)

    _SKILL_SCHEMA_CACHE[skill_name] = result
    return result


def _build_input_json(schema: dict, payload: dict) -> Optional[str]:
    """
    Extract data from `payload` matching `schema["input_json_fields"]` and return
    as a JSON string for --input-json, or None if nothing useful was found.

    Extraction rules:
      "papers"   → payload["papers"] or payload["articles"] (list of dicts)
      "rows"     → payload["rows"] or derived from payload["benchmarks"] /
                   payload["papers"] by picking numeric fields as (x, y)
      "vectors"  → payload["vectors"] or payload["embeddings"]
      "data"     → payload["data"] or first numeric list found in payload
    """
    fields = schema.get("input_json_fields", [])
    if not fields:
        return None

    extracted: dict = {}

    for field in fields:
        if field == "papers":
            candidates = payload.get("papers") or payload.get("articles") or []
            if candidates and isinstance(candidates, list):
                extracted["papers"] = candidates
        elif field == "rows":
            if payload.get("rows") and isinstance(payload["rows"], list):
                extracted["rows"] = payload["rows"]
            else:
                rows = _derive_numeric_rows(payload)
                if rows:
                    extracted["rows"] = rows
        elif field == "vectors":
            vecs = payload.get("vectors") or payload.get("embeddings") or []
            labels = payload.get("labels") or []
            if vecs and isinstance(vecs, list):
                extracted["vectors"] = vecs
                if labels:
                    extracted["labels"] = labels
        elif field == "data":
            data = payload.get("data") or []
            if not data:
                for v in payload.values():
                    if isinstance(v, list) and v and isinstance(v[0], (int, float)):
                        data = v
                        break
            if data:
                extracted["data"] = data

    if not extracted:
        return None
    return json.dumps(extracted)


def _derive_numeric_rows(payload: dict) -> list:
    """
    Try to extract (x, y) numeric pairs from benchmarks or papers.
    For scaling law data: x = log10(params), y = log10(loss) or cross-entropy.
    Returns list of {"x": float, "y": float} dicts, empty if nothing found.
    """
    # x: raw param counts → log10 (params always >> 1000)
    # y: perplexity → log10 if > 100, otherwise keep raw (loss typically 1-10)
    candidates = (
        payload.get("benchmarks")
        or payload.get("papers")
        or payload.get("articles")
        or []
    )
    rows = []
    for item in candidates:
        if not isinstance(item, dict):
            continue
        x_val = None
        for key in ("params", "parameter_count", "n_params", "parameters", "x"):
            v = item.get(key)
            if v is not None:
                try:
                    x_val = float(v)
                    if x_val > 1000:
                        x_val = math.log10(x_val)
                    break
                except (TypeError, ValueError):
                    pass
        y_val = None
        for key in ("loss", "perplexity", "cross_entropy", "test_loss", "y"):
            v = item.get(key)
            if v is not None:
                try:
                    y_val = float(v)
                    if y_val > 100:
                        y_val = math.log10(y_val)
                    break
                except (TypeError, ValueError):
                    pass
        if x_val is not None and y_val is not None:
            rows.append({"x": x_val, "y": y_val})
    return rows


def _skill_input_params(skill_name: str, skill_meta: dict) -> frozenset:
    """
    Return the set of CLI parameter names (snake_case) that `skill_name` accepts.

    Calls `python3 <script> --help` once and caches the result.  Falls back to
    empty set if the script is missing or crashes.
    """
    if skill_name in _SKILL_PARAM_CACHE:
        return _SKILL_PARAM_CACHE[skill_name]

    executables = skill_meta.get("executables", [])
    params: Set[str] = set()

    if executables:
        script = executables[0]
        try:
            proc = subprocess.run(
                [sys.executable, script, "--help"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            help_text = proc.stdout + proc.stderr
            # Extract every --flag-name, normalise hyphens → underscores
            for m in re.finditer(r"--([a-z][a-z0-9_-]+)", help_text):
                params.add(m.group(1).replace("-", "_"))
        except Exception:
            pass

    result = frozenset(params)
    _SKILL_PARAM_CACHE[skill_name] = result
    return result


def _find_match(
    payload: dict,
    skill_params: frozenset,
) -> Optional[Tuple[str, str, object]]:
    """
    Return (payload_key, param_name, value) for the first payload key that
    overlaps with skill_params, or None.

    Skips keys whose values are empty, nested dicts, or otherwise un-passable
    as a single CLI string.
    """
    for raw_key, value in payload.items():
        # Normalise payload key to match CLI convention
        norm = raw_key.replace("-", "_").lower()
        if norm not in skill_params:
            continue
        # List: take first element as a representative value (unless it is a
        # known multi-valued field that downstream skills accept as nargs="*").
        if isinstance(value, list):
            multi_keys = {
                "sequences",
                "aligned_sequences",
                "hotspot_positions",
                "protected_positions",
                "conserved_columns",
                "variable_columns",
            }
            if norm in multi_keys and all(not isinstance(x, (dict, list)) for x in value):
                pass  # keep full list
            else:
                value = value[0] if value else None
        # Skip nested objects and empty values
        if value is None or isinstance(value, dict):
            continue
        return raw_key, norm, value
    return None


# ---------------------------------------------------------------------------
# Main reactor
# ---------------------------------------------------------------------------

class ArtifactReactor:
    """
    Scans all agents' artifact stores, finds peer artifacts whose payload keys
    overlap with the current agent's skills' accepted parameters, runs those
    skills, and saves child artifacts with parent lineage.
    """

    def __init__(
        self,
        agent_name: str,
        agent_profile: dict,
        artifact_store: ArtifactStore,
    ):
        self.agent_name = agent_name
        self._agent_profile = dict(agent_profile or {})
        self.store = artifact_store
        self._base = Path.home() / ".scienceclaw" / "artifacts"
        self.consumed_path = self._base / agent_name / "consumed.txt"

        # Reuse the same registry and executor as deep_investigation
        self._registry = get_registry()
        self._executor = get_executor()

        # Restrict to agent's preferred_tools if specified
        preferred = agent_profile.get("preferred_tools", [])
        if preferred:
            self._allowed_skills: Optional[Set[str]] = set(preferred)
        else:
            self._allowed_skills = None  # unrestricted

        # If the profile declares a closed investigation team, only fulfil
        # needs broadcast by those agents (prevents cross-investigation pollution)
        partner_list = agent_profile.get("partner_agents", [])
        self._partner_agents: Optional[Set[str]] = set(partner_list) if partner_list else None

        # Optional: scope all scan_* operations to a single investigation_id.
        # This prevents cross-run pollution when the same agent identities are
        # reused across multiple demos in the shared global index.
        self._investigation_id_filter: str = (
            agent_profile.get("investigation_id_filter")
            or agent_profile.get("investigation_id")
            or ""
        )

        # Needs-driven behavior knobs (kept conservative by default)
        self._needs_fulfillment_budget: int = int(
            agent_profile.get("needs_fulfillment_budget", 2) or 2
        )
        self._max_variants_default: int = int(
            agent_profile.get("needs_max_variants_default", 1) or 1
        )

        self._peer_reactors: List["ArtifactReactor"] = []
        # Lazy-cached LLM reasoner — shared across all entity enrichment calls
        # within a single reactor instance (avoids per-artifact instantiation).
        self._reasoner = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register_peer(self, reactor: "ArtifactReactor") -> None:
        """Register a sibling reactor to receive mutation cascade outputs."""
        if reactor is not self and reactor not in self._peer_reactors:
            self._peer_reactors.append(reactor)

    def can_react(self, artifact: Artifact) -> bool:
        """Return True if this reactor has a skill compatible with artifact's payload."""
        return self._is_compatible(artifact, self._candidate_skills())

    def react_to_artifact(self, artifact: Artifact) -> Optional[Artifact]:
        """
        React to a specific artifact (e.g. a mutation child) without scanning the
        global index.  Calls _transform() directly; marks artifact as consumed on
        success so it won't be re-processed by scan_available() in future cycles.
        """
        child = self._transform(artifact)
        if child:
            self._mark_consumed(artifact.artifact_id)
        return child

    def scan_available(self, index_lines: Optional[List[str]] = None) -> List[Artifact]:
        """
        Return unclaimed peer artifacts compatible with at least one of this
        agent's skills.

        Reads from the global index (payload-free) for fast filtering, then
        loads the full artifact from the producer's per-agent store only for
        candidates that pass all filters.

        Compatibility = skill.input_params ∩ artifact.payload_keys ≠ ∅

        Args:
            index_lines: Pre-loaded raw text lines from global_index.jsonl.
                         If provided, skips the disk read (caller's responsibility).
        """
        global_index = self._base / "global_index.jsonl"
        if index_lines is None:
            if not global_index.exists():
                return []
            try:
                lines = global_index.read_text(encoding="utf-8").splitlines()
            except OSError:
                return []
        else:
            lines = index_lines

        consumed = self._load_consumed()
        candidate_skills = self._candidate_skills()
        available = []

        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            if entry.get("producer_agent") == self.agent_name:
                continue  # no self-loops
            if entry.get("artifact_id") in consumed:
                continue  # already reacted
            if self._investigation_id_filter and entry.get("investigation_id") != self._investigation_id_filter:
                continue

            # Load full artifact (with payload) only for viable candidates
            producer = entry.get("producer_agent", "")
            artifact_id = entry.get("artifact_id", "")
            store_path = self._base / producer / "store.jsonl"
            art = self._load_artifact_from_store(store_path, artifact_id)
            if art is None:
                continue

            if self._is_compatible(art, candidate_skills):
                available.append(art)

        return available

    def _load_artifact_from_store(
        self, store_path: Path, artifact_id: str
    ) -> Optional[Artifact]:
        """Load a single artifact by ID from a per-agent store file."""
        if not store_path.exists():
            return None
        try:
            for line in store_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if d.get("artifact_id") == artifact_id:
                    return Artifact.from_dict(d)
        except OSError:
            pass
        return None

    def react(self, limit: int = 3, investigation_id: str = "") -> List[Artifact]:
        """
        React to up to `limit` compatible peer artifacts.

        First, fulfils any peer needs this agent can satisfy (needs-driven
        reactions).  Then attempts multi-parent synthesis; falls back to
        single-parent transform for remaining unclaimed artifacts.  After normal
        reactions, runs mutation triggers to restructure stagnant / redundant /
        conflicting sub-graphs and optionally updates the mutation_policy artifact.

        Returns list of newly produced child artifacts (including mutations).
        """
        # Load global index ONCE for this cycle; pass to scan_* helpers.
        global_index = self._base / "global_index.jsonl"
        try:
            index_lines: Optional[List[str]] = (
                global_index.read_text(encoding="utf-8").splitlines()
                if global_index.exists()
                else []
            )
        except OSError:
            index_lines = None  # fall back to per-method reads

        # Needs-driven reactions take priority: fulfil explicit peer requests first
        needs_children = self.react_to_needs(limit=max(0, int(self._needs_fulfillment_budget)), index_lines=index_lines)
        children = list(needs_children)

        available = self.scan_available(index_lines=index_lines)

        # Attempt multi-parent synthesis first
        synthesized = self._react_multi(available, limit=2)
        consumed_in_multi = {pid for c in synthesized for pid in c.parent_artifact_ids}
        children.extend(synthesized)

        # Single-parent fallback for remaining unclaimed artifacts
        remaining = [a for a in available if a.artifact_id not in consumed_in_multi]
        for parent in remaining[:max(0, limit - len(children))]:
            child = self._transform(parent)
            if child:
                children.append(child)
                self._mark_consumed(parent.artifact_id)

        # ------------------------------------------------------------------
        # Mutation layer — runs after normal reactions
        # ------------------------------------------------------------------
        if investigation_id:
            from artifacts.mutator import ArtifactMutator

            mutator = ArtifactMutator(self.agent_name, self.store)
            # Convert raw str lines to dicts once for mutator (it expects List[dict])
            parsed_index_lines: Optional[List[dict]] = None
            if index_lines is not None:
                parsed_index_lines = []
                for _l in index_lines:
                    _l = _l.strip()
                    if _l:
                        try:
                            parsed_index_lines.append(json.loads(_l))
                        except json.JSONDecodeError:
                            pass
            triggers = mutator.detect_triggers(investigation_id, index_lines=parsed_index_lines)

            # Load policy to get per-investigation cap
            policy = mutator._load_policy(investigation_id)
            cap = policy.max_mutations_per_cycle

            for t in triggers[:cap]:
                mutated = mutator.apply(t)
                if mutated:
                    children.append(mutated)

            # Cascade mutation children to peer reactors immediately
            cascade_children: List[Artifact] = []
            for mutated in [c for c in children if "mutation_provenance" in c.payload]:
                for peer in self._peer_reactors:
                    if peer.can_react(mutated):
                        grandchild = peer.react_to_artifact(mutated)
                        if grandchild:
                            cascade_children.append(grandchild)
            children.extend(cascade_children)

            # Compute pressure from this cycle and maybe update policy
            reactions_this_cycle = len(synthesized) + len(
                [c for c in children if not c.parent_artifact_ids]
            )
            conflict_triggers = sum(1 for t in triggers if t.trigger_type == "conflict")
            redundancy_triggers = sum(
                1 for t in triggers if t.trigger_type == "redundancy"
            )
            total = max(1, len(triggers))
            pressure = {
                "conflict_rate": conflict_triggers / total,
                "redundancy_rate": redundancy_triggers / total,
            }
            policy_artifact = mutator.maybe_update_policy(investigation_id, pressure)
            if policy_artifact:
                children.append(policy_artifact)

        return children

    def _react_multi(self, available: List[Artifact], limit: int = 2) -> List[Artifact]:
        """
        Attempt multi-parent synthesis: combine 2+ compatible parent artifacts
        into a single derived artifact using a shared skill.

        For each skill with 2+ compatible artifacts:
        - Select up to `limit` parents (most recent first)
        - Merge payloads oldest→newest (newest values overwrite on key conflict)
        - Execute skill on merged payload
        - Create child with all parent IDs recorded

        Returns list of synthesized child artifacts.
        """
        candidate_skills = self._candidate_skills()
        consumed = self._load_consumed()

        # Build map: skill_name → list of compatible artifacts
        skill_to_artifacts: Dict[str, List[Artifact]] = {}
        for art in available:
            if art.artifact_id in consumed:
                continue
            for skill_name, skill_meta in candidate_skills.items():
                params = _skill_input_params(skill_name, skill_meta)
                payload_norm = {k.replace("-", "_").lower() for k in art.payload}
                if params & payload_norm:
                    skill_to_artifacts.setdefault(skill_name, []).append(art)

        synthesized = []
        already_consumed: Set[str] = set()

        for skill_name, arts in skill_to_artifacts.items():
            if len(arts) < 2:
                continue

            skill_meta = candidate_skills[skill_name]
            params = _skill_input_params(skill_name, skill_meta)

            # Skip any already consumed in this multi-pass
            eligible = [a for a in arts if a.artifact_id not in already_consumed]
            if len(eligible) < 2:
                continue

            # Sort ascending by (timestamp, producer_agent) — oldest first
            # so newest values overwrite on key conflict
            eligible.sort(key=lambda a: (a.timestamp, a.producer_agent))
            selected = eligible[:limit]

            # Merge payloads oldest→newest
            merged_payload: Dict[str, object] = {}
            for art in selected:
                merged_payload.update(art.payload)

            # Build exec params from merged payload
            exec_params: Dict[str, object] = {}
            payload_norm_map = {k.replace("-", "_").lower(): k for k in merged_payload}
            for norm_key in params & set(payload_norm_map.keys()):
                raw_key = payload_norm_map[norm_key]
                value = merged_payload[raw_key]
                if isinstance(value, list):
                    value = value[0] if value else None
                if value is None or isinstance(value, dict):
                    continue
                exec_params[norm_key] = value

            if not exec_params:
                continue

            result = self._executor.execute_skill(
                skill_name=skill_name,
                skill_metadata=skill_meta,
                parameters=exec_params,
                timeout=30,
            )

            if result.get("status") != "success":
                continue

            payload = result.get("result", {})
            if not isinstance(payload, dict):
                payload = {"output": payload}

            # Shared investigation_id if all parents share one, else cross
            inv_ids = {a.investigation_id for a in selected}
            investigation_id = inv_ids.pop() if len(inv_ids) == 1 else "cross_investigation"

            parent_ids = [a.artifact_id for a in selected]
            child = self.store.create_and_save(
                skill_used=skill_name,
                payload=payload,
                investigation_id=investigation_id,
                parent_artifact_ids=parent_ids,
            )
            for pid in parent_ids:
                self._mark_consumed(pid)
                already_consumed.add(pid)
            synthesized.append(child)

        return synthesized

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _candidate_skills(self) -> Dict[str, dict]:
        """Return registry entries for skills this agent is allowed to run."""
        all_skills = self._registry.skills
        if self._allowed_skills is None:
            return all_skills
        return {k: v for k, v in all_skills.items() if k in self._allowed_skills}

    def _is_compatible(self, art: Artifact, candidate_skills: Dict[str, dict]) -> bool:
        """Return True if any candidate skill can accept a key from art.payload."""
        payload_norm = {k.replace("-", "_").lower() for k in art.payload}
        for skill_name, skill_meta in candidate_skills.items():
            params = _skill_input_params(skill_name, skill_meta)
            if params & payload_norm:
                return True
        return False

    @staticmethod
    def _normalize_payload(raw) -> dict:
        """
        Flatten a skill result into a dict with top-level entity keys so the
        reactor's key-overlap matching can fire on subsequent agents.

        - dict → returned as-is
        - list of dicts → keys from the first item, plus aggregate keys:
            * 'items' = the full list (for agents that want all results)
            * 'count' = length
          All scalar values from the first item are promoted to top level.
        - anything else → {"output": raw}
        """
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, list):
            merged: Dict[str, object] = {"items": raw, "count": len(raw)}
            if raw and isinstance(raw[0], dict):
                for k, v in raw[0].items():
                    if not isinstance(v, (dict, list)):
                        merged[k] = v
            return merged
        return {"output": raw}

    def _transform(self, parent: Artifact) -> Optional[Artifact]:
        """
        Find the first compatible skill for `parent`, run it via SkillExecutor,
        and return the child artifact (or None on failure).
        """
        candidate_skills = self._candidate_skills()
        payload_keys = {k.replace("-", "_").lower(): k for k in parent.payload}

        for skill_name, skill_meta in candidate_skills.items():
            params = _skill_input_params(skill_name, skill_meta)
            overlap = params & set(payload_keys.keys())

            # --- Schema-driven --input-json injection ---
            # Discover skill's declared input schema via --describe-schema,
            # extract matching data from parent payload, inject as --input-json.
            # Also serves as a secondary compatibility path when key-overlap alone
            # does not match (e.g. skill accepts --input-json but payload keys are
            # domain-specific like "papers" / "vectors").
            _schema = _get_skill_schema(skill_name, skill_meta)
            _input_json_str: Optional[str] = None
            if _schema and "input_json" in params:
                _input_json_str = _build_input_json(_schema, parent.payload)

            if not overlap and not _input_json_str:
                continue

            # Build parameter dict from all overlapping keys
            exec_params: Dict[str, object] = {}
            for norm_key in overlap:
                raw_key = payload_keys[norm_key]
                value = parent.payload[raw_key]
                if isinstance(value, list):
                    multi_keys = {
                        "sequences",
                        "aligned_sequences",
                        "hotspot_positions",
                        "protected_positions",
                        "conserved_columns",
                        "variable_columns",
                    }
                    if norm_key in multi_keys and all(not isinstance(x, (dict, list)) for x in value):
                        pass  # keep full list
                    else:
                        value = value[0] if value else None
                if value is None or isinstance(value, dict):
                    continue
                exec_params[norm_key] = value

            # Inject --input-json when schema extraction succeeded
            if _input_json_str:
                exec_params["input_json"] = _input_json_str

            if not exec_params:
                continue

            # --- LLM entity enrichment ---
            # When the key-overlap match produced a generic/empty query, ask
            # the LLM to extract the most relevant entity name from the parent
            # artifact so the child skill gets a meaningful, specific input.
            skill_info = SKILL_INPUT_MAP.get(skill_name)
            if skill_info:
                param_name = skill_info["param"]
                current_val = exec_params.get(param_name) or exec_params.get("query") or ""
                is_generic = (
                    not current_val
                    or len(str(current_val)) < 6
                    or str(current_val).startswith("inv-")
                    or str(current_val) == parent.investigation_id
                )
                if is_generic:
                    try:
                        from autonomous.llm_reasoner import LLMScientificReasoner
                        if self._reasoner is None:
                            self._reasoner = LLMScientificReasoner(self.agent_name)
                        reasoner = self._reasoner
                        topic = parent.payload.get("topic", "")
                        results_so_far = _parse_rich_text_to_results(parent.payload)
                        llm_query = reasoner.derive_query_for_skill(
                            skill_name=skill_name,
                            skill_category=skill_info["entity"],
                            topic=topic or str(parent.payload)[:200],
                            results_so_far=results_so_far,
                        )
                        if llm_query:
                            exec_params[param_name] = llm_query
                            if param_name != "query":
                                exec_params["query"] = llm_query
                    except Exception:
                        pass

            result = self._executor.execute_skill(
                skill_name=skill_name,
                skill_metadata=skill_meta,
                parameters=exec_params,
                timeout=30,
            )

            if result.get("status") == "success":
                payload = self._normalize_payload(result.get("result", {}))
                child = self.store.create_and_save(
                    skill_used=skill_name,
                    payload=payload,
                    investigation_id=parent.investigation_id,
                    parent_artifact_ids=[parent.artifact_id],
                )
                return child

        return None

    def _load_consumed(self) -> Set[str]:
        if self.consumed_path.exists():
            return set(self.consumed_path.read_text(encoding="utf-8").splitlines())
        return set()

    def _mark_consumed(self, artifact_id: str) -> None:
        self.consumed_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.consumed_path, "a", encoding="utf-8") as fh:
            fh.write(artifact_id + "\n")

    # ------------------------------------------------------------------
    # Needs-driven reaction helpers
    # ------------------------------------------------------------------

    @property
    def consumed_needs_path(self) -> Path:
        """Path to the file tracking which (artifact_id, need_index) pairs
        have already been fulfilled by this agent."""
        return self._base / self.agent_name / "consumed_needs.txt"

    def _load_consumed_needs(self) -> Tuple[Set[str], Set[str]]:
        """
        Return (variant_keys, wildcard_keys).

        - variant_keys: strings of form 'artifact_id:need_index:variant_id'
        - wildcard_keys: strings of form 'artifact_id:need_index' (treat as “all variants consumed”)

        Backwards compatible with older files that stored only wildcard keys.
        """
        if self.consumed_needs_path.exists():
            lines = set(
                l.strip()
                for l in self.consumed_needs_path.read_text(encoding="utf-8").splitlines()
                if l.strip()
            )
            wildcards: Set[str] = set()
            variants: Set[str] = set()
            for line in lines:
                parts = line.split(":")
                if len(parts) >= 2:
                    wildcards.add(f"{parts[0]}:{parts[1]}")
                if len(parts) >= 3:
                    variants.add(f"{parts[0]}:{parts[1]}:{parts[2]}")
                elif len(parts) == 2:
                    # legacy wildcard entry
                    pass
            return variants, wildcards
        return set(), set()

    def _mark_need_consumed(self, artifact_id: str, need_index: int, variant_id: str) -> None:
        """Record that this agent has fulfilled one variant for need at need_index."""
        self.consumed_needs_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.consumed_needs_path, "a", encoding="utf-8") as fh:
            fh.write(f"{artifact_id}:{need_index}:{variant_id}\n")

    def _artifact_type_to_skills(self) -> Dict[str, List[str]]:
        """
        Build a map from artifact_type → list of skill names this agent can run
        to produce that type.

        Computed dynamically by inverting SKILL_DOMAIN_MAP and intersecting with
        the agent's candidate_skills, so no hardcoded mapping is needed.
        """
        candidate_skills = self._candidate_skills()
        type_to_skills: Dict[str, List[str]] = {}
        for skill_name in candidate_skills:
            for atype in SKILL_DOMAIN_MAP.get(skill_name, []):
                type_to_skills.setdefault(atype, []).append(skill_name)
        return type_to_skills

    def scan_needs(self, index_lines: Optional[List[str]] = None) -> List[Tuple[dict, int]]:
        """
        Scan global_index.jsonl for peer artifacts that broadcast needs this
        agent can fulfil.

        Returns list of (index_entry, need_index) tuples where:
        - index_entry  — the raw dict from global_index.jsonl
        - need_index   — position of the specific need in entry["needs"]

        Filters:
        - needs list must be non-empty
        - producer_agent must differ from this agent (no self-fulfilment)
        - (artifact_id, need_index) must not be in consumed_needs
        - need's artifact_type must be producible by at least one of this
          agent's skills (via _artifact_type_to_skills)

        Args:
            index_lines: Pre-loaded raw text lines from global_index.jsonl.
        """
        global_index = self._base / "global_index.jsonl"
        if index_lines is None:
            if not global_index.exists():
                return []
            try:
                lines = global_index.read_text(encoding="utf-8").splitlines()
            except OSError:
                return []
        else:
            lines = index_lines

        consumed_variants, consumed_wildcards = self._load_consumed_needs()
        type_to_skills = self._artifact_type_to_skills()
        results = []

        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            producer = entry.get("producer_agent", "")
            if producer == self.agent_name:
                continue  # no self-fulfilment

            # If investigation is closed-team, skip needs from outside agents
            if self._partner_agents is not None and producer not in self._partner_agents:
                continue
            if self._investigation_id_filter and entry.get("investigation_id") != self._investigation_id_filter:
                continue

            needs = entry.get("needs", [])
            if not needs:
                continue

            artifact_id = entry.get("artifact_id", "")
            for need_index, need in enumerate(needs):
                key = f"{artifact_id}:{need_index}"
                if key in consumed_wildcards:
                    continue  # already fulfilled
                atype = need.get("artifact_type", "")
                if atype in type_to_skills:
                    results.append((entry, need_index))

        return results

    def react_to_needs(self, limit: int = 2, index_lines: Optional[List[str]] = None) -> List[Artifact]:
        """
        Fulfil up to `limit` peer needs by running appropriate skills and
        creating child artifacts.

        For each unfulfilled need this agent can satisfy:
        1. Load the full parent artifact to get context
        2. Pick a skill that produces the requested artifact_type
        3. Run the skill with need.query as the primary parameter
        4. Save a child artifact with _fulfilled_need and _need_index in payload
        5. Mark the need as consumed

        Args:
            index_lines: Pre-loaded raw text lines from global_index.jsonl.

        Returns list of newly produced fulfillment artifacts.
        """
        candidates = self.scan_needs(index_lines=index_lines)
        if not candidates:
            return []

        type_to_skills = self._artifact_type_to_skills()
        fulfillments: List[Artifact] = []
        consumed_variants, consumed_wildcards = self._load_consumed_needs()

        # Use pre-loaded index lines for pressure ranking when provided
        global_lines: List[dict] = []
        if index_lines is not None:
            for line in index_lines:
                line = line.strip()
                if not line:
                    continue
                try:
                    global_lines.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        else:
            global_index = self._base / "global_index.jsonl"
            if global_index.exists():
                try:
                    for line in global_index.read_text(encoding="utf-8").splitlines():
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            global_lines.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
                except OSError:
                    global_lines = []

        # Rank candidates by deterministic “artifact pressure”
        try:
            from artifacts.pressure import NeedRef, score_need

            scored: List[Tuple[float, Tuple[dict, int]]] = []
            for entry, need_index in candidates:
                needs = entry.get("needs", []) or []
                if need_index >= len(needs) or not isinstance(needs[need_index], dict):
                    continue
                need = needs[need_index]
                ref = NeedRef(
                    parent_artifact_id=str(entry.get("artifact_id") or ""),
                    need_index=int(need_index),
                    producer_agent=str(entry.get("producer_agent") or ""),
                    investigation_id=str(entry.get("investigation_id") or ""),
                    artifact_type=str(need.get("artifact_type") or ""),
                    query=str(need.get("query") or ""),
                    rationale=str(need.get("rationale") or ""),
                    parent_timestamp=str(entry.get("timestamp") or ""),
                )
                depth = 0
                try:
                    depth = int(self.store.get_depth(ref.parent_artifact_id))
                except Exception:
                    depth = 0
                scored.append((score_need(need=ref, depth=depth, global_index_lines=global_lines), (entry, need_index)))
            scored.sort(key=lambda x: x[0], reverse=True)
            candidates = [pair for _, pair in scored] or candidates
        except Exception:
            pass

        strict_variants = bool(self._agent_profile.get("strict_need_variants", False))

        # `limit` historically behaved like "max fulfillments". For branching
        # needs (multiple variants per single need), we must allow multiple
        # artifacts per need or strict variants will fail when the budget is low.
        # Cap total artifacts to a small multiple of the budget.
        max_artifacts = max(1, int(limit)) * 6

        for entry, need_index in candidates[:limit]:
            if len(fulfillments) >= max_artifacts:
                break

            artifact_id = entry.get("artifact_id", "")
            producer = entry.get("producer_agent", "")
            needs = entry.get("needs", [])
            if need_index >= len(needs):
                continue

            need = needs[need_index]
            atype = need.get("artifact_type", "")
            query = need.get("query", "")
            rationale = need.get("rationale", "")

            if not query or not atype:
                continue

            # Pick first available skill that produces this artifact_type
            skill_names = type_to_skills.get(atype, [])
            if not skill_names:
                continue

            candidate_skills = self._candidate_skills()

            # Branching controls (optional; backward compatible)
            branch = bool(need.get("branch", False))
            max_variants = int(need.get("max_variants") or (self._max_variants_default if branch else 1) or 1)
            max_variants = max(1, min(6, max_variants))
            preferred_skills = need.get("preferred_skills") or []
            if not isinstance(preferred_skills, list):
                preferred_skills = []
            param_variants = need.get("param_variants") or []
            if not isinstance(param_variants, list):
                param_variants = []

            # Determine variant specs: list of (variant_id, skill_name, exec_params, strategy_label)
            def _build_exec_params(skill_name: str, skill_meta: dict, q: str, overrides: Optional[dict] = None) -> Dict[str, object]:
                params = _skill_input_params(skill_name, skill_meta)
                base: Dict[str, object] = {"query": q}
                if "search" in params and "query" not in params:
                    base = {"search": q}
                elif "smiles" in params and not any(k in params for k in ("query", "search")):
                    base = {"smiles": q}
                # Merge overrides last
                if overrides and isinstance(overrides, dict):
                    for k, v in overrides.items():
                        base[k] = v
                return base

            variants: List[Tuple[str, str, Dict[str, object], str]] = []

            # Param variants: same need, potentially same skill, different parameters
            if branch and param_variants:
                for idx_pv, pv in enumerate(param_variants[:max_variants]):
                    if not isinstance(pv, dict):
                        continue
                    pv_skill = pv.get("skill") or None
                    overrides = dict(pv.get("params") or pv)
                    overrides.pop("skill", None)
                    overrides.pop("variant_id", None)
                    chosen = None
                    if pv_skill and pv_skill in candidate_skills and pv_skill in skill_names:
                        chosen = pv_skill
                    else:
                        # fall back to first allowed skill
                        for sname in skill_names:
                            if sname in candidate_skills:
                                chosen = sname
                                break
                    if not chosen:
                        continue
                    vid = str(pv.get("variant_id") or f"pv{idx_pv}")
                    meta = candidate_skills[chosen]
                    ex_params = _build_exec_params(chosen, meta, query, overrides=overrides)
                    variants.append((f"{chosen}:{vid}", chosen, ex_params, "param_variant"))

            # Otherwise: pick distinct skills as competing hypotheses
            if not variants:
                pool: List[str] = []
                if branch and preferred_skills:
                    for s in preferred_skills:
                        if s in skill_names and s in candidate_skills:
                            pool.append(s)
                if not pool:
                    for s in skill_names:
                        if s in candidate_skills:
                            pool.append(s)
                if not pool:
                    continue
                take = 1 if not branch else min(max_variants, len(pool))
                for s in pool[:take]:
                    meta = candidate_skills[s]
                    variants.append((f"{s}:v0", s, _build_exec_params(s, meta, query), "skill_variant"))

            # Execute variants (branching) for this need
            wildcard_key = f"{artifact_id}:{need_index}"
            if wildcard_key in consumed_wildcards:
                continue

            expected = len(variants)
            succeeded = 0

            for variant_id, chosen_skill, exec_params, strategy in variants:
                if len(fulfillments) >= max_artifacts:
                    break
                consumed_key = f"{artifact_id}:{need_index}:{variant_id}"
                if consumed_key in consumed_variants:
                    continue

                chosen_meta = candidate_skills.get(chosen_skill)
                if not chosen_meta:
                    continue

                try:
                    result = self._executor.execute_skill(
                        skill_name=chosen_skill,
                        skill_metadata=chosen_meta,
                        parameters=exec_params,
                        timeout=45,
                    )
                except Exception:
                    continue

                if result.get("status") != "success":
                    continue

                payload = result.get("result", {})
                if not isinstance(payload, dict):
                    payload = {"output": str(payload)}

                # Tag the payload so loop_controller can detect fulfillment artifacts
                payload["_fulfilled_need"] = {
                    "artifact_type": atype,
                    "query": query,
                    "rationale": rationale,
                    "parent_artifact_id": artifact_id,
                    "producer_agent": producer,
                }
                payload["_need_index"] = need_index
                payload["_fulfillment_variant"] = {
                    "variant_id": variant_id,
                    "skill": chosen_skill,
                    "strategy": strategy,
                    "params": {k: v for k, v in exec_params.items() if k not in ("input_json",)},
                }

                child = self.store.create_and_save(
                    skill_used=chosen_skill,
                    payload=payload,
                    investigation_id=entry.get("investigation_id", ""),
                    parent_artifact_ids=[artifact_id],
                )
                self._mark_need_consumed(artifact_id, need_index, variant_id=variant_id)
                fulfillments.append(child)
                succeeded += 1
                print(
                    f"  [needs] Fulfilled need #{need_index} from {producer} "
                    f"({atype}, query='{query[:45]}', variant='{variant_id}')"
                )

            if strict_variants and branch and succeeded != expected:
                raise RuntimeError(
                    f"Need variants failed: {producer} need#{need_index} atype={atype} "
                    f"query={query!r} succeeded={succeeded}/{expected}"
                )

        return fulfillments


# ---------------------------------------------------------------------------
# Posting summary helper (used by loop_controller)
# ---------------------------------------------------------------------------

def summarise_reactions(children: List[Artifact], registry=None) -> str:
    """
    Build a human-readable summary of a batch of reaction artifacts for posting.

    Includes:
    - How many parents were consumed, from how many distinct agents
    - What skill produced each child and what artifact type resulted
    - Key payload values extracted from each child (compound name, prediction
      score, protein ID, top hit, etc.)
    """
    if not children:
        return "No reaction artifacts produced."

    parent_ids = [p for c in children for p in c.parent_artifact_ids]
    # parent agent names aren't stored on the child, but we can group by investigation
    inv_ids = list({c.investigation_id for c in children if c.investigation_id})

    lines = [
        f"Consumed {len(parent_ids)} peer artifact(s) → "
        f"produced {len(children)} derived artifact(s) "
        f"via {len({c.skill_used for c in children})} skill(s).",
        "",
    ]

    for child in children:
        key_values = _extract_key_values(child.payload, child.artifact_type)
        is_synthesis = len(child.parent_artifact_ids) > 1
        label = "SYNTHESIS" if is_synthesis else child.artifact_type
        parent_refs = ", ".join(p[:8] + "…" for p in child.parent_artifact_ids)
        lines.append(
            f"  • [{label}] via {child.skill_used} "
            f"(parents: {parent_refs}) — {key_values}"
        )

    if inv_ids:
        lines.append(f"\nLinked investigation(s): {', '.join(inv_ids[:3])}")
    lines.append(f"Artifact refs: {[c.artifact_id[:8] + '…' for c in children]}")

    return "\n".join(lines)


def _extract_key_values(payload: dict, artifact_type: str) -> str:
    """Pull a concise, human-readable value string from a payload dict."""
    # Ordered list of keys to try per artifact type
    TYPE_KEYS = {
        "admet_prediction": ["predictions", "BBB", "HIA", "solubility", "score"],
        "compound_data":    ["name", "iupac_name", "canonical_smiles", "molecular_formula"],
        "protein_data":     ["id", "accession", "gene_name", "protein_name", "organism"],
        "sequence_alignment": ["top_hit", "identity", "evalue", "hit_id"],
        "pubmed_results":   ["total", "count", "papers"],
        "rdkit_properties": ["molecular_weight", "logP", "tpsa", "hbd", "hba"],
    }

    candidates = TYPE_KEYS.get(artifact_type, [])
    # Fall back to first five non-empty scalar keys
    if not candidates:
        candidates = list(payload.keys())[:5]

    parts = []
    for k in candidates:
        v = payload.get(k)
        if v is None:
            continue
        if isinstance(v, dict):
            # One level deep: grab first scalar
            for sub_k, sub_v in v.items():
                if not isinstance(sub_v, (dict, list)):
                    parts.append(f"{sub_k}={sub_v}")
                    break
        elif isinstance(v, list):
            parts.append(f"{k}[{len(v)}]")
        else:
            parts.append(f"{k}={v}")
        if len(parts) >= 3:
            break

    return ", ".join(parts) if parts else "(no extractable values)"
