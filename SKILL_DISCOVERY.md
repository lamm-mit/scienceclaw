# Skill Discovery System

**Dynamic, intelligent scientific skill discovery for ScienceClaw agents**

## Overview

The Skill Discovery System enables ScienceClaw agents to dynamically discover and utilize scientific tools instead of using hardcoded tool chains. This makes agents truly adaptive - they can leverage the right tools for any research topic.

### What Changed

**Before:** Hardcoded tool selection
```python
# Old approach: rigid rules
if "protein" in topic:
    use_tools = ["pubmed", "uniprot"]
elif "compound" in topic:
    use_tools = ["pubmed", "pubchem"]
```

**After:** Dynamic skill discovery
```python
# New approach: intelligent selection
selected_skills = skill_selector.select_skills(topic, all_available_skills)
# LLM analyzes topic and chooses optimal tools
```

## System Architecture

### Three Core Components

1. **SkillRegistry** (`core/skill_registry.py`)
   - Scans `scienceclaw/skills/` directory
   - Parses SKILL.md metadata
   - Indexes by category, type, keywords
   - Provides search and suggestion APIs

2. **SkillExecutor** (`core/skill_executor.py`)
   - Universal execution engine
   - Handles Python scripts, packages, APIs
   - Returns standardized JSON results
   - Enables skill chaining

3. **LLMSkillSelector** (`core/skill_selector.py`)
   - Uses agent's LLM to select skills
   - Analyzes research topic
   - Determines optimal skill chain
   - Generates execution plan

### How It Works

```
Topic: "CRISPR Cas9 delivery systems"
       ↓
1. SkillRegistry.suggest_skills(topic)
   → Returns: ["pubmed", "cas", "gene-database", "openalex-database"]
       ↓
2. LLMSkillSelector.select_skills(topic, suggested)
   → LLM analyzes and picks: ["openalex-database", "cas", "gene-database"]
   → LLM provides reasoning for each
       ↓
3. SkillExecutor.execute_skill_chain([...])
   → Executes skills in order
   → Passes results between steps
       ↓
4. Deep Investigation System
   → Synthesizes results
   → Generates insights
   → Creates post
```

## Current Status

### ✅ Completed

- [x] Skill registry with auto-discovery (159 skills)
- [x] Universal skill executor
- [x] LLM-powered skill selector
- [x] Integration with deep_investigation.py
- [x] Added 142 Claude Scientific Skills
- [x] CLI tool for browsing skills (`skill_catalog.py`)
- [x] YAML frontmatter parsing for skill metadata

### 📊 Skill Inventory

**Total Skills: 159**

**By Category:**
- Biology: 118 skills
- General: 14 skills
- Compounds: 6 skills
- Literature: 5 skills
- Proteins: 5 skills
- Chemistry: 4 skills
- Pathways: 3 skills
- Drug Discovery: 2 skills
- Bioinformatics: 2 skills

**By Type:**
- Database: 76 skills (PubMed, UniProt, ChEMBL, OpenAlex, ClinVar, GWAS, etc.)
- Package: 38 skills (Biopython, Scanpy, RDKit, PyTorch Drug, etc.)
- Tool: 38 skills (BLAST, TDC, visualization, analysis)
- Integration: 7 skills (Benchling, Adaptyv, platforms)

### 🎯 High-Value Skills Added

**Literature & Knowledge:**
- openalex-database (240M+ scholarly works)
- biorxiv-database (preprints)
- clinicaltrials-database (clinical trials)
- citation-management

**Proteins & Sequences:**
- biopython (comprehensive toolkit)
- alphafold-database (structure predictions)
- esm (protein language models)
- pyopenms (mass spectrometry)
- uniprot-database (enhanced)

**Compounds & Drugs:**
- chembl-database (bioactive molecules)
- drugbank-database (comprehensive drug info)
- zinc-database (230M+ purchasable compounds)
- pubchem-database (enhanced)
- pytdc (Therapeutics Data Commons)

**Clinical & Medical:**
- clinvar-database (variant significance)
- cosmic-database (cancer mutations)
- clinpgx-database (pharmacogenomics)
- gwas-database (SNP-trait associations)

**Analysis & Computation:**
- scanpy (single-cell RNA-seq)
- torchdrug (graph neural networks)
- rdkit-database (cheminformatics)
- bioservices (multi-database wrapper)
- anndata (annotated data matrices)

**Specialized:**
- aeon (time series analysis)
- arboreto (gene regulatory networks)
- cirq (quantum circuits)
- patent search (USPTO)

## Usage

### 1. Browse Available Skills

```bash
# Show all skills
python3 skill_catalog.py

# Show statistics
python3 skill_catalog.py --stats

# Search for skills
python3 skill_catalog.py --search "protein"

# Filter by category
python3 skill_catalog.py --category biology

# Get suggestions for a topic
python3 skill_catalog.py --suggest "CRISPR delivery"
```

### 2. In Python Code

```python
from core.skill_registry import get_registry
from core.skill_selector import get_selector
from core.skill_executor import get_executor

# Get available skills
registry = get_registry()
stats = registry.stats()
print(f"Available: {stats['total_skills']} skills")

# Search for relevant skills
skills = registry.search_skills(
    query="drug discovery",
    category="compounds",
    limit=10
)

# Get suggestions
suggested = registry.suggest_skills_for_topic(
    "protein kinase inhibitor discovery"
)

# Use LLM to select skills
selector = get_selector(agent_name="YourAgent")
selected = selector.select_skills(
    topic="CRISPR Cas9 mechanisms",
    available_skills=list(registry.skills.values()),
    max_skills=5
)

# Execute a skill
executor = get_executor()
result = executor.execute_skill(
    skill_name="pubmed",
    skill_metadata=registry.get_skill("pubmed"),
    parameters={"query": "CRISPR", "max_results": 10}
)
```

### 3. In Agents (Automatic)

The skill discovery system is automatically integrated into `deep_investigation.py`:

```python
from autonomous.deep_investigation import run_deep_investigation

# Agent automatically discovers and uses optimal skills
result = run_deep_investigation(
    topic="mRNA vaccine delivery mechanisms",
    agent_name="BioAgent"
)
# System will:
# 1. Suggest relevant skills (openalex-database, pubmed, gene-database)
# 2. LLM selects optimal subset
# 3. Execute skills in order
# 4. Synthesize results into post
```

## Skill Format

### Two Formats Supported

#### Format 1: ScienceClaw Native (executable scripts)

```
skills/
└── pubmed/
    ├── SKILL.md          # Documentation
    ├── scripts/
    │   └── pubmed_search.py  # Executable
    └── requirements.txt  # Dependencies
```

#### Format 2: Claude Skills (LLM-guided)

```
skills/
└── openalex-database/
    ├── SKILL.md          # YAML frontmatter + markdown
    └── references/       # Optional supporting docs
```

**SKILL.md with YAML frontmatter:**
```markdown
---
name: openalex-database
description: Query and analyze scholarly literature using OpenAlex
---

# OpenAlex Database

## Overview
[detailed description]

## Core Capabilities
- Search for papers
- Analyze citations
- Track research trends
```

### Auto-Discovery Rules

The registry automatically:
1. Scans `skills/` directory
2. Parses SKILL.md (YAML frontmatter or markdown)
3. Extracts metadata (name, description, capabilities)
4. Identifies executables in `scripts/`
5. Categorizes by keywords
6. Determines type (database, package, tool, integration)

## Architecture Details

### SkillRegistry

**Capabilities:**
- Auto-discovery on initialization
- Caching to `~/.scienceclaw/skill_registry.json`
- Fast keyword-based search
- Topic-aware suggestions
- Category and type filtering

**API:**
```python
registry = SkillRegistry()
registry.discover_skills(force_refresh=True)
registry.search_skills(query="protein", category="biology")
registry.suggest_skills_for_topic("enzyme kinetics")
registry.get_skill("pubmed")
registry.get_categories()
registry.stats()
```

### SkillExecutor

**Capabilities:**
- Execute Python scripts (subprocess)
- Import Python packages (direct call)
- Make API calls (REST/GraphQL)
- Chain skill results
- Standardized JSON output

**Execution Modes:**
- Script: `python3 scripts/tool.py --param value`
- Package: `import tool; tool.method(params)`
- API: `requests.post(url, json=params)`

**API:**
```python
executor = SkillExecutor()
result = executor.execute_skill(name, metadata, params, timeout=30)
results = executor.execute_skill_chain([
    {"skill": "pubmed", "params": {"query": "CRISPR"}},
    {"skill": "gene-database", "params": {"gene": "CAS9"}}
])
```

### LLMSkillSelector

**Capabilities:**
- LLM-powered skill selection
- Reasoning about tool relevance
- Automatic parameter suggestion
- Investigation plan generation

**How It Works:**
1. Receives topic + available skills
2. Formats skills as catalog for LLM
3. LLM analyzes topic and selects 3-5 most relevant
4. LLM provides reasoning for each selection
5. LLM suggests parameters for execution

**API:**
```python
selector = LLMSkillSelector(agent_name="YourAgent")
selected = selector.select_skills(topic, available_skills, max_skills=5)
plan = selector.plan_investigation(topic, selected)
```

## Integration Points

### 1. Deep Investigation System

`autonomous/deep_investigation.py` now uses skill discovery:

```python
# In DeepInvestigator.__init__()
if get_registry:
    self.skill_registry = get_registry()
    self.skill_selector = get_selector(agent_name)
    self.skill_executor = get_executor()

# In run_deep_investigation()
suggested_skills = investigator.skill_registry.suggest_skills_for_topic(topic)
print(f"🎯 Relevant skills: {[s['name'] for s in suggested_skills[:5]]}")
```

### 2. Future Integrations

**Planned:**
- Heartbeat daemon skill selection
- Interactive skill recommendations in CLI
- Skill performance tracking (which work best)
- Automatic skill dependency installation
- Skill composition (combine multiple skills into workflows)

## Examples

### Example 1: Protein Research

```bash
$ python3 skill_catalog.py --suggest "protein kinase mechanisms"

🎯 Suggested Skills:
1. uniprot (proteins) - Protein sequences and annotations
2. pdb (proteins) - Protein structures
3. alphafold-database (biology) - Predicted structures
4. pubmed (literature) - Scientific literature
5. esm (biology) - Protein language models
```

### Example 2: Drug Discovery

```bash
$ python3 skill_catalog.py --suggest "small molecule inhibitors"

🎯 Suggested Skills:
1. chembl-database (compounds) - Bioactive molecules
2. pubchem-database (compounds) - Chemical structures
3. drugbank-database (compounds) - Drug information
4. pytdc (drug_discovery) - ADMET datasets
5. zinc-database (compounds) - Purchasable compounds
```

### Example 3: Clinical Research

```bash
$ python3 skill_catalog.py --suggest "cancer biomarkers"

🎯 Suggested Skills:
1. cosmic-database (biology) - Cancer mutations
2. clinvar-database (biology) - Variant significance
3. pubmed (literature) - Cancer literature
4. gene-database (biology) - Gene information
5. gwas-database (biology) - SNP-trait associations
```

## Benefits

### For Agents

1. **Adaptability**: No hardcoded rules, works for any topic
2. **Intelligence**: LLM decides what tools to use and why
3. **Scalability**: Add new skills without modifying code
4. **Depth**: Access to 159 specialized tools
5. **Quality**: Better tool selection → better research

### For Development

1. **Maintainability**: No hardcoded tool chains to update
2. **Extensibility**: Drop skills into `skills/` directory
3. **Testing**: Test registry/selector/executor independently
4. **Documentation**: Auto-generated from SKILL.md files

## Troubleshooting

### "No skills discovered"

```bash
# Force refresh the cache
python3 -c "from core.skill_registry import get_registry; get_registry().refresh()"
```

### "Skill not found"

```bash
# Check if skill exists
ls scienceclaw/skills/your-skill/

# Search for it
python3 skill_catalog.py --search "your-skill"
```

### "LLM skill selection failed"

The system falls back to keyword-based selection. Check:
1. OpenClaw is installed: `openclaw --version`
2. Agent has valid SOUL.md: `ls ~/.openclaw/workspace/SOUL.md`

### "Execution timeout"

Increase timeout in executor:
```python
result = executor.execute_skill(..., timeout=60)  # 60 seconds
```

## Next Steps

### Phase 1: Current (Complete) ✅
- [x] Skill discovery infrastructure
- [x] 159 skills available
- [x] Integration with deep investigation
- [x] CLI browsing tool

### Phase 2: Execution (In Progress)
- [ ] Test execution of 10 high-priority skills
- [ ] Create wrapper scripts for Claude skills
- [ ] Validate API credentials and dependencies
- [ ] Skill execution logging

### Phase 3: Intelligence
- [ ] Track skill performance (which work best)
- [ ] Learn from successful investigations
- [ ] Recommend skill combinations
- [ ] Auto-tune parameters

### Phase 4: Ecosystem
- [ ] Community skill sharing
- [ ] Skill marketplace
- [ ] Skill composition workflows
- [ ] Skill testing framework

## Contributing New Skills

### To Add a Skill:

1. Create directory in `scienceclaw/skills/`:
   ```bash
   mkdir scienceclaw/skills/my-new-skill
   ```

2. Create SKILL.md:
   ```markdown
   ---
   name: my-new-skill
   description: What this skill does
   ---
   
   # My New Skill
   
   ## Core Capabilities
   - Feature 1
   - Feature 2
   ```

3. (Optional) Add executable script:
   ```bash
   mkdir scienceclaw/skills/my-new-skill/scripts
   # Create Python script that outputs JSON
   ```

4. Refresh registry:
   ```bash
   python3 -c "from core.skill_registry import get_registry; get_registry().refresh()"
   ```

5. Test:
   ```bash
   python3 skill_catalog.py --search "my-new-skill"
   ```

## Technical Details

### Registry Cache

- Location: `~/.scienceclaw/skill_registry.json`
- Auto-refreshes when `skills/` directory changes
- Manual refresh: `registry.refresh()`

### Skill Metadata Schema

```json
{
  "name": "skill-name",
  "path": "/path/to/skill",
  "type": "database|package|tool|integration",
  "category": "biology|chemistry|compounds|proteins|...",
  "description": "What it does",
  "capabilities": ["Capability 1", "Capability 2"],
  "keywords": ["keyword1", "keyword2"],
  "executables": ["/path/to/script.py"],
  "dependencies": ["package1", "package2"]
}
```

### Performance

- Registry initialization: ~400ms (with cache)
- Skill search: < 10ms
- LLM skill selection: 30-45 seconds
- Fallback keyword selection: < 50ms

## Summary

The Skill Discovery System transforms ScienceClaw from using hardcoded tool chains to intelligently discovering and selecting the optimal tools for any research topic. With 159 scientific skills available and growing, agents can now conduct truly sophisticated, multi-disciplinary investigations.

**Key Innovation:** Instead of telling the agent "if protein, use UniProt", the agent's LLM analyzes the topic and decides which of 159 available tools are most relevant, why, and how to use them.

This is the foundation for truly intelligent, adaptive scientific agents.
