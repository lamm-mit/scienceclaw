#!/usr/bin/env python3
"""
RDKit cheminformatics for ScienceClaw: descriptors, SMARTS, substructure, MCS.
Requires: pip install rdkit
"""

import argparse
import json
import sys
from pathlib import Path

try:
    from rdkit import Chem
    from rdkit.Chem import Descriptors
    from rdkit.Chem import rdFMCS
except ImportError:
    print("Error: RDKit is required. Install with: pip install rdkit", file=sys.stderr)
    sys.exit(1)


def descriptors(smiles: str) -> dict:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return {"error": "Invalid SMILES"}
    return {
        "smiles": smiles,
        "MolWt": round(Descriptors.MolWt(mol), 2),
        "LogP": round(Descriptors.MolLogP(mol), 2),
        "TPSA": round(Descriptors.TPSA(mol), 2),
        "NumHDonors": Descriptors.NumHDonors(mol),
        "NumHAcceptors": Descriptors.NumHAcceptors(mol),
        "NumRotatableBonds": Descriptors.NumRotatableBonds(mol),
        "RingCount": Descriptors.RingCount(mol),
    }


def smarts_match(smiles: str, pattern: str) -> dict:
    mol = Chem.MolFromSmiles(smiles)
    pat = Chem.MolFromSmarts(pattern)
    if mol is None:
        return {"error": "Invalid SMILES"}
    if pat is None:
        return {"error": "Invalid SMARTS pattern"}
    matches = mol.GetSubstructMatches(pat)
    return {"smiles": smiles, "pattern": pattern, "matches": len(matches), "match": len(matches) > 0}


def substructure(smiles: str, sub_smiles: str) -> dict:
    mol = Chem.MolFromSmiles(smiles)
    sub = Chem.MolFromSmiles(sub_smiles)
    if mol is None:
        return {"error": "Invalid SMILES (molecule)"}
    if sub is None:
        return {"error": "Invalid SMILES (substructure)"}
    has = mol.HasSubstructMatch(sub)
    return {"smiles": smiles, "substructure": sub_smiles, "has_substructure": has}


def mcs(smiles_list: list) -> dict:
    if len(smiles_list) < 2:
        return {"error": "Provide at least two SMILES"}
    mols = [Chem.MolFromSmiles(s) for s in smiles_list]
    if any(m is None for m in mols):
        return {"error": "Invalid SMILES in list"}
    result = rdFMCS.FindMCS(mols)
    return {
        "smiles": smiles_list,
        "mcs_smarts": result.smartsString if result else None,
        "num_atoms": result.numAtoms if result else 0,
    }


def main():
    parser = argparse.ArgumentParser(description="RDKit tools: descriptors, SMARTS, substructure, MCS")
    parser.add_argument("command", choices=["descriptors", "smarts", "substructure", "mcs"])
    parser.add_argument("--smiles", "-s", help="SMILES string")
    parser.add_argument("--pattern", "-p", help="SMARTS pattern (for smarts)")
    parser.add_argument("--sub", help="Substructure SMILES (for substructure)")
    parser.add_argument("--format", choices=["summary", "json"], default="summary")
    parser.add_argument("extra", nargs="*", help="Extra SMILES (for mcs: second molecule)")
    args = parser.parse_args()

    out = None
    if args.command == "descriptors":
        if not args.smiles:
            print("Error: --smiles required", file=sys.stderr)
            sys.exit(1)
        out = descriptors(args.smiles)
    elif args.command == "smarts":
        if not args.smiles or not args.pattern:
            print("Error: --smiles and --pattern required", file=sys.stderr)
            sys.exit(1)
        out = smarts_match(args.smiles, args.pattern)
    elif args.command == "substructure":
        if not args.smiles or not args.sub:
            print("Error: --smiles and --sub required", file=sys.stderr)
            sys.exit(1)
        out = substructure(args.smiles, args.sub)
    elif args.command == "mcs":
        smi = [args.smiles] if args.smiles else []
        smi.extend(args.extra)
        if len(smi) < 2:
            print("Error: provide two SMILES (--smiles and one extra, or two extra)", file=sys.stderr)
            sys.exit(1)
        out = mcs(smi)

    if "error" in out:
        print(out["error"], file=sys.stderr)
        sys.exit(1)

    if args.format == "json":
        print(json.dumps(out, indent=2))
        return

    # Summary
    for k, v in out.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
