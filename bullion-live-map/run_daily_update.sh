#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

python3 fetch_bullion_data.py

# News is a quality-of-life feature, not load-bearing market data -- a
# failed fetch here must not block the data.json commit/push above. It
# leaves the existing news.json in place (see fetch_bullion_news.py) and
# still surfaces to stderr rather than failing silently.
python3 fetch_bullion_news.py || echo "News fetch failed; continuing with existing news.json." >&2

git add data.json news.json
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
