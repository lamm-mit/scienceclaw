# HEA Discovery Audit Artifacts

This directory contains the complete typed provenance and audit trail for the CategoryScienceClaw HEA fatigue-crack-growth investigation.

## Artifact Files

### Input Artifacts
- **01_art-b84dc4c5d57c616e_HEAFatigueDatabase.json**
  - Input: HEA fatigue database from Materials Cloud
  - Type: `HEAFatigueDatabase`
  - Content: 180+ composition, phase, and test records
  - Source: Materials Cloud HEA Fatigue Database (Chen et al. 2022)

### Model Artifacts
- **02_art-3fe62cab83f5ef43_RejectedThresholdOnlyFCGRModel.json**
  - Rejected model: Threshold-only ($M_0$) ranking
  - Type: `RejectedThresholdOnlyFCGRModel`
  - Why rejected: Cannot accommodate the contradiction (high threshold with high Paris slope)
  - Gate: Representational inadequacy gate

- **03_art-e47ce9cb1ead7a36_TwoAxisDamageToleranceMap.json**
  - Accepted model: Two-axis damage-tolerance map ($M_1$)
  - Type: `TwoAxisDamageToleranceMap`
  - What's new: Separates threshold resistance ($\Delta K_{th}$) from post-threshold stability ($m$)
  - Gate: Passes because resolves design contradiction

### Claim Artifacts
- **04_art-8698e59abc356fac_HEAFatigueScienceClaim.json**
  - Final scientific claim output by the system
  - Type: `HEAFatigueScienceClaim`
  - Content: The prospective design principle
  - Prediction: FCC+BCC materials with elevated threshold and elevated Paris slope require mechanical validation

## Audit Artifacts

### Discovery Graphs
- **categorical_discovery_graph.json**
  - Full typed provenance DAG
  - Nodes: HEA database → threshold values → Paris slopes → phase typing → gate decision → accepted model → claim
  - Edges: Show data flow and artifact relationships
  - Properties: content hashes, parent lineage, type information

- **HEA_FCGR_DISCOVERY_TEST.json**
  - Discovery test specification and results
  - Tests: Threshold comparison, Paris slope comparison, phase-stratified statistics
  - Results: FCC+BCC shows contradiction (favorable threshold, unfavorable slope)
  - Validation: Against all 180+ records in database

### Investigation Results
- **INVESTIGATION_RESULTS.md**
  - Plain-language summary of the investigation
  - Methods used for analysis
  - Key findings with statistics
  - Reproducibility notes

## What These Artifacts Show

1. **Typed State**: Every artifact has a type (Database, Model, Claim, etc.)
2. **Provenance**: Each artifact records its parents and how it was created
3. **Rejection**: The rejected model ($M_0$) remains as a first-class audit object
4. **Gate Records**: The decision process is documented in categorical_discovery_graph.json
5. **Residual Content**: The new risk class (high-threshold/high-slope materials) is the residual not captured by $M_0$

## Data Flow

```
HEAFatigueDatabase
    ↓
    ├→ Extract Threshold Values (ΔKth)
    ├→ Extract Paris Slopes (m)
    └→ Phase Classification (FCC, BCC, FCC+BCC)
    ↓
Stage 1: Threshold-Only Model (M₀)
    ↓
    └→ REJECTED: Cannot express Paris slope variation
    ↓
Stage 2: Two-Axis Model (M₁)
    ↓
    ├→ Passes gate: Resolves design contradiction
    ├→ New content: Risk stratification by (ΔKth, m)
    └→ HEAFatigueScienceClaim
```

## Reproducibility

All artifacts are:
- **Deterministic**: Same input → same artifact
- **Content-hashed**: Integrity verified by hash
- **Typed**: Schema-checked on load
- **Traceable**: Parent lineage documented

## Questions?

- What is $M_0$? The rejected threshold-only ranking model
- What is $M_1$? The accepted two-axis damage-tolerance model
- What's the contradiction? High threshold doesn't imply low Paris slope in FCC+BCC
- Why does this matter? Changes how HEA fatigue screening should be conducted
