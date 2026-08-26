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
import CupPitch from "./CupPitch";
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

  const { home, away } = tie.players;
  const predicted = [home, away].filter((e) => e.note);

  return (
    <div className="stack">
      <Card title="The elevens" flush>
        <CupPitch home={home} away={away} />
      </Card>

      {/* One caveat for the tie, not one per side. It sits under the pitch
          because that is the thing it is a caveat about, and it is never
          optional while an eleven is still a guess. */}
      {predicted.length > 0 && (
        <div className={s.warnStandalone}>
          <MicroLabel>Read this first</MicroLabel>
          <p className={s.warnText}>{predicted[0].note}</p>
        </div>
      )}

      {/* Side by side, because the whole point is comparing the two elevens. */}
      <div className={s.sideBySide}>
        <ElevenCard eleven={home} />
        <ElevenCard eleven={away} />
      </div>
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
    .join(" \u00b7 ");

  return (
    <Card title={`${eleven.team} · ${heading}`} subtitle={subtitle} flush>
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

/**
 * Deliberately narrow. Two tables sit side by side now, so nine columns would
 * scroll horizontally on every screen and the comparison would be lost. The
 * long tail (raw totals, where the minutes were played) lives in each row's
 * title attribute rather than in a column nobody can see.
 */
const PLAYER_COLUMNS: Column<CupPlayer>[] = [
  {
    key: "player",
    head: "Player",
    cell: (p) => (
      <span className={s.playerCell} title={`${p.spell}. ${p.fouls} fouls, ${p.foulsWon} won, ${p.tackles} tackles, ${p.yellows} yellow, ${p.reds} red.`}>
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
  { key: "fouls", head: "Fouls / 90", numeric: true, cell: (p) => p.foulsPer90 ?? "\u2014" },
  { key: "won", head: "Won / 90", numeric: true, cell: (p) => p.foulsWonPer90 ?? "\u2014" },
  { key: "tackles", head: "Tkl / 90", numeric: true, cell: (p) => p.tacklesPer90 ?? "\u2014" },
  { key: "yellows", head: "Yel", numeric: true, cell: (p) => p.yellows },
  { key: "apps", head: "Apps", numeric: true, cell: (p) => p.appearances },
];
