#!/usr/bin/env bash
# Check every page for horizontal overflow at a real phone width.
#
# Headless Chrome will not open a viewport narrower than 500px, so a
# --window-size of 390 renders at 500 and CLIPS the screenshot down to 390.
# That looks exactly like broken layout and is not. Reading it as a bug has
# cost this project two rounds of fixing things that were already fine, so this
# measures instead of eyeballing.
#
# Each route is loaded inside a 390px iframe, which gets a genuine 390px
# viewport, and reports scrollWidth against it. Equal is correct. Wider is a
# real bug, and the widest offending element is named.
#
# Usage: scripts/check-mobile.sh [width]
set -euo pipefail

WIDTH="${1:-390}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/site/out"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PORT=4199
TMP="${TMPDIR:-/tmp}"

[ -d "$OUT" ] || { echo "no build at $OUT. Run: npm --prefix site run build"; exit 1; }

npx --yes serve "$OUT" -l $PORT >/dev/null 2>&1 &
SERVER=$!
trap 'kill $SERVER 2>/dev/null; rm -f "$OUT"/_probe-*.html' EXIT
sleep 3

fail=0
printf '%-26s %8s %12s  %s\n' route viewport scrollWidth verdict
printf '%s\n' "------------------------------------------------------------------"

while read -r route; do
  page="/${route}"
  [ "$route" = "index" ] && page="/"
  probe="_probe-$(echo "$route" | tr / -).html"

  # One route per file, measured synchronously. The previous version walked
  # every route in one page and stalled: virtual time does not advance reliably
  # across a chain of iframe loads.
  cat > "$OUT/$probe" <<HTML
<!doctype html><meta charset="utf-8">
<style>body{margin:0;background:#000;color:#fff;font:14px monospace}
iframe{position:fixed;left:-9999px;width:${WIDTH}px;height:1200px;border:0}</style>
<pre id="o">pending</pre>
<iframe id="f" src="${page}"></iframe>
<script>
document.getElementById('f').onload = function () {
  var d = this.contentDocument;
  setTimeout(function () {
    var vw = d.documentElement.clientWidth, sw = d.documentElement.scrollWidth, worst = '';
    if (sw > vw + 1) {
      var bad = [];
      d.querySelectorAll('*').forEach(function (el) {
        var r = el.getBoundingClientRect();
        if (r.right > vw + 1 && el.scrollWidth <= el.clientWidth + 1)
          bad.push([Math.round(r.right), el.tagName.toLowerCase() + '.' + String(el.className || '').slice(0, 28)]);
      });
      bad.sort(function (a, b) { return b[0] - a[0]; });
      if (bad.length) worst = bad[0][1] + '@' + bad[0][0];
    }
    document.getElementById('o').textContent = vw + ' ' + sw + ' ' + worst;
  }, 300);
};
</script>
HTML

  "$CHROME" --headless --disable-gpu --dump-dom --virtual-time-budget=8000 \
    "http://localhost:$PORT/$probe" 2>/dev/null > "$TMP/dom.html" || true
  read -r vw sw worst <<<"$(sed -n 's|.*<pre id="o">\([^<]*\)</pre>.*|\1|p' "$TMP/dom.html" | head -1)"

  if [ -z "${vw:-}" ]; then
    printf '%-26s %8s %12s  %s\n' "$page" "?" "?" "COULD NOT MEASURE"
    fail=1
  elif [ "$sw" -gt "$((vw + 1))" ]; then
    printf '%-26s %8s %12s  %s\n' "$page" "$vw" "$sw" "OVERFLOWS  ${worst:-}"
    fail=1
  else
    printf '%-26s %8s %12s  %s\n' "$page" "$vw" "$sw" "ok"
  fi
done < <(cd "$OUT" && find . -name "*.html" -not -name "404.html" -not -name "_*" \
           | sed 's|^\./||; s|\.html$||' | sort)

echo
if [ "$fail" -eq 0 ]; then
  echo "PASS: nothing scrolls sideways at ${WIDTH}px"
else
  echo "FAIL: at least one page scrolls sideways at ${WIDTH}px"
fi
exit "$fail"
