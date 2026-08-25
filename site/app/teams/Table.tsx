"use client";

import Link from "next/link";
import { useState } from "react";
import { DataTable, PageHeader, Note } from "@/components/kit";
import type { TableRow, Teams } from "@/lib/data";
import ClubChip from "@/components/kit/ClubChip";
import { fixtureSlug } from "@/lib/slug";
import s from "./teams.module.css";

type Sort = "points" | "fouls" | "won" | "cards";

export function TeamsTable({ data }: { data: Teams }) {
  const [sort, setSort] = useState<Sort>("points");

  const rows = [...data.table].sort((a, b) => {
    if (sort === "fouls") return (b.foulsPerMatch ?? 0) - (a.foulsPerMatch ?? 0);
    if (sort === "won") return (b.foulsWonPerMatch ?? 0) - (a.foulsWonPerMatch ?? 0);
    if (sort === "cards") return (b.cardsPerMatch ?? 0) - (a.cardsPerMatch ?? 0);
    return b.points - a.points || b.goalDifference - a.goalDifference;
  });

  const position = new Map(
    [...data.table]
      .sort((a, b) => b.points - a.points || b.goalDifference - a.goalDifference)
      .map((r, i) => [r.team, i + 1])
  );

  // The temper ring's scale: every ring is this club's share of the hottest
  // fouls-per-match rate in the league, so the league leader wears a full arc.
  const rated = rows.filter((r) => r.foulsPerMatch != null);
  const temperMax = Math.max(...rated.map((r) => r.foulsPerMatch as number), 0);
  const temperRank = new Map(
    [...rated]
      .sort((a, b) => (b.foulsPerMatch as number) - (a.foulsPerMatch as number))
      .map((r, i) => [r.team, i + 1])
  );

  return (
    <div className="stack">
      <PageHeader
        title="Teams"
        lede={`The table for ${data.tableSeason}, with the discipline columns this site is actually about. Sort by any of them, and open a club for its squad.`}
      />

      <DataTable
        rows={rows}
        rowKey={(r: TableRow) => r.team}
        sortKey={sort}
        onSort={(k) => setSort(k as Sort)}
        onRowClick={(r) => {
          window.location.href = `/teams/${fixtureSlug(r.team)}`;
        }}
        columns={[
          { key: "pos", head: "#", numeric: true, cell: (r) => <span className={s.pos}>{position.get(r.team)}</span> },
          {
            key: "team",
            head: "Club",
            cell: (r) => (
              <span className={s.club}>
                {r.foulsPerMatch != null ? (
                  <ClubChip
                    name={r.team}
                    size="sm"
                    temper={{
                      value: r.foulsPerMatch,
                      max: temperMax,
                      rank: temperRank.get(r.team) ?? 0,
                      of: rows.length,
                    }}
                  />
                ) : (
                  <ClubChip name={r.team} size="sm" />
                )}
                {r.team}
              </span>
            ),
          },
          { key: "played", head: "Pl", numeric: true, cell: (r) => r.played },
          { key: "record", head: "W-D-L", cell: (r) => <span className={s.form}>{r.won}-{r.drawn}-{r.lost}</span> },
          { key: "gd", head: "GD", numeric: true, cell: (r) => (r.goalDifference > 0 ? `+${r.goalDifference}` : r.goalDifference) },
          { key: "points", head: "Pts", numeric: true, sort: () => 0, cell: (r) => <strong>{r.points}</strong> },
          { key: "fouls", head: "Fouls", numeric: true, sort: () => 0, cell: (r) => r.foulsPerMatch ?? "—" },
          { key: "won", head: "Fouls won", numeric: true, sort: () => 0, cell: (r) => r.foulsWonPerMatch ?? "—" },
          { key: "cards", head: "Cards", numeric: true, sort: () => 0, cell: (r) => r.cardsPerMatch ?? "—" },
          { key: "squad", head: "Squad", numeric: true, cell: (r) => r.players.length },
        ]}
      />

      <Note>
        Points and position cover {data.tableSeason}. Foul, fouls-won and card rates cover{" "}
        {data.rateSeasons}, because a week of a season is not enough evidence for a rate and
        a table means this season whatever has been played. A promoted club shows no rate
        until it has a top-flight record.
      </Note>
    </div>
  );
}
