"use client";

import { useMemo, useState } from "react";
import type { FixtureBoard as Board, PlayerRow } from "@/lib/data";
import { odds } from "@/lib/format";
import { Bars, DotArray } from "@/components/charts/pack";
import HeadToHead from "@/components/HeadToHead";
import s from "./board.module.css";

type Market = "committed" | "drawn";
type View = "compare" | "table" | "chart";
type SortKey = "p1plus" | "p2plus" | "p3plus" | "expectedMinutes" | "player";

const MARKETS: { key: Market; label: string }[] = [
  { key: "committed", label: "Fouls committed" },
  { key: "drawn", label: "Fouls won" },
];

export default function FixtureBoard({ fixture }: { fixture: Board }) {
  const [market, setMarket] = useState<Market>("committed");
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<SortKey>("p1plus");
  const [view, setView] = useState<View>("compare");

  const teams = Object.entries(fixture.teams);
  const tickets = fixture.tickets?.[market] ?? [];

  return (
    <div className={s.wrap}>
      <div className={s.controls}>
        <div className={s.tabs} role="tablist" aria-label="Market">
          {MARKETS.map((m) => (
            <button
              key={m.key}
              role="tab"
              aria-selected={market === m.key}
              className={market === m.key ? s.tabOn : s.tab}
              onClick={() => setMarket(m.key)}
            >
              {m.label}
            </button>
          ))}
        </div>
        <div className={s.tabs} role="tablist" aria-label="View">
          <button role="tab" aria-selected={view === "compare"}
            className={view === "compare" ? s.tabOn : s.tab} onClick={() => setView("compare")}>
            Compare
          </button>
          <button role="tab" aria-selected={view === "table"}
            className={view === "table" ? s.tabOn : s.tab} onClick={() => setView("table")}>
            Table
          </button>
          <button role="tab" aria-selected={view === "chart"}
            className={view === "chart" ? s.tabOn : s.tab} onClick={() => setView("chart")}>
            Chart
          </button>
        </div>
        <input
          className={s.search}
          type="search"
          placeholder="Find a player"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          aria-label="Find a player"
        />
      </div>

      {tickets.length > 0 && (
        <div className={s.tickets}>
          <h5 className={s.ticketHead}>
            Best combination for a total of 4, 5 or 6 {market === "committed" ? "fouls" : "fouls won"}
          </h5>
          <div className={s.ticketRow}>
            {tickets.map((t) => (
              <div key={t.target} className={s.ticket}>
                <div className={s.ticketTop}>
                  <span className={s.ticketTarget}>{t.target}</span>
                  <span className={s.ticketShape}>{t.shape}</span>
                </div>
                <ul className={s.ticketLegs}>
                  {t.legs.map((l) => (
                    <li key={l.player}>
                      <span>{l.player}</span>
                      <span className={s.legLine}>{l.fouls}+</span>
                    </li>
                  ))}
                </ul>
                <div className={s.ticketFoot}>
                  <strong>{t.outOf100}</strong> of 100 · fair {odds(t.fair)}
                </div>
              </div>
            ))}
          </div>
          <p className={s.ticketNote}>
            Combined by multiplying, which assumes the legs are independent. They are not: players
            in one match share a referee and a tempo, and that correlation is positive. So these are
            a floor, and the true chance is a little better.
          </p>
        </div>
      )}

      {view === "compare" ? (
        <HeadToHead fixture={fixture} />
      ) : view === "chart" ? (
        <div className={s.teams}>
          {teams.map(([team]) => {
            const rows = fixture.stats?.[market]?.[team] ?? [];
            const max = Math.max(0.1, ...Object.values(fixture.stats?.[market] ?? {}).flat().map((r) => r.value));
            return (
              <div key={team} className={s.teamCol}>
                <h5 className={s.teamName}>{team}</h5>
                <p className={s.chartCaption}>
                  {market === "committed" ? "Fouls committed" : "Fouls won"} per 90, career to date
                </p>
                <Bars rows={rows.map((r) => ({ label: r.player, value: r.value }))} max={max} />
              </div>
            );
          })}
        </div>
      ) : (
      <div className={s.teams}>
        {teams.map(([team, players]) => (
          <TeamTable
            key={team}
            team={team}
            players={players}
            market={market}
            query={query}
            sort={sort}
            onSort={setSort}
          />
        ))}
      </div>
      )}
    </div>
  );
}

function TeamTable({
  team, players, market, query, sort, onSort,
}: {
  team: string; players: PlayerRow[]; market: Market; query: string;
  sort: SortKey; onSort: (k: SortKey) => void;
}) {
  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    const filtered = q ? players.filter((p) => p.player.toLowerCase().includes(q)) : players;
    return [...filtered].sort((a, b) => {
      if (sort === "player") return a.player.localeCompare(b.player);
      if (sort === "expectedMinutes") return b.expectedMinutes - a.expectedMinutes;
      return b[market][sort] - a[market][sort];
    });
  }, [players, query, sort, market]);

  const head = (key: SortKey, label: string, num = true) => (
    <th className={num ? s.num : undefined}>
      <button className={sort === key ? s.sortOn : s.sort} onClick={() => onSort(key)}>
        {label}
      </button>
    </th>
  );

  return (
    <div className={s.teamCol}>
      <h5 className={s.teamName}>
        {team} <span className={s.count}>{rows.length}</span>
      </h5>
      <div className="scroll-x">
        <table className={s.table}>
          <thead>
            <tr>
              {head("player", "Player", false)}
              <th>Pos</th>
              {head("expectedMinutes", "Min")}
              {head("p1plus", "1+")}
              {head("p2plus", "2+")}
              {head("p3plus", "3+")}
              <th className={s.num}>Take 1+ at</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((p) => {
              const b = p[market];
              return (
                <tr key={p.player} className={p.thin ? s.thinRow : undefined}>
                  <td>
                    {p.player}
                    {p.confirmed && <span className={s.dot} title="In the confirmed eleven" />}
                  </td>
                  <td className="muted">{p.position ?? ""}</td>
                  <td className={s.num}>{Math.round(p.expectedMinutes)}</td>
                  <td className={s.num}>{Math.round(b.p1plus * 100)}</td>
                  <td className={s.num}>{Math.round(b.p2plus * 100)}</td>
                  <td className={s.num}>{Math.round(b.p3plus * 100)}</td>
                  <td className={s.num}>{odds(b.floor1 ?? 0)}</td>
                </tr>
              );
            })}
            {rows.length === 0 && (
              <tr><td colSpan={7} className="muted">No player matches that search.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
