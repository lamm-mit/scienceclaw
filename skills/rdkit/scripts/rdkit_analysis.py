#!/usr/bin/env python3
"""
Enhanced RDKit Analysis for Synthesis Planning
Full descriptor suite, functional group detection, complexity metrics, disconnection sites
"""

import argparse
import json
import sys
from typing import Dict, List

try:
    from rdkit import Chem
    from rdkit.Chem import Descriptors, Crippen, Lipinski, rdMolDescriptors
    from rdkit.Chem import AllChem
except ImportError:
    print("Error: RDKit is required. Install with: pip install rdkit", file=sys.stderr)
    sys.exit(1)


def full_descriptor_suite(smiles: str) -> Dict:
    """Calculate comprehensive molecular descriptors."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return {"error": "Invalid SMILES"}

    return {
        "smiles": smiles,
        "molecular_weight": round(Descriptors.MolWt(mol), 2),
        "logp": round(Descriptors.MolLogP(mol), 2),
        "tpsa": round(Descriptors.TPSA(mol), 2),
        "h_bond_donors": Descriptors.NumHDonors(mol),
        "h_bond_acceptors": Descriptors.NumHAcceptors(mol),
        "rotatable_bonds": Descriptors.NumRotatableBonds(mol),
        "ring_count": Descriptors.RingCount(mol),
        "aromatic_rings": Descriptors.NumAromaticRings(mol),
        "aliphatic_rings": Descriptors.NumAliphaticRings(mol),
        "heavy_atom_count": mol.GetNumHeavyAtoms(),
        "fraction_csp3": round(Descriptors.FractionCSP3(mol), 3),
        "num_stereocenters": len(Chem.FindMolChiralCenters(mol, includeUnassigned=True)),
    }


def identify_functional_groups(smiles: str) -> Dict:
    """Identify functional groups using SMARTS patterns."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return {"error": "Invalid SMILES"}

    # Common functional group SMARTS patterns
    patterns = {
        "alcohol": "[OX2H]",
        "phenol": "[OX2H][cX3]",
        "ketone": "[CX3](=O)[#6]",
        "aldehyde": "[CX3H1](=O)[#6]",
        "carboxylic_acid": "[CX3](=O)[OX2H1]",
        "ester": "[CX3](=O)[OX2][#6]",
        "amine": "[NX3;H2,H1;!$(NC=O)]",
        "amide": "[NX3][CX3](=[OX1])[#6]",
        "ether": "[OD2]([#6])[#6]",
        "alkene": "[CX3]=[CX3]",
        "alkyne": "[CX2]#[CX2]",
        "halide": "[F,Cl,Br,I]",
    }

    groups = {}
    for name, smarts in patterns.items():
        pattern = Chem.MolFromSmarts(smarts)
        if pattern:
            matches = mol.GetSubstructMatches(pattern)
            groups[name] = len(matches)

    return {
        "smiles": smiles,
        "functional_groups": groups,
        "total_groups": sum(groups.values())
    }


def calculate_complexity(smiles: str) -> Dict:
    """Calculate molecular complexity metrics."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return {"error": "Invalid SMILES"}

    # Bertz complexity
    try:
        bertz = rdMolDescriptors.BertzCT(mol)
    except:
        bertz = None

    # Synthetic accessibility score (1=easy, 10=difficult)
    try:
        from rdkit.Chem import RDConfig
        import os
        sys.path.append(os.path.join(RDConfig.RDContribDir, 'SA_Score'))
        import sascorer
        sa_score = sascorer.calculateScore(mol)
    except:
        sa_score = None

    return {
        "smiles": smiles,
        "bertz_complexity": round(bertz, 2) if bertz else None,
        "synthetic_accessibility": round(sa_score, 2) if sa_score else None,
        "num_rings": Descriptors.RingCount(mol),
        "num_stereocenters": len(Chem.FindMolChiralCenters(mol, includeUnassigned=True)),
    }


def find_disconnection_sites(smiles: str) -> Dict:
    """Identify strategic bonds for retrosynthetic disconnection."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return {"error": "Invalid SMILES"}

    disconnection_sites = []

    # Identify strategic bonds (non-ring, rotatable)
    for bond in mol.GetBonds():
        if not bond.IsInRing():
            begin_atom = bond.GetBeginAtom()
            end_atom = bond.GetEndAtom()

            # Strategic disconnections: C-C, C-O, C-N bonds
            if bond.GetBondType() == Chem.BondType.SINGLE:
                bond_type = f"{begin_atom.GetSymbol()}-{end_atom.GetSymbol()}"
                disconnection_sites.append({
                    "bond_idx": bond.GetIdx(),
                    "bond_type": bond_type,
                    "begin_atom": begin_atom.GetIdx(),
                    "end_atom": end_atom.GetIdx(),
                })

    return {
        "smiles": smiles,
        "num_disconnection_sites": len(disconnection_sites),
        "sites": disconnection_sites[:10]  # Limit to top 10
    }


def main():
    parser = argparse.ArgumentParser(
        description="Enhanced RDKit analysis for synthesis planning",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "command",
        choices=["descriptors", "functional_groups", "complexity", "disconnections", "full"],
        help="Analysis type"
    )
    parser.add_argument(
        "--smiles", "-s",
        required=True,
        help="Target molecule SMILES"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["summary", "json"],
        default="json",
        help="Output format"
    )

    args = parser.parse_args()

    if args.command == "descriptors":
        result = full_descriptor_suite(args.smiles)
    elif args.command == "functional_groups":
        result = identify_functional_groups(args.smiles)
    elif args.command == "complexity":
        result = calculate_complexity(args.smiles)
    elif args.command == "disconnections":
        result = find_disconnection_sites(args.smiles)
    elif args.command == "full":
        # Combine all analyses
        result = {
            "descriptors": full_descriptor_suite(args.smiles),
            "functional_groups": identify_functional_groups(args.smiles),
            "complexity": calculate_complexity(args.smiles),
            "disconnections": find_disconnection_sites(args.smiles),
        }

    if "error" in result:
        print(result["error"], file=sys.stderr)
        sys.exit(1)

    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        # Summary format
        for key, value in result.items():
            if isinstance(value, dict):
                print(f"\n{key}:")
                for k, v in value.items():
                    print(f"  {k}: {v}")
            else:
                print(f"{key}: {value}")


if __name__ == "__main__":
    main()
