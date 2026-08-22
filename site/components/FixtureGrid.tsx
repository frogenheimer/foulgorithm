"use client";

import { useMemo, useState } from "react";
import FixtureBoard from "@/components/FixtureBoard";
import type { FixtureBoard as Board } from "@/lib/data";
import { fouls } from "@/lib/format";
import s from "./grid.module.css";

/**
 * Fixtures as a grid of compact cards, with a day strip above.
 *
 * Replaces ten stacked full-width accordions, which meant comparing two
 * fixtures required scrolling between them and holding numbers in your head.
 * Ten cards fit in roughly one screen.
 *
 * Opening a card expands it to full width below the grid rather than in place,
 * so the grid never reflows underneath the reader.
 */
export default function FixtureGrid({ fixtures }: { fixtures: Board[] }) {
  const [day, setDay] = useState<string>("all");
  const [open, setOpen] = useState<string | null>(null);

  const days = useMemo(() => {
    const map = new Map<string, number>();
    for (const f of fixtures) {
      const key = f.kickoff.slice(0, 10);
      map.set(key, (map.get(key) ?? 0) + 1);
    }
    return [...map.entries()].sort();
  }, [fixtures]);

  const shown = day === "all" ? fixtures : fixtures.filter((f) => f.kickoff.startsWith(day));
  const active = open ? fixtures.find((f) => f.key === open) : null;

  return (
    <div>
      <div className={s.strip} role="tablist" aria-label="Match day">
        <button
          role="tab"
          aria-selected={day === "all"}
          className={day === "all" ? s.dayOn : s.day}
          onClick={() => setDay("all")}
        >
          <span className={s.dayName}>All</span>
          <span className={s.dayCount}>{fixtures.length}</span>
        </button>
        {days.map(([key, count]) => {
          const d = new Date(key + "T12:00:00Z");
          return (
            <button
              key={key}
              role="tab"
              aria-selected={day === key}
              className={day === key ? s.dayOn : s.day}
              onClick={() => setDay(key)}
            >
              <span className={s.dayName}>
                {d.toLocaleDateString("en-GB", { weekday: "short", timeZone: "Europe/London" })}
              </span>
              <span className={s.dayNum}>
                {d.toLocaleDateString("en-GB", { day: "numeric", timeZone: "Europe/London" })}
              </span>
              <span className={s.dayCount}>{count}</span>
            </button>
          );
        })}
      </div>

      <div className={s.grid}>
        {shown.map((f) => {
          const sum = f.summary;
          const isOpen = open === f.key;
          return (
            <button
              key={f.key}
              className={isOpen ? s.cardOn : s.card}
              onClick={() => setOpen(isOpen ? null : f.key)}
              aria-expanded={isOpen}
            >
              <span className={s.teams}>
                <span className={s.team}>{f.home}</span>
                <span className={s.v}>v</span>
                <span className={s.team}>{f.away}</span>
              </span>

              <span className={s.meta}>
                {new Date(f.kickoff).toLocaleString("en-GB", {
                  weekday: "short", hour: "2-digit", minute: "2-digit", timeZone: "Europe/London",
                })}
                {f.referee && ` · ${f.referee}`}
                {f.lineupConfirmed && <span className={s.confirmed}>XI</span>}
              </span>

              {sum && (
                <>
                  <span className={s.xf}>
                    <span className={s.xfValue}>{fouls(sum.expectedFouls)}</span>
                    <span className={s.xfLabel}>expected fouls</span>
                  </span>
                  <span className={s.top}>
                    <span className={s.topRow}>
                      <span className={s.topName}>{sum.topFouler.player}</span>
                      <span className={s.topVal}>{sum.topFouler.outOf100}</span>
                    </span>
                    <span className={s.topRow}>
                      <span className={s.topName}>{sum.topWinner.player}</span>
                      <span className={s.topVal}>{sum.topWinner.outOf100}</span>
                    </span>
                  </span>
                </>
              )}
            </button>
          );
        })}
      </div>

      {active && (
        <section className={s.detail}>
          <header className={s.detailHead}>
            <h3 className={s.detailTitle}>
              {active.home} <span className={s.v}>v</span> {active.away}
            </h3>
            <button className={s.close} onClick={() => setOpen(null)}>
              Close
            </button>
          </header>
          <FixtureBoard fixture={active} />
        </section>
      )}
    </div>
  );
}
