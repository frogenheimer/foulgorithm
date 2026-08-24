/**
 * The five's committed picks for one game, as a matrix.
 *
 * Rows are the players any model committed to here, columns are the five, and
 * a filled cell is a pick: the line it was made at, in the character's colour.
 * One glance answers the question the old odds-tier ladder never could: who
 * do they agree on, and who is one model's read alone.
 *
 * The data is the committed slates, the same picks the league table scores,
 * not a display-only selection. Row derivation lives in lib/fivepicks so it
 * can be tested without React; this file only paints it.
 */

import type { Slates } from "@/lib/data";
import { matrixRows } from "@/lib/fivepicks";
import s from "./fivepicks.module.css";

export default function FivePicks({
  slates,
  fixture,
  characters,
}: {
  slates: Slates;
  fixture: string;
  characters: { id: string; name: string }[];
}) {
  const sorted = matrixRows(
    slates,
    fixture,
    characters.map((ch) => ch.id)
  );

  if (!sorted.length) {
    return (
      <p className={s.empty}>
        No committed picks touch this game yet. They appear when the round&rsquo;s slates
        are published.
      </p>
    );
  }

  return (
    <div className={s.wrap}>
      <table className={s.table}>
        <thead>
          <tr>
            <th scope="col" className={s.playerHead}>
              Player
            </th>
            {characters.map((ch) => (
              <th
                key={ch.id}
                scope="col"
                className={s.charHead}
                style={{ ["--char" as string]: `var(--ch-${ch.id})` }}
              >
                <span className={s.swatch} aria-hidden />
                {ch.name}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((row) => (
            <tr key={row.key}>
              <th scope="row" className={s.playerCell}>
                {row.player}
                <span className={s.market}>
                  {row.market === "drawn" ? "fouls won" : "fouls"}
                </span>
              </th>
              {characters.map((ch) => (
                <td
                  key={ch.id}
                  className={row.byCharacter[ch.id] ? s.pickCell : s.blankCell}
                  style={{ ["--char" as string]: `var(--ch-${ch.id})` }}
                >
                  {row.byCharacter[ch.id] ?? ""}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
