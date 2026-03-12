#!/usr/bin/env python3
"""
molfeat - Molecular featurization

Compute molecular fingerprints and features from a SMILES string.

Usage:
    python molfeat_featurize.py --smiles "CC(=O)Oc1ccccc1C(=O)O"
    python molfeat_featurize.py -s "CCO" --format json
"""

import argparse
import json
import sys


def featurize(smiles: str) -> dict:
    try:
        import molfeat
        from molfeat.trans.fp import FPVecTransformer
    except ImportError:
        return {"error": "molfeat not installed", "smiles": smiles}

    try:
        from rdkit import Chem
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return {"error": f"Invalid SMILES: {smiles}"}
        canonical = Chem.MolToSmiles(mol)
    except Exception as e:
        return {"error": f"RDKit error: {e}", "smiles": smiles}

    result = {
        "smiles": smiles,
        "canonical_smiles": canonical,
        "skill": "molfeat",
        "molfeat_version": getattr(molfeat, "__version__", "unknown"),
    }

    # ECFP4 (Morgan r=2, 2048 bits)
    try:
        ecfp4 = FPVecTransformer(kind="ecfp:4", length=2048, n_jobs=1)
        fp = ecfp4([canonical])[0]
        result["ecfp4_n_bits"] = 2048
        result["ecfp4_set_bits"] = int(fp.sum())
        result["ecfp4_density"] = round(float(fp.mean()), 4)
    except Exception as e:
        result["ecfp4_error"] = str(e)

    # FCFP4
    try:
        fcfp4 = FPVecTransformer(kind="fcfp:4", length=2048, n_jobs=1)
        fp2 = fcfp4([canonical])[0]
        result["fcfp4_set_bits"] = int(fp2.sum())
    except Exception as e:
        result["fcfp4_error"] = str(e)

    # RDKit fingerprint
    try:
        rdkit_fp = FPVecTransformer(kind="rdkit", length=2048, n_jobs=1)
        fp3 = rdkit_fp([canonical])[0]
        result["rdkit_fp_set_bits"] = int(fp3.sum())
    except Exception as e:
        result["rdkit_fp_error"] = str(e)

    # MACCS keys (166 bits)
    try:
        maccs = FPVecTransformer(kind="maccs", n_jobs=1)
        fp4 = maccs([canonical])[0]
        result["maccs_set_bits"] = int(fp4.sum())
        result["maccs_n_bits"] = 166
    except Exception as e:
        result["maccs_error"] = str(e)

    return result


def main():
    parser = argparse.ArgumentParser(description="molfeat molecular featurization")
    parser.add_argument("--smiles", "-s", required=True, help="SMILES string to featurize")
    parser.add_argument("--format", "-f", default="json", choices=["json", "summary"],
                        help="Output format (default: json)")
    args = parser.parse_args()

    result = featurize(args.smiles)

    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        if "error" in result:
            print(f"Error: {result['error']}")
        else:
            print(f"SMILES: {result['smiles']}")
            print(f"Canonical: {result['canonical_smiles']}")
            print(f"ECFP4 set bits: {result.get('ecfp4_set_bits', 'n/a')} / {result.get('ecfp4_n_bits', 2048)}")
            print(f"FCFP4 set bits: {result.get('fcfp4_set_bits', 'n/a')}")
            print(f"MACCS set bits: {result.get('maccs_set_bits', 'n/a')} / {result.get('maccs_n_bits', 166)}")


if __name__ == "__main__":
    main()
