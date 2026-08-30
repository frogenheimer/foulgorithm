/**
 * The vidiprinter: settled bets as a teletype feed, the way scores used to
 * arrive on a Saturday afternoon. Newest game first, decided bets only, and
 * the old convention kept alive: a full house on the six is spelled out,
 * ALL SIX (6), so nobody reads it as a typo.
 */

import type { ArchivedFixture, SlipLeg } from "./data";
import { clubIdentity } from "./clubs";
import { betVerdict } from "./graded";

export type PrinterLine = { text: string; tone: "won" | "lost" };

const WORDS = ["ZERO", "ONE", "TWO", "THREE", "FOUR", "FIVE", "SIX", "SEVEN", "EIGHT"];

export function vidiprinterLines(
  archived: Record<string, ArchivedFixture>,
  cap = Infinity
): PrinterLine[] {
  const played = Object.values(archived)
    .filter((a) => a.result && a.bets && a.outcomes)
    .sort((a, b) => (a.kickoff < b.kickoff ? 1 : -1));

  const lines: PrinterLine[] = [];
  for (const a of played) {
    const [home, away] = a.label.split(" v ");
    const tag = `${clubIdentity(home).code} v ${clubIdentity(away).code}`;
    for (const ch of a.characters) {
      for (const bet of Object.values(a.bets?.[ch.id] ?? {})) {
        if (!bet) continue;
        const verdict = betVerdict(bet.legs as SlipLeg[], a.outcomes, true);
        if (verdict !== "came in" && verdict !== "no") continue;
        const landed = bet.legs.length;
        const full =
          verdict === "came in" && landed >= 6
            ? `ALL ${WORDS[Math.min(landed, 8)]} (${landed}) LANDED`
            : verdict.toUpperCase();
        lines.push({
          text: `${tag} · ${ch.name.toUpperCase()} · ${bet.label.toUpperCase()} · ${full}`,
          tone: verdict === "came in" ? "won" : "lost",
        });
        if (lines.length >= cap) return lines;
      }
    }
  }
  return lines;
}

/**
 * The order the one-line ticker plays (docs/50): every bet that landed
 * first, then the misses, each group in the feed's own newest-first order.
 * Nothing is dropped; the full report lists the same lines in this order.
 */
export function orderForTicker(lines: PrinterLine[]): PrinterLine[] {
  return [...lines.filter((l) => l.tone === "won"), ...lines.filter((l) => l.tone !== "won")];
}
