/**
 * Both elevens, with what each player has actually done.
 *
 * This is the half of these pages that was missing, and it exists on both
 * sides of a cross-division tie because the data does. The claim that
 * Championship player records could not be had was wrong: the league's own API
 * ranks competition 12 alongside competition 1, so a second-tier XI shows the
 * same columns as a top-flight one rather than names against rates.
 *
 * Every rate is a season total over minutes, not a per-match average, so it is
 * a fact about a player and never a prediction about this game. `spell` says
 * which division the minutes came from, because a pooled rate that does not
 * say where it came from is the same mistake as a pooled team record.
 */

import { Card, DataTable, MicroLabel, Note, Thin, thinRow } from "@/components/kit";
import type { Column } from "@/components/kit";
import type { CupEleven, CupPlayer, CupTie } from "@/lib/cups";
import s from "./stats.module.css";

export default function TiePlayers({ tie }: { tie: CupTie }) {
  if (!tie.players) {
    return (
      <Card title="The players">
        <p className={s.none}>
          Squad records have not been built yet. They fill in on the next
          publish.
        </p>
      </Card>
    );
  }

  return (
    <div className="stack">
      <ElevenCard eleven={tie.players.home} />
      <ElevenCard eleven={tie.players.away} />
    </div>
  );
}

function ElevenCard({ eleven }: { eleven: CupEleven }) {
  const heading = eleven.confirmed ? "Confirmed XI" : "Predicted XI";
  const subtitle = [
    eleven.confirmed ? "Named by the club" : "Our guess at the shape",
    eleven.formation,
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <Card title={`${eleven.team} · ${heading}`} subtitle={subtitle} flush>
      {/* The rotation caveat travels with every predicted eleven and is never
          optional: cup sides change eight or nine players and a tidy-looking
          table is exactly what makes that easy to forget. */}
      {eleven.note && (
        <div className={s.warnBox}>
          <MicroLabel>Read this first</MicroLabel>
          <p className={s.warnText}>{eleven.note}</p>
        </div>
      )}

      {eleven.players.length === 0 ? (
        <p className={s.noneInset}>
          No squad record for {eleven.team}. That is a gap in what we hold, not
          a claim about the club.
        </p>
      ) : (
        <DataTable
          rows={eleven.players}
          columns={PLAYER_COLUMNS}
          rowKey={(p) => `${p.player}-${p.shirt ?? "x"}`}
          rowClass={(p) => (p.thin ? thinRow : undefined)}
        />
      )}

      {eleven.short && eleven.players.length > 0 && (
        <Note>
          Fewer than eleven names. The squad we hold does not fill a team sheet,
          which is a gap in our data rather than a short-handed side.
        </Note>
      )}
    </Card>
  );
}

const PLAYER_COLUMNS: Column<CupPlayer>[] = [
  {
    key: "player",
    head: "Player",
    cell: (p) => (
      <span className={s.playerCell}>
        <span>{p.player}</span>
        {/* Under 450 minutes the rate is mostly noise. Marked rather than
            hidden, so the reader discounts it himself. The kit owns this mark
            so one explanation reaches every page that shows a weak rate. */}
        {p.thin && (
          <Thin title="Under 450 minutes on record, so this rate is weak evidence" />
        )}
      </span>
    ),
  },
  { key: "position", head: "Pos", cell: (p) => p.position },
  { key: "fouls", head: "Fouls / 90", numeric: true, cell: (p) => p.foulsPer90 ?? "—" },
  { key: "won", head: "Won / 90", numeric: true, cell: (p) => p.foulsWonPer90 ?? "—" },
  { key: "tackles", head: "Tackles / 90", numeric: true, cell: (p) => p.tacklesPer90 ?? "—" },
  { key: "yellows", head: "Yellows", numeric: true, cell: (p) => p.yellows },
  { key: "reds", head: "Reds", numeric: true, cell: (p) => p.reds },
  { key: "apps", head: "Apps", numeric: true, cell: (p) => p.appearances },
  {
    key: "spell",
    head: "Where those minutes were",
    cell: (p) => <span className={s.quiet}>{p.spell}</span>,
  },
];
