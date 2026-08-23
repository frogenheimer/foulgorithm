#!/usr/bin/env bash
# Every built page must resolve on the deployed site, not just locally.
#
# The static export writes stats.html and fixture/name.html. `npx serve` maps
# /stats to stats.html by default; Vercel with framework:null does not unless
# cleanUrls is set. So the local server was more forgiving than production and
# every sub-page 404ed live while passing every check here.
#
# Usage: scripts/check-routes.sh [base-url]
set -uo pipefail

BASE="${1:-https://foulgorithm.vercel.app}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/site/out"

[ -d "$OUT" ] || { echo "no build at $OUT"; exit 1; }

fail=0
printf '%-46s %s\n' ROUTE STATUS
printf '%s\n' "------------------------------------------------------"
while read -r page; do
  route="/${page}"
  [ "$page" = "index" ] && route="/"
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 20 "$BASE$route")
  printf '%-46s %s' "$route" "$code"
  if [ "$code" = "200" ]; then echo ""; else echo "  <- BROKEN"; fail=$((fail + 1)); fi
done < <(cd "$OUT" && find . -name "*.html" -not -name "404.html" -not -name "_*" \
           | sed 's|^\./||; s|\.html$||' | sort)

echo
if [ "$fail" -eq 0 ]; then echo "PASS: every built page resolves at $BASE"
else echo "FAIL: $fail route(s) do not resolve. Check cleanUrls in vercel.json."; fi
exit "$fail"
