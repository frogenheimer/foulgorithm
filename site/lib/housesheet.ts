/**
 * The house sheet, rebuilt client-side from whoever is on the pitches.
 *
 * A PORT of the pipeline's `_house_sheet` (publish/player_round.py) and it
 * has to stay one: same top-three ranking by the house's own price, same
 * 20/100 floor before a 3+ group earns its place, same one-star-per-player
 * rule with committed taking precedence at the same line. The published sheet
 * is shown verbatim until a reader swaps someone; from the first swap this
 * recomputes from the elevens now standing on the pitches.
 */

import { who } from "./who";
import type { Explorer, HouseSheet } from "./data";

const PICKS_PER_GROUP = 3;
const THREE_PLUS_FLOOR = 20;

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
        }));
      if (line === 3 && (!picks.length || picks[0].outOf100 < THREE_PLUS_FLOOR)) continue;
      if (picks.length) groups.push({ market, line, picks });
    }
  }

  const starred = new Set<string>();
  const order = [...groups].sort((a, b) =>
    a.market === b.market
      ? b.line - a.line
      : a.market === "committed"
        ? -1
        : 1
  );
  for (const group of order) {
    for (const pick of group.picks) {
      if (!starred.has(pick.player)) {
        pick.star = true;
        starred.add(pick.player);
        break;
      }
    }
  }
  return { groups };
}
