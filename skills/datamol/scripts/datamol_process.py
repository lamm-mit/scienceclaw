#!/usr/bin/env python3
"""
datamol - Molecular processing and property computation

Standardize a molecule and compute key physicochemical properties from a SMILES string.

Usage:
    python datamol_process.py --smiles "CC(=O)Oc1ccccc1C(=O)O"
    python datamol_process.py -s "CCO" --format json
"""

import argparse
import json
import sys


def process(smiles: str) -> dict:
    try:
        import datamol as dm
    except ImportError:
        return {"error": "datamol not installed", "smiles": smiles}

    try:
        mol = dm.to_mol(smiles, sanitize=True)
        if mol is None:
            return {"error": f"Invalid SMILES: {smiles}"}
    except Exception as e:
        return {"error": f"Molecule parse error: {e}", "smiles": smiles}

    result = {
        "smiles": smiles,
        "skill": "datamol",
        "datamol_version": getattr(dm, "__version__", "unknown"),
    }

    # Standardize
    try:
        std_mol = dm.standardize_mol(mol)
        result["canonical_smiles"] = dm.to_smiles(std_mol)
        result["standardized"] = True
    except Exception as e:
        result["canonical_smiles"] = dm.to_smiles(mol)
        result["standardize_error"] = str(e)

    # Core descriptors
    try:
        result["molecular_weight"] = round(dm.descriptors.mw(mol), 3)
    except Exception:
        pass
    try:
        result["clogp"] = round(dm.descriptors.clogp(mol), 3)
    except Exception:
        pass
    try:
        result["tpsa"] = round(dm.descriptors.tpsa(mol), 3)
    except Exception:
        pass
    try:
        result["n_hbd"] = dm.descriptors.n_hbd(mol)
    except Exception:
        pass
    try:
        result["n_hba"] = dm.descriptors.n_hba(mol)
    except Exception:
        pass
    try:
        result["n_rotatable_bonds"] = dm.descriptors.n_rotatable_bonds(mol)
    except Exception:
        pass
    try:
        result["n_aromatic_rings"] = dm.descriptors.n_aromatic_rings(mol)
    except Exception:
        pass
    try:
        result["n_stereo_centers"] = dm.descriptors.n_stereo_centers(mol)
    except Exception:
        pass
    try:
        result["n_rings"] = dm.descriptors.n_rings(mol)
    except Exception:
        pass

    # InChI
    try:
        result["inchi"] = dm.to_inchi(mol)
        result["inchikey"] = dm.to_inchikey(mol)
    except Exception:
        pass

    # SELFIES
    try:
        import selfies as sf
        result["selfies"] = sf.encoder(result.get("canonical_smiles", smiles))
    except Exception:
        pass

    return result


def main():
    parser = argparse.ArgumentParser(description="datamol molecular processing")
    parser.add_argument("--smiles", "-s", required=True, help="SMILES string to process")
    parser.add_argument("--format", "-f", default="json", choices=["json", "summary"],
                        help="Output format (default: json)")
    args = parser.parse_args()

    result = process(args.smiles)

    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        if "error" in result:
            print(f"Error: {result['error']}")
        else:
            print(f"SMILES        : {result['smiles']}")
            print(f"Canonical     : {result.get('canonical_smiles', 'n/a')}")
            print(f"MW            : {result.get('molecular_weight', 'n/a')}")
            print(f"cLogP         : {result.get('clogp', 'n/a')}")
            print(f"TPSA          : {result.get('tpsa', 'n/a')}")
            print(f"HBD / HBA     : {result.get('n_hbd', 'n/a')} / {result.get('n_hba', 'n/a')}")
            print(f"RotBonds      : {result.get('n_rotatable_bonds', 'n/a')}")
            print(f"AromaticRings : {result.get('n_aromatic_rings', 'n/a')}")


if __name__ == "__main__":
    main()
