/**
 * The five's committed picks for one game, as a matrix.
 *
 * Rows are the players any model committed to here, columns are the five, and
 * a filled cell is a pick: the line it was made at, in the character's colour.
 * One glance answers the question the old odds-tier ladder never could: who
 * do they agree on, and who is one model's read alone.
 *
 * The data is the committed slates, the same picks the league table scores,
 * not a display-only selection. If the team sheets are not in yet the section
 * says so and the picks regenerate when they land.
 */

import type { Slates } from "@/lib/data";
import s from "./fivepicks.module.css";

type Row = {
  player: string;
  market: string;
  byCharacter: Record<string, string>;
  backers: number;
};

export default function FivePicks({
  slates,
  fixture,
  characters,
  confirmed,
}: {
  slates: Slates;
  fixture: string;
  characters: { id: string; name: string }[];
  confirmed: boolean;
}) {
  const rows = new Map<string, Row>();

  for (const { id } of characters) {
    const own = slates.byCharacter[id];
    if (!own) continue;
    for (const shape of slates.shapes) {
      for (const leg of own[shape.key]?.legs ?? []) {
        if (leg.fixture !== fixture) continue;
        const key = `${leg.fullName ?? leg.player}|${leg.market}`;
        const row =
          rows.get(key) ??
          ({ player: leg.player, market: leg.market, byCharacter: {}, backers: 0 } as Row);
        if (!row.byCharacter[id]) {
          row.byCharacter[id] = `${leg.fouls}+`;
          row.backers += 1;
        }
        rows.set(key, row);
      }
    }
  }

  const sorted = [...rows.values()].sort(
    (a, b) => b.backers - a.backers || a.player.localeCompare(b.player)
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
            <tr key={`${row.player}-${row.market}`}>
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
      {!confirmed && (
        <p className={s.note}>
          * Team sheets are not in yet: these picks regenerate automatically when the
          lineups land, an hour before kickoff, and the version on the board at the
          round&rsquo;s first kickoff is the one that scores.
        </p>
      )}
    </div>
  );
}
