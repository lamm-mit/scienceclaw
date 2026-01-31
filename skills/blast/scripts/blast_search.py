#!/usr/bin/env python3
"""
BLAST Search Tool for ScienceClaw

Performs NCBI BLAST searches to find sequence homology.
Uses Biopython's NCBIWWW module for remote BLAST queries.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

try:
    from Bio.Blast import NCBIWWW, NCBIXML
    from Bio import SeqIO
except ImportError:
    print("Error: Biopython is required. Install with: pip install biopython")
    sys.exit(1)


def read_sequence(query: str) -> str:
    """Read sequence from string or FASTA file."""
    # Check if query is a file path
    if os.path.isfile(query):
        with open(query, 'r') as f:
            # Try to parse as FASTA
            for record in SeqIO.parse(f, "fasta"):
                return str(record.seq)
            # If not FASTA, read as plain text
            f.seek(0)
            return f.read().strip().replace('\n', '').replace(' ', '')
    else:
        # Assume it's a sequence string
        return query.strip().replace('\n', '').replace(' ', '')


def run_blast(
    query: str,
    program: str = "blastp",
    database: str = "nr",
    evalue: float = 10.0,
    max_hits: int = 10,
    email: str = None
) -> list:
    """
    Run NCBI BLAST search.

    Args:
        query: Sequence string or path to FASTA file
        program: BLAST program (blastn, blastp, blastx, tblastn, tblastx)
        database: Database to search
        evalue: E-value threshold
        max_hits: Maximum number of hits to return
        email: Email for NCBI (optional but recommended)

    Returns:
        List of hit dictionaries
    """
    sequence = read_sequence(query)

    if not sequence:
        raise ValueError("No sequence provided or found in file")

    # Validate sequence characters
    valid_protein = set("ACDEFGHIKLMNPQRSTVWXY*-")
    valid_nucleotide = set("ATCGURYMKSWHBVDN-")

    seq_upper = sequence.upper()

    if program in ["blastp", "tblastn"]:
        if not all(c in valid_protein for c in seq_upper):
            print("Warning: Sequence contains non-standard amino acid characters")
    elif program in ["blastn", "blastx", "tblastx"]:
        if not all(c in valid_nucleotide for c in seq_upper):
            print("Warning: Sequence contains non-standard nucleotide characters")

    print(f"Running {program} search against {database}...")
    print(f"Query length: {len(sequence)} residues")
    print(f"E-value threshold: {evalue}")
    print("")

    # Set email if provided
    if email:
        from Bio import Entrez
        Entrez.email = email
    elif os.environ.get("NCBI_EMAIL"):
        from Bio import Entrez
        Entrez.email = os.environ.get("NCBI_EMAIL")

    # Run BLAST
    start_time = time.time()

    try:
        result_handle = NCBIWWW.qblast(
            program=program,
            database=database,
            sequence=sequence,
            expect=evalue,
            hitlist_size=max_hits,
            format_type="XML"
        )
    except Exception as e:
        raise RuntimeError(f"BLAST search failed: {str(e)}")

    elapsed = time.time() - start_time
    print(f"Search completed in {elapsed:.1f} seconds")
    print("")

    # Parse results
    blast_records = NCBIXML.parse(result_handle)
    hits = []

    for record in blast_records:
        for alignment in record.alignments:
            for hsp in alignment.hsps:
                hit = {
                    "accession": alignment.accession,
                    "title": alignment.title,
                    "length": alignment.length,
                    "evalue": hsp.expect,
                    "score": hsp.score,
                    "bits": hsp.bits,
                    "identities": hsp.identities,
                    "positives": getattr(hsp, 'positives', hsp.identities),
                    "gaps": hsp.gaps,
                    "align_length": hsp.align_length,
                    "query_start": hsp.query_start,
                    "query_end": hsp.query_end,
                    "subject_start": hsp.sbjct_start,
                    "subject_end": hsp.sbjct_end,
                    "query_seq": hsp.query,
                    "match_seq": hsp.match,
                    "subject_seq": hsp.sbjct,
                    "percent_identity": round(100 * hsp.identities / hsp.align_length, 1),
                    "query_coverage": round(100 * (hsp.query_end - hsp.query_start + 1) / len(sequence), 1)
                }
                hits.append(hit)

                if len(hits) >= max_hits:
                    break
            if len(hits) >= max_hits:
                break
        if len(hits) >= max_hits:
            break

    return hits


def format_summary(hits: list) -> str:
    """Format hits as a summary table."""
    if not hits:
        return "No significant hits found."

    lines = []
    lines.append(f"Found {len(hits)} hits:\n")
    lines.append("-" * 100)
    lines.append(f"{'#':<3} {'Accession':<15} {'E-value':<12} {'Identity':<10} {'Coverage':<10} {'Description'}")
    lines.append("-" * 100)

    for i, hit in enumerate(hits, 1):
        # Truncate title
        title = hit['title']
        if '>' in title:
            title = title.split('>')[0]
        if len(title) > 50:
            title = title[:47] + "..."

        lines.append(
            f"{i:<3} {hit['accession']:<15} {hit['evalue']:<12.2e} "
            f"{hit['percent_identity']:<10.1f}% {hit['query_coverage']:<10.1f}% {title}"
        )

    lines.append("-" * 100)
    return "\n".join(lines)


def format_detailed(hits: list) -> str:
    """Format hits with alignment details."""
    if not hits:
        return "No significant hits found."

    lines = []
    lines.append(f"Found {len(hits)} hits:\n")

    for i, hit in enumerate(hits, 1):
        lines.append("=" * 80)
        lines.append(f"Hit #{i}: {hit['accession']}")
        lines.append(f"Title: {hit['title']}")
        lines.append(f"Length: {hit['length']}")
        lines.append("")
        lines.append(f"  E-value: {hit['evalue']:.2e}")
        lines.append(f"  Bit score: {hit['bits']:.1f}")
        lines.append(f"  Identity: {hit['identities']}/{hit['align_length']} ({hit['percent_identity']}%)")
        lines.append(f"  Positives: {hit['positives']}/{hit['align_length']}")
        lines.append(f"  Gaps: {hit['gaps']}/{hit['align_length']}")
        lines.append(f"  Query coverage: {hit['query_coverage']}%")
        lines.append("")
        lines.append(f"  Query range: {hit['query_start']}-{hit['query_end']}")
        lines.append(f"  Subject range: {hit['subject_start']}-{hit['subject_end']}")
        lines.append("")

        # Show alignment (truncated if too long)
        query_seq = hit['query_seq']
        match_seq = hit['match_seq']
        subject_seq = hit['subject_seq']

        # Display alignment in chunks
        chunk_size = 60
        for j in range(0, len(query_seq), chunk_size):
            q_chunk = query_seq[j:j+chunk_size]
            m_chunk = match_seq[j:j+chunk_size]
            s_chunk = subject_seq[j:j+chunk_size]

            pos = j + 1
            lines.append(f"  Query  {pos:>4}  {q_chunk}")
            lines.append(f"              {m_chunk}")
            lines.append(f"  Sbjct  {pos:>4}  {s_chunk}")
            lines.append("")

        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Search NCBI BLAST for sequence homology",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --query "MTEYKLVVVGAGGVGKSALTIQLIQ" --program blastp
  %(prog)s --query sequence.fasta --database swissprot
  %(prog)s --query "ATGCGATCG" --program blastn --evalue 0.001
        """
    )

    parser.add_argument(
        "--query", "-q",
        required=True,
        help="Sequence string or path to FASTA file"
    )
    parser.add_argument(
        "--program", "-p",
        default="blastp",
        choices=["blastn", "blastp", "blastx", "tblastn", "tblastx"],
        help="BLAST program to use (default: blastp)"
    )
    parser.add_argument(
        "--database", "-d",
        default="nr",
        help="Database to search (default: nr)"
    )
    parser.add_argument(
        "--evalue", "-e",
        type=float,
        default=10.0,
        help="E-value threshold (default: 10.0)"
    )
    parser.add_argument(
        "--max-hits", "-m",
        type=int,
        default=10,
        help="Maximum number of hits to return (default: 10)"
    )
    parser.add_argument(
        "--format", "-f",
        default="summary",
        choices=["summary", "detailed", "json"],
        help="Output format (default: summary)"
    )
    parser.add_argument(
        "--email",
        help="Email for NCBI (recommended for heavy usage)"
    )

    args = parser.parse_args()

    try:
        hits = run_blast(
            query=args.query,
            program=args.program,
            database=args.database,
            evalue=args.evalue,
            max_hits=args.max_hits,
            email=args.email
        )

        if args.format == "json":
            print(json.dumps(hits, indent=2))
        elif args.format == "detailed":
            print(format_detailed(hits))
        else:
            print(format_summary(hits))

    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
