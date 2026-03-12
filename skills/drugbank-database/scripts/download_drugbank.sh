#!/usr/bin/env bash
# Download DrugBank all-full-database via curl (alternative to drugbank-downloader).
# Requires: DRUGBANK_USERNAME and DRUGBANK_PASSWORD in environment.
#
# Usage:
#   export DRUGBANK_USERNAME="your@email.com"
#   export DRUGBANK_PASSWORD="your_password"
#   ./download_drugbank.sh [version] [output_path]
#
# Examples:
#   ./download_drugbank.sh                    # latest → drugbank_full.zip
#   ./download_drugbank.sh 5-1-14             # v5.1.14 → drugbank_5-1-14.zip
#   ./download_drugbank.sh 5-1-14 ./mydata/  # custom output dir

set -e

VERSION="${1:-latest}"
OUTPUT_DIR="${2:-.}"
OUTPUT_DIR="$(cd "$OUTPUT_DIR" && pwd)"

if [[ "$VERSION" == "latest" ]]; then
  URL="https://go.drugbank.com/releases/latest/downloads/all-full-database"
  OUTFILE="$OUTPUT_DIR/drugbank_full.zip"
else
  URL="https://go.drugbank.com/releases/${VERSION}/downloads/all-full-database"
  OUTFILE="$OUTPUT_DIR/drugbank_${VERSION}.zip"
fi

if [[ -z "$DRUGBANK_USERNAME" ]] || [[ -z "$DRUGBANK_PASSWORD" ]]; then
  echo "Error: Set DRUGBANK_USERNAME and DRUGBANK_PASSWORD" >&2
  echo "  export DRUGBANK_USERNAME=\"your@email.com\"" >&2
  echo "  export DRUGBANK_PASSWORD=\"your_password\"" >&2
  exit 1
fi

echo "Downloading DrugBank ($VERSION) to $OUTFILE ..."
curl -Lfv -o "$OUTFILE" -u "$DRUGBANK_USERNAME:$DRUGBANK_PASSWORD" "$URL"
echo ""
echo "Downloaded: $OUTFILE"
echo "Set DRUGBANK_XML_PATH to use with the skill:"
echo "  export DRUGBANK_XML_PATH=\"$OUTFILE\""
