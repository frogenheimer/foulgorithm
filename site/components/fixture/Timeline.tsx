"use client";

/**
 * The round as a chronological run: played behind you, live now, ahead below.
 *
 * A list of fixtures answers "what is on". A timeline answers "where are we",
 * which is the question someone actually opens this with on a Saturday
 * afternoon. The spine down the left is what makes scrolling read as moving
 * through time rather than through rows.
 *
 * State is carried by a word and a shape as well as a colour, so it survives
 * greyscale and colour blindness. One thing animates: the live marker, because
 * a match in progress is the only thing on the page changing while you look at
 * it. Everything else arrives once on scroll and then stays put.
 */

import Link from "next/link";
import { useEffect, useState } from "react";
import type { FixtureBoard } from "@/lib/data";
import { fixtureSlug } from "@/lib/slug";
import s from "./timeline.module.css";

type State = "past" | "live" | "upcoming";

/** A Premier League match runs about 115 minutes including the interval. */
const MATCH_MINUTES = 115;

export default function Timeline({
  fixtures,
  expected,
}: {
  fixtures: FixtureBoard[];
  expected: Record<string, number>;
}) {
  // Rendered on the server before the clock is known, so every fixture starts
  // as upcoming and settles once mounted. Deciding on the server would bake a
  // build-time "now" into a static page and call a finished match upcoming for
  // as long as the deploy lasted.
  const [now, setNow] = useState<number | null>(null);
  useEffect(() => {
    setNow(Date.now());
    const t = setInterval(() => setNow(Date.now()), 60_000);
    return () => clearInterval(t);
  }, []);

  const stateOf = (kickoff: string): State => {
    if (now === null) return "upcoming";
    const start = new Date(kickoff).getTime();
    if (now < start) return "upcoming";
    return now < start + MATCH_MINUTES * 60_000 ? "live" : "past";
  };

  const days = new Map<string, FixtureBoard[]>();
  for (const f of [...fixtures].sort((a, b) => a.kickoff.localeCompare(b.kickoff))) {
    const key = new Date(f.kickoff).toLocaleDateString("en-GB", {
      weekday: "long",
      day: "numeric",
      month: "long",
    });
    days.set(key, [...(days.get(key) ?? []), f]);
  }

  const today =
    now === null
      ? ""
      : new Date(now).toLocaleDateString("en-GB", {
          weekday: "long",
          day: "numeric",
          month: "long",
        });

  return (
    <div className={s.wrap}>
      {[...days].map(([day, games]) => {
        const live = games.filter((g) => stateOf(g.kickoff) === "live").length;
        const done = games.filter((g) => stateOf(g.kickoff) === "past").length;
        return (
          <section key={day} className={day === today ? `${s.day} ${s.today}` : s.day}>
            <h3 className={s.dayLabel}>
              {day}
              <span className={s.dayMeta}>
                {live > 0
                  ? `${live} under way`
                  : done === games.length
                    ? "all played"
                    : `${games.length} fixture${games.length === 1 ? "" : "s"}`}
              </span>
            </h3>

            <div className={s.games}>
              {games.map((f) => {
                const label = `${f.home} v ${f.away}`;
                const state = stateOf(f.kickoff);
                const total = expected[label];
                return (
                  <Link
                    key={label}
                    href={`/fixture/${fixtureSlug(label)}`}
                    className={`${s.card} ${state === "past" ? s.past : ""} ${
                      state === "live" ? s.live : ""
                    }`}
                  >
                    <div className={s.top}>
                      <span>
                        {new Date(f.kickoff).toLocaleTimeString("en-GB", {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </span>
                      <span>{f.referee ?? "No referee yet"}</span>
                    </div>

                    <div className={s.teams}>
                      <span className={s.row}>{f.home}</span>
                      <span className={s.row}>{f.away}</span>
                    </div>

                    <div className={s.foot}>
                      {state === "live" ? (
                        <span className={`${s.state} ${s.liveState}`}>
                          <span className={s.dot} aria-hidden />
                          Under way
                        </span>
                      ) : state === "past" ? (
                        <span className={s.state}>Played</span>
                      ) : f.lineupConfirmed ? (
                        <span className={`${s.state} ${s.confirmedState}`}>
                          <span className={s.dot} aria-hidden />
                          XI confirmed
                        </span>
                      ) : (
                        <span className={s.state}>XI predicted</span>
                      )}
                      {total ? (
                        <span className={s.expected}>{total.toFixed(1)} fouls</span>
                      ) : null}
                    </div>
                  </Link>
                );
              })}
            </div>
          </section>
        );
      })}
    </div>
  );
}
