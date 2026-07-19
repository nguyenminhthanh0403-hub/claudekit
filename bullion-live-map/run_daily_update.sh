#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

python3 fetch_bullion_data.py

git add data.json
if git diff --cached --quiet; then
  echo "No data changes; skipping commit."
else
  git commit -m "Update live financial data for $(date -u +%F)"
  # Reconcile with any commits that landed on main since this workspace was
  # last synced, so the push can't fail non-fast-forward and leave a stuck
  # local commit that halts every future run. --rebase keeps history linear.
  git pull --rebase origin main
  git push origin main
fi
