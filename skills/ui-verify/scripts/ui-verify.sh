#!/usr/bin/env bash
# ui-verify: autonomous UI render check via dev-browser.
# Wired as a Stop hook. Guards hard so it is a no-op outside running Next UI repos.
# Exit 0 = nothing to do / UI unchanged since last check.
# Exit 2 = UI changed or deterministic issue found -> stderr fed back to Claude to review + fix.
set -uo pipefail

URL="${UI_VERIFY_URL:-http://localhost:3000}"
TMP="${HOME}/.dev-browser/tmp"

# --- Guard 1: only run in a Next.js UI repo ---
[ -f package.json ] || exit 0
grep -q '"next"' package.json 2>/dev/null || exit 0

# --- Guard 2: dev server must be reachable ---
curl -sf -o /dev/null --max-time 2 "$URL" 2>/dev/null || exit 0

# --- Guard 3: dev-browser present ---
command -v dev-browser >/dev/null 2>&1 || exit 0

# Render + screenshot key breakpoints, scan for horizontal overflow.
OUT=$(dev-browser 2>/dev/null <<EOF
const bps = [320, 768, 1024, 1440];
const findings = [];
const shots = [];
for (const w of bps) {
  const page = await browser.getPage("verify" + w);
  await page.setViewportSize({ width: w, height: 900 });
  await page.goto("$URL", { waitUntil: "networkidle" });
  const scan = await page.evaluate(() => {
    const vw = document.documentElement.clientWidth;
    const out = [];
    if (document.documentElement.scrollWidth > vw + 1) {
      out.push("overflow-x: page scrolls " + document.documentElement.scrollWidth + "px in " + vw + "px viewport");
    }
    return out;
  });
  const p = await saveScreenshot(await page.screenshot({ fullPage: true }), "verify-" + w + ".png");
  shots.push(p);
  scan.forEach(f => findings.push("[" + w + "px] " + f));
}
console.log(JSON.stringify({ findings, shots }));
EOF
)

# dev-browser failed (Chromium missing, etc.) -> skip silently.
[ -z "$OUT" ] && exit 0

SHOTS=$(printf '%s' "$OUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print('\n'.join(d['shots']))" 2>/dev/null) || exit 0
FINDINGS=$(printf '%s' "$OUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print('\n'.join(d['findings']))" 2>/dev/null)

# --- Termination: only re-review when the 1440 render changed since last check ---
KEY=$(pwd | shasum | cut -c1-12)
STATE="${TMP}/.ui-verify-${KEY}"
BIG=$(printf '%s' "$SHOTS" | grep 'verify-1440' | head -1)
HASH=""
[ -n "$BIG" ] && [ -f "$BIG" ] && HASH=$(shasum "$BIG" | cut -c1-40)
LAST=""
[ -f "$STATE" ] && LAST=$(cat "$STATE")
printf '%s' "$HASH" > "$STATE"

# Unchanged UI and no hard finding -> done, stay silent.
if [ "$HASH" = "$LAST" ] && [ -z "$FINDINGS" ]; then
  exit 0
fi

{
  echo "ui-verify: rendered ${URL} across 320/768/1024/1440px."
  [ -n "$FINDINGS" ] && { echo "Deterministic issues:"; printf '%s\n' "$FINDINGS"; }
  echo "Read these screenshots and verify layout/alignment looks right; fix any misalignment, overflow, or spacing issues, then finish:"
  printf '%s\n' "$SHOTS"
} >&2
exit 2
