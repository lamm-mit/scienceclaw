#!/usr/bin/env python3
"""
medchem - Single-molecule medicinal chemistry evaluation

Evaluate drug-likeness, structural alerts, and complexity for a SMILES string.

Usage:
    python medchem_evaluate.py --smiles "CC(=O)Oc1ccccc1C(=O)O"
    python medchem_evaluate.py -s "CCO" --format json
"""

import argparse
import json
import warnings
warnings.filterwarnings("ignore")


def evaluate(smiles: str) -> dict:
    try:
        import medchem as mc
        import datamol as dm
    except ImportError as e:
        return {"error": f"Missing dependency: {e}", "smiles": smiles}

    try:
        mol = dm.to_mol(smiles, sanitize=True)
        if mol is None:
            return {"error": f"Invalid SMILES: {smiles}"}
    except Exception as e:
        return {"error": f"Molecule parse error: {e}", "smiles": smiles}

    from rdkit import Chem
    canonical = Chem.MolToSmiles(mol)

    result = {
        "smiles": smiles,
        "canonical_smiles": canonical,
        "skill": "medchem",
        "medchem_version": getattr(mc, "__version__", "unknown"),
    }

    # Rule of 5
    try:
        rf = mc.rules.RuleFilters(rule_list=["rule_of_five"])
        ro5 = rf([mol])
        row = ro5.iloc[0].to_dict()
        result["passes_ro5"] = bool(row.get("rule_of_five", row.get("pass_all", False)))
        result["passes_ro5_all"] = bool(row.get("pass_all", False))
    except Exception as e:
        result["ro5_error"] = str(e)

    # Complexity — SMCM (synthetic complexity)
    try:
        from medchem.complexity import SMCM
        result["complexity_smcm"] = round(float(SMCM(mol)), 3)
    except Exception as e:
        result["complexity_error"] = str(e)

    # Complexity — Barone (structural complexity)
    try:
        from medchem.complexity import BaroneCT
        result["complexity_barone"] = int(BaroneCT(mol))
    except Exception as e:
        result["complexity_barone_error"] = str(e)

    # NIBR structural filters
    try:
        nibr = mc.structural.NIBRFilters()
        rn = nibr([mol])
        row_n = rn.iloc[0].to_dict()
        result["passes_nibr"] = bool(row_n.get("pass_filter", False))
        result["nibr_status"] = str(row_n.get("status", ""))
        result["nibr_reasons"] = str(row_n.get("reasons", "")) or None
        result["nibr_severity"] = int(row_n.get("severity", 0))
        result["n_covalent_motifs"] = int(row_n.get("n_covalent_motif", 0))
    except Exception as e:
        result["nibr_error"] = str(e)

    # Common structural alerts
    try:
        caf = mc.structural.CommonAlertsFilters()
        rc = caf([mol])
        row_c = rc.iloc[0].to_dict()
        result["passes_common_alerts"] = bool(row_c.get("pass_filter", False))
        result["common_alerts_status"] = str(row_c.get("status", ""))
        reasons = row_c.get("reasons")
        result["common_alert_reasons"] = (list(reasons) if hasattr(reasons, '__iter__') and not isinstance(reasons, str) else str(reasons)) if reasons is not None else None
    except Exception as e:
        result["common_alerts_error"] = str(e)

    # Overall drug-like assessment
    passes = []
    if "passes_ro5" in result:
        passes.append(result["passes_ro5"])
    if "passes_nibr" in result:
        passes.append(result["passes_nibr"])
    if "passes_common_alerts" in result:
        passes.append(result["passes_common_alerts"])
    result["drug_like"] = all(passes) if passes else None

    return result


def main():
    parser = argparse.ArgumentParser(description="medchem single-molecule evaluation")
    parser.add_argument("--smiles", "-s", required=True, help="SMILES string to evaluate")
    parser.add_argument("--format", "-f", default="json", choices=["json", "summary"],
                        help="Output format (default: json)")
    args = parser.parse_args()

    result = evaluate(args.smiles)

    if args.format == "json":
        print(json.dumps(result, indent=2, default=str))
    else:
        if "error" in result:
            print(f"Error: {result['error']}")
        else:
            print(f"SMILES        : {result['smiles']}")
            print(f"Passes Ro5    : {result.get('passes_ro5', 'n/a')}")
            print(f"Passes NIBR   : {result.get('passes_nibr', 'n/a')} ({result.get('nibr_status', '')})")
            print(f"Common alerts : passes={result.get('passes_common_alerts', 'n/a')}")
            print(f"Complexity    : SMCM={result.get('complexity_smcm', 'n/a')}  Barone={result.get('complexity_barone', 'n/a')}")
            print(f"Drug-like     : {result.get('drug_like', 'n/a')}")


if __name__ == "__main__":
    main()
