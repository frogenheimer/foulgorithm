"use client";

/**
 * Both squads: the real pitch at the top, then every player in a sortable
 * table beside his opposite number.
 *
 * The pitch is `components/fixture/Pitch`, the same one the league fixture
 * pages draw, in read-only mode. It is not a copy. A copy was written first and
 * it lost the position badges, the out-of-position ring, the bench values and
 * the key, which is what a copy always does.
 *
 * Read-only because swapping recomputes a house sheet from whoever is standing
 * there, and a cup tie involving a Championship club has no model behind it to
 * recompute. `bases={["career"]}` for the same reason: these rows carry a
 * player's own rate and no prediction for this game.
 *
 * The tables carry the WHOLE squad, not the eleven. The eleven answers who is
 * playing; the squad answers who could come on and what happens if he does.
 */

import { useMemo, useState } from "react";
import { Card, DataTable, MicroLabel, Note, Thin, thinRow } from "@/components/kit";
import type { Column } from "@/components/kit";
import Pitch, { type Basis, type Market } from "@/components/fixture/Pitch";
import { toShape, toSquad } from "./toExplorer";
import type { CupEleven, CupPlayer, CupTie } from "@/lib/cups";
import s from "./stats.module.css";

export default function TiePlayers({ tie }: { tie: CupTie }) {
  const [market, setMarket] = useState<Market>("committed");
  const [sort, setSort] = useState("minutes");

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
  const fixture = `${tie.home} v ${tie.away}`;
  const predicted = [home, away].find((e) => e.note);

  return (
    <div className="stack">
      <Card title="The eleven on the pitch" flush>
        <Pitch
          home={{ club: home.team, shape: toShape(home), squad: toSquad(home, away.team, fixture) }}
          away={{ club: away.team, shape: toShape(away), squad: toSquad(away, home.team, fixture) }}
          selected={{}}
          onChange={() => {}}
          onReset={() => {}}
          market={market}
          onMarket={setMarket}
          basis="career"
          onBasis={() => {}}
          readOnly
          bases={["career"]}
        />
      </Card>

      {/* One caveat for the tie, under the pitch it qualifies, and never
          optional while either eleven is still a guess. */}
      {predicted && (
        <div className={s.warnStandalone}>
          <MicroLabel>Read this first</MicroLabel>
          <p className={s.warnText}>{predicted.note}</p>
        </div>
      )}

      <div className={s.sideBySide}>
        <SquadCard eleven={home} sort={sort} onSort={setSort} />
        <SquadCard eleven={away} sort={sort} onSort={setSort} />
      </div>
    </div>
  );
}

/**
 * One club's whole squad.
 *
 * `sort` is shared between the two cards on purpose: sorting one side by fouls
 * and leaving the other by minutes would put two differently-ordered lists
 * side by side and invite a comparison row by row that means nothing.
 */
function SquadCard({
  eleven,
  sort,
  onSort,
}: {
  eleven: CupEleven;
  sort: string;
  onSort: (key: string) => void;
}) {
  const starting = useMemo(
    () => new Set(eleven.players.map((p) => p.player)),
    [eleven.players]
  );

  const rows = useMemo(() => {
    const column = COLUMNS.find((c) => c.key === sort);
    const sorted = [...eleven.squad];
    if (column?.sort) sorted.sort(column.sort);
    return sorted;
  }, [eleven.squad, sort]);

  const heading = eleven.confirmed ? "Confirmed XI" : "Predicted XI";

  return (
    <Card
      title={`${eleven.team} squad`}
      subtitle={`${eleven.squad.length} players · ${heading}${
        eleven.formation ? ` · ${eleven.formation}` : ""
      }`}
      flush
    >
      {eleven.squad.length === 0 ? (
        <p className={s.noneInset}>
          No squad record for {eleven.team}. That is a gap in what we hold, not
          a claim about the club.
        </p>
      ) : (
        <DataTable
          rows={rows}
          columns={COLUMNS}
          rowKey={(p) => `${p.player}-${p.shirt ?? "x"}`}
          sortKey={sort}
          onSort={onSort}
          rowClass={(p) => (p.thin ? thinRow : undefined)}
        />
      )}

      {eleven.short && eleven.squad.length > 0 && (
        <Note>
          Fewer than eleven names on the sheet. A gap in our data rather than a
          short-handed side.
        </Note>
      )}
    </Card>
  );
}

/** Highest first for a rate; a player with no rate sinks rather than leads. */
function desc(pick: (p: CupPlayer) => number | null) {
  return (a: CupPlayer, b: CupPlayer) => (pick(b) ?? -1) - (pick(a) ?? -1);
}

/**
 * Deliberately narrow. Two tables sit side by side, so nine columns would
 * scroll on every screen and the comparison would be lost. The long tail
 * lives in each row's title.
 */
const COLUMNS: Column<CupPlayer>[] = [
  {
    key: "player",
    head: "Player",
    sort: (a, b) => a.player.localeCompare(b.player),
    cell: (p) => (
      <span
        className={s.playerCell}
        title={`${p.spell}. ${p.fouls} fouls, ${p.foulsWon} won, ${p.tackles} tackles, ${p.yellows} yellow, ${p.reds} red.`}
      >
        <span>{p.player}</span>
        {p.thin && (
          <Thin title="Under 450 minutes on record, so this rate is weak evidence" />
        )}
      </span>
    ),
  },
  { key: "position", head: "Pos", sort: (a, b) => a.position.localeCompare(b.position), cell: (p) => p.position },
  { key: "fouls", head: "Fouls / 90", numeric: true, sort: desc((p) => p.foulsPer90), cell: (p) => p.foulsPer90 ?? "—" },
  { key: "won", head: "Won / 90", numeric: true, sort: desc((p) => p.foulsWonPer90), cell: (p) => p.foulsWonPer90 ?? "—" },
  { key: "tackles", head: "Tkl / 90", numeric: true, sort: desc((p) => p.tacklesPer90), cell: (p) => p.tacklesPer90 ?? "—" },
  { key: "yellows", head: "Yel", numeric: true, sort: desc((p) => p.yellows), cell: (p) => p.yellows },
  { key: "minutes", head: "Mins", numeric: true, sort: desc((p) => p.minutes), cell: (p) => p.minutes },
];
