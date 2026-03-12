#!/usr/bin/env python3
import argparse
import json
import math
import io
from typing import Dict, List, Tuple

try:
    import requests
except Exception as exc:  # pragma: no cover
    raise SystemExit("requests is required for structure-contact-analysis") from exc

try:
    from Bio.PDB import PDBParser
except Exception as exc:  # pragma: no cover
    raise SystemExit("biopython is required for structure-contact-analysis") from exc


PDB_SEARCH_API = "https://search.rcsb.org/rcsbsearch/v2/query"
PDB_FILE_URL = "https://files.rcsb.org/download/{pdb_id}.pdb"


AA3 = {
    "ALA": "A", "CYS": "C", "ASP": "D", "GLU": "E", "PHE": "F", "GLY": "G", "HIS": "H",
    "ILE": "I", "LYS": "K", "LEU": "L", "MET": "M", "ASN": "N", "PRO": "P", "GLN": "Q",
    "ARG": "R", "SER": "S", "THR": "T", "VAL": "V", "TRP": "W", "TYR": "Y",
}


def _rcsb_search(query: str, max_results: int = 5) -> List[str]:
    req = {
        "query": {
            "type": "terminal",
            "service": "full_text",
            "parameters": {"value": query},
        },
        "return_type": "entry",
        "request_options": {
            "paginate": {"start": 0, "rows": max_results},
            "results_content_type": ["experimental"],
            "sort": [{"sort_by": "score", "direction": "desc"}],
        },
    }
    r = requests.post(PDB_SEARCH_API, json=req, headers={"Content-Type": "application/json"}, timeout=30)
    r.raise_for_status()
    data = r.json() if r.text.strip() else {}
    return [hit["identifier"] for hit in data.get("result_set", []) if hit.get("identifier")]


def _download_pdb(pdb_id: str) -> str:
    url = PDB_FILE_URL.format(pdb_id=str(pdb_id).upper())
    r = requests.get(url, timeout=45)
    r.raise_for_status()
    if not r.text.strip():
        raise RuntimeError(f"Empty PDB download for {pdb_id}")
    return r.text


def _chain_sequence(chain) -> str:
    seq = []
    for res in chain.get_residues():
        if res.id[0].strip():
            continue
        aa = AA3.get(res.resname.upper())
        if aa:
            seq.append(aa)
    return "".join(seq)


def _chain_len(chain) -> int:
    n = 0
    for res in chain.get_residues():
        if res.id[0].strip():
            continue
        if res.resname.upper() in AA3:
            n += 1
    return n


def _min_dist(res_a, res_b) -> float:
    dmin = math.inf
    for a in res_a.get_atoms():
        for b in res_b.get_atoms():
            try:
                d = (a.coord - b.coord)
                dist = float((d[0] ** 2 + d[1] ** 2 + d[2] ** 2) ** 0.5)
            except Exception:
                continue
            if dist < dmin:
                dmin = dist
    return dmin


def _sample_atom_coords(chain, max_atoms: int = 250) -> List[tuple]:
    coords: List[tuple] = []
    for atom in chain.get_atoms():
        try:
            c = atom.coord
            coords.append((float(c[0]), float(c[1]), float(c[2])))
        except Exception:
            continue
        if len(coords) >= max_atoms:
            break
    return coords


def _min_chain_distance(chain_a, chain_b) -> float:
    a_coords = _sample_atom_coords(chain_a)
    b_coords = _sample_atom_coords(chain_b)
    if not a_coords or not b_coords:
        return math.inf
    dmin = math.inf
    for ax, ay, az in a_coords:
        for bx, by, bz in b_coords:
            dx = ax - bx
            dy = ay - by
            dz = az - bz
            d2 = dx * dx + dy * dy + dz * dz
            if d2 < dmin:
                dmin = d2
    return float(dmin ** 0.5) if dmin != math.inf else math.inf


def _pick_peptide_and_protein(structure) -> Tuple[str, str]:
    """
    Heuristic selection for peptide–protein contact analysis:
    - peptide chain: shortest polymer chain in [5, 60] residues
    - protein chain: chain (>=60 residues) that is *closest* to the peptide
      (helps avoid picking antibodies/nanobodies or symmetric copies)
    """
    candidates = []
    model = None
    for m in structure:
        model = m
        for chain in m:
            clen = _chain_len(chain)
            if clen <= 0:
                continue
            candidates.append((chain.id, clen))
        break
    if not candidates or model is None:
        return "", ""

    peptide_candidates = sorted(
        [c for c in candidates if 5 <= c[1] <= 60], key=lambda x: x[1]
    )
    if not peptide_candidates:
        # No peptide-like chain present; returning empty is better than
        # accidentally doing a self-contact analysis.
        return "", ""
    pep_id = peptide_candidates[0][0]

    protein_candidates = [c for c in candidates if c[0] != pep_id and c[1] >= 60]
    if not protein_candidates:
        # Fallback: pick the longest non-peptide chain, if any.
        others = [c for c in candidates if c[0] != pep_id]
        return (pep_id, (max(others, key=lambda x: x[1])[0] if others else ""))

    pep_chain = model[pep_id]
    best = None
    for chain_id, _clen in protein_candidates:
        d = _min_chain_distance(pep_chain, model[chain_id])
        if best is None or d < best[0]:
            best = (d, chain_id)
    return pep_id, (best[1] if best else protein_candidates[0][0])


def contact_hotspots_from_structure(structure, cutoff: float = 4.5) -> dict:
    model = next(structure.get_models())
    pep_chain_id, prot_chain_id = _pick_peptide_and_protein(structure)
    if not pep_chain_id or not prot_chain_id or pep_chain_id == prot_chain_id:
        return {
            "peptide_chain": pep_chain_id,
            "protein_chain": prot_chain_id,
            "peptide_sequence": "",
            "protein_length": 0,
            "cutoff_angstrom": cutoff,
            "per_position_contacts": [],
            "binding_hotspots": [],
            "hotspot_positions": [],
            "sequence": "",
            "protected_positions": [],
            "error": "no_peptide_protein_pair_found",
        }
    pep = model[pep_chain_id]
    prot = model[prot_chain_id]

    pep_seq = _chain_sequence(pep)
    prot_seq_len = _chain_len(prot)

    pep_res = [r for r in pep.get_residues() if not r.id[0].strip() and r.resname.upper() in AA3]
    prot_res = [r for r in prot.get_residues() if not r.id[0].strip() and r.resname.upper() in AA3]

    per_pos = []
    for i, rpep in enumerate(pep_res, start=1):
        contacts = 0
        interacting: List[str] = []
        for rprot in prot_res:
            d = _min_dist(rpep, rprot)
            if d <= cutoff:
                contacts += 1
                resno = rprot.id[1]
                interacting.append(f"{prot_chain_id}:{resno}{rprot.resname}")
        per_pos.append({
            "position": i,
            "aa": AA3.get(rpep.resname.upper(), "X"),
            "contacts": contacts,
            "interacting_protein_residues": interacting[:25],
        })

    top = sorted(per_pos, key=lambda x: (-x["contacts"], x["position"]))[:6]
    hotspot_positions = [t["position"] for t in top if t["contacts"] > 0]
    return {
        "peptide_chain": pep_chain_id,
        "protein_chain": prot_chain_id,
        "peptide_sequence": pep_seq,
        "protein_length": prot_seq_len,
        "cutoff_angstrom": cutoff,
        "per_position_contacts": per_pos,
        "binding_hotspots": top,
        "hotspot_positions": hotspot_positions,
        # convenience overlap keys
        "sequence": pep_seq,
        "protected_positions": hotspot_positions,
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Compute peptide–protein contact hotspots from PDB")
    p.add_argument("--query", "-q", default="", help="RCSB PDB full-text search query (used if --pdb-id not provided)")
    p.add_argument("--pdb-id", default="", help="PDB ID to download and analyze")
    p.add_argument("--pdb-path", default="", help="Local PDB file path (offline mode)")
    p.add_argument("--distance-cutoff", type=float, default=4.5, help="Contact cutoff in Å (default 4.5)")
    p.add_argument("--max-results", type=int, default=5, help="Max PDB hits to consider from query (default 5)")
    p.add_argument("--format", "-f", choices=["json", "summary"], default="json")
    p.add_argument("--describe-schema", action="store_true")
    args = p.parse_args()

    if args.describe_schema:
        print(json.dumps({"input_json_fields": []}))
        return

    pdb_text = ""
    chosen_id = args.pdb_id.strip().upper()
    if args.pdb_path:
        with open(args.pdb_path, "r", encoding="utf-8") as fh:
            pdb_text = fh.read()
        chosen_id = chosen_id or "LOCAL"
    else:
        if not chosen_id:
            q = (args.query or "").strip()
            if not q:
                raise SystemExit("Provide --pdb-id, --pdb-path, or --query")
            hits = _rcsb_search(q, max_results=max(1, min(20, int(args.max_results))))
            if not hits:
                print(json.dumps({"query": q, "error": "No PDB hits found", "total": 0}, indent=2))
                return
            chosen_id = hits[0].upper()
        pdb_text = _download_pdb(chosen_id)

    parser = PDBParser(QUIET=True)
    structure = parser.get_structure(chosen_id, io.StringIO(pdb_text))

    payload = {"pdb_id": chosen_id, "query": args.query.strip(), **contact_hotspots_from_structure(structure, cutoff=float(args.distance_cutoff))}
    if args.format == "summary":
        hs = payload.get("hotspot_positions", [])
        print(f"PDB {chosen_id}: peptide len={len(payload.get('peptide_sequence',''))} hotspots={hs}")
        for h in payload.get("binding_hotspots", [])[:6]:
            print(f"  - pos{h['position']} {h['aa']}: contacts={h['contacts']}")
        return
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
