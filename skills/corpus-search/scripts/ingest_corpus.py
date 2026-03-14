#!/usr/bin/env python3
"""
PDF Corpus Ingestion for ScienceClaw

Walks a critical minerals data directory for PDFs, extracts text,
chunks at ~600 tokens with 100-token overlap, and upserts to a
Pinecone index with metadata for semantic search.

Maintains an ingest manifest (SHA-256 hashes) for incremental updates.
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import pdfplumber
except ImportError:
    print("Error: pdfplumber is required. Install with: pip install pdfplumber>=0.9.0", file=sys.stderr)
    sys.exit(1)

try:
    from pinecone import Pinecone
except ImportError:
    print("Error: pinecone is required. Install with: pip install pinecone>=5.0.0", file=sys.stderr)
    sys.exit(1)


# Commodity detection keywords (reused from OSTI skill pattern)
COMMODITY_KEYWORDS = {
    "rare_earth": [
        "rare earth", "REE", "HREE", "LREE", "lanthanide",
        "neodymium", "dysprosium", "terbium", "europium", "yttrium",
        "lanthanum", "cerium", "praseodymium", "samarium", "gadolinium",
    ],
    "lithium": ["lithium", "Li-ion", "spodumene", "brine"],
    "cobalt": ["cobalt"],
    "nickel": ["nickel", "laterite"],
    "copper": ["copper"],
    "gallium": ["gallium"],
    "graphite": ["graphite"],
    "germanium": ["germanium"],
    "manganese": ["manganese"],
    "platinum_group": ["platinum", "palladium", "rhodium", "PGM", "PGE"],
    "tungsten": ["tungsten", "wolframite", "scheelite"],
    "vanadium": ["vanadium"],
    "titanium": ["titanium", "ilmenite", "rutile"],
    "chromium": ["chromium", "chromite"],
    "antimony": ["antimony"],
    "barite": ["barite", "barium"],
    "beryllium": ["beryllium"],
    "bismuth": ["bismuth"],
    "niobium": ["niobium", "columbite"],
    "tantalum": ["tantalum", "coltan"],
    "tellurium": ["tellurium"],
    "indium": ["indium"],
    "zirconium": ["zirconium", "zircon"],
}

# Source organization aliases (directory name -> display name)
SOURCE_ORG_MAP = {
    "usgs": "USGS",
    "comtrade": "UN Comtrade",
    "worldbank": "World Bank",
    "world_bank": "World Bank",
    "sec": "SEC",
    "wto": "WTO",
    "mindat": "Mindat",
    "mincan": "MinCan",
    "doe": "DOE",
    "eia": "EIA",
    "iea": "IEA",
    "osti": "OSTI",
    "oecd": "OECD",
    "irena": "IRENA",
    "icmm": "ICMM",
    "unep": "UNEP",
    "climatewatch": "ClimateWatch",
    "energydata": "Energydata",
}

DEFAULT_INDEX = "scienceclaw-minerals-corpus"
DEFAULT_CORPUS_DIR = os.path.expanduser("~/critical-minerals-data")
MANIFEST_FILE = ".ingest_manifest.json"
CHUNK_TARGET_TOKENS = 600
CHUNK_OVERLAP_TOKENS = 100
UPSERT_BATCH_SIZE = 50
# Rough estimate: 1 token ~ 4 characters
CHARS_PER_TOKEN = 4


def sha256_file(filepath: str) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def detect_source_org(filepath: str, corpus_dir: str) -> str:
    """Auto-detect source organization from directory name."""
    rel = os.path.relpath(filepath, corpus_dir)
    parts = Path(rel).parts
    for part in parts:
        key = part.lower().replace("-", "_").replace(" ", "_")
        if key in SOURCE_ORG_MAP:
            return SOURCE_ORG_MAP[key]
    return "unknown"


def detect_commodity(text: str) -> str:
    """Auto-detect commodity from text content via keyword scan."""
    text_lower = text.lower()
    scores: Dict[str, int] = {}
    for commodity, keywords in COMMODITY_KEYWORDS.items():
        count = 0
        for kw in keywords:
            count += text_lower.count(kw.lower())
        if count > 0:
            scores[commodity] = count
    if not scores:
        return "general"
    return max(scores, key=scores.get)


def extract_pdf_text(filepath: str) -> List[Tuple[int, str]]:
    """
    Extract text from PDF using pdfplumber.

    Returns list of (page_number, text) tuples.
    """
    pages = []
    try:
        with pdfplumber.open(filepath) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                text = page.extract_text()
                if text and text.strip():
                    pages.append((i, text.strip()))
    except Exception as e:
        print(f"  Warning: Could not extract text from {filepath}: {e}", file=sys.stderr)
    return pages


def chunk_text(
    pages: List[Tuple[int, str]],
    target_tokens: int = CHUNK_TARGET_TOKENS,
    overlap_tokens: int = CHUNK_OVERLAP_TOKENS,
) -> List[Dict]:
    """
    Chunk page text at ~target_tokens with overlap, splitting on paragraph boundaries.

    Returns list of dicts with: text, page_number, chunk_index
    """
    target_chars = target_tokens * CHARS_PER_TOKEN
    overlap_chars = overlap_tokens * CHARS_PER_TOKEN
    chunks = []
    chunk_index = 0

    for page_num, page_text in pages:
        # Split into paragraphs (double newline or single newline with indent)
        paragraphs = re.split(r"\n\s*\n|\n(?=\s{2,})", page_text)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        current_chunk = ""
        for para in paragraphs:
            if len(current_chunk) + len(para) + 1 > target_chars and current_chunk:
                chunks.append({
                    "text": current_chunk.strip(),
                    "page_number": page_num,
                    "chunk_index": chunk_index,
                })
                chunk_index += 1
                # Overlap: keep the tail of the current chunk
                if overlap_chars > 0 and len(current_chunk) > overlap_chars:
                    current_chunk = current_chunk[-overlap_chars:]
                else:
                    current_chunk = ""

            if current_chunk:
                current_chunk += "\n\n" + para
            else:
                current_chunk = para

        # Flush remaining text from this page
        if current_chunk.strip():
            chunks.append({
                "text": current_chunk.strip(),
                "page_number": page_num,
                "chunk_index": chunk_index,
            })
            chunk_index += 1

    return chunks


def load_manifest(corpus_dir: str) -> Dict[str, str]:
    """Load ingest manifest (filepath -> SHA-256)."""
    manifest_path = os.path.join(corpus_dir, MANIFEST_FILE)
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def save_manifest(corpus_dir: str, manifest: Dict[str, str]):
    """Save ingest manifest."""
    manifest_path = os.path.join(corpus_dir, MANIFEST_FILE)
    os.makedirs(os.path.dirname(manifest_path) or ".", exist_ok=True)
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)


def find_pdfs(corpus_dir: str) -> List[str]:
    """Walk corpus directory and find all PDF files."""
    pdfs = []
    for root, dirs, files in os.walk(corpus_dir):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for filename in sorted(files):
            if filename.lower().endswith(".pdf"):
                pdfs.append(os.path.join(root, filename))
    return pdfs


def filter_files_to_ingest(
    pdfs: List[str],
    manifest: Dict[str, str],
    force: bool = False,
) -> List[str]:
    """Filter PDFs to only those that are new or changed."""
    if force:
        return pdfs

    to_ingest = []
    for filepath in pdfs:
        current_hash = sha256_file(filepath)
        if manifest.get(filepath) != current_hash:
            to_ingest.append(filepath)
    return to_ingest


def make_record_id(filepath: str, chunk_index: int, corpus_dir: str) -> str:
    """Create a deterministic record ID from filepath and chunk index."""
    rel = os.path.relpath(filepath, corpus_dir)
    # Replace path separators and spaces for a clean ID
    clean = re.sub(r"[^a-zA-Z0-9._-]", "_", rel)
    return f"{clean}_chunk{chunk_index}"


def ingest_file(
    filepath: str,
    corpus_dir: str,
    index,
    namespace: str = "",
    dry_run: bool = False,
) -> int:
    """
    Ingest a single PDF into Pinecone.

    Returns number of chunks upserted.
    """
    rel = os.path.relpath(filepath, corpus_dir)
    print(f"  Processing: {rel}", file=sys.stderr)

    # Extract text
    pages = extract_pdf_text(filepath)
    if not pages:
        print(f"    Skipped (no extractable text)", file=sys.stderr)
        return 0

    # Detect metadata
    source_org = detect_source_org(filepath, corpus_dir)
    full_text = " ".join(text for _, text in pages)
    commodity = detect_commodity(full_text)

    # Chunk
    chunks = chunk_text(pages)
    if not chunks:
        print(f"    Skipped (no chunks produced)", file=sys.stderr)
        return 0

    print(f"    {len(pages)} pages, {len(chunks)} chunks, source={source_org}, commodity={commodity}", file=sys.stderr)

    if dry_run:
        return len(chunks)

    # Build records and upsert in batches
    records = []
    for chunk in chunks:
        record_id = make_record_id(filepath, chunk["chunk_index"], corpus_dir)
        records.append({
            "_id": record_id,
            "text": chunk["text"],
            "source_file": rel,
            "source_org": source_org,
            "page_number": chunk["page_number"],
            "chunk_index": chunk["chunk_index"],
            "commodity": commodity,
            "file_type": "pdf",
        })

    # Upsert in batches with retry on rate limits
    for i in range(0, len(records), UPSERT_BATCH_SIZE):
        batch = records[i : i + UPSERT_BATCH_SIZE]
        batch_num = i // UPSERT_BATCH_SIZE + 1
        max_retries = 5
        for attempt in range(max_retries):
            try:
                index.upsert_records(namespace=namespace, records=batch)
                break
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    wait = 2 ** attempt * 15  # 15s, 30s, 60s, 120s, 240s
                    if attempt < max_retries - 1:
                        print(f"    Rate limited on batch {batch_num}, waiting {wait}s (attempt {attempt + 1}/{max_retries})", file=sys.stderr)
                        time.sleep(wait)
                    else:
                        print(f"    Failed batch {batch_num} after {max_retries} retries: {e}", file=sys.stderr)
                        return 0
                else:
                    print(f"    Error upserting batch {batch_num}: {e}", file=sys.stderr)
                    return 0
        # Brief pause between batches to be respectful
        if i + UPSERT_BATCH_SIZE < len(records):
            time.sleep(1.0)

    return len(records)


def main():
    parser = argparse.ArgumentParser(
        description="Ingest critical minerals PDFs into Pinecone for semantic search",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --corpus-dir ~/critical-minerals-data/ --dry-run
  %(prog)s --corpus-dir ~/critical-minerals-data/
  %(prog)s --corpus-dir ~/critical-minerals-data/ --force-reingest
        """,
    )
    parser.add_argument(
        "--corpus-dir",
        default=DEFAULT_CORPUS_DIR,
        help=f"Directory containing PDFs (default: {DEFAULT_CORPUS_DIR})",
    )
    parser.add_argument(
        "--index-name",
        default=DEFAULT_INDEX,
        help=f"Pinecone index name (default: {DEFAULT_INDEX})",
    )
    parser.add_argument(
        "--force-reingest",
        action="store_true",
        help="Re-ingest all files, ignoring manifest",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List files without ingesting",
    )
    parser.add_argument(
        "--namespace",
        default="__default__",
        help="Pinecone namespace (default: __default__)",
    )

    args = parser.parse_args()

    # Validate corpus directory
    if not os.path.isdir(args.corpus_dir):
        print(f"Error: Corpus directory not found: {args.corpus_dir}", file=sys.stderr)
        print("Create the directory and add PDF files to ingest.", file=sys.stderr)
        sys.exit(1)

    # Find PDFs
    all_pdfs = find_pdfs(args.corpus_dir)
    print(f"Found {len(all_pdfs)} PDF files in {args.corpus_dir}", file=sys.stderr)

    if not all_pdfs:
        print("No PDF files found. Nothing to do.", file=sys.stderr)
        sys.exit(0)

    # Filter by manifest (incremental)
    manifest = load_manifest(args.corpus_dir)
    to_ingest = filter_files_to_ingest(all_pdfs, manifest, force=args.force_reingest)
    print(f"{len(to_ingest)} files to process ({len(all_pdfs) - len(to_ingest)} already indexed)", file=sys.stderr)

    if not to_ingest:
        print("All files are up to date. Nothing to do.", file=sys.stderr)
        sys.exit(0)

    if args.dry_run:
        print("\n--- DRY RUN ---", file=sys.stderr)
        total_chunks = 0
        for filepath in to_ingest:
            rel = os.path.relpath(filepath, args.corpus_dir)
            source_org = detect_source_org(filepath, args.corpus_dir)
            pages = extract_pdf_text(filepath)
            chunks = chunk_text(pages) if pages else []
            commodity = detect_commodity(" ".join(t for _, t in pages)) if pages else "unknown"
            total_chunks += len(chunks)
            print(f"  {rel}: {len(pages)} pages, {len(chunks)} chunks, source={source_org}, commodity={commodity}", file=sys.stderr)
        print(f"\nTotal: {len(to_ingest)} files, {total_chunks} chunks would be ingested", file=sys.stderr)
        sys.exit(0)

    # Initialize Pinecone
    api_key = os.environ.get("PINECONE_API_KEY")
    if not api_key:
        print("Error: PINECONE_API_KEY environment variable is required", file=sys.stderr)
        sys.exit(1)

    pc = Pinecone(api_key=api_key)
    index = pc.Index(args.index_name)
    print(f"Connected to Pinecone index: {args.index_name}", file=sys.stderr)

    # Ingest files
    total_chunks = 0
    ingested_count = 0
    errors = []

    for filepath in to_ingest:
        n = ingest_file(
            filepath=filepath,
            corpus_dir=args.corpus_dir,
            index=index,
            namespace=args.namespace,
        )
        if n > 0:
            total_chunks += n
            ingested_count += 1
            # Update manifest with new hash
            manifest[filepath] = sha256_file(filepath)
        else:
            errors.append(filepath)

    # Save updated manifest
    save_manifest(args.corpus_dir, manifest)

    # Summary
    print(f"\nIngestion complete:", file=sys.stderr)
    print(f"  Files ingested: {ingested_count}/{len(to_ingest)}", file=sys.stderr)
    print(f"  Total chunks: {total_chunks}", file=sys.stderr)
    if errors:
        print(f"  Errors: {len(errors)} files failed", file=sys.stderr)
        for e in errors:
            print(f"    - {os.path.relpath(e, args.corpus_dir)}", file=sys.stderr)

    # Output summary as JSON to stdout
    print(json.dumps({
        "files_ingested": ingested_count,
        "files_total": len(to_ingest),
        "chunks_total": total_chunks,
        "errors": [os.path.relpath(e, args.corpus_dir) for e in errors],
        "index": args.index_name,
    }, indent=2))


if __name__ == "__main__":
    main()
