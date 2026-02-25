# TileDB-VCF

Scalable genomic variant storage and retrieval using TileDB arrays. Handles population-scale VCF/BCF datasets with parallel queries and cloud storage support (S3, Azure Blob, GCS).

## Installation

```bash
# Preferred: conda (Python < 3.10 required for full feature set)
conda install -c conda-forge -c tiledb tiledb-vcf

# Docker (recommended for reproducibility)
docker pull tiledb/tiledb-vcf:latest

# pip (limited functionality)
pip install tiledb-vcf
```

## Core Operations

### Create a TileDB-VCF Dataset

```python
import tiledbvcf

# Create new dataset
ds = tiledbvcf.Dataset("path/to/my_variants.tdb", mode="w")
ds.create()
```

```bash
# CLI: Create dataset
tiledbvcf create --uri s3://my-bucket/variants/
```

### Ingest VCF/BCF Files

```python
# Python
ds = tiledbvcf.Dataset("path/to/my_variants.tdb", mode="w")
ds.ingest_samples(
    sample_uris=["sample1.vcf.gz", "sample2.bcf", "sample3.vcf.gz"],
    scratch_space_path="/tmp/tiledbvcf_scratch",  # Temp space for sorting
    contigs_prefix_mappings={"chr": ""}  # Strip 'chr' prefix if needed
)
```

```bash
# CLI: Ingest
tiledbvcf store \
    --uri s3://my-bucket/variants/ \
    --samples sample1.vcf.gz sample2.vcf.gz sample3.vcf.gz \
    --scratch-space /tmp/scratch

# Incremental: add more samples later
tiledbvcf store \
    --uri s3://my-bucket/variants/ \
    --samples new_sample.vcf.gz
```

### Query Variants

```python
# Read specific genomic regions
ds = tiledbvcf.Dataset("path/to/my_variants.tdb", mode="r")

# Query by region
df = ds.read(
    attrs=["sample_name", "contig", "pos_start", "pos_end",
           "alleles", "info_DP", "fmt_GT", "fmt_GQ"],
    regions=["chr1:1-100000", "chr7:117559590-117559600"]  # CFTR region
)

# Filter to specific samples
df = ds.read(
    attrs=["sample_name", "pos_start", "alleles", "fmt_GT"],
    regions=["chr17:7571720-7590868"],  # TP53
    samples=["SAMPLE_001", "SAMPLE_002", "SAMPLE_003"]
)

# Export to pandas DataFrame (automatic)
print(df.head())
print(f"Found {len(df)} variant records")
```

```bash
# CLI: Query to VCF
tiledbvcf export \
    --uri s3://my-bucket/variants/ \
    --regions chr1:1-100000 \
    --output-path results/
```

### Parallel Queries

```python
# TileDB-VCF automatically parallelizes across threads
import tiledbvcf

ds = tiledbvcf.Dataset("s3://my-bucket/variants/", mode="r")

# Large cohort query - parallelized internally
df = ds.read(
    attrs=["sample_name", "contig", "pos_start", "alleles", "fmt_GT", "fmt_AF"],
    regions=["chr1:1-248956422"],  # Whole chromosome 1
    samples=None  # All samples
)

# Control parallelism
cfg = tiledbvcf.ReadConfig(
    memory_budget_mb=4096,  # 4GB memory budget
    thread_task_size_mb=64  # Per-thread chunk size
)
df = ds.read(attrs=..., regions=..., config=cfg)
```

### Cloud Storage

```python
import tiledb
import tiledbvcf

# Configure S3 access
tiledb.Config({
    "vfs.s3.aws_access_key_id": "YOUR_KEY",
    "vfs.s3.aws_secret_access_key": "YOUR_SECRET",
    "vfs.s3.region": "us-east-1"
})

# Or use IAM roles (recommended for EC2/ECS)
# Just use s3:// URIs directly

ds = tiledbvcf.Dataset("s3://my-bucket/variants/cohort.tdb", mode="r")
df = ds.read(
    attrs=["sample_name", "pos_start", "alleles"],
    regions=["chr22:1-51304566"]
)
```

## Key Attributes Available

| Attribute | Type | Description |
|-----------|------|-------------|
| `sample_name` | str | Sample identifier |
| `contig` | str | Chromosome (chr1, etc.) |
| `pos_start` | int | Variant start position (1-based) |
| `pos_end` | int | Variant end position |
| `alleles` | list[str] | REF + ALT alleles |
| `id` | str | Variant ID (rsID) |
| `filters` | list[str] | FILTER field values |
| `qual` | float | Variant quality score |
| `fmt_GT` | str | Genotype (0/1, 1/1, etc.) |
| `fmt_GQ` | int | Genotype quality |
| `fmt_DP` | int | Read depth |
| `fmt_AF` | float | Allele frequency |
| `info_*` | varies | Any INFO field |
| `fmt_*` | varies | Any FORMAT field |

## Docker Workflow

```bash
# Pull and run
docker run -v /data:/data tiledb/tiledb-vcf:latest \
    tiledbvcf store \
    --uri /data/variants.tdb \
    --samples /data/cohort/*.vcf.gz

# Interactive Python
docker run -it -v /data:/data tiledb/tiledb-vcf:latest python3
>>> import tiledbvcf
>>> ds = tiledbvcf.Dataset("/data/variants.tdb", mode="r")
```

## Downstream Analysis Integration

```python
# With pandas
df = ds.read(attrs=["sample_name", "pos_start", "alleles", "fmt_AF"],
             regions=["chr7:117000000-118000000"])

# With Dask for distributed computation
import dask
ddf = ds.read_dask(attrs=..., regions=...)

# Export to Parquet for downstream tools
df.to_parquet("variants_chr7.parquet")

# Integration with GWAS tools
import pandas as pd
gwas_df = df.pivot_table(index="pos_start", columns="sample_name", values="fmt_GT")
```

## Performance Notes

- **Ingestion**: ~500 samples/hour on single machine; scale horizontally
- **Query**: Parallel across regions and samples; 10-100x faster than tabix on large cohorts
- **Storage**: ~3-5x compression vs gzipped VCF for typical germline data
- **Incremental**: Add new samples without reprocessing existing data
- **Cloud-native**: S3/Azure/GCS without downloading data

## Use Cases

- Population genomics cohorts (UK Biobank, gnomAD scale)
- Rare variant discovery across thousands of samples
- Variant annotation pipelines requiring fast region queries
- Multi-omics integration with genomic coordinates
