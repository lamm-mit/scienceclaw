#!/usr/bin/env bash
# Publishes all scienceclaw skills to ClawHub.
# Workaround for the .git bug: copies each skill to /tmp before publishing.

set -e

SKILLS_DIR="$(cd "$(dirname "$0")/skills" && pwd)"
VERSION="${1:-1.0.1}"
CHANGELOG="${2:-Add skillKey metadata so skills register as /scienceclaw:investigate, /scienceclaw:post, /scienceclaw:query, /scienceclaw:local-files, /scienceclaw:status, /scienceclaw:watch slash commands in OpenClaw}"

declare -A NAMES=(
  [scienceclaw-investigate]="ScienceClaw: Multi-Agent Investigation"
  [scienceclaw-post]="ScienceClaw: Post to Infinite"
  [scienceclaw-query]="ScienceClaw: Query (Dry Run)"
  [scienceclaw-local-files]="ScienceClaw: Local File Investigation"
  [scienceclaw-status]="ScienceClaw: Agent Status"
  [scienceclaw-watch]="ScienceClaw: Watch (Live Collaboration)"
)

TAGS="scienceclaw,science,biology,chemistry,research,pubmed,multi-agent"

echo "Publishing ScienceClaw skill pack v${VERSION} to ClawHub..."
echo ""

for SLUG in "${!NAMES[@]}"; do
  NAME="${NAMES[$SLUG]}"
  SRC="$SKILLS_DIR/$SLUG"
  TMP="/tmp/clawhub-publish-$SLUG"

  if [ ! -d "$SRC" ]; then
    echo "⚠  Skipping $SLUG — folder not found"
    continue
  fi

  echo "→ Publishing $SLUG..."

  # Copy to /tmp to avoid the .git bug
  rm -rf "$TMP"
  rsync -a --exclude='.git' --exclude='__pycache__' "$SRC/" "$TMP/"

  clawhub publish "$TMP" \
    --slug "$SLUG" \
    --name "$NAME" \
    --version "$VERSION" \
    --changelog "$CHANGELOG" \
    --tags "$TAGS"

  rm -rf "$TMP"
  echo "✓ $SLUG published"
  echo ""
done

echo "All skills published! View at: https://clawhub.ai"
