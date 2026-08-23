#!/usr/bin/env bash
# End-to-end check that the whole thing still works.
#
# Not a substitute for the test suite. This runs the parts the tests mock or
# skip: the real sources, the real jobs, a real site build, and the pages a
# reader would actually open. Most of what has broken in this project broke
# between components rather than inside one.
#
# Usage: scripts/smoke.sh
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PY=".venv/bin/python"
fails=0

step () {
  printf '%-46s' "$1"
  shift
  if out=$("$@" 2>&1); then
    echo "ok"
  else
    echo "FAIL"
    echo "$out" | tail -6 | sed 's/^/    /'
    fails=$((fails + 1))
  fi
}

check () {
  printf '%-46s' "$1"
  shift
  if out=$(PYTHONPATH=src $PY -c "$1" 2>&1); then
    echo "${out:-ok}"
  else
    echo "FAIL"
    echo "$out" | tail -6 | sed 's/^/    /'
    fails=$((fails + 1))
  fi
}

echo "== tests =="
step "unit and integration (no network)" env PYTHONPATH=src $PY -m pytest tests/ -q -m "not network"
step "network-dependent tests"           env PYTHONPATH=src $PY -m pytest tests/ -q -m network

echo
echo "== live sources =="
check "fixtures" 'from foulgorithm.sources import football_data as f; r=f.fetch_fixtures(); print(f"{len(r)} fixtures")'
check "squads" 'from foulgorithm.sources import fpl; s=fpl.current_squads(); print(f"{sum(len(v) for v in s.values())} players, {len(s)} clubs")'
check "lineups" 'from foulgorithm.sources.lineups import for_round; print(f"{len(for_round())} confirmed")'
check "player season totals" 'from foulgorithm.sources import player_season_stats as p; print(f"{len(p.season_totals())} players")'
check "match history" 'from foulgorithm.sources import football_data as f
season = "2025-26"
print(str(len(f.parse(f.fetch(season)))) + " matches")'

echo
echo "== jobs =="
printf '%-46s' "lineup poll"
PYTHONPATH=src $PY -m foulgorithm.jobs.lineup_watch >/tmp/smoke.log 2>&1
c=$?; [ $c -le 1 ] && echo "ok (exit $c)" || { echo "FAIL (exit $c)"; tail -4 /tmp/smoke.log | sed 's/^/    /'; fails=$((fails+1)); }
printf '%-46s' "settle"
PYTHONPATH=src $PY -m foulgorithm.jobs.settle --dry-run >/tmp/smoke.log 2>&1
c=$?; [ $c -le 1 ] && echo "ok (exit $c)" || { echo "FAIL (exit $c)"; tail -4 /tmp/smoke.log | sed 's/^/    /'; fails=$((fails+1)); }

echo
echo "== published data =="
for f in players.json matchday.json overview.json track-record.json; do
  printf '%-46s' "$f"
  if [ -f "site/public/data/$f" ]; then
    $PY -c "import json,sys;d=json.load(open('site/public/data/$f'));print(f'{len(json.dumps(d))//1024} KB')" || fails=$((fails+1))
  else
    echo "MISSING"; fails=$((fails+1))
  fi
done
check "no model output on the stats sheet" 'import json;b=json.dumps(json.load(open("site/public/data/matchday.json"))).lower();bad=[w for w in ("probability","fair","predict") if w in b];print("clean" if not bad else "LEAKED "+str(bad))'
check "job state is committable" 'import subprocess,sys;from foulgorithm.jobs import lineup_watch,settle;bad=[str(p) for p in (lineup_watch.STATE,settle.SNAPSHOT) if subprocess.run(["git","check-ignore","-q",str(p)]).returncode==0];print("ok" if not bad else "IGNORED "+str(bad))'

echo
echo "== site =="
step "build" npm --prefix site run build
step "no page scrolls sideways at 390px" ./scripts/check-mobile.sh 390

echo
if [ $fails -eq 0 ]; then echo "SMOKE PASS"; else echo "SMOKE FAIL: $fails step(s)"; fi
exit $fails
