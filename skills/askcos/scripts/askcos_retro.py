#!/usr/bin/env python3
"""
ASKCOS Retrosynthetic Analysis — Template Relevance (TorchServe)

Queries a locally deployed ASKCOS template_relevance TorchServe service.
Default base URL: http://localhost:9410

Deployment: https://gitlab.com/mlpds_mit/askcosv2/retro/template_relevance
Docs:       https://askcos-docs.mit.edu/guide/4-Deployment/4.2-Standalone-deployment-of-individual-modules.html

Environment variables:
  ASKCOS_BASE_URL   Base URL of TorchServe instance (default: http://localhost:9410)
  ASKCOS_MODEL      Template set to use (default: reaxys)
                    Available: reaxys, pistachio, pistachio_ringbreaker,
                               bkms_metabolic, reaxys_biocatalysis
"""

import argparse
import json
import os
import sys
from typing import Dict, List, Optional

try:
    import requests
except ImportError:
    print("Error: requests is required. Install with: pip install requests", file=sys.stderr)
    sys.exit(1)

ASKCOS_BASE = os.environ.get("ASKCOS_BASE_URL", "http://localhost:9410")
ASKCOS_MODEL = os.environ.get("ASKCOS_MODEL", "reaxys")
AVAILABLE_MODELS = ["reaxys", "pistachio", "pistachio_ringbreaker", "bkms_metabolic", "reaxys_biocatalysis"]
REQUEST_TIMEOUT = 60


def query_retrosynthesis(
    smiles: str,
    base_url: str = ASKCOS_BASE,
    model: str = ASKCOS_MODEL,
    top_n: int = 10,
) -> Dict:
    """
    POST to the TorchServe template_relevance endpoint and return
    structured retrosynthetic suggestions.

    Response from the server:
      [{"templates": [...], "reactants": [...], "scores": [...]}]

    Each entry in reactants is a SMILES string of precursor(s);
    scores are template match confidences (0–1).
    """
    url = f"{base_url}/predictions/{model}"
    try:
        resp = requests.post(
            url,
            json={"smiles": [smiles]},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
    except requests.exceptions.ConnectionError:
        return {
            "error": (
                f"Cannot connect to ASKCOS at {base_url}. "
                "Start the container: docker start retro_template_relevance"
            )
        }
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP {e.response.status_code}: {e.response.text[:300]}"}
    except Exception as e:
        return {"error": str(e)}

    raw = resp.json()
    if not raw or not isinstance(raw, list):
        return {"error": f"Unexpected response format: {str(raw)[:200]}"}

    entry = raw[0]
    templates = entry.get("templates", [])
    reactants = entry.get("reactants", [])
    scores = entry.get("scores", [])

    suggestions = []
    for i, (reactant, score) in enumerate(zip(reactants[:top_n], scores[:top_n])):
        tmpl = templates[i] if i < len(templates) else {}
        suggestions.append({
            "rank": i + 1,
            "reactants_smiles": reactant,
            "score": round(float(score), 6),
            "template_smarts": tmpl.get("reaction_smarts", ""),
            "template_id": tmpl.get("_id", ""),
            "template_count": tmpl.get("num_examples") or tmpl.get("count", 0),
            "necessary_reagent": tmpl.get("necessary_reagent", ""),
        })

    return {
        "target": smiles,
        "model": model,
        "total_templates_matched": len(reactants),
        "suggestions": suggestions,
        "status": "success",
    }


def _summarise(result: Dict, top_n: int = 5) -> str:
    if "error" in result:
        return f"ASKCOS error: {result['error']}"

    lines = [
        f"ASKCOS ({result['model']}) — {result['target']}",
        f"Templates matched: {result['total_templates_matched']}",
        "",
    ]
    for s in result["suggestions"][:top_n]:
        reagent = f"  reagent: {s['necessary_reagent']}" if s["necessary_reagent"] else ""
        lines.append(
            f"  #{s['rank']:2d}  score={s['score']:.4f}  "
            f"n={s['template_count']:5d}  precursors: {s['reactants_smiles']}"
            + reagent
        )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="ASKCOS retrosynthetic template relevance prediction",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Available models: {', '.join(AVAILABLE_MODELS)}

Examples:
  %(prog)s --smiles "CC(C)C1CCC(C)CC1O"
  %(prog)s --smiles "CC(C)C1CCC(C)CC1O" --model pistachio --top 20
  ASKCOS_BASE_URL=http://localhost:9410 %(prog)s --smiles "c1ccccc1" --format json
        """,
    )
    parser.add_argument("--smiles", "-s", required=True, help="Target molecule SMILES")
    parser.add_argument(
        "--model", "-m",
        default=ASKCOS_MODEL,
        choices=AVAILABLE_MODELS,
        help=f"Template set (default: {ASKCOS_MODEL})",
    )
    parser.add_argument("--top", "-n", type=int, default=10, help="Top N suggestions (default: 10)")
    parser.add_argument("--base-url", default=ASKCOS_BASE, help=f"TorchServe base URL (default: {ASKCOS_BASE})")
    parser.add_argument(
        "--format", "-f",
        choices=["summary", "json"],
        default="json",
        help="Output format (default: json)",
    )

    args = parser.parse_args()
    result = query_retrosynthesis(args.smiles, base_url=args.base_url, model=args.model, top_n=args.top)

    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        print(_summarise(result, top_n=args.top))


if __name__ == "__main__":
    main()
