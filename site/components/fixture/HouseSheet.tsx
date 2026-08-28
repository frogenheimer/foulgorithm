/**
 * The house sheet: the model's own shouts for this game, no emotion attached.
 *
 * A graphite hero panel at the very top of the fixture page (docs/39's hero
 * treatment: near-black gradient, yellow edge-light), two columns, one per
 * market, line groups inside each. Three tiers badge the sheet, safe,
 * optimistic and rogue, one per line, safest first, and a player carries
 * at most one; the selection itself is made in the pipeline
 * (publish/player_round.py), never here.
 */

import type { HouseSheet as Sheet } from "@/lib/data";
import s from "./housesheet.module.css";

/** The three tiers, one per line (docs/41): the safe call, the optimistic
 *  one, and the rogue shout. A player carries at most one on the sheet. */
const TIER_TITLE = {
  safe: "The safe call: the best-priced 1+ shout",
  optimistic: "The optimistic call: the best 2+ shout",
  rogue: "The rogue shout: the best 3+ shout, a long one by design",
} as const;

const MARKETS = [
  { key: "committed", label: "Fouls committed" },
  { key: "drawn", label: "Fouls won" },
] as const;

export default function HouseSheet({
  sheet,
  rebuilt = false,
}: {
  sheet: Sheet;
  /** True once a reader has swapped the pitch and the sheet is recomputed live. */
  rebuilt?: boolean;
}) {
  if (!sheet.groups.length) return null;
  return (
    <div className={s.panel}>
      <span className={s.kicker}>{rebuilt ? "The house · your eleven" : "The house"}</span>
      <div className={s.columns}>
        {MARKETS.map((m) => {
          const groups = sheet.groups.filter((g) => g.market === m.key);
          if (!groups.length) return null;
          return (
            <div key={m.key} className={s.market}>
              <span className={s.marketLabel}>{m.label}</span>
              {groups.map((g) => (
                <div key={g.line} className={s.group}>
                  <span className={s.line}>{g.line}+</span>
                  <ul className={s.picks}>
                    {g.picks.map((p) => (
                      <li key={p.player} className={s.pick}>
                        <span className={s.player}>{p.player}</span>
                        {p.tier && (
                          <span className={`${s.tier} ${s[p.tier]}`} title={TIER_TITLE[p.tier]}>
                            {p.tier}
                          </span>
                        )}
                        <span className={s.price}>{p.outOf100}/100</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          );
        })}
      </div>
      <span className={s.foot}>
        {rebuilt
          ? "Recomputed live from the eleven you chose on the pitches below. Reset the pitch to see the published sheet again."
          : "The model’s shouts, priced by its own numbers. Safe is the best 1+ call, optimistic the best 2+, rogue the best 3+, one tier per player. Nothing here is a bet; the eleven’s committed bets are further down."}
      </span>
    </div>
  );
}
