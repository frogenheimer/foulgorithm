/**
 * The house sheet: the model's own shouts for this game, no emotion attached.
 *
 * A graphite hero panel at the very top of the fixture page (docs/39's hero
 * treatment: near-black gradient, yellow edge-light), two columns, one per
 * market, line groups inside each. Stars mark the sheet's best in the same
 * chip language as the league medals, and a player stars at most once, at
 * his rarest worthwhile line; the selection itself is made in the pipeline
 * (publish/player_round.py), never here.
 */

import type { HouseSheet as Sheet } from "@/lib/data";
import s from "./housesheet.module.css";

const MARKETS = [
  { key: "committed", label: "Fouls conceded" },
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
                        {p.star && (
                          <span className={s.star} title="The sheet's best">
                            &#9733;
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
          : "The model’s shouts, priced by its own numbers. Starred is the sheet’s best, one line per player. Nothing here is a bet; the eleven’s committed bets are further down."}
      </span>
    </div>
  );
}
