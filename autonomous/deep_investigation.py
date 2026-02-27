#!/usr/bin/env python3
"""
Deep Scientific Investigation System

Agents self-assemble their investigation using LLM-powered skill selection.
The LLM picks from the full skill catalog, executes what it chooses, and
synthesizes findings — no hardcoded tool chains, no fallbacks.
"""

import json
import os
import sys
import re
import time
import subprocess
from pathlib import Path
from typing import Dict, Optional, List, Any
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from memory.journal import AgentJournal
    from memory.investigation_tracker import InvestigationTracker
    from memory.knowledge_graph import KnowledgeGraph
except ImportError:
    AgentJournal = None
    InvestigationTracker = None
    KnowledgeGraph = None

try:
    from autonomous.llm_reasoner import LLMScientificReasoner
except ImportError:
    LLMScientificReasoner = None

try:
    from artifacts.artifact import ArtifactStore
except ImportError:
    ArtifactStore = None

from core.skill_registry import get_registry
from core.skill_selector import get_selector
from core.skill_executor import get_executor
from core.topic_analyzer import get_analyzer


class DeepInvestigator:
    def __init__(self, agent_name: str, agent_profile: Optional[Dict] = None):
        self.agent_name = agent_name
        self.agent_profile = agent_profile
        self.scienceclaw_dir = Path(__file__).parent.parent

        self.journal = AgentJournal(agent_name) if AgentJournal else None
        self.tracker = InvestigationTracker(agent_name) if InvestigationTracker else None
        self.knowledge = KnowledgeGraph(agent_name) if KnowledgeGraph else None

        self.llm_reasoner = LLMScientificReasoner(agent_name) if LLMScientificReasoner else None

        self.skill_registry = get_registry()
        self.skill_selector = get_selector(agent_name) if get_selector else None
        self.skill_executor = get_executor() if get_executor else None
        self.topic_analyzer = get_analyzer(agent_name) if get_analyzer else None
        self.artifact_store = ArtifactStore(agent_name) if ArtifactStore else None
        self._current_investigation_id = ""  # set per run_tool_chain call
        print(f"  ✨ Skill catalog: {len(self.skill_registry.skills)} skills available")

    def check_previous_work(self, topic: str) -> Dict:
        if not self.journal:
            return {"investigated": False}
        investigated_topics = self.journal.get_investigated_topics()
        if topic.lower() in [t.lower() for t in investigated_topics]:
            return {
                "investigated": True,
                "message": f"Agent has previously explored {topic}. Building on past work."
            }
        return {"investigated": False}

    # ------------------------------------------------------------------
    # Result validation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_empty_bucket(candidate_items: list) -> bool:
        return len(candidate_items) == 0

    @staticmethod
    def _is_irrelevant(query: str, items: list) -> bool:
        """Returns True if no item contains any token from the query string."""
        tokens = {t.lower() for t in query.split() if len(t) > 3}
        if not tokens:
            return False
        for item in items:
            text = " ".join(str(v) for v in item.values()).lower()
            if any(tok in text for tok in tokens):
                return False
        return True

    @staticmethod
    def _compound_has_properties(item: dict) -> bool:
        """Returns False if all numeric drug properties are missing."""
        props = item.get('molecule_properties') or {}
        mw = props.get('full_mwt') or item.get('mw')
        return bool(mw and str(mw) not in ('?', '', 'None', 'N/A'))

    def _retry_skill(self, skill_name: str, actual_skill_name: str, skill_meta: dict,
                     original_query: str, timeout: int = 60) -> Optional[Dict]:
        """
        Retry a skill with a simplified, skill-type-aware query.
        Entity skills (uniprot, pdb, blast) get the shortest plausible entity token.
        Discovery skills (pubmed, arxiv) get the first meaningful phrase.
        Returns the raw skill result dict on success, or None.
        """
        _skill_base = actual_skill_name.replace('-database', '')
        _ENTITY_SKILLS = {'uniprot', 'pdb', 'chembl', 'pubchem', 'blast',
                          'string', 'kegg', 'reactome'}

        if _skill_base in _ENTITY_SKILLS:
            # Entity skills need a short, precise name — extract the first short token
            # that looks like a gene/protein/compound name (≤10 chars, starts uppercase).
            tokens = [t.strip('.,;:()[]') for t in original_query.split()[:8]]
            simplified = next(
                (t for t in tokens if t and len(t) <= 10 and t[0].isupper()),
                tokens[0] if tokens else original_query,
            )
        else:
            # Discovery skills: strip context clauses, keep the core scientific phrase
            for sep in (' for ', ' in ', ' via ', ' of ', ' with '):
                if sep in original_query.lower():
                    simplified = original_query[:original_query.lower().index(sep)].strip()
                    break
            else:
                simplified = ' '.join(original_query.split()[:5])

        if simplified.lower() == original_query.lower() or not simplified:
            return None

        print(f"      ↩ Retry with simplified query: '{simplified}'", end="", flush=True)
        _QUERY_REMAP = {'uniprot': 'search', 'blast': 'query'}
        _skill_base = actual_skill_name.replace('-database', '')
        retry_params = {}
        if _skill_base in _QUERY_REMAP:
            retry_params[_QUERY_REMAP[_skill_base]] = simplified
        else:
            retry_params['query'] = simplified
        if _skill_base == 'uniprot':
            retry_params['format'] = 'json'
        try:
            result = self.skill_executor.execute_skill(
                skill_name=actual_skill_name,
                skill_metadata=skill_meta,
                parameters=retry_params,
                timeout=timeout,
            )
            if result.get('status') == 'success':
                print(f" ✓")
                return result.get('result', {})
            else:
                print(f" ✗ {result.get('error', 'failed')}")
        except Exception as e:
            print(f" ✗ {e}")
        return None

    def _resolve_smiles_for_topic(self, topic: str) -> Optional[str]:
        """
        Resolve canonical SMILES for a compound name from the topic string.
        Checks agent profile research.compounds first, then queries chembl/cas.
        Used only for SMILES-requiring skills (askcos etc) — not in loop controller.
        """
        # 1. Use pre-set SMILES from agent profile if available
        profile_compounds = (self.agent_profile or {}).get('research', {}).get('compounds', [])
        if profile_compounds:
            candidate = profile_compounds[0]
            if candidate and candidate.startswith(('C', 'c', 'O', 'N', '[', 'F', 'Cl', 'Br', 'I')):
                return candidate

        compound_name = ' '.join(topic.split()[:3])

        for skill_name in ('chembl', 'cas'):
            skill_meta = self.skill_registry.get_skill(skill_name)
            if not skill_meta:
                continue
            result = self.skill_executor.execute_skill(
                skill_name=skill_name,
                skill_metadata=skill_meta,
                parameters={'query': compound_name},
                timeout=20
            )
            if result.get('status') != 'success':
                continue
            data = result.get('result', {})
            entries = data if isinstance(data, list) else [data]
            for entry in entries:
                # Direct key (pubchem: canonical_smiles; cas: smiles)
                smiles = (entry.get('canonical_smiles') or entry.get('smiles')
                          or entry.get('canonicalSmiles'))
                # Nested key (chembl: molecule_structures.canonical_smiles)
                if not smiles and isinstance(entry.get('molecule_structures'), dict):
                    smiles = entry['molecule_structures'].get('canonical_smiles')
                if smiles and smiles.startswith(('C', 'c', 'O', 'N', '[', 'F', 'Cl', 'Br', 'I')):
                    return smiles
        return None

    def run_tool_chain(self, topic: str, pre_selected_skills: List[Dict[str, Any]],
                       skill_query_overrides: Optional[Dict[str, str]] = None) -> Dict:
        """
        Execute the LLM-selected skills and return raw results.
        No fallbacks. Skills self-assemble around the topic.
        """
        # Set investigation context for artifact tagging
        import re as _re
        self._current_investigation_id = _re.sub(r'[^a-z0-9_]', '_', topic.lower())[:40]

        results = {
            "topic": topic,
            "tools_used": [],
            "productive_tools": [],  # skills that returned non-empty, non-irrelevant results
            "papers": [],
            "proteins": [],
            "compounds": [],
            "raw": [],
        }

        from core.skill_selector import SkillSelection, SelectedSkill
        selected = [
            SelectedSkill(
                name=s['name'],
                reason=s.get('reason', ''),
                suggested_params=s.get('suggested_params', {}),
                category=s.get('category'),
                description=s.get('description')
            )
            for s in pre_selected_skills
        ]
        skill_selection = SkillSelection(topic=topic, selected_skills=selected)
        print(f"  🛠️  Executing {len(selected)} skills: {[s.name for s in selected]}")

        for i, skill in enumerate(skill_selection.selected_skills, 1):
            skill_name = skill.name
            actual_skill_name = skill_name
            print(f"  [{i}/{len(selected)}] {skill_name}...", end="", flush=True)

            try:
                skill_meta = self.skill_registry.get_skill(skill_name)

                # Try stripping -database suffix as an alias
                if not skill_meta and skill_name.endswith('-database'):
                    alt = skill_name[:-9]  # len('-database') == 9
                    skill_meta = self.skill_registry.get_skill(alt)
                    if skill_meta:
                        actual_skill_name = alt

                if not skill_meta:
                    print(f" ✗ not in registry")
                    continue

                params = dict(skill.suggested_params) if skill.suggested_params else {}

                _skill_base = actual_skill_name.replace('-database', '')
                _skill_category = skill_meta.get('category', '')

                # Skills that primarily discover broad evidence — use the full topic query.
                _DISCOVERY_SKILLS = {'pubmed', 'arxiv', 'semanticscholar'}
                # Skills that expect a focused entity name — derive from accumulated results.
                _ENTITY_SKILLS = {'uniprot', 'pdb', 'chembl', 'pubchem', 'blast',
                                  'string', 'kegg', 'reactome'}
                # Skills that use a non-standard query param name
                _QUERY_REMAP = {'uniprot': 'search', 'blast': 'query'}

                # Only override the query param when it is absent or was copied blindly
                # from the topic by the LLM skill selector.
                def _query_already_set() -> bool:
                    return any(k in params for k in ('query', 'search', 'term', 'keyword', 'topic'))

                if _skill_base in _ENTITY_SKILLS:
                    # Check thread-aware overrides first (highest quality signal).
                    _override = (skill_query_overrides or {}).get(_skill_base)
                    if _override:
                        _focused = _override
                    else:
                        # Strip context clauses after common separators.
                        import re as _re2
                        _parts = _re2.split(r'\s+(?:via|in|with|of|for|and)\s+',
                                            topic, maxsplit=1)
                        _candidate = _parts[0].strip()
                        # If no separator found, _candidate == full topic.
                        # Cap entity queries at 3 words — entity skills need short,
                        # precise names (e.g. "PCSK9", "LDLR"), not whole sentences.
                        if _candidate == topic:
                            _candidate = ' '.join(topic.split()[:3])
                        _focused = _candidate
                else:
                    # Broad discovery skills — use full topic so the LLM-selector's
                    # differentiated queries are built from the complete context.
                    _focused = topic

                if _skill_base in _QUERY_REMAP:
                    _correct_param = _QUERY_REMAP[_skill_base]
                    for _wrong in ('query', 'term', 'keyword', 'topic'):
                        if _wrong in params and _wrong != _correct_param:
                            params[_correct_param] = params.pop(_wrong)
                    if not any(k in params for k in (_correct_param, 'search')):
                        params[_correct_param] = _focused
                    else:
                        # Replace whatever the LLM selector suggested with our derived query
                        for _k in (_correct_param, 'search'):
                            if _k in params:
                                params[_k] = _focused
                else:
                    # Standard skills
                    if not _query_already_set():
                        params['query'] = _focused
                    elif _skill_base in _ENTITY_SKILLS:
                        # Entity skills: always use the derived focused entity name —
                        # the LLM selector tends to copy the full topic verbatim here.
                        for _k in ('query', 'search', 'term', 'keyword', 'topic'):
                            if _k in params:
                                params[_k] = _focused
                                break
                    # else: discovery skill with LLM-set query — preserve it.
                    # The LLM selector intentionally differentiates multiple pubmed/arxiv
                    # calls; overriding them all with the same topic string is what caused
                    # every pubmed call to execute the identical query.

                # Skills that require --smiles instead of a query string
                _SMILES_SKILLS = {'askcos'}

                if _skill_base in _SMILES_SKILLS:
                    if 'smiles' not in params:
                        resolved = self._resolve_smiles_for_topic(topic)
                        if resolved:
                            params = {'smiles': resolved}
                        else:
                            print(f" ✗ could not resolve SMILES for topic")
                            continue
                    # Strip query-style params that would confuse askcos
                    for _k in ('query', 'search', 'term', 'keyword', 'topic', 'name'):
                        params.pop(_k, None)
                    # Remap result-count params to askcos's --top flag
                    for _k in ('num_results', 'max_results', 'limit', 'n', 'count'):
                        if _k in params:
                            params.setdefault('top', params.pop(_k))
                        else:
                            params.pop(_k, None)

                # Force JSON output for skills that support it
                if _skill_base == 'uniprot' and 'format' not in params:
                    params['format'] = 'json'

                result = self.skill_executor.execute_skill(
                    skill_name=actual_skill_name,
                    skill_metadata=skill_meta,
                    parameters=params,
                    timeout=60
                )

                if result.get('status') == 'success':
                    results["tools_used"].append(actual_skill_name)
                    skill_result = result.get('result', {})

                    # Normalise wrapped output (skill_executor wraps unparseable text as {"output": ...})
                    if isinstance(skill_result, dict) and 'output' in skill_result:
                        output_text = skill_result['output']
                        parsed = None
                        # 1. Try JSON array
                        arr_match = re.search(r'(\[.*\])', output_text, re.DOTALL)
                        if arr_match:
                            try:
                                parsed = json.loads(arr_match.group(1))
                            except json.JSONDecodeError:
                                pass
                        # 2. Try splitting on "--- Result N ---" markers (ChEMBL, some others)
                        if parsed is None:
                            blocks = re.split(r'---\s*Result\s*\d+[^-]*---', output_text)
                            objs = []
                            for block in blocks[1:]:  # skip header before first marker
                                block = block.strip()
                                if block.startswith('{'):
                                    # JSON block (--format json mode)
                                    try:
                                        objs.append(json.loads(block))
                                    except json.JSONDecodeError:
                                        try:
                                            objs.append(json.loads(block.rsplit('\n---', 1)[0].strip()))
                                        except json.JSONDecodeError:
                                            pass
                                else:
                                    # Key-value summary block (default mode): parse "  Key:  Value" lines
                                    obj: Dict[str, Any] = {}
                                    for line in block.splitlines():
                                        if ':' in line:
                                            k, _, v = line.partition(':')
                                            k = k.strip().lower().replace(' ', '_')
                                            v = v.strip()
                                            if v and v != 'N/A' and v != 'None' and v != 'None g/mol':
                                                obj[k] = v
                                    if obj:
                                        objs.append(obj)
                            if objs:
                                parsed = objs if len(objs) > 1 else objs[0]
                        # 3. Try PDB/numbered structure format: "N. [ID] Title\n   Key: Value"
                        if parsed is None:
                            pdb_entries = re.findall(
                                r'\d+\.\s+\[(\w+)\]\s+(.+?)(?=\n\d+\.\s+\[|\Z)',
                                output_text, re.DOTALL
                            )
                            if pdb_entries:
                                objs = []
                                for pdb_id, rest in pdb_entries[:8]:
                                    lines = rest.strip().splitlines()
                                    title = lines[0].strip() if lines else ''
                                    entry: Dict[str, Any] = {'id': pdb_id, 'name': title, 'pdb_id': pdb_id}
                                    for line in lines[1:]:
                                        if ':' in line:
                                            k, _, v = line.partition(':')
                                            k = k.strip().lower().replace(' ', '_')
                                            v = v.strip()
                                            if v and v not in ('N/A', 'Unknown', ''):
                                                entry[k] = v
                                    objs.append(entry)
                                if objs:
                                    parsed = objs
                        # 4. Try single top-level JSON object
                        if parsed is None:
                            obj_match = re.search(r'(\{.*\})', output_text, re.DOTALL)
                            if obj_match:
                                try:
                                    parsed = json.loads(obj_match.group(1))
                                except json.JSONDecodeError:
                                    pass
                        if parsed is not None:
                            skill_result = parsed

                    # Bucket results — normalise across skill output schemas
                    category = skill_meta.get('category', '')
                    _quality = "ok"  # assumed until proven otherwise
                    _skill_base_v = actual_skill_name.replace('-database', '')
                    _is_entity_skill = _skill_base_v in ('uniprot', 'pdb', 'chembl', 'pubchem',
                                                          'blast', 'string', 'kegg', 'reactome')
                    _is_discovery_skill = _skill_base_v in ('pubmed', 'arxiv', 'semanticscholar')

                    if 'literature' in category or skill_name in ('pubmed', 'arxiv'):
                        papers = skill_result if isinstance(skill_result, list) else skill_result.get('papers', [])
                        candidate_papers = [p for p in papers[:5] if isinstance(p, dict)]

                        # Rule A: empty result
                        if self._is_empty_bucket(candidate_papers):
                            _quality = "empty"
                            print(f" ✗ empty result", end="")
                            # Retry with shorter query
                            _retry_result = self._retry_skill(
                                skill_name, actual_skill_name, skill_meta, _focused, timeout=60)
                            if _retry_result is not None:
                                retry_papers = _retry_result if isinstance(_retry_result, list) else _retry_result.get('papers', [])
                                candidate_papers = [p for p in retry_papers[:5] if isinstance(p, dict)]
                                if candidate_papers:
                                    _quality = "ok"
                                    skill_result = _retry_result

                        if _quality == "ok":
                            results["papers"].extend(candidate_papers)

                    elif 'protein' in category or skill_name in ('uniprot', 'blast', 'pdb'):
                        if isinstance(skill_result, list):
                            raw_proteins = skill_result
                        elif isinstance(skill_result, dict):
                            raw_proteins = (skill_result.get('proteins') or
                                            skill_result.get('structures') or
                                            skill_result.get('hits') or
                                            skill_result.get('results') or [])
                        else:
                            raw_proteins = []
                        raw_proteins = [p for p in raw_proteins[:5] if isinstance(p, dict)]

                        # Rule A: empty result
                        if self._is_empty_bucket(raw_proteins):
                            _quality = "empty"
                            print(f" ✗ empty result", end="")
                            _retry_result = self._retry_skill(
                                skill_name, actual_skill_name, skill_meta, _focused, timeout=60)
                            if _retry_result is not None:
                                if isinstance(_retry_result, list):
                                    raw_proteins = [p for p in _retry_result[:5] if isinstance(p, dict)]
                                elif isinstance(_retry_result, dict):
                                    raw_proteins = [p for p in (
                                        _retry_result.get('proteins') or
                                        _retry_result.get('structures') or
                                        _retry_result.get('hits') or
                                        _retry_result.get('results') or [])[:5]
                                        if isinstance(p, dict)]
                                if raw_proteins:
                                    _quality = "ok"
                                    skill_result = _retry_result

                        # Rule B: irrelevant results (entity skills only)
                        if _quality == "ok" and _is_entity_skill and raw_proteins:
                            if self._is_irrelevant(_focused, raw_proteins):
                                _quality = "irrelevant"
                                print(f" ✗ irrelevant result", end="")
                                # Retry with simplified query
                                _retry_result = self._retry_skill(
                                    skill_name, actual_skill_name, skill_meta, _focused, timeout=60)
                                if _retry_result is not None:
                                    if isinstance(_retry_result, list):
                                        retry_proteins = [p for p in _retry_result[:5] if isinstance(p, dict)]
                                    elif isinstance(_retry_result, dict):
                                        retry_proteins = [p for p in (
                                            _retry_result.get('proteins') or
                                            _retry_result.get('structures') or
                                            _retry_result.get('hits') or
                                            _retry_result.get('results') or [])[:5]
                                            if isinstance(p, dict)]
                                    else:
                                        retry_proteins = []
                                    if retry_proteins and not self._is_irrelevant(_focused, retry_proteins):
                                        _quality = "ok"
                                        raw_proteins = retry_proteins
                                        skill_result = _retry_result

                        if _quality == "ok":
                            for p in raw_proteins:
                                # Normalise UniProt JSON format (primaryAccession, uniProtkbId, proteinDescription)
                                desc = p.get('proteinDescription') or {}
                                rec_name = desc.get('recommendedName') or {}
                                full_name = rec_name.get('fullName') or {}
                                uniprot_name = full_name.get('value') or p.get('uniProtkbId') or ''
                                # PDB: title field, pdb_id field
                                pdb_title = p.get('title', '')
                                pdb_id = p.get('pdb_id', '')
                                name = (p.get('name') or uniprot_name or pdb_title or
                                        p.get('id') or p.get('primaryAccession') or pdb_id or 'Unknown')
                                accession = (p.get('primaryAccession') or p.get('accession') or
                                             p.get('id') or pdb_id or '')
                                info = p.get('info') or p.get('annotation') or ''
                                if not info:
                                    if pdb_title:
                                        method = p.get('method', '')
                                        res = p.get('resolution', '')
                                        info = f"{method} {res}".strip() if method else ''
                                    else:
                                        org = p.get('organism') or {}
                                        if isinstance(org, dict):
                                            info = org.get('scientificName', '')
                                results["proteins"].append({
                                    "name": name,
                                    "id": accession,
                                    "info": info[:200],
                                    "source": actual_skill_name,
                                })

                    elif 'compound' in category or 'chem' in skill_name:
                        # ChEMBL returns a list of molecule dicts; flatten nested fields
                        raw_list = skill_result if isinstance(skill_result, list) else skill_result.get('compounds', [skill_result] if skill_result else [])
                        candidate_compounds = [item for item in raw_list[:5] if isinstance(item, dict)]

                        # Rule A: empty result
                        if self._is_empty_bucket(candidate_compounds):
                            _quality = "empty"
                            print(f" ✗ empty result", end="")
                            _retry_result = self._retry_skill(
                                skill_name, actual_skill_name, skill_meta, _focused, timeout=60)
                            if _retry_result is not None:
                                retry_list = _retry_result if isinstance(_retry_result, list) else _retry_result.get('compounds', [_retry_result])
                                candidate_compounds = [item for item in retry_list[:5] if isinstance(item, dict)]
                                if candidate_compounds:
                                    _quality = "ok"
                                    skill_result = _retry_result

                        # Rule B: irrelevant results (entity skills only)
                        if _quality == "ok" and _is_entity_skill and candidate_compounds:
                            if self._is_irrelevant(_focused, candidate_compounds):
                                _quality = "irrelevant"
                                print(f" ✗ irrelevant result", end="")
                                _retry_result = self._retry_skill(
                                    skill_name, actual_skill_name, skill_meta, _focused, timeout=60)
                                if _retry_result is not None:
                                    retry_list = _retry_result if isinstance(_retry_result, list) else _retry_result.get('compounds', [_retry_result])
                                    retry_compounds = [item for item in retry_list[:5] if isinstance(item, dict)]
                                    if retry_compounds and not self._is_irrelevant(_focused, retry_compounds):
                                        _quality = "ok"
                                        candidate_compounds = retry_compounds
                                        skill_result = _retry_result

                        if _quality == "ok":
                            for item in candidate_compounds:
                                # Rule C: skip compounds with no numeric properties
                                if not self._compound_has_properties(item):
                                    continue
                                mol_structs = item.get('molecule_structures') or {}
                                smiles = (mol_structs.get('canonical_smiles') or
                                          item.get('canonical_smiles') or
                                          item.get('smiles', ''))
                                name = (item.get('pref_name') or item.get('name') or
                                        item.get('molecule_chembl_id', 'Unknown'))
                                props = item.get('molecule_properties') or {}
                                results["compounds"].append({
                                    "name": name,
                                    "smiles": smiles,
                                    "mw": props.get('full_mwt', item.get('mw', '')),
                                    "chembl_id": item.get('molecule_chembl_id', ''),
                                    "max_phase": item.get('max_phase', ''),
                                    "source": actual_skill_name,
                                    **{k: v for k, v in item.items()
                                       if k not in ('molecule_structures', 'molecule_properties',
                                                    'molecule_synonyms', 'cross_references', 'molfile')},
                                })

                    elif 'pathway' in category or skill_name in ('kegg-database', 'string-database', 'reactome-database'):
                        # Pathway skills return dicts with lists of pathways/genes/proteins/drugs
                        data = skill_result if isinstance(skill_result, dict) else {}
                        # Pathway entries → treat as papers (literature-like pathway refs)
                        for pw in (data.get('pathways') or [])[:4]:
                            if isinstance(pw, dict):
                                results["papers"].append({
                                    "title": pw.get('name', pw.get('id', 'Pathway')),
                                    "pmid": pw.get('id', ''),
                                    "source": actual_skill_name,
                                    "abstract": pw.get('description', ''),
                                })
                        # Gene/protein entries → proteins
                        for gene in (data.get('genes') or data.get('proteins') or [])[:4]:
                            if isinstance(gene, dict):
                                results["proteins"].append({
                                    "name": gene.get('name') or gene.get('preferredName') or gene.get('id', 'Unknown'),
                                    "id": gene.get('id', ''),
                                    "info": gene.get('annotation') or gene.get('definition', ''),
                                    "source": actual_skill_name,
                                })
                        # Drug entries from KEGG → compounds
                        for drug in (data.get('drugs') or [])[:3]:
                            if isinstance(drug, dict):
                                results["compounds"].append({
                                    "name": drug.get('name', drug.get('id', 'Unknown')),
                                    "id": drug.get('id', ''),
                                    "source": actual_skill_name,
                                })
                        # STRING interaction entries → proteins
                        for interact in (data.get('interactions') or [])[:4]:
                            if isinstance(interact, dict):
                                for field in ('preferredName_A', 'preferredName_B'):
                                    pname = interact.get(field, '')
                                    if pname:
                                        results["proteins"].append({
                                            "name": pname,
                                            "source": "string-database",
                                            "info": f"String score: {interact.get('score', '')}",
                                        })

                    # Save artifact (always, for audit) with quality tag
                    if self.artifact_store and isinstance(skill_result, dict):
                        _artifact = self.artifact_store.create_and_save(
                            skill_used=actual_skill_name,
                            payload=skill_result,
                            investigation_id=self._current_investigation_id,
                            result_quality=_quality,
                        )
                        skill_result["_artifact_id"] = _artifact.artifact_id
                        # Collect IDs so post_generator can attach them to the Infinite post
                        results.setdefault("artifact_ids", []).append(_artifact.artifact_id)

                    results["raw"].append({"skill": actual_skill_name, "data": skill_result,
                                           "result_quality": _quality})
                    if _quality == "ok":
                        results["productive_tools"].append(actual_skill_name)
                        print(f" ✓")
                    else:
                        print(f" (saved as audit artifact, quality={_quality})")
                else:
                    print(f" ✗ {result.get('error', 'failed')}")

            except Exception as e:
                print(f" ✗ {e}")

        # LLM synthesises insights from whatever the skills returned
        results["insights"] = self._generate_insights(results)

        # LLM identifies what data the investigation still needs — broadcast to peers
        if self.llm_reasoner:
            try:
                results["needs"] = self.llm_reasoner.generate_needs(topic, results)
            except Exception as _needs_err:
                print(f"    Note: needs generation failed ({_needs_err})")
                results["needs"] = []
        else:
            results["needs"] = []

        return results

    def run_computational_validation(
        self,
        smiles_list: List[str],
        sequences: List[str],
        topic: str
    ) -> Dict[str, Any]:
        """
        Feature 1: Run computational skills on extracted entities to generate new data.

        Unlike the discovery phase (which reads databases), this phase *generates*
        new predictions by running ADMET models, molecular property calculations,
        and sequence homology searches on the discovered entities.

        Args:
            smiles_list: SMILES strings extracted from discovered compounds (max 5)
            sequences: Protein sequences extracted from discovered proteins (max 3)
            topic: Research topic for context

        Returns:
            Dict with keys: predictions, properties (keyed by compound/sequence)
        """
        computational = {"predictions": [], "properties": []}

        # Cap inputs to avoid timeouts
        smiles_list = [s for s in smiles_list if s and len(s) > 2][:5]
        sequences = [s for s in sequences if s and len(s) > 10][:3]

        if not smiles_list and not sequences:
            return computational

        print(f"  🧮 Computational validation: {len(smiles_list)} SMILES, {len(sequences)} sequences")

        # --- TDC ADMET predictions on SMILES ---
        tdc_skill = self.skill_registry.get_skill("tdc")
        if tdc_skill and smiles_list:
            for smiles in smiles_list:
                try:
                    result = self.skill_executor.execute_skill(
                        skill_name="tdc",
                        skill_metadata=tdc_skill,
                        parameters={"smiles": smiles, "model": "BBB_Martins-AttentiveFP"},
                        timeout=45
                    )
                    if result.get("status") == "success":
                        pred = result.get("result", {})
                        computational["predictions"].append({
                            "smiles": smiles,
                            "tool": "tdc",
                            "model": "BBB_Martins-AttentiveFP",
                            "result": pred
                        })
                        print(f"    ✓ TDC prediction for {smiles[:20]}...")
                except Exception as e:
                    print(f"    ✗ TDC failed for {smiles[:20]}: {e}")

        # --- RDKit molecular properties on SMILES ---
        # rdkit_tools.py uses positional "descriptors" command + --smiles flag,
        # so we call it directly via subprocess instead of through skill_executor.
        rdkit_script = self.scienceclaw_dir / "skills" / "rdkit" / "scripts" / "rdkit_tools.py"
        if rdkit_script.exists() and smiles_list:
            import subprocess as _sp
            for smiles in smiles_list[:3]:
                try:
                    proc = _sp.run(
                        ["python3", str(rdkit_script), "descriptors", "--smiles", smiles],
                        capture_output=True, text=True, timeout=30,
                        cwd=str(self.scienceclaw_dir)
                    )
                    if proc.returncode == 0 and proc.stdout.strip():
                        # Parse "key: value" lines into dict
                        props: Dict[str, Any] = {}
                        for line in proc.stdout.splitlines():
                            if ":" in line:
                                k, _, v = line.partition(":")
                                props[k.strip()] = v.strip()
                        if props:
                            computational["properties"].append({
                                "smiles": smiles,
                                "tool": "rdkit",
                                "result": props
                            })
                            print(f"    ✓ RDKit properties for {smiles[:20]}...")
                except Exception as e:
                    print(f"    ✗ RDKit failed for {smiles[:20]}: {e}")

        # --- BLAST homology for protein sequences ---
        blast_skill = self.skill_registry.get_skill("blast")
        if blast_skill and sequences:
            for seq in sequences[:2]:
                try:
                    result = self.skill_executor.execute_skill(
                        skill_name="blast",
                        skill_metadata=blast_skill,
                        parameters={"query": seq, "program": "blastp"},
                        timeout=60
                    )
                    if result.get("status") == "success":
                        blast_data = result.get("result", {})
                        computational["predictions"].append({
                            "sequence": seq[:20] + "...",
                            "tool": "blast",
                            "result": blast_data
                        })
                        print(f"    ✓ BLAST homology for sequence ({len(seq)} aa)")
                except Exception as e:
                    print(f"    ✗ BLAST failed: {e}")

        total = len(computational["predictions"]) + len(computational["properties"])
        print(f"  🧮 Computational validation complete: {total} results generated")
        return computational

    def _extract_smiles_and_sequences(self, results: Dict) -> tuple:
        """Extract SMILES strings and protein sequences from discovery results."""
        import re
        smiles_list = []
        sequences = []

        # All SMILES key variants (PubChem uses CanonicalSMILES/ConnectivitySMILES)
        _smiles_keys = (
            "smiles", "canonical_smiles", "isomeric_smiles", "SMILES",
            "CanonicalSMILES", "CanonicalSmiles", "ConnectivitySMILES",
            "IsomericSMILES", "canonicalSmiles",
        )

        def _looks_like_smiles(val: str) -> bool:
            """Basic heuristic: SMILES contain C/N/O and ring/bond chars."""
            return (len(val) > 3 and
                    any(c in val for c in "CNOScnos") and
                    not val.startswith("http"))

        # Extract SMILES from compounds
        for compound in results.get("compounds", []):
            for key in _smiles_keys:
                val = compound.get(key)
                if val and isinstance(val, str) and _looks_like_smiles(val):
                    smiles_list.append(val)
                    break

        # Extract sequences from proteins
        for protein in results.get("proteins", []):
            for key in ("sequence", "seq", "aa_sequence"):
                val = protein.get(key)
                if val and isinstance(val, str) and len(val) > 10:
                    sequences.append(val)
                    break

        # Scan raw results: dicts for SMILES keys, text output for embedded values
        for raw_item in results.get("raw", []):
            data = raw_item.get("data", {})
            if isinstance(data, dict):
                # Check standard SMILES keys in dict
                for key in _smiles_keys:
                    val = data.get(key)
                    if val and isinstance(val, str) and _looks_like_smiles(val) and val not in smiles_list:
                        smiles_list.append(val)
                # Scan text output field (pubchem prints mixed text+JSON)
                text_output = data.get("output", "")
                if isinstance(text_output, str):
                    for match in re.finditer(
                        r'(?:CanonicalSMILES|ConnectivitySMILES|SMILES|smiles)["\s:]+([^\s",\n]{4,})',
                        text_output
                    ):
                        candidate = match.group(1).strip().strip('"')
                        if _looks_like_smiles(candidate) and candidate not in smiles_list:
                            smiles_list.append(candidate)

        return list(dict.fromkeys(smiles_list))[:5], list(dict.fromkeys(sequences))[:3]

    def _generate_insights(self, results: Dict) -> List[str]:
        if self.llm_reasoner:
            try:
                return self.llm_reasoner.generate_insights(results.get("topic", ""), results)
            except Exception as e:
                print(f"    Note: LLM insight generation failed ({e})")
        return []

    def generate_figures(self, topic: str, investigation_results: Dict) -> List[str]:
        figures_dir = Path.home() / ".scienceclaw" / "figures"
        figures_dir.mkdir(parents=True, exist_ok=True)

        datavis_script = self.scienceclaw_dir / "skills" / "datavis" / "scripts" / "plot_data.py"
        if not datavis_script.exists():
            return []

        generated: List[str] = []
        topic_slug = re.sub(r"[^a-z0-9]+", "_", topic.lower())[:40]
        ts = int(time.time())
        papers = investigation_results.get("papers", [])
        proteins = investigation_results.get("proteins", [])
        compounds = investigation_results.get("compounds", [])

        if len(papers) >= 3:
            year_counts: Dict[str, int] = {}
            for p in papers:
                year = str(p.get("year", p.get("pub_year", p.get("pubdate", "Unknown"))))
                year = year[:4] if len(year) >= 4 else "Unknown"
                year_counts[year] = year_counts.get(year, 0) + 1
            known = {k: v for k, v in year_counts.items() if k != "Unknown" and k.isdigit()}
            if len(known) >= 2:
                sorted_years = sorted(known.keys())
                data_json = json.dumps([{"Year": y, "Papers": known[y]} for y in sorted_years])
                out_path = str(figures_dir / f"{topic_slug}_{ts}_papers.png")
                cmd = [sys.executable, str(datavis_script), "bar",
                       "--json", data_json, "--x", "Year", "--y", "Papers",
                       "--title", f"Publication Landscape: {topic[:50]}",
                       "--xlabel", "Year", "--ylabel", "Paper Count", "--output", out_path]
                try:
                    r = subprocess.run(cmd, capture_output=True, text=True,
                                       cwd=str(self.scienceclaw_dir), timeout=30)
                    if r.returncode == 0 and Path(out_path).exists():
                        generated.append(out_path)
                        print(f"  📊 Figure: publication landscape → {out_path}")
                except Exception:
                    pass

        if len(compounds) >= 3:
            data_rows = []
            for i, c in enumerate(compounds[:12]):
                mw = c.get("molecular_weight") or c.get("mw") or c.get("MW")
                if mw:
                    try:
                        data_rows.append({"Index": i + 1, "MW": float(mw)})
                    except (ValueError, TypeError):
                        pass
            if len(data_rows) >= 3:
                data_json = json.dumps(data_rows)
                out_path = str(figures_dir / f"{topic_slug}_{ts}_compounds.png")
                cmd = [sys.executable, str(datavis_script), "scatter",
                       "--json", data_json, "--x", "Index", "--y", "MW",
                       "--title", f"Compound MW Landscape: {topic[:45]}",
                       "--xlabel", "Compound Index", "--ylabel", "Molecular Weight (Da)",
                       "--output", out_path]
                try:
                    r = subprocess.run(cmd, capture_output=True, text=True,
                                       cwd=str(self.scienceclaw_dir), timeout=30)
                    if r.returncode == 0 and Path(out_path).exists():
                        generated.append(out_path)
                        print(f"  📊 Figure: compound landscape → {out_path}")
                except Exception:
                    pass

        return generated

    def generate_sophisticated_content(self, topic: str, investigation_results: Dict) -> Dict:
        papers = investigation_results.get("papers", [])
        insights = investigation_results.get("insights", [])
        tools_used = investigation_results.get("tools_used", [])
        productive_tools = investigation_results.get("productive_tools", []) or tools_used
        proteins = investigation_results.get("proteins", [])
        compounds = investigation_results.get("compounds", [])

        if proteins:
            title = f"{topic}: Molecular Mechanisms via {proteins[0].get('name', 'Key Proteins')}"
        elif compounds:
            title = f"{topic}: Chemical Basis and Therapeutic Implications"
        else:
            title = f"{topic}: A Multi-Tool Investigation"

        hyp_result = self.llm_reasoner.generate_hypothesis(topic, papers, proteins, compounds)
        hypothesis = f"**Scientific Question:** {hyp_result['question']}\n\n**Hypothesis:** {hyp_result['hypothesis']}"
        if insights:
            hypothesis += f"\n\n**Supporting Evidence:** {insights[0]}"

        method = f"**Investigative Approach:**\nThis investigation self-assembled using {len(productive_tools)} tools selected by LLM analysis:\n\n"
        for i, tool in enumerate(productive_tools, 1):
            method += f"{i}. **{tool}**\n"
        method += f"\n**Full skill catalog size:** {len(self.skill_registry.skills)} available skills"

        findings = "**Key Discoveries:**"
        if papers:
            findings += f"\n\n---\n\n**Literature** ({len(papers)} papers):\n"
            for paper in papers[:3]:
                t = paper.get('title', 'Unknown').lstrip('0123456789. ')
                findings += f"- {t} (PMID:{paper.get('pmid', 'N/A')})\n"
        if proteins:
            findings += f"\n---\n\n**Proteins** ({len(proteins)}):\n"
            for p in proteins[:4]:
                info = p.get('info') or p.get('annotation') or ''
                info_str = f" — {info[:100]}" if info else ''
                findings += f"- **{p.get('name', 'Unknown')}**{info_str}\n"
        if compounds:
            findings += f"\n---\n\n**Compounds** ({len(compounds)}):\n"
            for c in compounds[:4]:
                smiles = c.get('smiles', '')
                smiles_str = f" (`{smiles[:30]}`)" if smiles else ''
                chembl = c.get('chembl_id', '')
                chembl_str = f" [{chembl}]" if chembl else ''
                mw = c.get('mw', '')
                mw_str = f" MW={mw}" if mw else ''
                findings += f"- **{c.get('name', 'Unknown')}**{chembl_str}{smiles_str}{mw_str}\n"
        computational = investigation_results.get("computational", {})
        comp_predictions = computational.get("predictions", [])
        comp_properties = computational.get("properties", [])
        if comp_predictions or comp_properties:
            findings += f"\n---\n\n**Computational Results** ({len(comp_predictions)} predictions, {len(comp_properties)} property sets):\n"
            for pred in comp_predictions[:3]:
                tool = pred.get("tool", "unknown")
                smiles = pred.get("smiles", pred.get("sequence", ""))[:20]
                res = pred.get("result", {})
                findings += f"- [{tool}] {smiles}...: {str(res)[:100]}\n"
            for prop in comp_properties[:2]:
                smiles = prop.get("smiles", "")[:20]
                res = prop.get("result", {})
                findings += f"- [rdkit] {smiles}...: MW={res.get('molecular_weight', res.get('MW', 'N/A'))}\n"

        refinement_cycles = investigation_results.get("refinement_cycles", 0)
        approved = investigation_results.get("approved_by_reflector", False)
        if refinement_cycles > 0:
            findings += f"\n---\n\n**Investigation Rigor:** {refinement_cycles} refinement cycle(s) completed. Reflector {'approved ✅' if approved else 'review pending'}.\n"

        if insights:
            findings += f"\n---\n\n**Insights:**\n"
            for insight in insights:
                clean = insight.replace('INSIGHT:', '').replace('Insight:', '').strip()
                if clean:
                    findings += f"- {clean}\n"

        conclusion_text = self.llm_reasoner.generate_conclusion(
            topic=topic,
            hypothesis=hypothesis,
            insights=insights,
            has_proteins=len(proteins) > 0,
            has_compounds=len(compounds) > 0,
            paper_count=len(papers)
        )
        conclusion = f"\n\n**Conclusions & Implications:**\n\n{conclusion_text}"

        content = f"{hypothesis}\n\n{method}\n\n{findings}\n\n{conclusion}"

        print("  📈 Generating figures (basic)...")
        figure_paths = self.generate_figures(topic, investigation_results)

        # PlotAgent: LLM-driven, publication-quality figure suite (Sparks-style)
        try:
            from autonomous.plot_agent import run_plot_agent
            print("  🎨 Running PlotAgent for advanced figures...")
            advanced_paths = run_plot_agent(
                agent_name=self.agent_name,
                topic=topic,
                investigation_results=investigation_results,
            )
            # Merge; advanced figures take priority, basic ones fill the rest
            existing_names = {Path(p).name for p in advanced_paths}
            for bp in figure_paths:
                if Path(bp).name not in existing_names:
                    advanced_paths.append(bp)
            figure_paths = advanced_paths
        except Exception as e:
            print(f"    Note: PlotAgent unavailable ({e}), using basic figures")

        if figure_paths:
            content += "\n\n**Figures:**\n"
            for fp in figure_paths:
                content += f"- `{fp}`\n"

        result = {
            "title": title,
            "hypothesis": hypothesis.split('\n')[0].replace('**', '').replace('Scientific Question:', '').strip(),
            "method": f"LLM-assembled investigation using {', '.join(productive_tools)}",
            "findings": findings,
            "content": content,
            "figures": figure_paths,
        }

        if self.llm_reasoner:
            try:
                print("  🔍 Adversarial reflection (Feature 2)...")
                reflection = self.llm_reasoner.adversarial_reflection_loop(
                    topic=topic,
                    hypothesis=hypothesis,
                    insights=insights,
                    papers=papers
                )
                # Apply reflector-approved revisions
                if reflection.get("hypothesis") and len(reflection["hypothesis"]) > 50:
                    result["hypothesis"] = reflection["hypothesis"]
                # Store reflection metadata for callers
                result["reflection_cycles"] = reflection.get("cycles", 0)
                result["reflection_approved"] = reflection.get("approved", False)
            except Exception as e:
                print(f"    Note: Adversarial reflection unavailable ({e})")

        return result

    def _map_gap_to_skill(self, gap: str) -> Optional[str]:
        """Map a gap description to a skill name using keyword matching.

        Note: 'rdkit' is intentionally excluded — RDKit descriptors are already
        computed in run_computational_validation() on every cycle via direct subprocess.
        Gap-fill routing only returns skills compatible with the generic skill_executor
        (--query interface).
        """
        gap_lower = gap.lower()
        if any(k in gap_lower for k in ("homolog", "sequence", "blast", "evolutionary", "similarity")):
            return "blast"
        if any(k in gap_lower for k in ("protein", "uniprot", "function", "domain", "annotation")):
            return "uniprot"
        if any(k in gap_lower for k in ("compound", "chemical", "pubchem", "smiles", "structure")):
            return "pubchem"
        if any(k in gap_lower for k in ("literature", "paper", "pubmed", "publication", "study")):
            return "pubmed"
        if any(k in gap_lower for k in ("bioactivity", "ic50", "chembl", "assay", "ki", "inhibition")):
            return "chembl"
        if any(k in gap_lower for k in ("preprint", "arxiv", "recent", "machine learning")):
            return "arxiv"
        return None

    def run_refinement_loop(
        self,
        topic: str,
        initial_results: Dict,
        pre_selected_skills: List[Dict],
        max_refinement_cycles: int = 2
    ) -> Dict:
        """
        Feature 3: Iterative evidence-gap refinement loop.

        After the initial discovery + computational validation cycle:
        1. Run adversarial reflection to identify evidence gaps
        2. Map gaps to skills and run targeted follow-up queries
        3. Merge new data and re-generate insights
        4. Repeat until approved or max_cycles exhausted

        Args:
            topic: Research topic
            initial_results: Results from first run_tool_chain() + computational validation
            pre_selected_skills: Skills already used (to avoid re-running same skills)
            max_refinement_cycles: Maximum additional cycles beyond the initial pass

        Returns:
            Enriched results dict with refinement_cycles and approved_by_reflector fields
        """
        results = dict(initial_results)
        results.setdefault("computational", {"predictions": [], "properties": []})
        results["refinement_cycles"] = 0
        results["approved_by_reflector"] = False

        if not self.llm_reasoner:
            return results

        used_skills = set(results.get("tools_used", []))

        for cycle in range(1, max_refinement_cycles + 1):
            print(f"\n  🔁 Refinement cycle {cycle}/{max_refinement_cycles}")

            current_hypothesis = results.get("insights", [""])[0] if results.get("insights") else topic
            current_insights = results.get("insights", [])

            # Identify evidence gaps
            gaps = self.llm_reasoner.identify_evidence_gaps(
                hypothesis=current_hypothesis,
                insights=current_insights
            )

            if not gaps:
                print(f"    No evidence gaps identified — stopping refinement")
                results["approved_by_reflector"] = True
                break

            print(f"    Gaps identified: {gaps}")

            # Map gaps to skills
            skills_to_run = []
            for gap in gaps:
                skill_name = self._map_gap_to_skill(gap)
                if skill_name and skill_name not in used_skills:
                    skill_meta = self.skill_registry.get_skill(skill_name)
                    if skill_meta:
                        skills_to_run.append({"name": skill_name, "gap": gap, "meta": skill_meta})
                        used_skills.add(skill_name)

            if not skills_to_run:
                print(f"    No new skills can address identified gaps — stopping")
                results["approved_by_reflector"] = True
                break

            # Run targeted skills for gap-filling
            for skill_info in skills_to_run:
                skill_name = skill_info["name"]
                skill_meta = skill_info["meta"]
                gap_desc = skill_info["gap"]
                print(f"    🎯 Running {skill_name} to fill gap: {gap_desc[:60]}...")
                try:
                    # Ask LLM what to query given the gap description + accumulated evidence
                    _gf_query: Optional[str] = None
                    if self.llm_reasoner:
                        try:
                            _gf_query = self.llm_reasoner.derive_query_for_skill(
                                skill_name=skill_name,
                                skill_category=skill_meta.get('category', ''),
                                topic=f"{topic} — gap: {gap_desc}",
                                results_so_far=results,
                            )
                        except Exception:
                            pass
                    if not _gf_query:
                        _gf_query = topic  # fallback
                    _QUERY_PARAM_GF = {'uniprot': 'search', 'blast': 'query'}
                    _gf_qparam = _QUERY_PARAM_GF.get(skill_name, 'query')
                    _gf_params = {_gf_qparam: _gf_query}
                    if skill_name in ('uniprot', 'uniprot-database'):
                        _gf_params['format'] = 'json'
                    result = self.skill_executor.execute_skill(
                        skill_name=skill_name,
                        skill_metadata=skill_meta,
                        parameters=_gf_params,
                        timeout=60
                    )
                    if result.get("status") == "success":
                        results["tools_used"].append(skill_name)
                        skill_result = result.get("result", {})
                        # Apply same output normalizer as main tool chain
                        if isinstance(skill_result, dict) and 'output' in skill_result:
                            output_text = skill_result['output']
                            _parsed = None
                            _arr = re.search(r'(\[.*\])', output_text, re.DOTALL)
                            if _arr:
                                try: _parsed = json.loads(_arr.group(1))
                                except json.JSONDecodeError: pass
                            if _parsed is None:
                                _blocks = re.split(r'---\s*Result\s*\d+[^-]*---', output_text)
                                _objs = []
                                for _block in _blocks[1:]:
                                    _block = _block.strip()
                                    if _block.startswith('{'):
                                        try: _objs.append(json.loads(_block))
                                        except json.JSONDecodeError: pass
                                    else:
                                        _obj: Dict[str, Any] = {}
                                        for _line in _block.splitlines():
                                            if ':' in _line:
                                                _k, _, _v = _line.partition(':')
                                                _k = _k.strip().lower().replace(' ', '_')
                                                _v = _v.strip()
                                                if _v and _v not in ('N/A', 'None', 'None g/mol'):
                                                    _obj[_k] = _v
                                        if _obj:
                                            _objs.append(_obj)
                                if _objs:
                                    _parsed = _objs if len(_objs) > 1 else _objs[0]
                            if _parsed is None:
                                _obj_m = re.search(r'(\{.*\})', output_text, re.DOTALL)
                                if _obj_m:
                                    try: _parsed = json.loads(_obj_m.group(1))
                                    except json.JSONDecodeError: pass
                            if _parsed is not None:
                                skill_result = _parsed
                        results["raw"].append({"skill": skill_name, "data": skill_result, "gap_fill": True})

                        # Merge into appropriate bucket (reuse same logic as main tool chain)
                        category = skill_meta.get("category", "")
                        if "literature" in category or skill_name in ("pubmed", "arxiv"):
                            new_papers = skill_result if isinstance(skill_result, list) else skill_result.get("papers", [])
                            results["papers"].extend([p for p in new_papers[:3] if isinstance(p, dict)])
                        elif "protein" in category or skill_name in ("uniprot", "blast", "pdb"):
                            if isinstance(skill_result, list):
                                new_proteins = skill_result
                            elif isinstance(skill_result, dict):
                                new_proteins = (skill_result.get("proteins") or
                                                skill_result.get("structures") or
                                                skill_result.get("hits") or
                                                skill_result.get("results") or [])
                            else:
                                new_proteins = []
                            for _p in new_proteins[:3]:
                                if not isinstance(_p, dict):
                                    continue
                                _desc = _p.get("proteinDescription") or {}
                                _rec = _desc.get("recommendedName") or {}
                                _fn = _rec.get("fullName") or {}
                                _uname = _fn.get("value") or _p.get("uniProtkbId") or ""
                                _pname = (_p.get("name") or _uname or _p.get("title") or
                                          _p.get("id") or _p.get("primaryAccession") or
                                          _p.get("pdb_id") or "Unknown")
                                _acc = (_p.get("primaryAccession") or _p.get("accession") or
                                        _p.get("id") or _p.get("pdb_id") or "")
                                _info = _p.get("info") or _p.get("annotation") or ""
                                if not _info:
                                    _org = _p.get("organism") or {}
                                    _info = (_org.get("scientificName", "") if isinstance(_org, dict)
                                             else f"{_p.get('method','')} {_p.get('resolution','')}".strip())
                                results["proteins"].append({
                                    "name": _pname, "id": _acc,
                                    "info": _info[:200], "source": skill_name,
                                })
                        elif "compound" in category or "chem" in skill_name:
                            raw_list = skill_result if isinstance(skill_result, list) else skill_result.get("compounds", [skill_result])
                            for item in raw_list[:3]:
                                if not isinstance(item, dict):
                                    continue
                                mol_structs = item.get("molecule_structures") or {}
                                smiles = (mol_structs.get("canonical_smiles") or item.get("canonical_smiles") or item.get("smiles", ""))
                                name = item.get("pref_name") or item.get("name") or item.get("molecule_chembl_id", "Unknown")
                                results["compounds"].append({"name": name, "smiles": smiles, "source": skill_name})
                        elif "pathway" in category or skill_name in ("kegg-database", "string-database", "reactome-database"):
                            data = skill_result if isinstance(skill_result, dict) else {}
                            for pw in (data.get("pathways") or [])[:3]:
                                if isinstance(pw, dict):
                                    results["papers"].append({"title": pw.get("name", pw.get("id", "Pathway")), "pmid": pw.get("id", ""), "source": skill_name})
                            for gene in (data.get("genes") or data.get("proteins") or [])[:3]:
                                if isinstance(gene, dict):
                                    results["proteins"].append({"name": gene.get("name") or gene.get("preferredName") or gene.get("id", "Unknown"), "source": skill_name})

                        print(f"      ✓ {skill_name} gap-fill successful")
                    else:
                        print(f"      ✗ {skill_name}: {result.get('error', 'failed')}")
                except Exception as e:
                    print(f"      ✗ {skill_name}: {e}")

            # Re-extract SMILES/sequences from enriched data and re-validate
            smiles_list, sequences = self._extract_smiles_and_sequences(results)
            if smiles_list or sequences:
                new_computational = self.run_computational_validation(smiles_list, sequences, topic)
                results["computational"]["predictions"].extend(new_computational.get("predictions", []))
                results["computational"]["properties"].extend(new_computational.get("properties", []))

            # Re-generate insights from enriched data
            results["insights"] = self._generate_insights(results)
            results["refinement_cycles"] = cycle

            # Run quick reflection check
            if results["insights"]:
                reflection = self.llm_reasoner.adversarial_reflection_loop(
                    topic=topic,
                    hypothesis=results["insights"][0] if results["insights"] else topic,
                    insights=results["insights"],
                    papers=results.get("papers", []),
                    max_cycles=1  # Single reflection pass per refinement cycle
                )
                if reflection.get("approved"):
                    results["approved_by_reflector"] = True
                    print(f"    ✅ Reflector approved at refinement cycle {cycle}")
                    break

        return results

    def log_investigation(self, topic: str, investigation_results: Dict):
        if not self.journal:
            return
        try:
            self.journal.log_observation(
                content=f"Conducted investigation of {topic} using {len(investigation_results.get('tools_used', []))} tools",
                source="deep_investigation",
                tags=[topic, "multi-tool"]
            )
            for insight in investigation_results.get("insights", [])[:2]:
                self.journal.log_hypothesis(
                    hypothesis=insight,
                    motivation=f"Generated from {topic} investigation"
                )
        except Exception:
            pass


def run_deep_investigation(agent_name: str, topic: str,
                           community: Optional[str] = None,
                           agent_profile: Optional[Dict] = None,
                           skill_query_overrides: Optional[Dict[str, str]] = None) -> Dict:
    """
    Main entry point. LLM selects skills, agent self-assembles, no fallbacks.
    """
    if agent_profile:
        agent_name = agent_profile.get("name", agent_name)
        role = agent_profile.get("role", "")
        print(f"\n🔬 {agent_name}" + (f" ({role})" if role else "") + ": Initiating Investigation")
    else:
        print(f"\n🔬 {agent_name}: Initiating Investigation")
    print(f"📋 Topic: {topic}\n")

    investigator = DeepInvestigator(agent_name, agent_profile=agent_profile)

    previous = investigator.check_previous_work(topic)
    if previous.get("investigated"):
        print(f"  💾 {previous['message']}\n")

    # LLM analyses the topic and selects skills — constrained to agent's preferred_tools
    # if specified, so each agent only exercises its own skill set.
    print(f"  🤖 LLM analysing topic and selecting skills...")
    preferred_tools = (agent_profile or {}).get("preferred_tools", [])
    if preferred_tools:
        preferred_set = set(preferred_tools)
        all_skills = [
            s for s in investigator.skill_registry.skills.values()
            if s.get("name") in preferred_set
        ]
        if not all_skills:
            # Fallback: skill registry keys may differ — try case-insensitive match
            all_skills = [
                s for s in investigator.skill_registry.skills.values()
                if s.get("name", "").lower() in {p.lower() for p in preferred_tools}
            ]
        if not all_skills:
            # Last resort: use full catalog
            all_skills = list(investigator.skill_registry.skills.values())
        print(f"  🎯 Constrained to {len(all_skills)} preferred skill(s): {[s.get('name') for s in all_skills]}")
    else:
        all_skills = list(investigator.skill_registry.skills.values())
    analysis, pre_selected_skills = investigator.topic_analyzer.analyze_and_select_skills(
        topic=topic, available_skills=all_skills, max_skills=12, agent_profile=agent_profile
    )

    from autonomous.skill_diversity import ensure_minimum_skills, measure_diversity
    pre_selected_skills = ensure_minimum_skills(pre_selected_skills, min_skills=5)

    diversity = measure_diversity(pre_selected_skills)
    print(f"  💡 {analysis.reasoning}")
    if analysis.key_concepts:
        print(f"  📌 Key concepts: {', '.join(analysis.key_concepts[:3])}")
    print(f"  📊 {diversity['skill_count']} skills selected: {', '.join([s['name'] for s in pre_selected_skills])}")
    print()

    # Initial discovery pass
    results = investigator.run_tool_chain(topic, pre_selected_skills,
                                          skill_query_overrides=skill_query_overrides)

    # Feature 1: Computational validation on discovered entities
    smiles_list, sequences = investigator._extract_smiles_and_sequences(results)
    computational = investigator.run_computational_validation(smiles_list, sequences, topic)
    results["computational"] = computational

    # Feature 3: Iterative refinement loop (includes Feature 2 adversarial reflection)
    results = investigator.run_refinement_loop(
        topic=topic,
        initial_results=results,
        pre_selected_skills=pre_selected_skills,
        max_refinement_cycles=2
    )

    tools_used = results.get('tools_used', [])
    if tools_used:
        try:
            from autonomous.skill_usage_tracker import get_usage_tracker
            get_usage_tracker(agent_name).record_usage(tools_used, topic)
        except Exception:
            pass

    comp_count = (len(results.get("computational", {}).get("predictions", [])) +
                  len(results.get("computational", {}).get("properties", [])))
    print(f"\n  ✓ Investigation complete!")
    print(f"  📊 Tools used: {', '.join(results['tools_used'])}")
    print(f"  📄 Papers: {len(results['papers'])}")
    print(f"  🧮 Computational results: {comp_count}")
    print(f"  🔁 Refinement cycles: {results.get('refinement_cycles', 0)}")
    print(f"  ✅ Approved by reflector: {results.get('approved_by_reflector', False)}")
    print(f"  💡 Insights: {len(results['insights'])}\n")

    content = investigator.generate_sophisticated_content(topic, results)
    investigator.log_investigation(topic, results)

    # Emit a synthesis artifact so peer agents can discover needs signals
    if investigator.artifact_store:
        try:
            _synthesis_payload = {
                "topic": topic,
                "tools_used": results.get("tools_used", []),
                "paper_count": len(results.get("papers", [])),
                "protein_count": len(results.get("proteins", [])),
                "compound_count": len(results.get("compounds", [])),
                "insight_count": len(results.get("insights", [])),
                "open_questions": content.get("findings", "")[:500],
                "query": topic[:120],
            }
            _syn_artifact = investigator.artifact_store.create_and_save(
                skill_used="_synthesis",
                payload=_synthesis_payload,
                investigation_id=investigator._current_investigation_id,
                needs=results.get("needs", []),
            )
            results.setdefault("artifact_ids", []).append(_syn_artifact.artifact_id)
        except Exception as _syn_err:
            print(f"  Note: synthesis artifact save failed ({_syn_err})")

    content["agent_name"] = agent_name
    content["investigation_results"] = results

    # Feature 4: Principle extraction from accumulated investigation history
    try:
        from autonomous.principle_extractor import PrincipleExtractor
        extractor = PrincipleExtractor(agent_name)
        principles = extractor.extract_principles(
            topic=topic,
            current_findings=content.get("findings", ""),
            agent_name=agent_name
        )
        if principles:
            content["principles"] = principles
            principles_text = "\n\n**Extracted Scientific Principles:**\n"
            for p in principles:
                confidence = p.get("confidence", "medium")
                evidence = p.get("evidence_count", 2)
                principles_text += f"- {p['principle']} *(confidence: {confidence}, evidence: {evidence} investigations)*\n"
            content["findings"] += principles_text
    except Exception as e:
        print(f"  Note: Principle extraction failed ({e})")

    return content


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run a deep scientific investigation")
    parser.add_argument("topic", nargs="?", default=None)
    parser.add_argument("--agent", "-a", default=None)
    parser.add_argument("--community", "-c", default=None)
    args = parser.parse_args()
    if not args.topic:
        parser.print_help()
        sys.exit(1)
    agent_name = args.agent
    if not agent_name:
        try:
            profile_path = Path.home() / ".scienceclaw" / "agent_profile.json"
            if profile_path.exists():
                with open(profile_path) as f:
                    agent_name = json.load(f).get("name", "Agent")
            else:
                agent_name = "Agent"
        except Exception:
            agent_name = "Agent"
    run_deep_investigation(agent_name, args.topic, args.community)
