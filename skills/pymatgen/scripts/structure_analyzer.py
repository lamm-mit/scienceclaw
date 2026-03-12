#!/usr/bin/env python3
"""
Structure analysis tool using pymatgen.

Analyzes crystal structures and provides comprehensive information including:
- Composition and formula
- Space group and symmetry
- Lattice parameters
- Density
- Coordination environment
- Bond lengths and angles

Usage:
    python structure_analyzer.py structure_file [options]
    python structure_analyzer.py --query SiC [options]
    python structure_analyzer.py --formula SiC [options]
    python structure_analyzer.py --mp-id mp-7631 [options]

Examples:
    python structure_analyzer.py POSCAR
    python structure_analyzer.py structure.cif --symmetry --neighbors
    python structure_analyzer.py --query SiC --format json
    python structure_analyzer.py --mp-id mp-7631 --format json
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

try:
    from pymatgen.core import Structure
    from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
    from pymatgen.analysis.local_env import CrystalNN
except ImportError:
    print("Error: pymatgen is not installed. Install with: pip install pymatgen")
    sys.exit(1)


def _fetch_structure_from_mp(identifier: str) -> "Structure":
    """
    Fetch a pymatgen Structure from the Materials Project by MP ID or formula.
    Tries mp_api first, then pymatgen MPRester, then CIF download via requests.
    """
    import os as _os
    from pathlib import Path as _Path

    cfg = _Path.home() / ".scienceclaw" / "materials_config.json"
    api_key = _os.environ.get("MP_API_KEY")
    if not api_key and cfg.exists():
        try:
            api_key = json.loads(cfg.read_text()).get("api_key")
        except Exception:
            pass

    is_mp_id = bool(re.match(r'^mp-\d+$', identifier.strip(), re.IGNORECASE))

    # 1) Try next-gen mp_api client
    try:
        from mp_api.client import MPRester
        with MPRester(api_key) as mpr:
            if is_mp_id:
                docs = list(mpr.materials.summary.search(
                    material_ids=[identifier.strip()], fields=["material_id", "structure"]
                ))
            else:
                docs = list(mpr.materials.summary.search(
                    formula=identifier.strip(), fields=["material_id", "structure"]
                ))
            if docs:
                struct = getattr(docs[0], "structure", None)
                if struct is not None:
                    return struct
    except Exception:
        pass

    # 2) Try pymatgen legacy MPRester
    try:
        from pymatgen.ext.matproj import MPRester as _LegacyRester
        with _LegacyRester(api_key) as mpr:
            if is_mp_id:
                struct = mpr.get_structure_by_material_id(identifier.strip())
            else:
                results = mpr.get_structures(identifier.strip())
                struct = results[0] if results else None
            if struct is not None:
                return struct
    except Exception:
        pass

    # 3) Download CIF via REST and parse with pymatgen
    try:
        import requests
        import tempfile
        mp_id = identifier.strip()
        if not is_mp_id:
            # Resolve formula → mp_id via summary endpoint
            r = requests.get(
                "https://api.materialsproject.org/materials/summary/",
                params={"formula": mp_id, "_fields": "material_id", "_limit": 1},
                headers={"x-api-key": api_key or ""},
                timeout=20,
            )
            data = r.json().get("data", [])
            if data:
                mp_id = data[0].get("material_id", mp_id)
        cif_url = f"https://api.materialsproject.org/materials/{mp_id}/cif/"
        r = requests.get(cif_url, headers={"x-api-key": api_key or ""}, timeout=20)
        r.raise_for_status()
        with tempfile.NamedTemporaryFile(suffix=".cif", delete=False, mode="w") as tmp:
            tmp.write(r.text)
            tmp_path = tmp.name
        struct = Structure.from_file(tmp_path)
        import os as _os2; _os2.unlink(tmp_path)
        return struct
    except Exception as e:
        raise RuntimeError(
            f"Could not fetch structure for '{identifier}' from Materials Project: {e}\n"
            "Install mp-api (pip install mp-api) or provide a local structure file."
        )


def analyze_structure(struct: Structure, args) -> dict:
    """
    Perform comprehensive structure analysis.

    Args:
        struct: Pymatgen Structure object
        args: Command line arguments

    Returns:
        Dictionary containing analysis results
    """
    results = {}

    # Basic information
    print("\n" + "="*60)
    print("STRUCTURE ANALYSIS")
    print("="*60)

    print("\n--- COMPOSITION ---")
    print(f"Formula (reduced):    {struct.composition.reduced_formula}")
    print(f"Formula (full):       {struct.composition.formula}")
    print(f"Formula (Hill):       {struct.composition.hill_formula}")
    print(f"Chemical system:      {struct.composition.chemical_system}")
    print(f"Number of sites:      {len(struct)}")
    print(f"Number of species:    {len(struct.composition.elements)}")
    print(f"Molecular weight:     {struct.composition.weight:.2f} amu")

    results['composition'] = {
        'reduced_formula': struct.composition.reduced_formula,
        'formula': struct.composition.formula,
        'hill_formula': struct.composition.hill_formula,
        'chemical_system': struct.composition.chemical_system,
        'num_sites': len(struct),
        'molecular_weight': struct.composition.weight,
    }

    # Lattice information
    print("\n--- LATTICE ---")
    print(f"a = {struct.lattice.a:.4f} Å")
    print(f"b = {struct.lattice.b:.4f} Å")
    print(f"c = {struct.lattice.c:.4f} Å")
    print(f"α = {struct.lattice.alpha:.2f}°")
    print(f"β = {struct.lattice.beta:.2f}°")
    print(f"γ = {struct.lattice.gamma:.2f}°")
    print(f"Volume:               {struct.volume:.2f} ų")
    print(f"Density:              {struct.density:.3f} g/cm³")

    results['lattice'] = {
        'a': struct.lattice.a,
        'b': struct.lattice.b,
        'c': struct.lattice.c,
        'alpha': struct.lattice.alpha,
        'beta': struct.lattice.beta,
        'gamma': struct.lattice.gamma,
        'volume': struct.volume,
        'density': struct.density,
    }

    # Symmetry analysis
    if args.symmetry:
        print("\n--- SYMMETRY ---")
        try:
            sga = SpacegroupAnalyzer(struct)

            spacegroup_symbol = sga.get_space_group_symbol()
            spacegroup_number = sga.get_space_group_number()
            crystal_system = sga.get_crystal_system()
            point_group = sga.get_point_group_symbol()

            print(f"Space group:          {spacegroup_symbol} (#{spacegroup_number})")
            print(f"Crystal system:       {crystal_system}")
            print(f"Point group:          {point_group}")

            # Get symmetry operations
            symm_ops = sga.get_symmetry_operations()
            print(f"Symmetry operations:  {len(symm_ops)}")

            results['symmetry'] = {
                'spacegroup_symbol': spacegroup_symbol,
                'spacegroup_number': spacegroup_number,
                'crystal_system': crystal_system,
                'point_group': point_group,
                'num_symmetry_ops': len(symm_ops),
            }

            # Show equivalent sites
            sym_struct = sga.get_symmetrized_structure()
            print(f"Symmetry-equivalent site groups: {len(sym_struct.equivalent_sites)}")

        except Exception as e:
            print(f"Could not determine symmetry: {e}")

    # Site information
    print("\n--- SITES ---")
    print(f"{'Index':<6} {'Species':<10} {'Wyckoff':<10} {'Frac Coords':<30}")
    print("-" * 60)

    for i, site in enumerate(struct):
        coords_str = f"[{site.frac_coords[0]:.4f}, {site.frac_coords[1]:.4f}, {site.frac_coords[2]:.4f}]"
        wyckoff = "N/A"

        if args.symmetry:
            try:
                sga = SpacegroupAnalyzer(struct)
                sym_struct = sga.get_symmetrized_structure()
                wyckoff = sym_struct.equivalent_sites[0][0].species_string  # Simplified
            except:
                pass

        print(f"{i:<6} {site.species_string:<10} {wyckoff:<10} {coords_str:<30}")

    # Neighbor analysis
    if args.neighbors:
        print("\n--- COORDINATION ENVIRONMENT ---")
        try:
            cnn = CrystalNN()

            for i, site in enumerate(struct):
                neighbors = cnn.get_nn_info(struct, i)
                print(f"\nSite {i} ({site.species_string}):")
                print(f"  Coordination number: {len(neighbors)}")

                if len(neighbors) > 0 and len(neighbors) <= 12:
                    print(f"  Neighbors:")
                    for j, neighbor in enumerate(neighbors):
                        neighbor_site = struct[neighbor['site_index']]
                        distance = site.distance(neighbor_site)
                        print(f"    {neighbor_site.species_string} at {distance:.3f} Å")

        except Exception as e:
            print(f"Could not analyze coordination: {e}")

    # Distance matrix (for small structures)
    if args.distances and len(struct) <= 20:
        print("\n--- DISTANCE MATRIX (Å) ---")
        distance_matrix = struct.distance_matrix

        # Print header
        print(f"{'':>4}", end="")
        for i in range(len(struct)):
            print(f"{i:>8}", end="")
        print()

        # Print matrix
        for i in range(len(struct)):
            print(f"{i:>4}", end="")
            for j in range(len(struct)):
                if i == j:
                    print(f"{'---':>8}", end="")
                else:
                    print(f"{distance_matrix[i][j]:>8.3f}", end="")
            print()

    print("\n" + "="*60)

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Analyze crystal structures using pymatgen",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "structure_file",
        nargs="?",
        default=None,
        help="Structure file to analyze (CIF, POSCAR, etc.) — optional if --query/--formula/--mp-id given"
    )

    # Remote fetch via Materials Project
    parser.add_argument(
        "--query", "--search", "--term",
        dest="query", default="",
        help="Formula or MP ID to fetch from Materials Project (e.g. SiC, mp-7631)"
    )
    parser.add_argument(
        "--formula", "-f",
        dest="formula", default="",
        help="Chemical formula to fetch from Materials Project (e.g. SiC)"
    )
    parser.add_argument(
        "--mp-id", "-m",
        dest="mp_id", default="",
        help="Materials Project ID to fetch (e.g. mp-7631)"
    )
    parser.add_argument(
        "--format",
        choices=["json", "summary"],
        default="summary",
        help="Output format (json or summary text)"
    )

    parser.add_argument(
        "--symmetry", "-s",
        action="store_true",
        default=True,
        help="Perform symmetry analysis (default: on)"
    )

    parser.add_argument(
        "--neighbors", "-n",
        action="store_true",
        help="Analyze coordination environment"
    )

    parser.add_argument(
        "--distances", "-d",
        action="store_true",
        help="Show distance matrix (for structures with ≤20 atoms)"
    )

    parser.add_argument(
        "--export", "-e",
        choices=["json", "yaml"],
        help="Export analysis results to file"
    )

    parser.add_argument(
        "--output", "-o",
        help="Output file for exported results"
    )

    args = parser.parse_args()

    # Resolve identifier: --mp-id > --formula > --query > positional
    identifier = (args.mp_id or args.formula or args.query or "").strip()

    # Load structure
    if args.structure_file:
        try:
            struct = Structure.from_file(args.structure_file)
            identifier = identifier or args.structure_file
        except Exception as e:
            print(f"Error reading structure file: {e}", file=sys.stderr)
            sys.exit(1)
    elif identifier:
        try:
            struct = _fetch_structure_from_mp(identifier)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        parser.error("Provide a structure file or one of --query/--formula/--mp-id")

    # Analyze structure — suppress stdout prints in JSON mode so only JSON goes to stdout
    if args.format == "json":
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            results = analyze_structure(struct, args)
    else:
        results = analyze_structure(struct, args)
    results["query"] = identifier

    # --format json: print JSON to stdout (used by skill executor)
    if args.format == "json":
        print(json.dumps(results, indent=2, default=str))
        return

    # --export file
    if args.export:
        output_file = args.output or f"analysis.{args.export}"
        if args.export == "json":
            with open(output_file, "w") as f:
                json.dump(results, f, indent=2, default=str)
            print(f"\n✓ Analysis exported to {output_file}")
        elif args.export == "yaml":
            try:
                import yaml
                with open(output_file, "w") as f:
                    yaml.dump(results, f, default_flow_style=False)
                print(f"\n✓ Analysis exported to {output_file}")
            except ImportError:
                print("Error: PyYAML is not installed. Install with: pip install pyyaml")


if __name__ == "__main__":
    main()
