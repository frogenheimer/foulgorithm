/**
 * The round, at a glance, grouped by day.
 *
 * This is the first thing on the site and it is deliberately not a
 * recommendation. It answers "what is on" and "which of these looks busy",
 * then gets out of the way. The read on any single game lives one click deeper,
 * on a page with its own URL.
 */

import Link from "next/link";
import type { FixtureBoard } from "@/lib/data";
import { fixtureSlug } from "@/lib/data";
import s from "./fixtures.module.css";

export default function FixtureCards({
  fixtures,
  expected,
}: {
  fixtures: FixtureBoard[];
  /** fixture label -> expected total fouls, from the house model */
  expected: Record<string, number>;
}) {
  const byDay = new Map<string, FixtureBoard[]>();
  for (const f of fixtures) {
    const day = new Date(f.kickoff).toLocaleDateString("en-GB", {
      weekday: "long",
      day: "numeric",
      month: "long",
    });
    byDay.set(day, [...(byDay.get(day) ?? []), f]);
  }

  return (
    <div style={{ display: "grid", gap: "var(--s6)" }}>
      {[...byDay].map(([day, games]) => (
        <section key={day}>
          <h3 className={s.day}>{day}</h3>
          <div className={s.grid}>
            {games.map((f) => {
              const label = `${f.home} v ${f.away}`;
              const total = expected[label];
              return (
                <Link key={label} href={`/fixture/${fixtureSlug(label)}`} className={s.card}>
                  <div className={s.when}>
                    <span>
                      {new Date(f.kickoff).toLocaleTimeString("en-GB", {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                    <span>{f.referee ?? "No referee yet"}</span>
                  </div>

                  <div className={s.teams}>
                    <span className={s.team}>{f.home}</span>
                    <span className={s.team}>{f.away}</span>
                  </div>

                  <div className={s.foot}>
                    {f.lineupConfirmed ? (
                      <span className={s.confirmed}>
                        <span className={s.dot} aria-hidden />
                        XI confirmed
                      </span>
                    ) : (
                      <span>XI predicted</span>
                    )}
                    {total ? (
                      <span className={s.expected}>{total.toFixed(1)} fouls</span>
                    ) : (
                      <span className={s.go}>Open &rarr;</span>
                    )}
                  </div>
                </Link>
              );
            })}
          </div>
        </section>
      ))}
    </div>
  );
}
