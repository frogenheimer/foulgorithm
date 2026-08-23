#!/usr/bin/env bash
# Enforce docs/brandbook.md.
#
# Writing a rule in a styleguide does not enforce it. The previous guide said
# "never hard-code a spacing value" and the repo contained 31 of them, plus 56
# hard-coded font sizes across ten values. Nothing checked, so nothing held.
#
# Every rule carries a BASELINE: the count that existed when the rule was
# switched on. At or under the baseline prints one quiet line. Going ABOVE it
# fails. Nothing raises a baseline automatically, so the numbers only fall.
#
#   scripts/audit-ui.sh                    report against the baseline
#   scripts/audit-ui.sh --update-baseline  lock in an improvement
#   scripts/audit-ui.sh --list             show every offending line
#
# To silence one genuine exception, mark the line:
#   /* audit-ignore B3: brand mark colour is an asset, not a token */
# On the line itself, or on either of the two lines above it, so a CSS comment
# can sit where a CSS comment belongs. The rule id is required and a reason is
# expected: a suppression that does not say which rule it silences is
# indistinguishable from one nobody understood.
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/site"
BASELINE="$ROOT/scripts/ui-baseline.json"
MODE="${1:-report}"

# Files the rules apply to. tokens.css is exempt by design: it is the one place
# raw values are allowed to exist.
css_files () { find app components -name "*.css" ! -name "tokens.css" 2>/dev/null; }
tsx_files () { find app components -name "*.tsx" 2>/dev/null; }

declare -a IDS DESCS COUNTS
FOUND=""

# hits <id> <description> <file-list-cmd> <grep-pattern>
hits () {
  local id="$1" desc="$2" files="$3" pat="$4"
  local n=0 lines=""
  while IFS= read -r f; do
    [ -f "$f" ] || continue
    while IFS= read -r line; do
      # Suppressed on the line itself, or on one of the two lines above it.
      # A CSS comment naturally sits above the declaration it explains, and a
      # rule that demands otherwise gets contorted around rather than obeyed.
      case "$line" in *"audit-ignore $id"*) continue;; esac
      local num="${line%%:*}"
      local before
      before=$(sed -n "$((num > 2 ? num - 2 : 1)),$((num - 1))p" "$f" 2>/dev/null)
      case "$before" in *"audit-ignore $id"*) continue;; esac
      lines="${lines}${f}: ${line}"$'\n'
      n=$((n + 1))
    done < <(grep -nE "$pat" "$f" 2>/dev/null || true)
  done < <(eval "$files")
  IDS+=("$id"); DESCS+=("$desc"); COUNTS+=("$n")
  FOUND="${FOUND}### $id"$'\n'"${lines}"
}

echo "Auditing against docs/brandbook.md"
echo

hits B1 "raw font-size in px (six tokens exist)" css_files \
  'font-size:[[:space:]]*[0-9.]+px'

hits B2 "raw px in padding, margin or gap (ten steps exist)" css_files \
  '(padding|margin|gap)[a-z-]*:[^;]*[0-9]+px'

hits B3 "hex colour outside tokens.css" css_files \
  '#[0-9a-fA-F]{3,8}\b'

hits B4 "raw border-radius in px" css_files \
  'border-radius:[[:space:]]*[0-9.]+px'

hits B5 "font-weight outside 400, 500, 600" css_files \
  'font-weight:[[:space:]]*(100|200|300|700|800|900|bold|bolder|lighter)'

hits B6 "transition or animation without var(--ease)" css_files \
  '(transition|animation):[^;]*(ease-in|ease-out|linear|cubic-bezier)'

hits B7 "raw <table> in a page or component (use DataTable)" tsx_files \
  '<table'

hits B8 "display:flex or grid on a class named *cell* (breaks table layout)" css_files \
  '^\.[a-zA-Z]*[Cc]ell[a-zA-Z]*[^{]*\{[^}]*display:[[:space:]]*(flex|grid)'

hits B9 "standalone .table definition (one DataTable, not nine)" css_files \
  '^\.table[[:space:]]*\{'

hits B10 "hex colour in a component file" tsx_files \
  '#[0-9a-fA-F]{6}\b'

# ---- an overflow-x box must carry min-width: 0, or it widens the page ----
missing=0
while IFS= read -r f; do
  [ -f "$f" ] || continue
  o=$(grep -c 'overflow-x:[[:space:]]*auto' "$f" 2>/dev/null); o=${o:-0}
  m=$(grep -c 'min-width:[[:space:]]*0' "$f" 2>/dev/null); m=${m:-0}
  [ "$o" -gt "$m" ] && missing=$((missing + o - m))
done < <(css_files)
IDS+=("B11"); DESCS+=("overflow-x box without min-width: 0"); COUNTS+=("$missing")

# ---- report ----
if [ "$MODE" = "--list" ]; then
  echo "$FOUND"
  exit 0
fi

fails=0
improved=0
declare -a NEW_JSON
printf '%-6s %-52s %7s %9s  %s\n' RULE RULE_DESCRIPTION COUNT BASELINE ""
printf '%s\n' "--------------------------------------------------------------------------------------"
for i in "${!IDS[@]}"; do
  id="${IDS[$i]}"; n="${COUNTS[$i]}"
  base=$( [ -f "$BASELINE" ] && "$ROOT/.venv/bin/python" -c "
import json,sys
try: print(json.load(open('$BASELINE')).get('$id', 0))
except Exception: print(0)" || echo 0 )
  verdict=""
  if [ "$n" -gt "$base" ]; then verdict="REGRESSION +$((n - base))"; fails=$((fails + 1))
  elif [ "$n" -lt "$base" ]; then verdict="improved -$((base - n))"; improved=$((improved + 1))
  elif [ "$n" -eq 0 ]; then verdict="clean"
  fi
  printf '%-6s %-52s %7s %9s  %s\n' "$id" "${DESCS[$i]}" "$n" "$base" "$verdict"
  NEW_JSON+=("\"$id\": $n")
done

if [ "$MODE" = "--update-baseline" ]; then
  printf '{\n  %s\n}\n' "$(IFS=,$'\n  '; echo "${NEW_JSON[*]}")" > "$BASELINE"
  echo; echo "Baseline updated. Counts can now only fall."
  exit 0
fi

echo
if [ "$fails" -gt 0 ]; then
  echo "FAIL: $fails rule(s) above baseline. Fix them, or if the code is genuinely"
  echo "      not what the rule thinks, mark the line: /* audit-ignore <ID>: reason */"
  echo "      Raising a baseline to make this pass is a decision, not a workaround."
  exit 1
fi
[ "$improved" -gt 0 ] && echo "PASS, and $improved rule(s) improved. Lock it in: scripts/audit-ui.sh --update-baseline"
[ "$improved" -eq 0 ] && echo "PASS: nothing above baseline."
exit 0
