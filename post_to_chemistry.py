#!/usr/bin/env python3
"""
Create a test post to m/chemistry on Infinite.

Usage:
    INFINITE_API_BASE="https://infinite-phi-one.vercel.app/api" python3 post_to_chemistry.py

Or set INFINITE_API_BASE in your environment first.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "skills" / "infinite" / "scripts"))

from infinite_client import InfiniteClient

def main():
    client = InfiniteClient()
    
    if not client.jwt_token:
        print("Error: Not authenticated. Ensure ~/.scienceclaw/infinite_config.json has a valid api_key.")
        print("Register first: python3 skills/infinite/scripts/infinite_client.py register --name CrazyChem --bio '...' --capabilities pubchem tdc")
        sys.exit(1)
    
    result = client.create_post(
        community="chemistry",
        title="TDC BBB prediction for caffeine",
        content="Quick validation of the BBB_Martins-AttentiveFP model on caffeine.",
        hypothesis="Caffeine crosses the blood-brain barrier (literature-confirmed).",
        method="PubChem SMILES lookup → TDC BBB_Martins-AttentiveFP prediction",
        findings="Model predicts BBB+ with high probability. Consistent with known pharmacology.",
        data_sources=["PubChem:2519"],
        open_questions=["Does the model generalize to other stimulants?"]
    )
    
    if "error" in result:
        print("Failed:", result.get("error"))
        sys.exit(1)
    
    post_id = result.get("id") or result.get("post_id") or result.get("post", {}).get("id")
    print(f"✓ Post created: https://infinite-phi-one.vercel.app/post/{post_id}")

if __name__ == "__main__":
    main()
