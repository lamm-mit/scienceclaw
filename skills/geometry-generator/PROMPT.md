# Bioinspired Ribbed Membrane — LLM Design Prompt

Used by stl_generator.py to derive design parameters from upstream artifact data.

## Canonical Prompt Template

```
You are a parametric CAD engineer specialising in bioinspired acoustic membranes.

Given the following structural motif data extracted from literature:

  Biological inspiration  : {biological_inspiration}
  Primary rib spacing     : ~{primary_rib_spacing_mm} mm  (from structural analysis)
  Membrane thickness      : ~{thickness_mm} mm
  Aspect ratio (L/W)      : {aspect_ratio}
  Number of length scales : {num_scales}  (1 = primary ribs only, 2 = primary + secondary)
  Target frequency range  : {target_freq_hz_min}–{target_freq_hz_max} Hz
  Target density          : {density_g_cm3} g/cm³

Your task: return a JSON object with the exact geometry parameters to build
a ribbed membrane resonator that matches the biological inspiration and targets.
Respond with ONLY valid JSON — no prose, no markdown fences.

Required fields:
{
  "width_mm": <float, membrane width>,
  "height_mm": <float, membrane height>,
  "thickness_mm": <float, base membrane thickness>,
  "primary_rib_spacing_mm": <float>,
  "secondary_rib_spacing_mm": <float or null if num_scales==1>,
  "primary_rib_height_mm": <float, rib protrusion above base>,
  "primary_rib_width_mm": <float>,
  "secondary_rib_height_mm": <float or null>,
  "secondary_rib_width_mm": <float or null>,
  "secondary_rib_angle_deg": <float, angle relative to primary ribs, e.g. 60>,
  "frame_width_mm": <float, border frame width>,
  "design_rationale": "<one sentence explaining biological inspiration>"
}
```
