"use client";

/**
 * The season as a chronological run: played behind you, live now, ahead below.
 *
 * A list of fixtures answers "what is on". A timeline answers "where are we",
 * which is what someone opens this with on a Saturday afternoon. The spine down
 * the left is what makes scrolling read as moving through time rather than
 * through rows.
 *
 * A played match shows what actually happened, not just that it did: the score
 * and the three numbers this site is about. Those come from the league's own
 * team stats, so they are the result rather than an estimate of it.
 *
 * State is a word and a shape as well as a colour, so it survives greyscale.
 * One thing animates: a match in progress is the only element on the page
 * changing while you look at it.
 */

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import type { SeasonFixture } from "@/lib/data";
import { fixtureSlug } from "@/lib/slug";
import s from "./timeline.module.css";

type State = "past" | "live" | "upcoming";

/** A match runs about 115 minutes including the interval. */
const MATCH_MINUTES = 115;

export default function Timeline({
  fixtures,
  matchweeks,
  currentMatchweek,
  expected,
  hasPage,
}: {
  fixtures: SeasonFixture[];
  matchweeks: number[];
  currentMatchweek: number;
  /** fixture label -> expected total fouls, for the round we have modelled */
  expected: Record<string, number>;
  /** Fixtures with a page of their own. Only this round has one. */
  hasPage: Set<string>;
}) {
  const [week, setWeek] = useState<number | "all">("all");

  // Rendered before the clock is known, so everything starts as upcoming and
  // settles on mount. Deciding on the server would bake the deploy's clock into
  // a static page and call a finished match upcoming until the next build.
  const [now, setNow] = useState<number | null>(null);
  useEffect(() => {
    setNow(Date.now());
    const t = setInterval(() => setNow(Date.now()), 60_000);
    return () => clearInterval(t);
  }, []);

  const stateOf = (f: SeasonFixture): State => {
    if (f.status === "C") return "past";
    if (now === null) return "upcoming";
    const start = new Date(f.kickoff).getTime();
    if (now < start) return "upcoming";
    return now < start + MATCH_MINUTES * 60_000 ? "live" : "past";
  };

  const shown = useMemo(
    () => (week === "all" ? fixtures : fixtures.filter((f) => f.matchweek === week)),
    [fixtures, week]
  );

  const days = useMemo(() => {
    const out = new Map<string, SeasonFixture[]>();
    for (const f of [...shown].sort((a, b) => a.kickoff.localeCompare(b.kickoff))) {
      const key = new Date(f.kickoff).toLocaleDateString("en-GB", {
        weekday: "long",
        day: "numeric",
        month: "long",
      });
      out.set(key, [...(out.get(key) ?? []), f]);
    }
    return out;
  }, [shown]);

  const today =
    now === null
      ? ""
      : new Date(now).toLocaleDateString("en-GB", {
          weekday: "long",
          day: "numeric",
          month: "long",
        });

  return (
    <div>
      <div className={s.picker}>
        <div className={s.weeks}>
          <button
            type="button"
            className={week === "all" ? s.weekOn : s.week}
            onClick={() => setWeek("all")}
          >
            All matchweeks
          </button>
          {matchweeks.map((w) => (
            <button
              key={w}
              type="button"
              className={week === w ? s.weekOn : s.week}
              onClick={() => setWeek(w)}
            >
              MW{w}
              {w === currentMatchweek ? " ·" : ""}
            </button>
          ))}
        </div>
      </div>

      <div className={s.wrap}>
        {[...days].map(([day, games]) => {
          const live = games.filter((g) => stateOf(g) === "live").length;
          const done = games.filter((g) => stateOf(g) === "past").length;
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
                {games.map((f) => (
                  <Game
                    key={`${f.home}-${f.away}-${f.kickoff}`}
                    fixture={f}
                    state={stateOf(f)}
                    expected={expected[`${f.home} v ${f.away}`]}
                    linked={hasPage.has(`${f.home} v ${f.away}`)}
                  />
                ))}
              </div>
            </section>
          );
        })}
      </div>
    </div>
  );
}

function Game({
  fixture: f,
  state,
  expected,
  linked,
}: {
  fixture: SeasonFixture;
  state: State;
  expected?: number;
  linked: boolean;
}) {
  const label = `${f.home} v ${f.away}`;
  const cls = `${s.card} ${state === "past" ? s.past : ""} ${state === "live" ? s.live : ""}`;

  const body = (
    <>
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
        <span className={s.row}>
          {f.home}
          {f.score && <span className={s.score}>{f.score[0]}</span>}
        </span>
        <span className={s.row}>
          {f.away}
          {f.score && <span className={s.score}>{f.score[1]}</span>}
        </span>
      </div>

      {f.result ? (
        <div className={s.result}>
          <div className={s.stats}>
            <span>
              Fouls{" "}
              <span className={s.statValue}>
                {f.result.home?.fouls ?? "—"}&ndash;{f.result.away?.fouls ?? "—"}
              </span>
            </span>
            <span>
              Cards{" "}
              <span className={s.statValue}>
                {f.result.home?.cards ?? 0}&ndash;{f.result.away?.cards ?? 0}
              </span>
            </span>
            {expected ? (
              <span>
                We said <span className={s.statValue}>{expected.toFixed(0)}</span>
              </span>
            ) : null}
          </div>
        </div>
      ) : (
        <div className={s.foot}>
          {state === "live" ? (
            <span className={`${s.state} ${s.liveState}`}>
              <span className={s.dot} aria-hidden />
              Under way
            </span>
          ) : state === "past" ? (
            <span className={s.state}>Played</span>
          ) : (
            <span className={s.state}>{linked ? "Modelled" : "Not yet modelled"}</span>
          )}
          {expected ? <span className={s.expected}>{expected.toFixed(1)} fouls</span> : null}
        </div>
      )}
    </>
  );

  // Only this round has a page. Linking the rest would be a promise of depth
  // that is not there yet.
  return linked ? (
    <Link href={`/fixture/${fixtureSlug(label)}`} className={cls}>
      {body}
    </Link>
  ) : (
    <div className={cls}>{body}</div>
  );
}
