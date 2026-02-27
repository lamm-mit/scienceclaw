#!/usr/bin/env python3
"""
Artifact layer for the scienceclaw agent system.

Every skill invocation produces an Artifact — a versioned, addressable,
content-hashed record of what a specific skill returned for a specific agent
during a specific investigation.

Artifacts are appended to:
    ~/.scienceclaw/artifacts/{agent_name}/store.jsonl

Pattern mirrors memory/journal.py (JSONL append-only, one JSON object per line).

Address scheme: artifact://{agent_name}/{artifact_id}
"""

import hashlib
import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4


# ---------------------------------------------------------------------------
# Skill domain map
# One entry per skill family (covering 200+ skills).
# Keys are the skill names as used in agent profiles ("preferred_tools").
# Values are the artifact types that skill family may produce.
# ---------------------------------------------------------------------------
SKILL_DOMAIN_MAP: Dict[str, List[str]] = {
    # -----------------------------------------------------------------------
    # Literature / preprints / citation
    # -----------------------------------------------------------------------
    "pubmed":                       ["pubmed_results"],
    "pubmed-database":              ["pubmed_results"],
    "arxiv":                        ["pubmed_results"],
    "biorxiv-database":             ["pubmed_results"],
    "openalex-database":            ["pubmed_results"],
    "literature-review":            ["pubmed_results", "report"],
    "citation-management":          ["pubmed_results"],
    "fabric":                       ["pubmed_results", "report"],
    "research-lookup":              ["pubmed_results", "web_content"],
    "perplexity-search":            ["web_content", "pubmed_results"],
    # legacy / alternate names kept for backwards compat
    "europe-pmc":                   ["pubmed_results"],
    "semantic-scholar":             ["pubmed_results"],

    # -----------------------------------------------------------------------
    # Protein / sequence / structure
    # -----------------------------------------------------------------------
    "uniprot":                      ["protein_data"],
    "uniprot-database":             ["protein_data"],
    "blast":                        ["sequence_alignment"],
    "biopython":                    ["sequence_alignment", "protein_data"],
    "bioservices":                  ["protein_data", "compound_data", "pathway_data"],
    "sequence":                     ["sequence_alignment", "protein_data"],
    "gget":                         ["protein_data", "genomic_data", "sequence_alignment"],
    "esm":                          ["sequence_design", "protein_data", "structure_data"],
    "adaptyv":                      ["protein_data", "admet_prediction"],
    "string-database":              ["network_data", "protein_data"],
    "brenda-database":              ["pathway_data", "protein_data"],
    # legacy names
    "interpro":                     ["protein_data"],
    "pfam":                         ["protein_data"],

    # -----------------------------------------------------------------------
    # 3-D structure / docking / MD
    # -----------------------------------------------------------------------
    "pdb":                          ["structure_data"],
    "pdb-database":                 ["structure_data"],
    "alphafold-database":           ["structure_data"],
    "diffdock":                     ["structure_data"],
    "openmm":                       ["simulation_data", "structure_data"],
    "rowan":                        ["simulation_data", "compound_data", "structure_data"],
    "qmmm_adaptive":                ["simulation_data"],
    # legacy name
    "alphafold":                    ["structure_data"],

    # -----------------------------------------------------------------------
    # Chemistry / compounds
    # -----------------------------------------------------------------------
    "pubchem":                      ["compound_data"],
    "pubchem-database":             ["compound_data"],
    "chembl":                       ["compound_data"],
    "chembl-database":              ["compound_data"],
    "cas":                          ["compound_data"],
    "nistwebbook":                  ["compound_data"],
    "zinc-database":                ["compound_data"],
    "drugbank-database":            ["drug_data", "compound_data"],
    "hmdb-database":                ["metabolomics_data"],
    "metabolomics-workbench-database": ["metabolomics_data"],
    "matchms":                      ["metabolomics_data", "spectral_data"],
    "pyopenms":                     ["spectral_data", "metabolomics_data"],
    # legacy names
    "nist-webbook":                 ["compound_data"],

    # -----------------------------------------------------------------------
    # Cheminformatics / molecular properties
    # -----------------------------------------------------------------------
    "askcos":                       ["retrosynthesis"],
    "rdkit":                        ["rdkit_properties", "polymer_properties"],
    "datamol":                      ["rdkit_properties", "compound_data", "polymer_properties"],
    "medchem":                      ["rdkit_properties", "compound_data"],
    "molfeat":                      ["rdkit_properties", "ml_prediction"],
    # legacy name
    "openbabel":                    ["rdkit_properties"],

    # -----------------------------------------------------------------------
    # ADMET / drug properties
    # -----------------------------------------------------------------------
    "tdc":                          ["admet_prediction"],
    "pytdc":                        ["admet_prediction"],
    "deepchem":                     ["admet_prediction", "ml_prediction"],
    "torchdrug":                    ["ml_prediction", "admet_prediction"],
    # legacy name
    "admet-ai":                     ["admet_prediction"],

    # -----------------------------------------------------------------------
    # Pathways / systems biology / metabolic modeling
    # -----------------------------------------------------------------------
    "kegg-database":                ["pathway_data"],
    "reactome-database":            ["pathway_data"],
    "cobrapy":                      ["simulation_data", "pathway_data"],
    "opentargets-database":         ["target_data", "genomic_data"],
    # legacy names
    "go-database":                  ["pathway_data"],

    # -----------------------------------------------------------------------
    # Genomics / variants / epigenomics
    # -----------------------------------------------------------------------
    "ensembl-database":             ["genomic_data"],
    "clinvar-database":             ["genomic_data"],
    "gene-database":                ["genomic_data"],
    "gwas-database":                ["genomic_data"],
    "cosmic-database":              ["genomic_data"],
    "ena-database":                 ["genomic_data", "sequence_alignment"],
    "geo-database":                 ["expression_data", "genomic_data"],
    "deeptools":                    ["genomic_data", "expression_data"],
    "pysam":                        ["genomic_data"],
    "dnanexus-integration":         ["genomic_data"],
    "latchbio-integration":         ["genomic_data"],
    "geniml":                       ["genomic_data"],
    "gtars":                        ["genomic_data"],
    "etetoolkit":                   ["genomic_data"],
    "scikit-bio":                   ["genomic_data", "sequence_alignment"],
    # legacy names
    "ensembl":                      ["genomic_data"],
    "clinvar":                      ["genomic_data"],
    "gnomad":                       ["genomic_data"],
    "dbsnp":                        ["genomic_data"],

    # -----------------------------------------------------------------------
    # Gene expression / single-cell omics
    # -----------------------------------------------------------------------
    "scanpy":                       ["single_cell_data", "expression_data"],
    "scvi-tools":                   ["single_cell_data"],
    "anndata":                      ["single_cell_data"],
    "cellxgene-census":             ["single_cell_data", "expression_data"],
    "lamindb":                      ["single_cell_data"],
    "pydeseq2":                     ["expression_data"],
    "arboreto":                     ["network_data", "expression_data"],

    # -----------------------------------------------------------------------
    # Imaging / pathology / cytometry
    # -----------------------------------------------------------------------
    "pathml":                       ["imaging_data"],
    "histolab":                     ["imaging_data"],
    "pydicom":                      ["imaging_data"],
    "omero-integration":            ["imaging_data"],
    "flowio":                       ["imaging_data"],
    "imaging-data-commons":         ["imaging_data"],

    # -----------------------------------------------------------------------
    # Materials science / quantum chemistry
    # -----------------------------------------------------------------------
    "materials":                    ["materials_data"],
    "pymatgen":                     ["materials_data"],
    "ase":                          ["materials_data", "simulation_data", "polymer_properties"],
    "mopac":                        ["simulation_data", "materials_data"],
    # legacy names
    "materials-project":            ["materials_data"],
    "aflow":                        ["materials_data"],

    # -----------------------------------------------------------------------
    # Quantum computing
    # -----------------------------------------------------------------------
    "qiskit":                       ["quantum_computation"],
    "cirq":                         ["quantum_computation"],
    "pennylane":                    ["quantum_computation"],
    "qutip":                        ["quantum_computation"],

    # -----------------------------------------------------------------------
    # Machine learning / statistics / optimisation
    # -----------------------------------------------------------------------
    "scikit-learn":                 ["ml_prediction"],
    "pytorch-lightning":            ["ml_prediction"],
    "torch_geometric":              ["ml_prediction", "network_data"],
    "transformers":                 ["nlp_output", "ml_prediction"],
    "stable-baselines3":            ["ml_prediction"],
    "pufferlib":                    ["ml_prediction"],
    "shap":                         ["ml_prediction"],
    "umap-learn":                   ["ml_prediction", "figure"],
    "pymc":                         ["ml_prediction"],
    "pymoo":                        ["ml_prediction"],
    "aeon":                         ["ml_prediction", "time_series_data"],
    "statistical-analysis":         ["ml_prediction"],
    "statsmodels":                  ["ml_prediction"],
    "hypogenic":                    ["ml_prediction", "report"],

    # -----------------------------------------------------------------------
    # Simulation / dynamics / CFD
    # -----------------------------------------------------------------------
    # Note: openmm entry is already defined above under "3-D structure / docking / MD"
    "fluidsim":                     ["simulation_data"],
    "simpy":                        ["simulation_data"],
    "matlab":                       ["simulation_data", "ml_prediction"],
    "sympy":                        ["simulation_data"],

    # -----------------------------------------------------------------------
    # Network / graph analysis
    # -----------------------------------------------------------------------
    "networkx":                     ["network_data"],

    # -----------------------------------------------------------------------
    # Biosignal / time series / physiology
    # -----------------------------------------------------------------------
    "neurokit2":                    ["time_series_data"],
    "neuropixels-analysis":         ["time_series_data"],

    # -----------------------------------------------------------------------
    # Clinical / health data
    # -----------------------------------------------------------------------
    "clinicaltrials-database":      ["clinical_data"],
    "clinpgx-database":             ["pharmacogenomics_data", "clinical_data"],
    "fda-database":                 ["drug_data", "clinical_data"],
    "pyhealth":                     ["clinical_data", "ml_prediction"],
    "scikit-survival":              ["ml_prediction", "clinical_data"],
    "clinical-decision-support":    ["report", "clinical_data"],
    "clinical-reports":             ["report", "clinical_data"],
    "treatment-plans":              ["report", "clinical_data"],

    # -----------------------------------------------------------------------
    # Data I/O / document parsing
    # -----------------------------------------------------------------------
    "pdf":                          ["document_content"],
    "docx":                         ["document_content"],
    "xlsx":                         ["document_content"],
    "markitdown":                   ["document_content"],
    "exploratory-data-analysis":    ["report"],

    # -----------------------------------------------------------------------
    # Visualisation / figures
    # -----------------------------------------------------------------------
    "datavis":                      ["figure"],
    "matplotlib":                   ["figure"],
    "seaborn":                      ["figure"],
    "plotly":                       ["figure"],
    "scientific-visualization":     ["figure"],
    "scientific-schematics":        ["figure"],
    "generate-image":               ["figure"],
    "infographics":                 ["figure"],
    "diagramming":                  ["figure"],
    # legacy name
    "pymol":                        ["figure"],

    # -----------------------------------------------------------------------
    # Report / document generation
    # -----------------------------------------------------------------------
    "scientific-writing":           ["report"],
    "scientific-slides":            ["report"],
    "latex-posters":                ["report"],
    "pptx-posters":                 ["report"],
    "venue-templates":              ["report"],
    "market-research-reports":      ["report"],
    "research-grants":              ["report"],
    "paper-2-web":                  ["report"],
    "iso-13485-certification":      ["report"],
    "data-storytelling":            ["report"],
    "denario":                      ["report", "pubmed_results"],

    # -----------------------------------------------------------------------
    # Peer review / critical thinking / evaluation
    # -----------------------------------------------------------------------
    "peer-review":                  ["peer_validation", "report"],
    "scientific-critical-thinking": ["peer_validation"],
    "scholar-evaluation":           ["peer_validation", "report"],

    # -----------------------------------------------------------------------
    # Hypothesis / brainstorming / reasoning
    # -----------------------------------------------------------------------
    "hypothesis-generation":        ["synthesis"],
    "scientific-brainstorming":     ["synthesis"],
    "prompt-engineering-patterns":  ["synthesis"],

    # -----------------------------------------------------------------------
    # Web / search
    # -----------------------------------------------------------------------
    "websearch":                    ["web_content"],
    "browser-automation":           ["web_content"],
    "firecrawl-scraper":            ["web_content"],

    # -----------------------------------------------------------------------
    # Economic / geospatial / astronomical
    # -----------------------------------------------------------------------
    "fred-economic-data":           ["economic_data"],
    "datacommons-client":           ["economic_data"],
    "geopandas":                    ["geospatial_data"],
    "astropy":                      ["astronomical_data"],

    # -----------------------------------------------------------------------
    # Patent / IP
    # -----------------------------------------------------------------------
    "uspto-database":               ["patent_data"],

    # -----------------------------------------------------------------------
    # Lab integration / automation / ELN
    # -----------------------------------------------------------------------
    "opentrons-integration":        ["lab_integration"],
    "pylabrobot":                   ["lab_integration"],
    "benchling-integration":        ["lab_integration"],
    "labarchive-integration":       ["lab_integration"],
    "protocolsio-integration":      ["lab_integration"],

    # -----------------------------------------------------------------------
    # Platform / infrastructure / utilities (no domain restriction)
    # -----------------------------------------------------------------------
    "infinite":                     ["raw_output"],
    "modal":                        ["raw_output"],
    "dask":                         ["raw_output"],
    "polars":                       ["raw_output"],
    "vaex":                         ["raw_output"],
    "zarr-python":                  ["raw_output"],
    "get-available-resources":      ["raw_output"],
    "tooluniverse":                 ["raw_output"],

    # -----------------------------------------------------------------------
    # ToolUniverse research workflows (70+ skills)
    # -----------------------------------------------------------------------
    # Drug discovery / pharmacology
    "adverse-event-detection":              ["clinical_data", "drug_data"],
    "binder-discovery":                     ["compound_data", "structure_data"],
    "drug-drug-interaction":                ["drug_data", "clinical_data"],
    "drug-repurposing":                     ["drug_data", "compound_data", "target_data"],
    "drug-research":                        ["drug_data", "compound_data", "report"],
    "drug-target-validation":              ["target_data", "protein_data", "report"],
    "network-pharmacology":                 ["network_data", "drug_data", "compound_data"],
    "pharmacovigilance":                    ["drug_data", "clinical_data"],
    "chemical-compound-retrieval":          ["compound_data"],
    "chemical-safety":                      ["admet_prediction", "compound_data"],

    # Proteins / antibodies / structure
    "antibody-engineering":                 ["protein_data", "structure_data"],
    "protein-interactions":                 ["network_data", "protein_data"],
    "protein-structure-retrieval":          ["structure_data", "protein_data"],
    "protein-therapeutic-design":           ["protein_data", "structure_data"],
    "sequence-retrieval":                   ["sequence_alignment", "genomic_data"],
    "phylogenetics":                        ["sequence_alignment", "genomic_data"],

    # Genomics / variants
    "cancer-variant-interpretation":        ["genomic_data", "clinical_data"],
    "crispr-screen-analysis":               ["genomic_data", "expression_data"],
    "gwas-drug-discovery":                  ["genomic_data", "target_data"],
    "gwas-finemapping":                     ["genomic_data"],
    "gwas-snp-interpretation":              ["genomic_data"],
    "gwas-study-explorer":                  ["genomic_data"],
    "gwas-trait-to-gene":                   ["genomic_data", "target_data"],
    "polygenic-risk-score":                 ["genomic_data", "ml_prediction"],
    "structural-variant-analysis":          ["genomic_data"],
    "variant-analysis":                     ["genomic_data"],
    "variant-interpretation":               ["genomic_data", "clinical_data"],

    # Omics / transcriptomics
    "epigenomics":                          ["genomic_data", "expression_data"],
    "expression-data-retrieval":            ["expression_data"],
    "gene-enrichment":                      ["pathway_data", "expression_data"],
    "metabolomics":                         ["metabolomics_data"],
    "metabolomics-analysis":                ["metabolomics_data"],
    "multi-omics-integration":              ["expression_data", "genomic_data", "metabolomics_data"],
    "multiomic-disease-characterization":   ["expression_data", "genomic_data", "report"],
    "proteomics-analysis":                  ["protein_data", "expression_data"],
    "rnaseq-deseq2":                        ["expression_data"],
    "single-cell":                          ["single_cell_data", "expression_data"],
    "spatial-omics-analysis":              ["single_cell_data", "imaging_data"],
    "spatial-transcriptomics":              ["single_cell_data", "expression_data"],

    # Disease / clinical / precision medicine
    "clinical-guidelines":                  ["clinical_data", "report"],
    "clinical-trial-design":                ["clinical_data", "report"],
    "clinical-trial-matching":              ["clinical_data"],
    "disease-research":                     ["report", "clinical_data", "genomic_data"],
    "immunotherapy-response-prediction":    ["ml_prediction", "clinical_data"],
    "infectious-disease":                   ["genomic_data", "drug_data", "report"],
    "precision-medicine-stratification":    ["clinical_data", "genomic_data"],
    "precision-oncology":                   ["clinical_data", "genomic_data", "report"],
    "rare-disease-diagnosis":               ["clinical_data", "genomic_data"],

    # Systems biology / immune
    "immune-repertoire-analysis":           ["genomic_data", "protein_data"],
    "systems-biology":                      ["pathway_data", "network_data"],
    "target-research":                      ["target_data", "protein_data", "report"],

    # Literature / imaging / statistics
    "image-analysis":                       ["imaging_data"],
    "literature-deep-research":             ["pubmed_results", "report"],
    "statistical-modeling":                 ["ml_prediction"],
    "offer-k-dense-web":            ["raw_output"],
    "document-skills":              ["raw_output"],

    # -----------------------------------------------------------------------
    # Synthesis / validation / mutation policy (internal cross-cutting types)
    # -----------------------------------------------------------------------
    "_synthesis":                   ["synthesis"],
    "_validation":                  ["peer_validation"],
    "candidate_evaluator":          ["candidate_evaluation"],
    "candidate_ranker":             ["candidate_ranking"],
    "_mutation_policy":             ["mutation_policy"],
}


class ArtifactDomainError(Exception):
    """Raised when an agent tries to claim an artifact outside its skill domain."""


@dataclass
class Artifact:
    """
    Versioned, addressable wrapper around a single skill invocation's output.

    Fields are immutable after creation. The content_hash ensures integrity.
    """
    artifact_id: str
    artifact_type: str       # from SKILL_DOMAIN_MAP values
    producer_agent: str      # agent name from config
    skill_used: str          # e.g. "pubmed", "tdc", "blast"
    schema_version: str      # bump when Artifact fields change
    payload: dict            # unchanged skill JSON output
    investigation_id: str    # links to InvestigationTracker entry (or topic slug)
    timestamp: str           # ISO 8601 UTC
    content_hash: str        # sha256(canonical JSON of payload)
    parent_artifact_ids: List[str] = field(default_factory=list)  # DAG lineage
    result_quality: str = "ok"  # "ok" | "empty" | "irrelevant"
    needs: List[dict] = field(default_factory=list)  # LLM-generated need signals

    @staticmethod
    def _hash_payload(payload: dict) -> str:
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @classmethod
    def create(
        cls,
        artifact_type: str,
        producer_agent: str,
        skill_used: str,
        payload: dict,
        investigation_id: str = "",
        parent_artifact_ids: Optional[List[str]] = None,
        result_quality: str = "ok",
        needs: Optional[List[dict]] = None,
    ) -> "Artifact":
        """Factory: generates id, timestamp, and hash automatically."""
        return cls(
            artifact_id=str(uuid4()),
            artifact_type=artifact_type,
            producer_agent=producer_agent,
            skill_used=skill_used,
            schema_version="1.0",
            payload=payload,
            investigation_id=investigation_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            content_hash=cls._hash_payload(payload),
            parent_artifact_ids=parent_artifact_ids or [],
            result_quality=result_quality,
            needs=needs or [],
        )

    def address(self) -> str:
        """Return the canonical address for this artifact."""
        return f"artifact://{self.producer_agent}/{self.artifact_id}"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Artifact":
        d = dict(d)
        d.setdefault("parent_artifact_ids", [])
        d.setdefault("result_quality", "ok")
        d.setdefault("needs", [])
        return cls(**d)


class ArtifactStore:
    """
    Append-only JSONL store for artifacts.

    Storage: ~/.scienceclaw/artifacts/{agent_name}/store.jsonl
    One JSON object per line (same pattern as AgentJournal).
    """

    SCHEMA_VERSION = "1.0"

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        base = Path(os.path.expanduser("~/.scienceclaw"))
        self.store_path = base / "artifacts" / agent_name / "store.jsonl"
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self._global_index_path = base / "artifacts" / "global_index.jsonl"

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def save(self, artifact: Artifact) -> str:
        """Append artifact to per-agent store and global index. Returns artifact_id."""
        line = json.dumps(artifact.to_dict(), ensure_ascii=False) + "\n"
        with open(self.store_path, "a", encoding="utf-8") as fh:
            fh.write(line)
        self._append_global_index(artifact)
        return artifact.artifact_id

    def _append_global_index(self, artifact: Artifact) -> None:
        """
        Append a minimal index entry to the global cross-agent index.

        Only the fields needed for discovery are stored — not the full payload —
        keeping the index fast to scan even with thousands of artifacts.
        """
        entry = {
            "artifact_id":        artifact.artifact_id,
            "artifact_type":      artifact.artifact_type,
            "producer_agent":     artifact.producer_agent,
            "skill_used":         artifact.skill_used,
            "investigation_id":   artifact.investigation_id,
            "timestamp":          artifact.timestamp,
            "content_hash":       artifact.content_hash,
            "parent_artifact_ids": artifact.parent_artifact_ids,
            "needs":              artifact.needs,
        }
        with open(self._global_index_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def create_and_save(
        self,
        skill_used: str,
        payload: dict,
        investigation_id: str = "",
        parent_artifact_ids: Optional[List[str]] = None,
        result_quality: str = "ok",
        needs: Optional[List[dict]] = None,
    ) -> Artifact:
        """
        Convenience: build Artifact from skill name + payload, save, return it.

        Looks up artifact_type from SKILL_DOMAIN_MAP; falls back to "raw_output".
        result_quality: "ok" | "empty" | "irrelevant" — tagged for downstream filtering.
        needs: LLM-generated need signals broadcast to peer agents.
        """
        artifact_type = SKILL_DOMAIN_MAP.get(skill_used, ["raw_output"])[0]
        artifact = Artifact.create(
            artifact_type=artifact_type,
            producer_agent=self.agent_name,
            skill_used=skill_used,
            payload=payload,
            investigation_id=investigation_id,
            parent_artifact_ids=parent_artifact_ids or [],
            result_quality=result_quality,
            needs=needs or [],
        )
        self.save(artifact)
        return artifact

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def _iter_lines(self):
        if not self.store_path.exists():
            return
        with open(self.store_path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        pass

    def get(self, artifact_id: str) -> Optional[Artifact]:
        """Retrieve artifact by ID (linear scan — store is typically small)."""
        for record in self._iter_lines():
            if record.get("artifact_id") == artifact_id:
                return Artifact.from_dict(record)
        return None

    def list(
        self,
        artifact_type: Optional[str] = None,
        skill_used: Optional[str] = None,
        investigation_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Artifact]:
        """Return artifacts matching all provided filters (AND semantics)."""
        results = []
        for record in self._iter_lines():
            if artifact_type and record.get("artifact_type") != artifact_type:
                continue
            if skill_used and record.get("skill_used") != skill_used:
                continue
            if investigation_id and record.get("investigation_id") != investigation_id:
                continue
            results.append(Artifact.from_dict(record))
            if len(results) >= limit:
                break
        return results

    def get_depth(self, artifact_id: str, _memo: Optional[Dict[str, int]] = None) -> int:
        """
        Compute DAG depth of artifact_id by traversing parent_artifact_ids
        in the global index (payload-free, fast).

        Depth 0 = root artifact (no parents).
        Depth N = max(depth(parents)) + 1.

        Uses memoization to avoid redundant traversal.
        """
        if _memo is None:
            _memo = {}
        if artifact_id in _memo:
            return _memo[artifact_id]

        parent_ids = self._get_parent_ids_from_index(artifact_id)
        if not parent_ids:
            _memo[artifact_id] = 0
            return 0

        depth = max(self.get_depth(p, _memo) for p in parent_ids) + 1
        _memo[artifact_id] = depth
        return depth

    def _get_parent_ids_from_index(self, artifact_id: str) -> List[str]:
        """Scan global_index.jsonl for artifact_id and return its parent_artifact_ids."""
        if not self._global_index_path.exists():
            return []
        try:
            for line in self._global_index_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if entry.get("artifact_id") == artifact_id:
                    return entry.get("parent_artifact_ids", [])
        except OSError:
            pass
        return []

    # ------------------------------------------------------------------
    # Domain gating helpers
    # ------------------------------------------------------------------

    @staticmethod
    def allowed_artifact_types_for_agent(agent_profile: dict) -> List[str]:
        """
        Derive the set of artifact types this agent is allowed to produce/claim,
        based on preferred_tools in agent_profile.json.

        An agent with no preferred_tools gets all artifact types (no restriction).
        """
        preferred = agent_profile.get("preferred_tools", [])
        if not preferred:
            # No restriction — all types allowed
            return list({t for types in SKILL_DOMAIN_MAP.values() for t in types})
        allowed = set()
        for tool in preferred:
            for t in SKILL_DOMAIN_MAP.get(tool, []):
                allowed.add(t)
        # Always permit synthesis, validation, and mutation_policy regardless of profile
        allowed.update(["synthesis", "peer_validation", "raw_output", "mutation_policy"])
        return list(allowed)

    def assert_agent_can_claim(
        self,
        artifact_id: str,
        agent_profile: dict,
    ) -> Artifact:
        """
        Load artifact and verify the agent's domain covers it.

        Returns the Artifact on success, raises ArtifactDomainError otherwise.
        """
        artifact = self.get(artifact_id)
        if artifact is None:
            raise ArtifactDomainError(f"Artifact {artifact_id} not found in store")
        allowed = self.allowed_artifact_types_for_agent(agent_profile)
        if artifact.artifact_type not in allowed:
            raise ArtifactDomainError(
                f"Agent '{self.agent_name}' (tools: "
                f"{agent_profile.get('preferred_tools', [])}) cannot claim "
                f"artifact type '{artifact.artifact_type}' "
                f"(artifact {artifact_id})"
            )
        return artifact


# ---------------------------------------------------------------------------
# Registration artifact helpers
# ---------------------------------------------------------------------------

def _get_system_version() -> str:
    """Read system version from version.py, falling back to '1.0'."""
    try:
        version_path = Path(__file__).parent.parent / "version.py"
        if version_path.exists():
            text = version_path.read_text(encoding="utf-8")
            for line in text.splitlines():
                if "__version__" in line:
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        return parts[1].strip().strip('"\'')
    except Exception:
        pass
    return "1.0"


def emit_registration_artifact(agent_name: str, agent_profile: dict) -> "Artifact":
    """Emit a registration_metadata artifact when an agent profile is created."""
    store = ArtifactStore(agent_name)
    payload = {
        "agent_name": agent_name,
        "preferred_tools": agent_profile.get(
            "preferred_tools",
            agent_profile.get("preferences", {}).get("tools", []),
        ),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "system_version": _get_system_version(),
    }
    artifact = Artifact.create(
        artifact_type="registration_metadata",
        producer_agent=agent_name,
        skill_used="system_registration",
        payload=payload,
        investigation_id="",
        parent_artifact_ids=[],
    )
    store.save(artifact)
    return artifact
