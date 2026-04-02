# Drug Research Tool Reference

Detailed tool chains, code examples, output templates, and validation guidance for the drug-research skill.

---

## FDA Label Core Fields Bundle

For approved drugs, the agent retrieves these FDA label sections early (after getting set_id from `DailyMed_search_spls`):

### Critical Label Sections

Call `DailyMed_get_spl_sections_by_setid(setid=set_id, sections=[...])` with these sections:

**Phase 1 (Mechanism & Chemistry)**:
- `mechanism_of_action` -> Section 3.1
- `pharmacodynamics` -> Section 3.1
- `chemistry` -> Section 2.4

**Phase 2 (ADMET & PK)**:
- `clinical_pharmacology` -> Section 4
- `pharmacokinetics` -> Section 4.1-4.4
- `drug_interactions` -> Section 4.3, 6.5

**Phase 3 (Safety & Dosing)**:
- `warnings_and_cautions` -> Section 6.3
- `adverse_reactions` -> Section 6.1
- `dosage_and_administration` -> Section 6.6, 8.2

**Phase 4 (PGx & Clinical)**:
- `pharmacogenomics` -> Section 7
- `clinical_studies` -> Section 5.5
- `description` -> Section 2.5 (formulation)
- `inactive_ingredients` -> Section 2.5

### Label Extraction Strategy

```
1. Get set_id: DailyMed_search_spls(drug_name)

2. Batch call for all core sections (or 3-4 calls with 4-5 sections each):
   DailyMed_get_spl_sections_by_setid(setid=set_id, sections=["mechanism_of_action", "pharmacodynamics", ...])

3. Extract and populate report sections as data is retrieved
```

---

## Compound Disambiguation (Phase 1)

Establish compound identity before any research.

### Identifier Resolution Chain

```
1. PubChem_get_CID_by_compound_name(compound_name)
   -> Extract: CID, canonical SMILES, formula

2. ChEMBL_search_compounds(query=drug_name)
   -> Extract: ChEMBL ID, pref_name

3. DailyMed_search_spls(drug_name)
   -> Extract: Set ID, NDC codes (if approved)

4. PharmGKB_search_drugs(query=drug_name)
   -> Extract: PharmGKB ID (PA...)
```

### Handle Naming Ambiguity

| Issue | Example | Resolution |
|-------|---------|------------|
| Salt forms | metformin vs metformin HCl | Note all CIDs; use parent compound |
| Isomers | omeprazole vs esomeprazole | Verify SMILES; separate entries if distinct |
| Prodrugs | enalapril vs enalaprilat | Document both; note conversion |
| Brand confusion | Different products same name | Clarify with user |

---

## Tool Chains by Research Path

### PATH 1: Chemical Properties & CMC

**Objective**: Full physicochemical profile, salt forms, formulation details

**Multi-Step Chain**:
```
1. PubChem_get_compound_properties_by_CID(cid)
   -> Extract: MW, formula, XLogP, TPSA, HBD, HBA, rotatable bonds

2. ADMETAI_predict_physicochemical_properties(smiles=[smiles])
   -> Extract: MW, logP, HBD, HBA, Lipinski, QED, stereo_centers, TPSA

3. ADMETAI_predict_solubility_lipophilicity_hydration(smiles=[smiles])
   -> Extract: Solubility_AqSolDB, Lipophilicity_AstraZeneca

4. DailyMed_search_spls(drug_name)
   -> Extract SPL set_id, then:

5. DailyMed_get_spl_sections_by_setid(setid=set_id, sections=["chemistry"])
   -> Extract: Salt forms, polymorphs, molecular formula, structure diagram

6. DailyMed_get_spl_sections_by_setid(setid=set_id, sections=["description", "inactive_ingredients"])
   -> Extract: Formulation details, excipients, dosage forms

7. FORMULATION COMPARISON (if multiple formulations exist):
   a. DailyMed_search_spls(drug_name) -> identify all formulations (IR, ER, XR, etc.)
   b. For each formulation:
      - DailyMed_parse_clinical_pharmacology(setid) -> extract PK parameters
      - Parse: Tmax, Cmax, AUC, half-life
   c. Create comparison table showing bioavailability differences
```

**Type Normalization**: Convert all numeric IDs to strings before API calls.

**Output Template**:
```markdown
### 2.1 Physicochemical Profile

| Property | Value | Drug-Likeness | Source |
|----------|-------|---------------|--------|
| **Molecular Weight** | 129.16 g/mol | (< 500) | PubChem |
| **LogP** | -2.64 | (< 5) | ADMET-AI |
| **TPSA** | 91.5 A2 | (< 140) | PubChem |
| **H-Bond Donors** | 2 | (<= 5) | PubChem |
| **H-Bond Acceptors** | 5 | (< 10) | PubChem |
| **Rotatable Bonds** | 2 | (< 10) | PubChem |

**Lipinski Rule of Five**: PASS (0 violations)
**QED Score**: 0.74 (Good drug-likeness)

*Sources: PubChem via PubChem_get_compound_properties_by_CID, ADMET-AI via ADMETAI_predict_physicochemical_properties*

### 2.6 Formulation Comparison (If Multiple Formulations Available)

| Formulation | Tmax (h) | Cmax (ng/mL) | AUC (ng*h/mL) | Half-life (h) | Dosing |
|-------------|----------|--------------|---------------|---------------|--------|
| **IR (Immediate Release)** | 2.5 | 1200 | 8400 | 6.5 | 500 mg TID |
| **ER (Extended Release)** | 7.0 | 950 | 8900 | 6.5 | 1000 mg QD |
```

### PATH 2: Mechanism & Targets

**Objective**: FDA label MOA + experimental targets + selectivity

**Multi-Step Chain**:
```
1. DailyMed_search_spls(drug_name) -> get set_id

2. DailyMed_get_spl_sections_by_setid(setid=set_id, sections=["mechanism_of_action", "pharmacodynamics"])
   -> Extract: Official FDA MOA description [T1]

3. ChEMBL_search_activities(molecule_chembl_id=chembl_id, limit=100)
   -> Extract: Activity records with target_chembl_id, pChEMBL, standard_type
   -> Parse unique target_chembl_id values (convert to strings)

4. ChEMBL_get_target(target_chembl_id) for each unique target
   -> Extract: Target name, UniProt ID, organism [T1]

5. DGIdb_get_drug_info(drugs=[drug_name])
   -> Extract: Target genes, interaction types, sources [T2]

6. PubChem_get_bioactivity_summary_by_CID(cid)
   -> Extract: Assay summary, active/inactive counts [T2]
```

**CRITICAL**:
- **Avoid `ChEMBL_get_molecule_targets`** - it returns unfiltered targets including irrelevant entries
- **Derive targets from activities instead**: Filter to potent activities (pChEMBL >= 6.0 or IC50/EC50 <= 1 uM)
- **Type normalization**: Convert all ChEMBL IDs to strings before API calls

**Output Template**:
```markdown
### 3.1 Primary Mechanism of Action

**FDA Label MOA**: [Quote from DailyMed]

*Source: DailyMed SPL via DailyMed_get_spl_sections_by_setid (mechanism_of_action) [T1]*

### 3.2 Primary Target(s)

| Target | UniProt | Type | Potency | Assays | Evidence | Source |
|--------|---------|------|---------|--------|----------|--------|
| PRKAA1 (AMPK a1) | Q13131 | Activator | EC50 ~10 uM | 12 | T1 | ChEMBL |

*Source: ChEMBL via ChEMBL_search_activities -> ChEMBL_get_target (filtered to pChEMBL >= 6.0)*
```

### PATH 3: ADMET Properties

**Objective**: Full ADMET profile - predictions + FDA label PK

**Primary Chain (ADMET-AI)**:
```
1. ADMETAI_predict_bioavailability(smiles=[smiles])
   -> Extract: Bioavailability_Ma, HIA_Hou, PAMPA_NCATS, Caco2_Wang, Pgp_Broccatelli

2. ADMETAI_predict_BBB_penetrance(smiles=[smiles])
   -> Extract: BBB_Martins (0-1 probability)

3. ADMETAI_predict_CYP_interactions(smiles=[smiles])
   -> Extract: CYP1A2, CYP2C9, CYP2C19, CYP2D6, CYP3A4 (inhibitor/substrate)

4. ADMETAI_predict_clearance_distribution(smiles=[smiles])
   -> Extract: Clearance, Half_Life_Obach, VDss_Lombardo, PPBR_AZ

5. ADMETAI_predict_toxicity(smiles=[smiles])
   -> Extract: AMES, hERG, DILI, ClinTox, LD50_Zhu, Carcinogens
```

**Fallback Chain (If ADMET-AI Fails)**:
```
6. DailyMed_get_spl_sections_by_setid(setid=set_id, sections=["clinical_pharmacology", "pharmacokinetics"])
   -> Extract: Absorption, distribution, metabolism, excretion from label [T1]

7. DailyMed_get_spl_sections_by_setid(setid=set_id, sections=["drug_interactions"])
   -> Extract: CYP interactions, transporter interactions [T1]

8. PubMed_search_articles(query="[drug] pharmacokinetics", max_results=10)
   -> Extract: PK parameters from clinical studies [T2]
```

**CRITICAL Dependency Gate**:
- If ADMET-AI tools fail (invalid SMILES, API error, validation error), the agent automatically switches to fallback
- Section 4 must never be left as "predictions unavailable"
- The agent populates Section 4 with either predictions OR label data OR literature PK

### PATH 4: Clinical Trials

**Objective**: Complete clinical development picture with accurate phase counts

**Multi-Step Chain**:
```
1. search_clinical_trials(intervention=drug_name, pageSize=100)
   -> Extract: Full result set with NCT IDs, phases, statuses, conditions

2. COMPUTE PHASE COUNTS from results:
   -> Count by phase: Phase 1, Phase 2, Phase 3, Phase 4
   -> Count by status: Completed, Recruiting, Active not recruiting, Terminated
   -> Group by condition/indication (top 5)

3. SELECT REPRESENTATIVE TRIALS:
   -> Top 5 Phase 3 completed trials (by enrollment or recency)
   -> Top 5 Phase 4 post-marketing trials
   -> Top 3 recruiting trials

4. get_clinical_trial_conditions_and_interventions(nct_ids=[selected_ids])
   -> Extract: Detailed conditions, interventions, arm groups

5. extract_clinical_trial_outcomes(nct_ids=[completed_phase3])
   -> Extract: Primary outcomes, efficacy measures, p-values

6. extract_clinical_trial_adverse_events(nct_ids=[completed_ids])
   -> Extract: Serious AEs, common AEs by organ system

7. fda_pharmacogenomic_biomarkers(drug_name=drug_name)
   -> Extract: FDA-required biomarker testing, approved companion diagnostics [T1]

8. DailyMed_get_spl_sections_by_setid(setid=set_id, sections=["indications_and_usage"])
   -> Parse for: "testing required", "biomarker", "companion diagnostic" [T1]

9. PharmGKB_search_drugs(query=drug_name)
   -> Extract: PharmGKB drug ID for response predictors

10. PharmGKB_get_clinical_annotations(drug_id=pharmgkb_id)
    -> Extract: Response/toxicity biomarkers with clinical evidence levels [T2]
```

**CRITICAL**:
- Section 5.2 must show actual counts by phase/status, not just a list of trials
- Section 5.6 must document: FDA-required testing (T1), companion diagnostics (T1), response predictors (T2)

### PATH 5: Post-Marketing Safety & Drug Interactions

**Objective**: Real-world safety signals + DDI guidance + dose modifications

**FAERS Chain**:
```
1. FAERS_count_reactions_by_drug_event(medicinalproduct=drug_name)
   -> Extract: Top 20 adverse reactions by MedDRA term [T1]

2. FAERS_count_seriousness_by_drug_event(medicinalproduct=drug_name)
   -> Extract: Serious vs non-serious counts & ratio [T1]

3. FAERS_count_outcomes_by_drug_event(medicinalproduct=drug_name)
   -> Extract: Recovered, recovering, fatal, unresolved counts [T1]

4. FAERS_count_death_related_by_drug(medicinalproduct=drug_name)
   -> Extract: Fatal outcome count [T1]

5. FAERS_count_patient_age_distribution(medicinalproduct=drug_name)
   -> Extract: Reports by age group [T1]
```

**Drug Interactions Chain**:
```
6. DailyMed_get_spl_sections_by_setid(setid=set_id, sections=["drug_interactions"])
   -> Extract: DDI table, CYP interactions, contraindicated combinations [T1]

7. DailyMed_get_spl_sections_by_setid(setid=set_id, sections=["dosage_and_administration", "warnings_and_cautions"])
   -> Extract: Dose modification triggers [T1]

8. DailyMed_get_spl_by_setid(setid=set_id)
   -> Parse full XML for drug-food interactions [T1]

9. search_clinical_trials(intervention=f"{drug_name} AND combination", pageSize=50)
   -> Extract: Approved combinations, regimens [T1]

10. DailyMed_get_spl_sections_by_setid(setid=set_id, sections=["indications_and_usage", "dosage_and_administration"])
    -> Parse for: combination therapy details [T1]
```

**FAERS Reporting Requirements**:
- Include date window (e.g., "Reports from 2004-2026")
- Report seriousness breakdown (not just top PTs)
- Add limitations paragraph: Small N, voluntary reporting, causality not established, reporting bias

**Output Templates for Safety Sections**:

```markdown
### 6.2 Post-Marketing Safety (FAERS)

**Total FAERS Reports**: [count] (Date range: [start] - [end])

#### Seriousness Breakdown
| Category | Count | Percentage |
|----------|-------|------------|
| Serious | X | X% |
| Non-Serious | X | X% |

#### Data Limitations
FAERS data represents voluntary reports and has important limitations:
- **Small sample size** relative to total prescriptions
- **Reporting bias**: Serious events more likely to be reported
- **Causality not established**: Reports do not prove drug caused the event
- **Incomplete data**: Many reports lack outcome information

### 6.6 Dose Modification Guidance

#### Hepatic Impairment
| ALT/AST Level | Action |
|---------------|--------|
| ALT >3x ULN | Hold dose; reassess liver function |
| ALT >5x ULN | Discontinue permanently |

#### Renal Impairment
| eGFR (mL/min/1.73m2) | Dosing |
|----------------------|--------|
| >=60 | No adjustment |
| 45-59 | Reduce dose |
| <30 | Contraindicated |

### 6.5.2 Drug-Food Interactions

| Food/Beverage | Effect | Mechanism | Recommendation | Source |
|---------------|--------|-----------|----------------|--------|
```

### PATH 6: Pharmacogenomics

**Objective**: PGx associations and dosing guidelines

**Primary Chain (PharmGKB)**:
```
1. PharmGKB_search_drugs(query=drug_name)
   -> Extract: PharmGKB drug ID

2. PharmGKB_get_drug_details(drug_id)
   -> Extract: Cross-references, related genes

3. PharmGKB_get_clinical_annotations(gene_id)  # For each related gene
   -> Extract: Variant-drug associations, evidence levels

4. PharmGKB_get_dosing_guidelines(gene=gene_symbol)
   -> Extract: CPIC/DPWG guideline recommendations
```

**Fallback Chain (If PharmGKB Fails)**:
```
5. DailyMed_get_spl_sections_by_setid(setid=set_id, sections=["pharmacogenomics", "clinical_pharmacology"])
   -> Extract: Label-based PGx information [T1]

6. PubMed_search_articles(query="[drug] pharmacogenomics", max_results=5)
   -> Extract: Published PGx associations [T2]
```

**CRITICAL**:
- If PharmGKB tools fail (API error, timeout), the agent switches to fallback
- The agent documents the failure and indicates "PharmGKB unavailable; using label + literature"
- Section 7 is always populated with either PharmGKB data OR label data OR "No PGx associations identified"

### PATH 7: Regulatory Status & Patents

**Objective**: Comprehensive regulatory and intellectual property landscape

**Multi-Step Chain**:
```
1. DailyMed_search_spls(drug_name=drug_name)
   -> Extract: SetID for regulatory label data

2. FDA_OrangeBook_search_drug(brand_name=drug_name)
   -> Extract: Application number, approval dates [T1]

3. FDA_OrangeBook_get_approval_history(appl_no=app_number)
   -> Extract: Original approval date, supplements, label changes [T1]

4. FDA_OrangeBook_get_exclusivity(brand_name=drug_name)
   -> Extract: Exclusivity types, expiration dates [T1]

5. FDA_OrangeBook_get_patent_info(brand_name=drug_name)
   -> Extract: Patent numbers, substance/formulation claims [T1]

6. FDA_OrangeBook_check_generic_availability(brand_name=drug_name)
   -> Extract: Generic entries, TE codes, first generic date [T1]

7. DailyMed_get_spl_sections_by_setid(setid=set_id, sections=["indications_and_usage"])
   -> Parse for: breakthrough designation, priority review, orphan status [T1]

8. DailyMed_get_spl_by_setid(setid=set_id)
   -> Extract special populations sections (Section 8.5):
   -> pediatric_use (LOINC 34076-0)
   -> geriatric_use (LOINC 34082-8)
   -> pregnancy (LOINC 42228-7)
   -> nursing_mothers (LOINC 34080-2)

9. Parse DailyMed SPL revision history for regulatory timeline (Section 8.6)

10. Combine FDA_OrangeBook_get_approval_history + label data:
    -> Create regulatory timeline table
    -> Document approval pathway
    -> Note limitation: US-only data [T1]
```

**CRITICAL**:
- Orange Book data is US-only; the agent documents limitation for EMA/PMDA
- Special populations require XML parsing from full SPL (DailyMed_get_spl_by_setid)
- Look for LOINC section codes to reliably extract special population data

### PATH 8: Real-World Evidence

**Objective**: Complement clinical trial efficacy with real-world effectiveness data

**Multi-Step Chain**:
```
1. search_clinical_trials(study_type="OBSERVATIONAL", intervention=drug_name, pageSize=50)
   -> Extract: RWE studies, registry trials, observational cohorts [T1]

2. PubMed_search_articles(query=f"{drug_name} (real-world OR observational OR effectiveness)", max_results=20)
   -> Extract: RWE publications, adherence studies, off-label use [T2]

3. PubMed_search_articles(query=f"{drug_name} (registry OR post-marketing OR surveillance)", max_results=10)
   -> Extract: Post-marketing surveillance, long-term outcomes [T2]

4. Compare efficacy vs effectiveness:
   -> Clinical trial primary outcomes vs real-world outcomes
   -> Trial inclusion criteria vs real-world patient demographics
   -> Adherence rates in trials vs clinical practice
```

### PATH 9: Comparative Analysis

**Objective**: Position drug within therapeutic class with head-to-head and indirect comparisons

**Multi-Step Chain**:
```
1. Identify comparator drugs:
   -> User provides OR infer from indication + mechanism

2. For each comparator, run abbreviated tool chain:
   a. PubChem_get_CID_by_compound_name(compound=comparator)
   b. ChEMBL_search_activities(chemblid=comparator_chemblid, target=primary_target, max_results=20)
   c. search_clinical_trials(intervention=comparator, condition=indication, pageSize=20)
   d. FAERS_count_reactions_by_drug_event(medicinalproduct=comparator)

3. Search for head-to-head trials:
   search_clinical_trials(intervention=f"{drug_name} AND {comparator}")

4. PubMed_search_articles(query=f"{drug_name} vs {comparator}", max_results=10)

5. Create comparison tables across dimensions:
   -> Potency, selectivity, ADMET, efficacy, safety, cost (if available)
```

---

## Type Normalization & Error Prevention

### Common Validation Errors

Many ToolUniverse tools require **string** inputs but may return **integers** or **floats**. The agent converts IDs to strings.

**Problem Examples**:
- ChEMBL target IDs: `12345` (int) -> must be `"12345"` (str)
- PubMed IDs: `23456789` (int) -> must be `"23456789"` (str)
- Clinical trial NCT IDs: sometimes parsed as numbers

### Type Normalization

Before calling any tool with ID parameters:

```python
# Convert all IDs to strings
chembl_ids = [str(id) for id in chembl_ids]
nct_ids = [str(id) for id in nct_ids]
pmids = [str(id) for id in pmids]
```

### Pre-Call Checklist

Before each API call:
- All ID parameters are strings
- Lists contain strings, not ints/floats
- No `None` or `null` values in required fields
- Arrays are non-empty if required

---

## Evidence Grading System

### Evidence Tiers

| Tier | Symbol | Description | Example |
|------|--------|-------------|---------|
| **T1** | Three stars | Phase 3 RCT, meta-analysis, FDA approval | Pivotal trial, label indication |
| **T2** | Two stars | Phase 1/2 trial, large case series | Dose-finding study |
| **T3** | One star | In vivo animal, in vitro cellular | Mouse PK study |
| **T4** | No stars | Review mention, computational prediction | ADMET-AI prediction |

### Application in Report

```markdown
Metformin reduces hepatic glucose output via AMPK activation [T1: FDA Label].
Phase 3 trials demonstrated HbA1c reduction of 1.0-1.5% [T1: NCT00123456].
Preclinical studies suggest anti-cancer properties [T3: PMID:23456789].
ADMET-AI predicts low hERG liability (0.12) [T4: computational].
```

---

## Fallback Chains

| Primary Tool | Fallback | Use When |
|--------------|----------|----------|
| `PubChem_get_CID_by_compound_name` | `ChEMBL_search_compounds` | Name not in PubChem |
| `ChEMBL_get_molecule_targets` | **Use `ChEMBL_search_activities` instead** | Avoid this tool (returns irrelevant targets) |
| `ChEMBL_get_bioactivity_by_chemblid` | `PubChem_get_bioactivity_summary_by_CID` | No ChEMBL ID |
| `DailyMed_search_spls` | `PubChem_get_drug_label_info_by_CID` | DailyMed timeout |
| `PharmGKB_get_dosing_guidelines` | `DailyMed_get_spl_sections_by_setid` (pharmacogenomics) | PharmGKB API error |
| `PharmGKB_search_drugs` | `DailyMed_get_spl_sections_by_setid` + `PubMed_search_articles` | PharmGKB unavailable |
| `FAERS_count_reactions_by_drug_event` | Document "FAERS unavailable" + use label AEs | API error |
| `ADMETAI_*` (all tools) | `DailyMed_get_spl_sections_by_setid` (clinical_pharmacology, pharmacokinetics) | Invalid SMILES or API error |

---

## Quick Reference: Tools by Use Case

| Use Case | Primary Tool | Fallback | Evidence |
|----------|--------------|----------|----------|
| Name -> CID | `PubChem_get_CID_by_compound_name` | `ChEMBL_search_compounds` | T1 |
| SMILES -> CID | `PubChem_get_CID_by_SMILES` | - | T1 |
| Properties | `PubChem_get_compound_properties_by_CID` | `ADMETAI_predict_physicochemical_properties` | T1 / T2 |
| Salt forms | `DailyMed_get_spl_sections_by_setid` (chemistry) | - | T1 |
| Formulation | `DailyMed_get_spl_sections_by_setid` (description, inactive_ingredients) | - | T1 |
| Drug-likeness | `ADMETAI_predict_physicochemical_properties` | Calculate from properties | T2 |
| FDA MOA | `DailyMed_get_spl_sections_by_setid` (mechanism_of_action) | - | T1 |
| Targets | `ChEMBL_search_activities` -> `ChEMBL_get_target` | `DGIdb_get_drug_info` | T1 |
| **Avoid** | ~~`ChEMBL_get_molecule_targets`~~ | Use activities-based approach | N/A |
| Bioactivity | `ChEMBL_search_activities` | `PubChem_get_bioactivity_summary_by_CID` | T1 |
| Absorption | `ADMETAI_predict_bioavailability` | `DailyMed` clinical_pharmacology | T2 / T1 |
| BBB | `ADMETAI_predict_BBB_penetrance` | `DailyMed` clinical_pharmacology | T2 / T1 |
| CYP | `ADMETAI_predict_CYP_interactions` | `DailyMed` drug_interactions | T2 / T1 |
| Toxicity | `ADMETAI_predict_toxicity` | `DailyMed` warnings_and_cautions | T2 / T1 |
| Trials | `search_clinical_trials` | - | T1 |
| Phase counts | **Compute from `search_clinical_trials` results** | - | T1 |
| Trial outcomes | `extract_clinical_trial_outcomes` | - | T1 |
| FAERS | `FAERS_count_reactions_by_drug_event` | Label adverse_reactions | T1 |
| Dose mods | `DailyMed_get_spl_sections_by_setid` (dosage_and_administration, warnings) | - | T1 |
| Label | `DailyMed_search_spls` | `PubChem_get_drug_label_info_by_CID` | T1 |
| PGx | `PharmGKB_search_drugs` | `DailyMed` pharmacogenomics + PubMed | T2 / T1 |
| CPIC | `PharmGKB_get_dosing_guidelines` | `DailyMed` pharmacogenomics | T1 / T2 |
| Literature | `PubMed_search_articles` | `EuropePMC_search_articles` | Varies |

---

## Section Completeness Checklist

Before finalizing any report, verify each section meets minimum requirements:

### Section 1 (Identity)
- PubChem CID with link
- ChEMBL ID with link (or "Not in ChEMBL")
- Canonical SMILES
- Molecular formula and weight
- At least 3 brand names OR "Generic only"
- Salt forms identified (or "Parent compound only")

### Section 2 (Chemistry)
- 6+ physicochemical properties in table format (including pKa if available)
- Lipinski rule assessment with pass/fail
- QED score with interpretation
- Solubility data (predicted or label-based)
- Salt forms documented (or "Parent compound only")
- 2D structure image embedded (PubChem link)
- Formulation details if available (dosage forms, excipients)

### Section 3 (Mechanism)
- FDA label MOA text quoted (if approved drug) OR literature MOA summary
- Primary mechanism described in 2-3 sentences
- At least 1 primary target with UniProt ID
- Activity type and potency (IC50/EC50/Ki) with assay count
- Target selectivity table (including mutant forms if relevant)
- Off-target activity addressed (or "Highly selective")

### Section 4 (ADMET)
- All 5 subsections present (A, D, M, E, T)
- Absorption: bioavailability + at least 2 other endpoints
- Distribution: BBB + VDss or PPB
- Metabolism: CYP substrate/inhibitor status for 3+ CYPs
- Excretion: clearance OR half-life
- Toxicity: AMES + hERG + at least 1 other
- If ADMET-AI fails, fallback to FDA label PK sections

### Section 5 (Clinical)
- Development status clearly stated
- Actual counts by phase/status in table format
- Indication breakdown by counts
- Approved indications with year (or "Not approved")
- Representative trial list with clear labels
- Key efficacy data with trial references

### Section 6 (Safety)
- Top 5 adverse events with frequencies
- FAERS seriousness breakdown
- FAERS date window documented
- FAERS limitations paragraph
- Black box warnings (or "None")
- At least 3 drug-drug interactions with mechanism
- Dose modification triggers

### Section 7 (PGx)
- Pharmacogenes listed (or "None identified")
- CPIC/DPWG guideline status (or "No guideline available")
- At least 1 clinical annotation OR "No annotations identified"
- If PharmGKB fails, fallback to label PGx + literature

### Section 10 (Conclusions)
- 5-point scorecard covering: efficacy, safety, PK, druggability, competition
- 3+ key strengths
- 3+ key concerns/limitations
- At least 2 research gaps identified

---

## Drug Profile Scorecard Template

Include in Section 10:

```markdown
### 10.1 Drug Profile Scorecard

| Criterion | Score (1-5) | Rationale |
|-----------|-------------|-----------|
| **Efficacy Evidence** | 5 | Multiple Phase 3 trials, decades of use |
| **Safety Profile** | 4 | Well-tolerated; rare but serious risks |
| **PK/ADMET** | 4 | Good bioavailability; known elimination |
| **Target Validation** | 4 | Mechanism well-established |
| **Competitive Position** | 3 | First-line but many alternatives |
| **Overall** | 4.0 | **Strong drug profile** |

**Interpretation**:
- 5 = Excellent, 4 = Good, 3 = Moderate, 2 = Concerning, 1 = Poor
```

---

## Automated Completeness Audit

Before finalizing the report, the agent runs this audit and appends findings to Section 11.

### Audit Process

1. Review each section against minimum requirements (see checklist above)
2. Flag any missing data with specific tool call recommendations
3. Document tool failures and fallback attempts
4. Generate completeness score (% of minimum requirements met)

### Audit Output Template

```markdown
## Report Completeness Audit

**Overall Completeness**: X% (N/M minimum requirements met)

### Missing Data Items

| Section | Missing Item | Recommended Action |
|---------|--------------|-------------------|

### Tool Failures Encountered

| Tool | Error | Fallback Used |
|------|-------|---------------|

### Data Confidence Assessment

| Section | Confidence | Evidence Tier | Notes |
|---------|-----------|---------------|-------|

### Quality Control Metrics

#### Data Recency
| Source | Last Updated | Data Age | Status |
|--------|-------------|----------|--------|

#### Cross-Source Validation
| Property | Source A | Source B | Agreement |
|----------|---------|---------|-----------|

#### Completeness Score
| Category | Score | Details |
|----------|-------|---------|

#### Evidence Distribution
| Tier | Count | Percentage | Interpretation |
|------|-------|------------|----------------|
```

---

## Report Template

The agent creates the report file `[DRUG]_drug_report.md` before any data collection, with these sections initialized to `[Researching...]`:

1. Executive Summary
2. Compound Identity (1.1 Database Identifiers, 1.2 Structural Information, 1.3 Names & Synonyms)
3. Chemical Properties (2.1 Physicochemical Profile, 2.2 Drug-Likeness Assessment, 2.3 Solubility & Permeability, 2.4 Salt Forms & Polymorphs, 2.5 Structure Visualization)
4. Mechanism & Targets (3.1 Primary Mechanism of Action, 3.2 Primary Targets, 3.3 Target Selectivity & Off-Targets, 3.4 Bioactivity Profile)
5. ADMET Properties (4.1 Absorption, 4.2 Distribution, 4.3 Metabolism, 4.4 Excretion, 4.5 Toxicity Predictions)
6. Clinical Development (5.1 Development Status, 5.2 Clinical Trial Landscape, 5.3 Approved Indications, 5.4 Investigational Indications, 5.5 Key Efficacy Data, 5.6 Biomarkers & Companion Diagnostics)
7. Safety Profile (6.1 Clinical Adverse Events, 6.2 Post-Marketing Safety (FAERS), 6.3 Black Box Warnings, 6.4 Contraindications, 6.5 Drug-Drug Interactions, 6.5.2 Drug-Food Interactions, 6.6 Dose Modification Guidance, 6.7 Drug Combinations & Regimens)
8. Pharmacogenomics (7.1 Relevant Pharmacogenes, 7.2 Clinical Annotations, 7.3 Dosing Guidelines, 7.4 Actionable Variants)
9. Regulatory & Labeling (8.1 Approval Status, 8.2 Label Highlights, 8.3 Patents & Exclusivity, 8.4 Label Changes & Warnings, 8.5 Special Populations, 8.6 Regulatory Timeline & History)
10. Literature & Research Landscape (9.1 Publication Metrics, 9.2 Research Themes, 9.3 Recent Key Publications, 9.4 Real-World Evidence)
11. Conclusions & Assessment (10.1 Drug Profile Scorecard, 10.2 Key Strengths, 10.3 Key Concerns/Limitations, 10.4 Research Gaps, 10.5 Comparative Analysis)
12. Data Sources & Methodology (11.1 Primary Data Sources, 11.2 Tool Call Summary, 11.3 Quality Control Metrics)
