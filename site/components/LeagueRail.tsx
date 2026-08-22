"use client";

import { useState } from "react";
import type { LeagueLeaders } from "@/lib/data";
import s from "./rail-stats.module.css";

/**
 * Current-season league leaders. Context, deliberately quiet.
 *
 * This is not the product, so it should not compete with it: small type, no
 * chart, no colour beyond the bar. It exists so a reader can sanity-check our
 * numbers against what is actually happening this season.
 */
export default function LeagueRail({ data }: { data: LeagueLeaders }) {
  const keys = Object.keys(data);
  const [active, setActive] = useState(keys[0]);
  if (!keys.length) return null;

  const group = data[active];
  const max = Math.max(...group.leaders.map((l) => l.value), 1);

  return (
    <aside className={s.rail}>
      <h3 className={s.title}>This season</h3>

      <div className={s.tabs} role="tablist" aria-label="Statistic">
        {keys.map((k) => (
          <button
            key={k}
            role="tab"
            aria-selected={active === k}
            className={active === k ? s.tabOn : s.tab}
            onClick={() => setActive(k)}
          >
            {short(data[k].label)}
          </button>
        ))}
      </div>

      <ol className={s.list}>
        {group.leaders.map((l) => (
          <li key={l.player + l.rank} className={s.row}>
            <span className={s.rank}>{l.rank}</span>
            <span className={s.who}>
              <span className={s.name}>{l.player}</span>
              <span className={s.club}>{l.team}</span>
            </span>
            <span className={s.bar} aria-hidden="true">
              <span style={{ width: `${(l.value / max) * 100}%` }} />
            </span>
            <span className={s.value}>{l.value}</span>
          </li>
        ))}
      </ol>

      <p className={s.note}>
        Live from the league&apos;s own data, so it moves as the season does. Totals, not rates, so
        early in a season these are as much about minutes played as about style.
      </p>
    </aside>
  );
}

function short(label: string) {
  return label
    .replace("Fouls committed", "Fouls")
    .replace("Fouls won", "Won")
    .replace("Yellow cards", "Cards")
    .replace("Tackles", "Tackles");
}
