#!/bin/bash
# Add all native-macos-app GitHub issues to Project 2 (Kanban + Roadmap views).
# Prerequisites:
#   gh auth refresh -h github.com -s project,read:project
# Usage:
#   ./scripts/add-issues-to-project.sh

set -euo pipefail

REPO="roto31/Plex-NFO-creator-and-Poster-Art-creator"
PROJECT_NUMBER="2"
OWNER="roto31"

if ! gh auth status 2>&1 | grep -q "read:project"; then
  echo "ERROR: GitHub token missing read:project scope." >&2
  echo "Run: gh auth refresh -h github.com -s project,read:project" >&2
  exit 2
fi

echo "Adding native-macos-app issues to project ${OWNER}#${PROJECT_NUMBER}..."

gh issue list -R "${REPO}" --label native-macos-app --state open --limit 200 \
  --json url -q '.[].url' | while read -r url; do
  if [[ -n "${url}" ]]; then
    gh project item-add "${PROJECT_NUMBER}" --owner "${OWNER}" --url "${url}" || true
  fi
done

echo "Done. Open Kanban: https://github.com/users/roto31/projects/2/views/7"
