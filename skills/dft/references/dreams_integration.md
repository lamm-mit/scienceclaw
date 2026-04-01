# DREAMS Integration Reference

## Overview

[DREAMS](https://github.com/BattModels/material_agent) (paper: https://arxiv.org/pdf/2507.14267) is a hierarchical multi-agent DFT simulation framework. ScienceClaw's DFT skill delegates execution to DREAMS rather than generating raw Quantum Espresso input files directly.

## Integration Points

### Job Submission
- DREAMS handles input file generation (pw.x input from structure)
- ScienceClaw's `dft_submit.py` wraps this in a SLURM batch script
- The DREAMS command is configurable via `~/.scienceclaw/dft_config.json`

### Configuration (`~/.scienceclaw/dft_config.json`)
```json
{
  "dreams_command": "dreams-run",
  "qe_module": "quantum-espresso/7.2",
  "partition": "standard",
  "ntasks": 16,
  "walltime": "04:00:00",
  "dreams_config_path": "~/.dreams/config.yaml"
}
```

### Result Parsing
- DREAMS produces structured output that `dft_retrieve.py` can parse
- Fallback: direct QE output parsing for energy, forces, convergence

## TODO
- [ ] Import DREAMS Python API once package is installable
- [ ] Map DREAMS workflow types to ScienceClaw calc_type parameter
- [ ] Handle DREAMS multi-step workflows (relax → SCF → bands)
- [ ] Wire DREAMS result schema to ScienceClaw artifact format
