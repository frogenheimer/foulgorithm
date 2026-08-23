"use client";

/**
 * Referee numbers, sortable, with this round's appointments attached.
 *
 * Without the appointments this table is trivia. With them, a reader can see
 * that the man running 12% above the league on fouls has the game they were
 * already looking at, which is the only reason to publish it.
 *
 * Every column here is an observation and none of them is a referee effect. One
 * assigned more derbies shows more of everything without being any stricter,
 * and separating the two needs a model with team effects in it. The model does
 * not use these numbers, and the page says so.
 */

import { useMemo, useState } from "react";
import type { Appointment, RefereeRow } from "@/lib/data";
import { DataTable } from "@/components/kit";
import s from "./referees.module.css";

type Sort = "fouls" | "cards" | "strict" | "matches" | "name";

export default function Table({
  rows,
  appointments,
}: {
  rows: RefereeRow[];
  appointments: Appointment[];
}) {
  const [sort, setSort] = useState<Sort>("fouls");
  const [thisRound, setThisRound] = useState(appointments.length > 0);

  const byReferee = useMemo(() => {
    const out = new Map<string, string[]>();
    for (const a of appointments) {
      out.set(a.referee, [...(out.get(a.referee) ?? []), a.fixture]);
    }
    return out;
  }, [appointments]);

  const shown = useMemo(() => {
    const filtered = thisRound ? rows.filter((r) => byReferee.has(r.referee)) : rows;
    const by: Record<Sort, (a: RefereeRow, b: RefereeRow) => number> = {
      fouls: (a, b) => b.foulsPerMatch - a.foulsPerMatch,
      cards: (a, b) => (b.cardsPerMatch ?? 0) - (a.cardsPerMatch ?? 0),
      strict: (a, b) => (b.cardsPerFoul ?? 0) - (a.cardsPerFoul ?? 0),
      matches: (a, b) => b.matches - a.matches,
      name: (a, b) => a.referee.localeCompare(b.referee),
    };
    return [...filtered].sort(by[sort]);
  }, [rows, byReferee, thisRound, sort]);

  // Appointed referees with too few matches to earn a row. Naming them is
  // better than letting a reader assume the list above is complete.
  const unlisted = useMemo(
    () => [...byReferee.keys()].filter((name) => !rows.some((r) => r.referee === name)),
    [byReferee, rows]
  );

  return (
    <div className={s.wrap}>
      <div className={s.controls}>
        {appointments.length > 0 && (
          <label className={s.check}>
            <input
              type="checkbox"
              checked={thisRound}
              onChange={(e) => setThisRound(e.target.checked)}
            />
            Only this round&apos;s referees
          </label>
        )}
        <span className={s.count}>
          {shown.length} of {rows.length} referees
        </span>
      </div>

      <DataTable
        rows={shown}
        rowKey={(r) => r.referee}
        sortKey={sort}
        onSort={(k) => setSort(k as Sort)}
        columns={[
          {
            key: "name",
            head: "Referee",
            sort: () => 0,
            cell: (r) => <span className={s.name}>{r.referee}</span>,
          },
          {
            key: "round",
            head: "This round",
            cell: (r) => {
              const games = byReferee.get(r.referee);
              return games ? (
                <span className={s.fixture}>{games.join(", ")}</span>
              ) : (
                <span className={s.none}>&mdash;</span>
              );
            },
          },
          { key: "matches", head: "Matches", numeric: true, sort: () => 0, cell: (r) => r.matches },
          {
            key: "fouls",
            head: "Fouls",
            numeric: true,
            sort: () => 0,
            cell: (r) => <span className={s.strong}>{r.foulsPerMatch}</span>,
          },
          {
            key: "vs",
            head: "vs league",
            numeric: true,
            // Signed, so direction survives without the colour.
            cell: (r) => {
              const off = Math.round((r.vsLeague - 1) * 100);
              return off === 0 ? "level" : `${off > 0 ? "+" : ""}${off}%`;
            },
          },
          { key: "cards", head: "Cards", numeric: true, sort: () => 0, cell: (r) => r.cardsPerMatch ?? "—" },
          { key: "reds", head: "Reds", numeric: true, cell: (r) => r.redsPerMatch ?? "—" },
          {
            key: "strict",
            head: "Fouls booked",
            numeric: true,
            sort: () => 0,
            cell: (r) => (
              <span className={s.strong}>
                {r.cardsPerFoul !== null ? `${(r.cardsPerFoul * 100).toFixed(1)}%` : "—"}
              </span>
            ),
          },
        ]}
      />

      {thisRound && unlisted.length > 0 && (
        <p className={s.note}>
          {unlisted.join(", ")} {unlisted.length === 1 ? "has" : "have"} a fixture this round
          but too few matches in the window to show a row. Named here so the list above does
          not read as complete.
        </p>
      )}
    </div>
  );
}
