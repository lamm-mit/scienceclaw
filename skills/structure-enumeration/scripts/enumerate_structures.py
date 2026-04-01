#!/usr/bin/env python3
"""Generate candidate crystal structures by element substitution.

Supports three sources for prototype structures:
1. Materials Project lookup (--prototypes with formulas or --mp-ids)
2. Local CIF/POSCAR files (--prototype-files)
3. Build from spacegroup + Wyckoff positions (--wyckoff, JSON format)

For each prototype, substitutes the metal site with target metals.
"""

import argparse
import json
import os
import sys
from pathlib import Path

DEFAULT_OUTPUT_DIR = Path.home() / ".scienceclaw" / "enumerated_structures"


def fetch_from_mp(formula: str):
    """Fetch a structure from Materials Project by formula."""
    from mp_api.client import MPRester
    api_key = os.environ.get("MP_API_KEY")
    if not api_key:
        print(f"Warning: MP_API_KEY not set, cannot fetch {formula}",
              file=sys.stderr)
        return None, None
    with MPRester(api_key) as mpr:
        docs = mpr.materials.summary.search(
            formula=formula,
            fields=["material_id", "structure", "formula_pretty"],
        )
        if not docs:
            print(f"Warning: '{formula}' not found in Materials Project, skipping",
                  file=sys.stderr)
            return None, None
        return docs[0].structure, docs[0].material_id


def fetch_by_mpid(mp_id: str):
    """Fetch a structure from Materials Project by ID."""
    from mp_api.client import MPRester
    api_key = os.environ.get("MP_API_KEY")
    if not api_key:
        return None, None
    with MPRester(api_key) as mpr:
        structure = mpr.get_structure_by_material_id(mp_id)
        return structure, mp_id


def build_from_wyckoff(spec: dict):
    """Build a structure from spacegroup + Wyckoff positions.

    spec format:
    {
        "name": "LaH10",
        "spacegroup": 225,
        "lattice": {"a": 5.1}  or  {"a": 5.1, "c": 8.0},
        "species": ["La", "H", "H"],
        "coords": [[0,0,0], [0.25,0.25,0.25], [0.118,0.118,0.118]]
    }
    """
    from pymatgen.core import Structure, Lattice

    sg = spec["spacegroup"]
    lat = spec["lattice"]
    if "c" in lat:
        lattice = Lattice.hexagonal(lat["a"], lat["c"])
    else:
        lattice = Lattice.cubic(lat["a"])

    structure = Structure.from_spacegroup(
        sg, lattice, spec["species"], spec["coords"]
    )
    return structure


def identify_metal_site(structure) -> str:
    """Identify the metal element (heaviest non-H element)."""
    elements = set(structure.composition.elements)
    non_h = [e for e in elements if e.symbol != "H"]
    if not non_h:
        return None
    return max(non_h, key=lambda e: e.atomic_mass).symbol


def substitute_metal(structure, original_metal: str, new_metal: str):
    """Replace one element with another."""
    from pymatgen.transformations.standard_transformations import (
        SubstitutionTransformation,
    )
    sub = SubstitutionTransformation({original_metal: new_metal})
    return sub.apply_transformation(structure)


def main():
    parser = argparse.ArgumentParser(
        description="Generate candidate structures by element substitution")
    parser.add_argument("--prototypes",
                        help="Comma-separated formulas to fetch from MP")
    parser.add_argument("--mp-ids",
                        help="Comma-separated MP IDs")
    parser.add_argument("--prototype-files",
                        help="Comma-separated paths to local CIF/POSCAR files")
    parser.add_argument("--wyckoff",
                        help='JSON array of Wyckoff specs: '
                             '[{"name":"LaH10","spacegroup":225,'
                             '"lattice":{"a":5.1},'
                             '"species":["La","H","H"],'
                             '"coords":[[0,0,0],[0.25,0.25,0.25],[0.118,0.118,0.118]]}]')
    parser.add_argument("--metals", required=True,
                        help="Comma-separated target metals")
    parser.add_argument("--output-dir", "-o",
                        default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--format", default="summary",
                        choices=["summary", "json"])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.prototypes and not args.mp_ids and not args.prototype_files and not args.wyckoff:
        print("Error: provide --prototypes, --mp-ids, --prototype-files, or --wyckoff",
              file=sys.stderr)
        sys.exit(1)

    metals = [m.strip() for m in args.metals.split(",") if m.strip()]
    output_dir = Path(args.output_dir)

    # Collect prototype structures: (structure, label, metal_element)
    prototypes = []

    # 1. From Materials Project formulas
    if args.prototypes:
        for formula in args.prototypes.split(","):
            formula = formula.strip()
            if not formula:
                continue
            print(f"Fetching {formula} from Materials Project...",
                  file=sys.stderr)
            try:
                structure, mp_id = fetch_from_mp(formula)
                if structure is None:
                    continue
                metal = identify_metal_site(structure)
                prototypes.append((structure, formula, metal))
                print(f"  Found {mp_id}: {structure.composition.reduced_formula}, "
                      f"metal={metal}, {len(structure)} atoms", file=sys.stderr)
            except Exception as e:
                print(f"  Warning: failed for {formula}: {e}", file=sys.stderr)

    # 2. From MP IDs
    if args.mp_ids:
        for mp_id in args.mp_ids.split(","):
            mp_id = mp_id.strip()
            if not mp_id:
                continue
            print(f"Fetching {mp_id}...", file=sys.stderr)
            try:
                structure, _ = fetch_by_mpid(mp_id)
                if structure is None:
                    continue
                metal = identify_metal_site(structure)
                formula = structure.composition.reduced_formula
                prototypes.append((structure, formula, metal))
                print(f"  Got {formula}, metal={metal}", file=sys.stderr)
            except Exception as e:
                print(f"  Warning: failed for {mp_id}: {e}", file=sys.stderr)

    # 3. From local files
    if args.prototype_files:
        from pymatgen.core import Structure
        for path_str in args.prototype_files.split(","):
            path = Path(path_str.strip())
            if not path.exists():
                print(f"  Warning: file not found: {path}", file=sys.stderr)
                continue
            structure = Structure.from_file(str(path))
            metal = identify_metal_site(structure)
            formula = structure.composition.reduced_formula
            prototypes.append((structure, formula, metal))
            print(f"  Loaded {path.name}: {formula}, metal={metal}",
                  file=sys.stderr)

    # 4. From Wyckoff specifications
    if args.wyckoff:
        try:
            wyckoff_specs = json.loads(args.wyckoff)
            if isinstance(wyckoff_specs, dict):
                wyckoff_specs = [wyckoff_specs]
            for spec in wyckoff_specs:
                name = spec.get("name", "unknown")
                print(f"Building {name} from Wyckoff positions "
                      f"(SG {spec['spacegroup']})...", file=sys.stderr)
                try:
                    structure = build_from_wyckoff(spec)
                    metal = identify_metal_site(structure)
                    prototypes.append((structure, name, metal))
                    print(f"  Built {structure.composition.reduced_formula}, "
                          f"metal={metal}, {len(structure)} atoms",
                          file=sys.stderr)
                except Exception as e:
                    print(f"  Warning: failed to build {name}: {e}",
                          file=sys.stderr)
        except json.JSONDecodeError as e:
            print(f"Warning: could not parse --wyckoff JSON: {e}",
                  file=sys.stderr)

    if not prototypes:
        output = {
            "status": "no_prototypes_found",
            "error": "No prototype structures could be loaded. "
                     "Try --wyckoff to build from spacegroup + Wyckoff positions, "
                     "or --prototype-files for local CIF files.",
        }
        print(json.dumps(output, indent=2))
        return

    # Generate substituted structures
    generated = []
    for structure, proto_label, original_metal in prototypes:
        for metal in metals:
            if metal == original_metal:
                continue

            new_formula_approx = proto_label.replace(original_metal, metal)
            label = f"{new_formula_approx}_from_{proto_label}"

            entry = {
                "label": label,
                "metal": metal,
                "prototype": proto_label,
                "original_metal": original_metal,
            }

            if not args.dry_run:
                try:
                    new_struct = substitute_metal(structure, original_metal, metal)
                    output_dir.mkdir(parents=True, exist_ok=True)
                    cif_path = output_dir / f"{label}.cif"
                    new_struct.to(str(cif_path), fmt="cif")
                    entry["formula"] = new_struct.composition.reduced_formula
                    entry["n_atoms"] = len(new_struct)
                    entry["cif_path"] = str(cif_path)
                except Exception as e:
                    entry["error"] = str(e)
                    print(f"  Warning: substitution failed for {label}: {e}",
                          file=sys.stderr)
            else:
                entry["formula"] = new_formula_approx
                entry["cif_path"] = str(output_dir / f"{label}.cif")

            generated.append(entry)

    # Also save original prototypes
    if not args.dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)
        for structure, proto_label, metal in prototypes:
            cif_path = output_dir / f"{proto_label}_prototype.cif"
            structure.to(str(cif_path), fmt="cif")

    output = {
        "status": "success" if not args.dry_run else "dry_run",
        "output_dir": str(output_dir),
        "prototypes_used": [pl for _, pl, _ in prototypes],
        "metals": metals,
        "total_generated": len(generated),
        "structures": generated,
    }

    if args.format == "json":
        print(json.dumps(output, indent=2))
    else:
        print(f"{'DRY RUN: ' if args.dry_run else ''}Generated "
              f"{len(generated)} structures from "
              f"{len(prototypes)} prototype(s)")
        print(f"  Prototypes: {', '.join(pl for _, pl, _ in prototypes)}")
        print(f"  Metals: {', '.join(metals)}")
        if not args.dry_run:
            print(f"  Output: {output_dir}/")
        for g in generated:
            err = f" [ERROR: {g['error']}]" if "error" in g else ""
            print(f"  {g['label']:<35s} {g.get('formula', '?'):<12s}"
                  f" {g.get('n_atoms', '?'):>4} atoms{err}")


if __name__ == "__main__":
    main()
