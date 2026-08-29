/**
 * Every var(--x) the site uses must resolve to a token.
 *
 * A token rename swept tokens.css and missed the chart layer: fourteen dead
 * names (--seq-450, --text-muted, --series-2, ...) shipped, and every unset
 * fill fell back to SVG black. In dark mode that is data on a near-black
 * surface. audit-ui.sh polices raw values but never checked that a reference
 * resolves, so nothing held. This does.
 */

import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const ROOT = join(__dirname, "..");

/** Set by next/font at runtime, or per-element inline (the character accent). */
const RUNTIME_TOKENS = new Set(["--font-inter", "--font-geist-mono", "--font-space", "--font-hand", "--char"]);

function walk(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const full = join(dir, name);
    if (statSync(full).isDirectory()) return walk(full);
    return /\.(css|tsx|ts)$/.test(name) ? [full] : [];
  });
}

describe("design tokens", () => {
  it("every var() reference resolves to a defined token", () => {
    const files = [...walk(join(ROOT, "app")), ...walk(join(ROOT, "components"))];

    // tokens.css plus component-local custom properties (a chart may scope a
    // layout variable to itself; that is a definition too).
    const known = new Set<string>();
    for (const file of files) {
      if (!file.endsWith(".css")) continue;
      const css = readFileSync(file, "utf8");
      for (const m of css.matchAll(/(--[a-z0-9-]+)\s*:/g)) known.add(m[1]);
    }

    const missing = new Map<string, string[]>();
    for (const file of files) {
      const text = readFileSync(file, "utf8");
      for (const m of text.matchAll(/var\((--[a-z0-9-]+)/g)) {
        const token = m[1];
        // `var(--ch-${...})` reaches this scan truncated to its literal prefix.
        if (known.has(token) || RUNTIME_TOKENS.has(token) || token === "--ch-") continue;
        const at = file.slice(ROOT.length + 1);
        missing.set(token, [...(missing.get(token) ?? []), at]);
      }
    }

    const report = [...missing]
      .map(([token, files]) => `${token} (${[...new Set(files)].join(", ")})`)
      .join("\n");
    expect(report, `tokens used but never defined:\n${report}`).toBe("");
  });
});
