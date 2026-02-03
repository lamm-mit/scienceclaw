#!/usr/bin/env python3
"""
TDC Binding Effect Prediction for ScienceClaw

Predicts binding-related effects (BBB, hERG, CYP3A4) using Therapeutics Data Commons
models from Hugging Face. Requires PyTDC and DeepPurpose.

Ref: https://huggingface.co/tdc/models
"""

import argparse
import json
import sys
from pathlib import Path

# Optional heavy deps
try:
    from tdc import tdc_hf_interface
except ImportError:
    tdc_hf_interface = None

TDC_MODELS = [
    "BBB_Martins-AttentiveFP",
    "BBB_Martins-CNN",
    "BBB_Martins-Morgan",
    "herg_karim-AttentiveFP",
    "herg_karim-CNN",
    "herg_karim-Morgan",
    "CYP3A4_Veith-AttentiveFP",
    "CYP3A4_Veith-CNN",
    "CYP3A4_Veith-Morgan",
]

MODEL_TASK = {
    "BBB_Martins": "BBB penetration",
    "herg_karim": "hERG blockade",
    "CYP3A4_Veith": "CYP3A4 inhibition",
}


def _task_for_model(name: str) -> str:
    for prefix, task in MODEL_TASK.items():
        if name.startswith(prefix):
            return task
    return "binding effect"


def _require_tdc():
    if tdc_hf_interface is not None:
        return True
    print("Error: TDC is not installed. Install with:")
    print("  pip install PyTDC DeepPurpose")
    print("  pip install 'dgl' 'torch'")
    print("See: https://huggingface.co/tdc/models")
    print("Or install optional deps from ScienceClaw requirements.")
    sys.exit(1)


def list_models():
    print("TDC binding-effect models (Hugging Face):")
    print("")
    for m in TDC_MODELS:
        task = _task_for_model(m)
        print(f"  {m:<30}  {task}")
    print("")
    print("Use: --model <name> with --smiles <SMILES>")


def predict(smiles_list: list, model_name: str, output_format: str = "summary") -> list:
    _require_tdc()
    if model_name not in TDC_MODELS:
        print(f"Error: unknown model '{model_name}'. Use --list-models to see options.")
        sys.exit(1)

    # Cache dir for downloaded weights (TDC appends model name to this path)
    cache_dir = Path.home() / ".scienceclaw" / "tdc_models"
    cache_dir.mkdir(parents=True, exist_ok=True)
    load_path = str(cache_dir)

    try:
        tdc_hf = tdc_hf_interface(model_name)
        dp_model = tdc_hf.load_deeppurpose(load_path)
        preds = tdc_hf.predict_deeppurpose(dp_model, smiles_list)
    except Exception as e:
        print(f"Error during prediction: {e}")
        sys.exit(1)

    task = _task_for_model(model_name)
    results = []
    if not isinstance(preds, (list, tuple)):
        preds = [preds]
    for i, smi in enumerate(smiles_list):
        pred = preds[i] if i < len(preds) else preds[0]
        try:
            val = int(float(pred))
        except (TypeError, ValueError):
            val = pred
        results.append({
            "smiles": smi,
            "model": model_name,
            "task": task,
            "prediction": val,
            "label": "yes" if val == 1 else "no",
        })
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Predict binding-related effects (BBB, hERG, CYP3A4) using TDC models from Hugging Face."
    )
    parser.add_argument("--smiles", "-s", help="Single SMILES string")
    parser.add_argument("--smiles-file", "-f", help="File with one SMILES per line")
    parser.add_argument(
        "--model", "-m",
        default="BBB_Martins-AttentiveFP",
        help="TDC model name (default: BBB_Martins-AttentiveFP). Use --list-models to see all.",
    )
    parser.add_argument("--list-models", action="store_true", help="List available models and exit")
    parser.add_argument("--format", choices=("summary", "json"), default="summary", help="Output format")
    args = parser.parse_args()

    if args.list_models:
        list_models()
        return

    smiles_list = []
    if args.smiles:
        smiles_list.append(args.smiles.strip())
    if args.smiles_file:
        path = Path(args.smiles_file)
        if not path.exists():
            print(f"Error: file not found: {path}")
            sys.exit(1)
        for line in path.read_text().splitlines():
            line = line.strip().split("#")[0].strip()
            if line:
                smiles_list.append(line)
    if not smiles_list:
        print("Error: provide --smiles or --smiles-file")
        parser.print_help()
        sys.exit(1)

    results = predict(smiles_list, args.model, args.format)

    if args.format == "json":
        print(json.dumps(results, indent=2))
        return

    # Summary
    task = _task_for_model(args.model)
    print(f"Model: {args.model}")
    print(f"Task:  {task}")
    print("")
    for r in results:
        print(f"  SMILES:   {r['smiles']}")
        print(f"  Prediction: {r['prediction']} ({r['label']})")
        print("")


if __name__ == "__main__":
    main()
