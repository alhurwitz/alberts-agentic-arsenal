---
name: ui-verify
description: Render a running UI in a real browser and verify layout/alignment looks right, so Claude self-checks instead of the user saying "line that up" / "move it over". Use after editing frontend files (*.tsx/*.jsx/*.css) in a Next.js UI, when the user asks to verify the UI, check the layout, confirm alignment, or check responsive breakpoints. Also runs autonomously via the Stop hook when a dev server is up.
---

# ui-verify

Closes the visual feedback loop: render the running UI in Chromium (via `dev-browser`),
screenshot key breakpoints, scan for hard layout bugs, then judge alignment from the
screenshots. Purpose — stop the user having to say "go check it looks right".

## Preconditions
- `dev-browser` installed (CLI + Chromium). Verify: `dev-browser status`.
- The UI dev server running. Default URL `http://localhost:3000`; override with
  `UI_VERIFY_URL` env var (e.g. `export UI_VERIFY_URL=http://localhost:8080`).
- Repo is a Next.js UI (has `package.json` with `"next"`).

## Run
```
bash ~/.claude/skills/ui-verify/scripts/ui-verify.sh
```
It prints (to stderr) the deterministic findings + screenshot paths, or exits silently
when the UI is unchanged and clean.

## What it checks
1. **Deterministic** — horizontal overflow (page wider than viewport) at 320/768/1024/1440px.
2. **Visual (you judge)** — `Read` each screenshot path and verify: elements line up to a
   consistent left edge, spacing rhythm is even, nothing clipped/overlapping, hierarchy reads.
   Match spacing against the repo's design-system spacing tokens, if it has them.

## After findings
Fix the CSS/layout, then the Stop hook re-renders. The loop terminates automatically once
the 1440px render stops changing (state cached in `~/.dev-browser/tmp/.ui-verify-*`).

## Autonomous mode (hook)
Wired as a `Stop` hook in `~/.claude/settings.json`. Guards make it a no-op unless:
UI repo + dev server reachable + `dev-browser` present. On a changed/failing UI it exits 2,
feeding the screenshot paths back so Claude reviews and fixes without being asked.

## Manual dev-browser primitive (reference)
```
dev-browser <<'EOF'
const page = await browser.getPage("main");
await page.setViewportSize({ width: 1440, height: 900 });
await page.goto("http://localhost:3000", { waitUntil: "networkidle" });
const box = await page.evaluate(() => JSON.parse(JSON.stringify(
  document.querySelector("main").getBoundingClientRect())));
console.log(JSON.stringify(box));
await saveScreenshot(await page.screenshot({ fullPage: true }), "home.png");
EOF
```
Pages are full Playwright Page objects (`goto`, `evaluate`, `locator`, `screenshot`, ...).
Sandbox has no `process`/`fs`/`fetch`; file I/O only via `saveScreenshot`/`writeFile`/`readFile`
into `~/.dev-browser/tmp/`.
