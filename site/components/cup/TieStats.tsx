/**
 * One tie, as raw record.
 *
 * The mirrored-row shape is the league fixture page's and it is the right one:
 * a shared centre label means the comparison happens by looking across, rather
 * than by holding a number in your head while you find its opposite in a
 * second table.
 *
 * The addition here is that the two sides can be in different divisions, so
 * every value carries its own division's rank underneath it and neither number
 * is ever adjusted toward the other. The bar is one hue on both sides: a
 * red-versus-green split would read as good-versus-bad, and more fouls is
 * neither.
 */

import { Card, Callout, DataTable, MicroLabel, Note } from "@/components/kit";
import type { Column } from "@/components/kit";
import { sideNote } from "@/lib/cups";
import type { CompareBlock, CupTie, MatchTotal, MeetingRow } from "@/lib/cups";
import s from "./stats.module.css";

export default function TieStats({ tie }: { tie: CupTie }) {
  return (
    <div className="stack">
      {tie.crossDivision && (
        <Callout>
          <strong>Two different scales.</strong> {tie.crossDivision}
        </Callout>
      )}

      {tie.total && <TotalBlock tie={tie} />}

      {tie.compare.map((block) => (
        <Comparison key={block.title} tie={tie} block={block} />
      ))}

      {tie.referee && <Referee tie={tie} />}

      <HeadToHead tie={tie} />

      {tie.lineups && <Lineups tie={tie} />}
    </div>
  );
}

/* ---------- the one model number ---------- */

function TotalBlock({ tie }: { tie: CupTie }) {
  const total = tie.total!;
  return (
    <Card title="Expected total fouls" subtitle={total.note}>
      <p className={s.hero}>
        {total.expectedFouls.toFixed(1)}
        <em>fouls, both sides</em>
      </p>

      <DataTable
        rows={total.lines}
        columns={LINE_COLUMNS}
        rowKey={(l) => String(l.line)}
      />

      {total.unpriced.length > 0 && (
        <Note>
          {total.unpriced.join(" and ")} could not be priced from a second-tier
          record, so {total.unpriced.length > 1 ? "they sit" : "they sit"} on the
          league average. That is a floor, not a read on the club.
        </Note>
      )}
    </Card>
  );
}

/* ---------- the mirrored blocks ---------- */

function Comparison({ tie, block }: { tie: CupTie; block: CompareBlock }) {
  return (
    <Card title={block.title} flush>
      <div className={s.wrap}>
        <div className={s.head}>
          <span className={s.team}>{tie.home}</span>
          <span className={s.vs}>versus</span>
          <span className={`${s.team} ${s.right}`}>{tie.away}</span>
        </div>

        <dl className={s.rows}>
          {block.rows.map((r) => {
            const h = r.home ?? 0;
            const a = r.away ?? 0;
            const total = h + a || 1;
            const known = r.home !== null && r.away !== null;
            return (
              <div key={r.label} className={s.row}>
                <dd className={s.stack}>
                  <span className={`${s.value} ${r.higher === "home" ? s.lead : ""}`}>
                    {r.home === null ? <span className={s.none}>no data</span> : r.home}
                  </span>
                  {r.homeRank && <span className={s.rank}>{r.homeRank}</span>}
                </dd>

                <div className={s.middle}>
                  <dt className={s.label}>{r.label}</dt>
                  {known && (
                    <div className={s.bar} aria-hidden="true">
                      <span className={s.left} style={{ width: `${(h / total) * 100}%` }} />
                      <span className={s.rightBar} style={{ width: `${(a / total) * 100}%` }} />
                    </div>
                  )}
                </div>

                <dd className={`${s.stack} ${s.alignRight}`}>
                  <span className={`${s.value} ${r.higher === "away" ? s.lead : ""}`}>
                    {r.away === null ? <span className={s.none}>no data</span> : r.away}
                  </span>
                  {r.awayRank && <span className={s.rank}>{r.awayRank}</span>}
                </dd>
              </div>
            );
          })}
        </dl>

        <p className={s.sample}>
          {sideNote(tie.record.home)} · {sideNote(tie.record.away)}
        </p>
      </div>
    </Card>
  );
}

/* ---------- the official ---------- */

function Referee({ tie }: { tie: CupTie }) {
  const r = tie.referee!;
  return (
    <Card title="The referee" subtitle={r.note}>
      <div className={s.metrics}>
        <Metric label="Official" value={r.referee} />
        <Metric label="Matches" value={r.matches} />
        <Metric label="Fouls per match" value={r.foulsPerMatch} />
        <Metric label="Cards per foul" value={r.cardsPerFoul} />
      </div>

      {r.thin && (
        <Note>
          Only {r.matches} matches on record for this official, so read these
          lightly.
        </Note>
      )}

      <div className={s.underRef}>
        {(["home", "away"] as const).map((which) => {
          const club = r.clubs[which];
          const name = which === "home" ? tie.home : tie.away;
          return (
            <div key={which} className={s.underCard}>
              <MicroLabel>{name} under {r.referee}</MicroLabel>
              {club.matches === 0 ? (
                <p className={s.none}>Never had this official on record</p>
              ) : (
                <p className={s.underValue}>
                  {club.foulsPerMatch} fouls a match
                  <em>over {club.matches} {club.matches === 1 ? "match" : "matches"}</em>
                </p>
              )}
            </div>
          );
        })}
      </div>
    </Card>
  );
}

/* ---------- past meetings ---------- */

function HeadToHead({ tie }: { tie: CupTie }) {
  const h2h = tie.headToHead;
  if (!h2h.meetings) {
    return (
      <Card title="Past meetings">
        <p className={s.none}>
          {tie.home} and {tie.away} have not met in a league match we hold, which
          runs back to 2000/01 in both divisions.
        </p>
      </Card>
    );
  }

  return (
    <Card
      title="Past meetings"
      subtitle={`${h2h.meetings} on record, averaging ${h2h.totalFouls} fouls between them`}
      flush
    >
      <DataTable
        rows={h2h.rows}
        columns={MEETING_COLUMNS}
        rowKey={(m) => `${m.date}-${m.home}`}
      />
    </Card>
  );
}

/* ---------- confirmed elevens ---------- */

function Lineups({ tie }: { tie: CupTie }) {
  const lu = tie.lineups!;
  return (
    <Card
      title="Confirmed elevens"
      subtitle="Names only. Second-tier players have no foul record at any price, so showing rates on one side would make the two columns say different things."
    >
      <div className={s.underRef}>
        {(["home", "away"] as const).map((which) => {
          const side = lu[which];
          const name = which === "home" ? tie.home : tie.away;
          return (
            <div key={which} className={s.underCard}>
              <MicroLabel>
                {name}
                {side?.formation ? ` · ${side.formation}` : ""}
              </MicroLabel>
              {side ? (
                <ol className={s.eleven}>
                  {side.starters.map((p) => (
                    <li key={p}>{p}</li>
                  ))}
                </ol>
              ) : (
                <p className={s.none}>Not posted yet</p>
              )}
            </div>
          );
        })}
      </div>
    </Card>
  );
}

const LINE_COLUMNS: Column<MatchTotal["lines"][number]>[] = [
  { key: "line", head: "Line", numeric: true, cell: (l) => l.line },
  {
    key: "over",
    head: "Over",
    numeric: true,
    cell: (l) => `${Math.round(l.probOver * 100)}/100`,
  },
  {
    key: "fair",
    head: "Fair odds",
    numeric: true,
    cell: (l) => l.fairOddsOver.toFixed(2),
  },
];

const MEETING_COLUMNS: Column<MeetingRow>[] = [
  { key: "date", head: "Date", cell: (m) => m.date },
  // Named on every row on purpose. A second-tier meeting is not evidence
  // about a first-tier tie, and only the label tells a reader which it was.
  { key: "division", head: "Division", cell: (m) => m.division ?? "\u2014" },
  { key: "match", head: "Match", cell: (m) => `${m.home} v ${m.away}` },
  {
    key: "score",
    head: "Score",
    numeric: true,
    cell: (m) => `${m.homeGoals}\u2013${m.awayGoals}`,
  },
  {
    key: "fouls",
    head: "Fouls",
    numeric: true,
    cell: (m) => `${m.homeFouls}\u2013${m.awayFouls}`,
  },
  {
    key: "cards",
    head: "Cards",
    numeric: true,
    cell: (m) =>
      m.homeYellows === null ? "\u2014" : `${m.homeYellows}\u2013${m.awayYellows}`,
  },
  { key: "referee", head: "Referee", cell: (m) => m.referee ?? "\u2014" },
];

function Metric({ label, value }: { label: string; value: string | number | null }) {
  return (
    <div className={s.metric}>
      <MicroLabel>{label}</MicroLabel>
      <span className={s.metricValue}>{value ?? "—"}</span>
    </div>
  );
}
