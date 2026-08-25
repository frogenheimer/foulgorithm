/**
 * The five's league table. It lives on The five page, which IS the league:
 * who is winning the game between the models is that page's whole question
 * (docs/38). Zeros are a state, not an absence: the table renders at 0-0-0
 * with a one-line note until the first round settles, because a table that
 * vanishes reads as a bug and was reported as one.
 */

import { Card, DataTable, Note } from "@/components/kit";
import type { Standing } from "@/lib/data";
import { anyPlayed } from "@/lib/standings";
import { modelName } from "@/lib/names";

export default function Standings({
  standings,
  names,
}: {
  standings: Standing[];
  /** id -> name as written, so the table never capitalises ids in CSS. */
  names?: Record<string, string>;
}) {
  return (
    <Card
      title="The table"
      subtitle="On every game, all five commit to the same three bets: six players at 1+, three at 2+, and a mixed two-and-two. Identical shapes, so this measures which players they pick and not how hard a bet they chose. Every leg lands is a win, all but one is a draw. FD is foul difference: a landed leg counts +1, and a miss counts how far it missed by."
      flush
    >
      <DataTable
        rows={standings}
        rowKey={(r) => r.id}
        columns={[
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
          { key: "points", head: "Pts", numeric: true, cell: (r) => r.points },
        ]}
      />
      {!anyPlayed(standings) && (
        <Note>
          All square until the first round settles. A slate is only scored once every
          leg in it has an outcome, because counting an unsettled leg as a miss would
          turn &ldquo;we do not know&rdquo; into &ldquo;they got it wrong&rdquo;.
        </Note>
      )}
    </Card>
  );
}
