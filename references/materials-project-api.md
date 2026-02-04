# Materials Project API Reference

Reference for the [Materials Project](https://materialsproject.org/) API used by the ScienceClaw **materials** skill. The Materials Project provides computed properties for inorganic materials (structures, band gaps, density, etc.).

**Next-gen API (documentation & dashboard):** [https://next-gen.materialsproject.org/api](https://next-gen.materialsproject.org/api)

## Overview

- **What it is:** Open database of computed materials properties (DFT, etc.) for discovery and design.
- **Use cases:** Look up material by ID (e.g. `mp-149`), get formula, band gap, density, symmetry; build workflows with pymatgen or direct REST calls.
- **ScienceClaw skill:** `skills/materials/` — `materials_lookup.py` uses pymatgen’s `MPRester` with your API key.

## API Key

1. **Register:** Create an account at [Materials Project](https://materialsproject.org/).
2. **Get API key:** In your account, open the [API page](https://next-gen.materialsproject.org/api) (next-gen dashboard) or the legacy [API key page](https://legacy.materialsproject.org/api) and generate an API key.
3. **Use in ScienceClaw:**
   - **Environment:** `export MP_API_KEY=your_key`
   - **Config file:** `~/.scienceclaw/materials_config.json`:
     ```json
     { "api_key": "your_materials_project_api_key" }
     ```

The **materials** skill reads the key from `MP_API_KEY` or `~/.scienceclaw/materials_config.json`.

## API Versions

- **Next-gen API:** [https://next-gen.materialsproject.org/api](https://next-gen.materialsproject.org/api) — current docs and dashboard.
- **Legacy API:** Still supported by pymatgen’s `MPRester` for many lookups (e.g. by material ID).

## Typical Usage (ScienceClaw)

```bash
# From ScienceClaw repo root (set MP_API_KEY or config first)
python3 skills/materials/scripts/materials_lookup.py --mp-id mp-149
python3 skills/materials/scripts/materials_lookup.py --mp-id mp-149 --format json
```

## References

- [Materials Project](https://materialsproject.org/)
- [Next-gen API](https://next-gen.materialsproject.org/api)
- [pymatgen MPRester](https://pymatgen.org/pymatgen.ext.matproj.html)
