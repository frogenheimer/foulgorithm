/**
 * The house sheet, rebuilt client-side from whoever is on the pitches.
 *
 * A PORT of the pipeline's `_house_sheet` (publish/player_round.py) and it
 * has to stay one: same top-three ranking by the house's own price, same
 * 20/100 floor before a 3+ group earns its place, same safest-first tiers
 * with a player badged at most once. The published sheet
 * is shown verbatim until a reader swaps someone; from the first swap this
 * recomputes from the elevens now standing on the pitches.
 */

import { who } from "./who";
import type { Explorer, HouseSheet } from "./data";

const PICKS_PER_GROUP = 3;
const THREE_PLUS_FLOOR = 20;
const TIERS: [number, "safe" | "optimistic" | "rogue"][] = [
  [1, "safe"],
  [2, "optimistic"],
  [3, "rogue"],
];

export function houseSheetFrom(
  explorer: Explorer,
  fixture: string,
  onPitch: Set<string>
): HouseSheet {
  const houseIdx = explorer.models.indexOf(explorer.house);
  const rows = explorer.rows.filter(
    (r) => r.fixture === fixture && onPitch.has(who(r.fullName))
  );

  const groups: HouseSheet["groups"] = [];
  for (const market of ["committed", "drawn"] as const) {
    for (const line of [1, 2, 3]) {
      const li = explorer.lines.indexOf(line - 0.5);
      if (li < 0) continue;
      const picks = rows
        .map((r) => ({ r, p: r[market]?.[li]?.[houseIdx] ?? 0 }))
        .filter((x) => x.p > 0)
        .sort((a, b) => b.p - a.p)
        .slice(0, PICKS_PER_GROUP)
        .map((x) => ({
          player: x.r.player,
          fullName: x.r.fullName,
          outOf100: Math.round(x.p * 100),
          star: false,
          tier: null,
        }));
      if (line === 3 && (!picks.length || picks[0].outOf100 < THREE_PLUS_FLOOR)) continue;
      if (picks.length) groups.push({ market, line, picks });
    }
  }

  // Three tiers, one per line, badged safest first (docs/41): 1+ is SAFE,
  // 2+ OPTIMISTIC, 3+ ROGUE. A player carries at most one tier on the sheet.
  const badged = new Set<string>();
  for (const [line, tier] of TIERS) {
    for (const group of groups) {
      if (group.line !== line) continue;
      for (const pick of group.picks) {
        if (!badged.has(pick.player)) {
          pick.tier = tier;
          pick.star = true;
          badged.add(pick.player);
          break;
        }
      }
    }
  }
  return { groups };
}
