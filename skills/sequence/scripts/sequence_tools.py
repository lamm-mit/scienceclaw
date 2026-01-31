#!/usr/bin/env python3
"""
Sequence Analysis Tools for ScienceClaw

Provides sequence analysis capabilities using Biopython:
- Translation
- Statistics
- Reverse complement
- File parsing
- ORF finding
- Motif searching
"""

import argparse
import json
import os
import re
import sys
from typing import List, Dict, Optional, Tuple

try:
    from Bio import SeqIO
    from Bio.Seq import Seq
    from Bio.SeqUtils import gc_fraction, molecular_weight
    from Bio.SeqUtils.ProtParam import ProteinAnalysis
    from Bio.Data import CodonTable
except ImportError:
    print("Error: Biopython is required. Install with: pip install biopython")
    sys.exit(1)


def read_sequence(input_str: str) -> Tuple[str, str]:
    """
    Read sequence from string or file.

    Returns:
        Tuple of (sequence, sequence_id)
    """
    if os.path.isfile(input_str):
        # Try to parse as sequence file
        for fmt in ["fasta", "genbank", "embl"]:
            try:
                with open(input_str, 'r') as f:
                    for record in SeqIO.parse(f, fmt):
                        return str(record.seq), record.id
            except Exception:
                continue

        # Read as plain text
        with open(input_str, 'r') as f:
            seq = f.read().strip()
            # Remove FASTA header if present
            if seq.startswith(">"):
                lines = seq.split("\n")
                seq = "".join(lines[1:])
            return seq.replace("\n", "").replace(" ", ""), "sequence"
    else:
        return input_str.strip().replace("\n", "").replace(" ", "").upper(), "sequence"


def detect_sequence_type(sequence: str) -> str:
    """Detect if sequence is DNA, RNA, or protein."""
    seq_upper = sequence.upper()

    # Check for RNA
    if "U" in seq_upper and "T" not in seq_upper:
        return "rna"

    # Check for DNA
    dna_chars = set("ATCGN")
    if all(c in dna_chars for c in seq_upper):
        return "dna"

    # Check if mostly nucleotide with some ambiguity codes
    nucleotide_chars = set("ATCGUNRYWSKMBDHV")
    non_nuc = sum(1 for c in seq_upper if c not in nucleotide_chars)
    if non_nuc / len(seq_upper) < 0.1:
        return "dna"

    return "protein"


def translate_sequence(
    sequence: str,
    table: int = 1,
    frame: int = 1,
    all_frames: bool = False,
    to_stop: bool = False
) -> Dict:
    """
    Translate DNA/RNA to protein.

    Args:
        sequence: DNA/RNA sequence
        table: Codon table number
        frame: Reading frame (1-3 or -1 to -3)
        all_frames: Translate all 6 frames
        to_stop: Stop at first stop codon

    Returns:
        Dictionary with translation results
    """
    seq = Seq(sequence.upper())

    # Convert RNA to DNA
    if "U" in str(seq):
        seq = seq.back_transcribe()

    results = {}

    if all_frames:
        frames = [1, 2, 3, -1, -2, -3]
    else:
        frames = [frame]

    for f in frames:
        if f > 0:
            # Forward frame
            start = f - 1
            frame_seq = seq[start:]
        else:
            # Reverse frame
            rev_seq = seq.reverse_complement()
            start = abs(f) - 1
            frame_seq = rev_seq[start:]

        # Trim to multiple of 3
        frame_seq = frame_seq[:len(frame_seq) - (len(frame_seq) % 3)]

        try:
            if to_stop:
                protein = frame_seq.translate(table=table, to_stop=True)
            else:
                protein = frame_seq.translate(table=table)

            frame_name = f"frame_{f}" if f > 0 else f"frame_neg{abs(f)}"
            results[frame_name] = {
                "protein": str(protein),
                "length": len(protein),
                "start": start + 1,
                "dna_length": len(frame_seq)
            }
        except Exception as e:
            frame_name = f"frame_{f}" if f > 0 else f"frame_neg{abs(f)}"
            results[frame_name] = {"error": str(e)}

    return results


def compute_stats(sequence: str, seq_type: str = "auto") -> Dict:
    """
    Compute sequence statistics.

    Args:
        sequence: Sequence string
        seq_type: dna, rna, protein, or auto

    Returns:
        Dictionary with statistics
    """
    if seq_type == "auto":
        seq_type = detect_sequence_type(sequence)

    seq_upper = sequence.upper()
    stats = {
        "type": seq_type,
        "length": len(sequence)
    }

    if seq_type in ["dna", "rna"]:
        # Nucleotide statistics
        seq = Seq(seq_upper)

        # GC content
        stats["gc_content"] = round(gc_fraction(seq) * 100, 2)

        # Base composition
        composition = {}
        for base in "ATCGU":
            count = seq_upper.count(base)
            if count > 0:
                composition[base] = count
        stats["composition"] = composition

        # AT/GC ratio
        at = seq_upper.count("A") + seq_upper.count("T") + seq_upper.count("U")
        gc = seq_upper.count("G") + seq_upper.count("C")
        if gc > 0:
            stats["at_gc_ratio"] = round(at / gc, 3)

        # Molecular weight (approximate)
        try:
            if seq_type == "dna":
                mw = molecular_weight(seq, seq_type="DNA")
            else:
                mw = molecular_weight(seq, seq_type="RNA")
            stats["molecular_weight"] = round(mw, 2)
        except Exception:
            pass

    else:
        # Protein statistics
        try:
            # Remove stop codons for analysis
            clean_seq = seq_upper.replace("*", "")
            analysis = ProteinAnalysis(clean_seq)

            stats["molecular_weight"] = round(analysis.molecular_weight(), 2)
            stats["isoelectric_point"] = round(analysis.isoelectric_point(), 2)
            stats["instability_index"] = round(analysis.instability_index(), 2)
            stats["gravy"] = round(analysis.gravy(), 3)  # hydrophobicity

            # Amino acid composition
            aa_count = analysis.count_amino_acids()
            stats["composition"] = {aa: count for aa, count in aa_count.items() if count > 0}

            # Amino acid percentages
            aa_percent = analysis.get_amino_acids_percent()
            stats["composition_percent"] = {aa: round(pct * 100, 1)
                                            for aa, pct in aa_percent.items() if pct > 0.01}

        except Exception as e:
            stats["error"] = str(e)

    return stats


def reverse_complement(sequence: str) -> str:
    """Get reverse complement of DNA sequence."""
    seq = Seq(sequence.upper())
    return str(seq.reverse_complement())


def parse_file(
    filepath: str,
    file_format: str = "auto",
    output_format: str = "summary"
) -> List[Dict]:
    """
    Parse sequence file.

    Args:
        filepath: Path to sequence file
        file_format: fasta, genbank, embl, or auto
        output_format: summary, fasta, or json

    Returns:
        List of sequence records
    """
    if file_format == "auto":
        ext = os.path.splitext(filepath)[1].lower()
        format_map = {
            ".fa": "fasta",
            ".fasta": "fasta",
            ".fna": "fasta",
            ".faa": "fasta",
            ".gb": "genbank",
            ".gbk": "genbank",
            ".genbank": "genbank",
            ".embl": "embl"
        }
        file_format = format_map.get(ext, "fasta")

    records = []

    for record in SeqIO.parse(filepath, file_format):
        rec_data = {
            "id": record.id,
            "name": record.name,
            "description": record.description,
            "length": len(record.seq),
            "sequence": str(record.seq)
        }

        # Add annotations if available
        if record.annotations:
            rec_data["annotations"] = {k: str(v) for k, v in record.annotations.items()
                                       if isinstance(v, (str, int, float))}

        # Add features for GenBank
        if file_format == "genbank" and record.features:
            features = []
            for feat in record.features[:20]:  # Limit features
                features.append({
                    "type": feat.type,
                    "location": str(feat.location),
                    "qualifiers": {k: v[0] if len(v) == 1 else v
                                   for k, v in feat.qualifiers.items()}
                })
            rec_data["features"] = features

        records.append(rec_data)

    return records


def find_orfs(
    sequence: str,
    min_length: int = 30,
    table: int = 1
) -> List[Dict]:
    """
    Find Open Reading Frames.

    Args:
        sequence: DNA sequence
        min_length: Minimum ORF length in codons
        table: Codon table

    Returns:
        List of ORFs found
    """
    seq = Seq(sequence.upper())
    orfs = []

    # Get start and stop codons from table
    codon_table = CodonTable.unambiguous_dna_by_id[table]
    start_codons = codon_table.start_codons
    stop_codons = codon_table.stop_codons

    # Search both strands
    for strand, nuc_seq in [("+", seq), ("-", seq.reverse_complement())]:
        for frame in range(3):
            # Extract codons
            for i in range(frame, len(nuc_seq) - 2, 3):
                codon = str(nuc_seq[i:i+3])

                if codon in start_codons:
                    # Found start, look for stop
                    for j in range(i + 3, len(nuc_seq) - 2, 3):
                        stop_codon = str(nuc_seq[j:j+3])
                        if stop_codon in stop_codons:
                            orf_len = (j - i) // 3
                            if orf_len >= min_length:
                                orf_seq = nuc_seq[i:j+3]
                                protein = orf_seq.translate(table=table, to_stop=True)

                                if strand == "+":
                                    start_pos = i + 1
                                    end_pos = j + 3
                                else:
                                    start_pos = len(seq) - j - 2
                                    end_pos = len(seq) - i

                                orfs.append({
                                    "strand": strand,
                                    "frame": frame + 1,
                                    "start": start_pos,
                                    "end": end_pos,
                                    "length_codons": orf_len,
                                    "length_nt": len(orf_seq),
                                    "sequence": str(orf_seq),
                                    "protein": str(protein)
                                })
                            break

    # Sort by length
    orfs.sort(key=lambda x: x["length_codons"], reverse=True)

    return orfs


def search_motif(sequence: str, pattern: str) -> List[Dict]:
    """
    Search for motif/pattern in sequence.

    Args:
        sequence: Sequence to search
        pattern: Pattern (supports IUPAC codes)

    Returns:
        List of matches
    """
    # Convert IUPAC codes to regex
    iupac_dna = {
        "R": "[AG]",
        "Y": "[CT]",
        "S": "[GC]",
        "W": "[AT]",
        "K": "[GT]",
        "M": "[AC]",
        "B": "[CGT]",
        "D": "[AGT]",
        "H": "[ACT]",
        "V": "[ACG]",
        "N": "[ACGT]"
    }

    regex_pattern = pattern.upper()
    for code, replacement in iupac_dna.items():
        regex_pattern = regex_pattern.replace(code, replacement)

    matches = []
    seq_upper = sequence.upper()

    for match in re.finditer(regex_pattern, seq_upper):
        matches.append({
            "start": match.start() + 1,
            "end": match.end(),
            "sequence": match.group()
        })

    return matches


def format_translation_output(results: Dict) -> str:
    """Format translation results."""
    lines = []

    for frame, data in results.items():
        lines.append(f"\n{frame.replace('_', ' ').title()}:")
        lines.append("-" * 40)

        if "error" in data:
            lines.append(f"  Error: {data['error']}")
        else:
            lines.append(f"  DNA length: {data['dna_length']} bp")
            lines.append(f"  Protein length: {data['length']} aa")
            lines.append(f"  Protein sequence:")

            protein = data['protein']
            for i in range(0, len(protein), 60):
                lines.append(f"    {protein[i:i+60]}")

    return "\n".join(lines)


def format_stats_output(stats: Dict) -> str:
    """Format statistics output."""
    lines = []

    lines.append(f"Sequence Type: {stats['type'].upper()}")
    lines.append(f"Length: {stats['length']}")
    lines.append("")

    if stats['type'] in ['dna', 'rna']:
        lines.append(f"GC Content: {stats['gc_content']}%")
        if 'at_gc_ratio' in stats:
            lines.append(f"AT/GC Ratio: {stats['at_gc_ratio']}")
        if 'molecular_weight' in stats:
            lines.append(f"Molecular Weight: {stats['molecular_weight']:,.2f} Da")

        lines.append("\nBase Composition:")
        for base, count in sorted(stats['composition'].items()):
            pct = (count / stats['length']) * 100
            lines.append(f"  {base}: {count} ({pct:.1f}%)")

    else:
        if 'molecular_weight' in stats:
            lines.append(f"Molecular Weight: {stats['molecular_weight']:,.2f} Da")
        if 'isoelectric_point' in stats:
            lines.append(f"Isoelectric Point (pI): {stats['isoelectric_point']}")
        if 'instability_index' in stats:
            stable = "stable" if stats['instability_index'] < 40 else "unstable"
            lines.append(f"Instability Index: {stats['instability_index']} ({stable})")
        if 'gravy' in stats:
            lines.append(f"GRAVY (hydrophobicity): {stats['gravy']}")

        if 'composition_percent' in stats:
            lines.append("\nAmino Acid Composition (>1%):")
            for aa, pct in sorted(stats['composition_percent'].items(), key=lambda x: -x[1]):
                lines.append(f"  {aa}: {pct}%")

    return "\n".join(lines)


def format_orfs_output(orfs: List[Dict]) -> str:
    """Format ORF finding results."""
    if not orfs:
        return "No ORFs found meeting the minimum length requirement."

    lines = []
    lines.append(f"Found {len(orfs)} ORFs:\n")
    lines.append("-" * 80)

    for i, orf in enumerate(orfs[:20], 1):  # Limit output
        lines.append(f"\nORF #{i}:")
        lines.append(f"  Strand: {orf['strand']}, Frame: {orf['frame']}")
        lines.append(f"  Position: {orf['start']}-{orf['end']}")
        lines.append(f"  Length: {orf['length_codons']} codons ({orf['length_nt']} nt)")
        lines.append(f"  Protein ({len(orf['protein'])} aa):")

        protein = orf['protein']
        for j in range(0, min(len(protein), 120), 60):
            lines.append(f"    {protein[j:j+60]}")
        if len(protein) > 120:
            lines.append(f"    ... ({len(protein) - 120} more residues)")

    if len(orfs) > 20:
        lines.append(f"\n... and {len(orfs) - 20} more ORFs")

    return "\n".join(lines)


def format_motif_output(matches: List[Dict], pattern: str) -> str:
    """Format motif search results."""
    if not matches:
        return f"No matches found for pattern: {pattern}"

    lines = []
    lines.append(f"Found {len(matches)} matches for pattern '{pattern}':\n")

    for i, match in enumerate(matches[:50], 1):
        lines.append(f"  {i}. Position {match['start']}-{match['end']}: {match['sequence']}")

    if len(matches) > 50:
        lines.append(f"\n... and {len(matches) - 50} more matches")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Sequence analysis tools",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Translate command
    translate_parser = subparsers.add_parser("translate", help="Translate DNA to protein")
    translate_parser.add_argument("--sequence", "-s", required=True, help="DNA/RNA sequence or file")
    translate_parser.add_argument("--table", "-t", type=int, default=1, help="Codon table (default: 1)")
    translate_parser.add_argument("--frame", "-f", type=int, default=1, help="Reading frame (default: 1)")
    translate_parser.add_argument("--all-frames", "-a", action="store_true", help="Translate all 6 frames")
    translate_parser.add_argument("--to-stop", action="store_true", help="Stop at first stop codon")
    translate_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Compute sequence statistics")
    stats_parser.add_argument("--sequence", "-s", required=True, help="Sequence or file")
    stats_parser.add_argument("--type", "-t", default="auto", choices=["dna", "rna", "protein", "auto"])
    stats_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # Revcomp command
    revcomp_parser = subparsers.add_parser("revcomp", help="Reverse complement")
    revcomp_parser.add_argument("--sequence", "-s", required=True, help="DNA sequence or file")

    # Parse command
    parse_parser = subparsers.add_parser("parse", help="Parse sequence files")
    parse_parser.add_argument("--file", "-f", required=True, help="Input file")
    parse_parser.add_argument("--format", default="auto", choices=["fasta", "genbank", "embl", "auto"])
    parse_parser.add_argument("--output", "-o", default="summary", choices=["summary", "fasta", "json"])

    # ORFs command
    orfs_parser = subparsers.add_parser("orfs", help="Find Open Reading Frames")
    orfs_parser.add_argument("--sequence", "-s", help="DNA sequence")
    orfs_parser.add_argument("--file", "-f", help="DNA sequence file")
    orfs_parser.add_argument("--min-length", "-m", type=int, default=30, help="Minimum ORF length in codons")
    orfs_parser.add_argument("--table", "-t", type=int, default=1, help="Codon table")
    orfs_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # Motif command
    motif_parser = subparsers.add_parser("motif", help="Search for motifs")
    motif_parser.add_argument("--sequence", "-s", required=True, help="Sequence to search")
    motif_parser.add_argument("--pattern", "-p", required=True, help="Pattern to find")
    motif_parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        if args.command == "translate":
            seq, _ = read_sequence(args.sequence)
            results = translate_sequence(
                seq,
                table=args.table,
                frame=args.frame,
                all_frames=args.all_frames,
                to_stop=args.to_stop
            )
            if args.json:
                print(json.dumps(results, indent=2))
            else:
                print(format_translation_output(results))

        elif args.command == "stats":
            seq, _ = read_sequence(args.sequence)
            results = compute_stats(seq, args.type)
            if args.json:
                print(json.dumps(results, indent=2))
            else:
                print(format_stats_output(results))

        elif args.command == "revcomp":
            seq, _ = read_sequence(args.sequence)
            result = reverse_complement(seq)
            print(f"Original:           {seq[:60]}{'...' if len(seq) > 60 else ''}")
            print(f"Reverse complement: {result[:60]}{'...' if len(result) > 60 else ''}")

        elif args.command == "parse":
            records = parse_file(args.file, args.format, args.output)

            if args.output == "json":
                print(json.dumps(records, indent=2))
            elif args.output == "fasta":
                for rec in records:
                    print(f">{rec['id']} {rec['description']}")
                    seq = rec['sequence']
                    for i in range(0, len(seq), 60):
                        print(seq[i:i+60])
            else:
                print(f"Parsed {len(records)} sequences:\n")
                for rec in records[:20]:
                    print(f"  {rec['id']}: {rec['length']} bp - {rec['description'][:50]}")

        elif args.command == "orfs":
            if args.file:
                seq, _ = read_sequence(args.file)
            elif args.sequence:
                seq, _ = read_sequence(args.sequence)
            else:
                print("Error: Either --sequence or --file is required")
                sys.exit(1)

            results = find_orfs(seq, args.min_length, args.table)
            if args.json:
                print(json.dumps(results, indent=2))
            else:
                print(format_orfs_output(results))

        elif args.command == "motif":
            seq, _ = read_sequence(args.sequence)
            matches = search_motif(seq, args.pattern)
            if args.json:
                print(json.dumps(matches, indent=2))
            else:
                print(format_motif_output(matches, args.pattern))

    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
