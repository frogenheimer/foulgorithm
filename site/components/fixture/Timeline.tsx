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
import type { FixtureOption, SettledOption, SeasonFixture } from "@/lib/data";
import { fixtureSlug } from "@/lib/slug";
import { cardKind } from "@/lib/timeline";
import { Combobox } from "@/components/kit";
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
  options,
  settled,
}: {
  fixtures: SeasonFixture[];
  matchweeks: number[];
  currentMatchweek: number;
  /** fixture label -> expected total fouls, for the round we have modelled */
  expected: Record<string, number>;
  /** Fixtures with a page of their own. Only this round has one. */
  hasPage: Set<string>;
  /** One call per fixture, five fouls or more. */
  options: Record<string, FixtureOption[]>;
  settled: Record<string, { version: number; options: SettledOption[] }>;
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
      {/* A dropdown, not a scrolling row of thirty-eight buttons. The row put
          the whole season in a horizontally scrolling box where the current
          matchweek was usually off-screen, and marked it with a bare middle dot
          that meant nothing to anyone who had not been told. */}
      <div className={s.picker}>
        <Combobox
          value={week === "all" ? "all" : `${week}`}
          options={[
            { value: "all", label: "All matchweeks" },
            ...matchweeks.map((w) => ({
              value: `${w}`,
              label: `Matchweek ${w}`,
              meta: w === currentMatchweek ? "current" : undefined,
            })),
          ]}
          onChange={(v) => setWeek(v === "all" ? "all" : Number(v))}
          label="Which matchweek to show"
          placeholder="Search matchweeks"
          trigger={(open) => (
            <button type="button" className={s.weekTrigger} onClick={open}>
              <span className={s.weekLabel}>
                {week === "all" ? "All matchweeks" : `Matchweek ${week}`}
              </span>
              {week !== "all" && week === currentMatchweek && (
                <span className={s.weekNow}>current</span>
              )}
              <Chevron />
            </button>
          )}
        />
        {week === "all" && currentMatchweek != null && (
          <span className={s.weekNote}>Matchweek {currentMatchweek} is under way</span>
        )}
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
                    options={options[`${f.home} v ${f.away}`]}
                    settled={settled[`${f.home} v ${f.away}`]}
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

function Chevron() {
  return (
    <svg viewBox="0 0 12 12" width="10" height="10" aria-hidden>
      <path
        d="M3 4.5 6 7.5 9 4.5"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function Game({
  fixture: f,
  state,
  expected,
  linked,
  options,
  settled,
}: {
  fixture: SeasonFixture;
  state: State;
  expected?: number;
  linked: boolean;
  options?: FixtureOption[];
  settled?: { version: number; options: SettledOption[] };
}) {
  const label = `${f.home} v ${f.away}`;
  const cls = `${s.card} ${state === "past" ? s.past : ""} ${state === "live" ? s.live : ""}`;
  const kind = cardKind(state, Boolean(f.result), Boolean(options?.length));

  // The diet: kickoff, teams, expected fouls, the crossover as one line, one
  // link. The referee, the per-leg detail and the method sentence are one
  // click in. A played card keeps its result and the settled card, because a
  // loss must stay as visible as a win and past fixtures have no page yet.
  const head = (
    <>
      <div className={s.top}>
        <span>
          {new Date(f.kickoff).toLocaleTimeString("en-GB", {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </span>
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
    </>
  );

  const body = (
    <>
      {kind === "played" && f.result ? (
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

          {/* What the card said, marked against what happened. Only fixtures we
              recorded a card for before kickoff appear here. */}
          {settled?.options.length ? (
            <ul className={s.settled}>
              {settled.options.map((o) => (
                <li
                  key={o.band}
                  className={[
                    s.settledRow,
                    o.landed === true ? s.landed : "",
                    o.landed === false ? s.missed : "",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                >
                  <span className={s.settledOdds}>{o.odds.toFixed(2)}</span>
                  <span className={s.settledLegs}>
                    {o.legs.map((l) => (
                      <span
                        key={`${l.player}-${l.fouls}`}
                        className={
                          l.landed === true
                            ? s.legLanded
                            : l.landed === false
                              ? s.legMissed
                              : s.legOpen
                        }
                      >
                        {l.player} {l.fouls}+
                      </span>
                    ))}
                  </span>
                  <span className={s.settledMark}>
                    {o.landed === true ? "came in" : o.landed === false ? "no" : "open"}
                  </span>
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : kind === "crossover" && options?.length ? (
        <div className={s.picks}>
          {options.map((o) => (
            <div key={o.band} className={s.pick}>
              <span className={s.pickRow}>
                <span className={s.pickWho}>
                  The five&rsquo;s crossover
                  {o.lineupsConfirmed === false ? "\u2009*" : ""}
                </span>
                <span className={s.pickSummary}>
                  {o.legs.length} pick{o.legs.length === 1 ? "" : "s"}
                </span>
                <span className={s.pickOdds}>{o.outOf100}/100</span>
              </span>
              {expected ? (
                <span className={s.expected}>{expected.toFixed(1)} fouls expected</span>
              ) : null}
              {o.lineupsConfirmed === false && (
                <span className={s.pickMeta}>
                  * built before the team sheets: regenerates automatically when the
                  lineups land, an hour before kickoff
                </span>
              )}
            </div>
          ))}
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
  // that is not there yet. With the disclosures gone the card holds no
  // interactive content, so the whole card is the link; reintroducing a
  // <details> inside it would mean splitting the link up again, because
  // interactive content inside an <a> is invalid and swallows the click.
  return linked ? (
    <Link href={`/fixture/${fixtureSlug(label)}`} className={`${cls} ${s.cardLink}`}>
      {head}
      {body}
    </Link>
  ) : (
    <div className={cls}>
      {head}
      {body}
    </div>
  );
}
