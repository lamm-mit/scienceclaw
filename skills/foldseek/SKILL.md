# Foldseek Structure Similarity Search

Ultra-fast protein structure similarity search. Finds structural homologs in PDB, AlphaFold Database, and custom databases orders of magnitude faster than DALI or TM-align.

## Installation

```bash
# Conda (recommended)
conda install -c conda-forge -c bioconda foldseek

# Binary download
wget https://mmseqs.com/foldseek/foldseek-linux-avx2.tar.gz
tar xvzf foldseek-linux-avx2.tar.gz
export PATH=$(pwd)/foldseek/bin:$PATH

# Docker
docker pull ghcr.io/steineggerlab/foldseek
```

## Download Databases

```bash
# PDB (experimentally determined structures, ~200K)
foldseek databases PDB pdb_db tmp/

# AlphaFold Database (200M+ predicted structures)
foldseek databases Alphafold/UniProt afdb_db tmp/

# AlphaFold SwissProt (high-confidence subset, ~500K)
foldseek databases Alphafold/UniProt50 afdb_swissprot tmp/

# ESMAtlas (300M+ structures from ESMFold)
foldseek databases ESMAtlas esmatlas_db tmp/
```

## Basic Search

```bash
# Search query structure against PDB
foldseek easy-search query.pdb pdb_db results.tsv tmp/ \
    --format-output "query,target,pident,alnlen,evalue,bits,prob,lddt,lddtfull,taxid,taxname,qlen,tlen,nident"

# Against AlphaFold database
foldseek easy-search query.pdb afdb_db results.tsv tmp/ \
    --exhaustive-search 1 \
    --format-output "query,target,pident,evalue,bits,prob,alntmscore,taxname"
```

## Python API

```python
import subprocess
import pandas as pd

def foldseek_search(query_pdb: str, database: str, tmp_dir: str = "tmp/",
                    e_value: float = 1e-3, max_hits: int = 100) -> pd.DataFrame:
    """Run Foldseek and return results as DataFrame."""
    out_tsv = "foldseek_results.tsv"

    cols = "query,target,pident,alnlen,evalue,bits,prob,alntmscore,taxname"
    cmd = [
        "foldseek", "easy-search",
        query_pdb, database, out_tsv, tmp_dir,
        "-e", str(e_value),
        "--max-seqs", str(max_hits),
        "--format-output", cols
    ]
    subprocess.run(cmd, check=True)

    df = pd.read_csv(out_tsv, sep="\t", names=cols.split(","))
    return df.sort_values("alntmscore", ascending=False)

# Usage
results = foldseek_search("designed_binder.pdb", "pdb_db")
print(results[["target", "pident", "alntmscore", "evalue", "taxname"]].head(20))
```

## Key Output Fields

| Field | Description | Threshold |
|-------|-------------|-----------|
| `alntmscore` | TM-score of alignment (0–1) | >0.5 = same fold |
| `pident` | Sequence identity (%) | varies |
| `prob` | Probability of homology (0–1) | >0.5 = likely homolog |
| `evalue` | E-value | <0.001 = significant |
| `lddt` | Local distance difference test | >0.7 = good local similarity |
| `taxname` | Source organism | — |

## Multi-Query / Batch Search

```bash
# Create query database from multiple PDB files
foldseek createdb query_structures/ query_db

# Search all vs. PDB
foldseek search query_db pdb_db result_db tmp/ -e 1e-3
foldseek convertalis query_db pdb_db result_db results.tsv \
    --format-output "query,target,alntmscore,evalue,taxname"
```

## Use Cases

### Check Design Novelty

```python
results = foldseek_search("new_design.pdb", "pdb_db")
top = results[results["alntmscore"] > 0.5]

if len(top) == 0:
    print("Novel fold — no PDB structural homologs found")
else:
    print(f"Similar to known structures:")
    print(top[["target", "alntmscore", "pident"]].head(5))
```

### Find Templates for Homology Modeling

```python
results = foldseek_search("target.pdb", "pdb_db", e_value=0.01)
templates = results[
    (results["alntmscore"] > 0.6) &
    (results["pident"] > 30)  # Enough sequence identity for modeling
]
```

### Cluster Designs by Structure

```bash
# All-vs-all structural comparison
foldseek createdb designs/ designs_db
foldseek search designs_db designs_db result_db tmp/ \
    --alignment-type 1 -e 1e-3
foldseek cluster designs_db cluster_db tmp/ \
    --min-seq-id 0 -c 0.8  # 80% TM-score threshold
```

## Foldseek vs TM-align vs DALI

| Tool | Speed (10K vs PDB) | Accuracy |
|------|-------------------|---------|
| Foldseek | **~1 min** | ~95% of TM-align |
| TM-align | ~20 hours | Reference |
| DALI | ~48 hours | Reference |
