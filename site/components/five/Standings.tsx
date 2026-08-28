/**
 * The five's league table. It lives on The five page, which IS the league:
 * who is winning the game between the models is that page's whole question
 * (docs/38). Zeros are a state, not an absence: the table renders at 0-0-0
 * with a one-line note until the first round settles, because a table that
 * vanishes reads as a bug and was reported as one.
 */

import { Card, DataTable, Note } from "@/components/kit";
import m from "./standings.module.css";
import type { Standing } from "@/lib/data";
import { anyPlayed } from "@/lib/standings";
import { modelName } from "@/lib/names";

export default function Standings({
  standings,
  names,
  priced = false,
}: {
  standings: Standing[];
  /** True once the bets are the priced bands of docs/42. */
  priced?: boolean;
  /** id -> name as written, so the table never capitalises ids in CSS. */
  names?: Record<string, string>;
}) {
  const played = anyPlayed(standings);
  const position = new Map(standings.map((r, i) => [r.id, i + 1]));
  return (
    <Card
      title="The table"
      subtitle={
        priced
          ? "On every game, every competitor makes three bets at three fixed prices set by the house model: a banker, a value bet and a long shot, any shape they like inside the price. Every leg lands is a win, one foul short in total is a draw. FD is foul difference: a landed leg counts +1, a miss counts how far it missed by. Bold is how rare their picks are by the house's own price; WB banks that rarity only when a pick lands, and it breaks ties behind FD."
          : "On every game, every competitor commits to the same three bets: six players at 1+, three at 2+, and a mixed two-and-two. Every leg lands is a win, all but one is a draw. FD is foul difference: a landed leg counts +1, a miss counts how far it missed by. Bold is how rare their picks are by the house's own price, averaged over everything they have committed; WB banks that rarity only when a pick lands, and it breaks ties behind FD."
      }
      flush
    >
      <DataTable
        rows={standings}
        rowKey={(r) => r.id}
        columns={[
          {
            key: "pos",
            head: "",
            cell: (r) => {
              const p = position.get(r.id) ?? 0;
              const medal = played && p <= 3 ? m[`pos${p}` as keyof typeof m] : "";
              return <span className={`${m.pos} ${medal}`}>{p}</span>;
            },
          },
          { key: "name", head: "", cell: (r) => modelName(r.id, names) },
          { key: "played", head: "P", numeric: true, cell: (r) => r.played },
          { key: "won", head: "W", numeric: true, cell: (r) => r.won },
          { key: "drawn", head: "D", numeric: true, cell: (r) => r.drawn },
          { key: "lost", head: "L", numeric: true, cell: (r) => r.lost },
          {
            key: "landed",
            head: "Legs",
            numeric: true,
            cell: (r) => `${r.legsLanded}/${r.legsLanded + r.legsMissed}`,
          },
          {
            key: "fd",
            head: "FD",
            numeric: true,
            cell: (r) => (r.difference > 0 ? `+${r.difference}` : r.difference),
          },
          {
            key: "bold",
            head: "Bold",
            numeric: true,
            cell: (r) => (r.boldness != null ? Math.round(r.boldness * 100) : "\u2014"),
          },
          {
            key: "wb",
            head: "WB",
            numeric: true,
            cell: (r) => (r.winBoldness != null ? r.winBoldness.toFixed(1) : "\u2014"),
          },
          { key: "points", head: "Pts", numeric: true, cell: (r) => r.points },
        ]}
      />
      {!played && (
        <Note>
          All square until the first round settles. A slate is only scored once every
          leg in it has an outcome, because counting an unsettled leg as a miss would
          turn &ldquo;we do not know&rdquo; into &ldquo;they got it wrong&rdquo;.
        </Note>
      )}
    </Card>
  );
}
