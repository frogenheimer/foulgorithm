"use client";

/**
 * The head-to-head stats sheet, mirrored around a centre column.
 *
 * Printed tip sheets set the two clubs as separate tables side by side, which
 * repeats every header twice and leaves the reader matching rows by eye. One
 * shared label down the middle does the same job with half the ink, and the
 * comparison it exists for becomes a glance rather than a search.
 *
 * Nothing on this page comes from a model. That is the whole point of it: this
 * is for the reader who would rather be handed the numbers than be told what to
 * back, and every figure here can be checked against a scoreboard.
 */

import { useState } from "react";
import type { Matchday, MatchdayFixture, TeamSheet } from "@/lib/data";
import Dots from "./Dots";
import s from "./matchday.module.css";

const ORDER = [
  "foulsFor",
  "foulsAgainst",
  "cardsFor",
  "cardsAgainst",
  "shotsFor",
  "shotsAgainst",
  "cornersFor",
  "cornersAgainst",
];

export default function Sheet({ data }: { data: Matchday }) {
  const [index, setIndex] = useState(0);
  const fixture = data.fixtures[index];
  if (!fixture) return null;

  return (
    <div className={s.wrap}>
      <div className={s.picker} role="tablist" aria-label="Fixture">
        {data.fixtures.map((f, i) => (
          <button
            key={f.home + f.away}
            type="button"
            role="tab"
            aria-selected={i === index}
            className={i === index ? s.pickOn : s.pick}
            onClick={() => setIndex(i)}
          >
            {f.home} <span className={s.v}>v</span> {f.away}
          </button>
        ))}
      </div>

      <Fixture fixture={fixture} window={data.window} />
    </div>
  );
}

function Fixture({ fixture, window }: { fixture: MatchdayFixture; window: number }) {
  const home = fixture.teams[fixture.home];
  const away = fixture.teams[fixture.away];
  const ref = fixture.referee;

  return (
    <div className={s.sheet}>
      {/* Header, caption and comparison share one column so the club names sit
          at the edges of the table rather than at the edges of the card, which
          left them stranded once the table stopped stretching. */}
      <div className={s.headline}>
      <header className={s.head}>
        <h2 className={s.club}>
          {fixture.home}
          {home.division !== "Premier League" && (
            <span className={s.division}>{home.division} record</span>
          )}
        </h2>
        <div className={s.ref}>
          <span className={s.refLabel}>Referee</span>
          <span className={s.refName}>{ref.name ?? "Not yet appointed"}</span>
          {ref.matches > 0 && (
            <span className={s.refStats}>
              {ref.foulsPerMatch} fouls · {ref.yellowsPerMatch} cards · {ref.matches} matches
            </span>
          )}
        </div>
        <h2 className={`${s.club} ${s.right}`}>
          {fixture.away}
          {away.division !== "Premier League" && (
            <span className={s.division}>{away.division} record</span>
          )}
        </h2>
      </header>

      {/* Outside the table, not as its caption. A caption's own text width
          feeds the table's preferred width, so this one line was dragging the
          whole comparison out to fill its container however the columns were
          sized. The caption stays for screen readers. */}
      <p className={s.caption}>
        Per match, and whether the line landed in each of the last {window}. Most
        recent on the left.
      </p>

      <div className={s.compareScroller}>
      <table className={s.compare}>
        <caption className={s.srOnly}>
          Fouls, cards, shots and corners per match for both clubs, with recent form
        </caption>
        <tbody>
          {ORDER.map((key) => (
            <Row key={key} k={key} home={home} away={away} window={window} />
          ))}
        </tbody>
      </table>
      </div>
      </div>

      {ref.matches > 0 && (
        <p className={s.refCaveat}>
          A referee&apos;s own numbers, not a referee effect. One assigned more derbies
          shows more cards without being stricter, and separating the two takes a model.
          This page does not use one.
        </p>
      )}

      <div className={s.split}>
        <Players side={home} name={fixture.home} window={window} />
        <Players side={away} name={fixture.away} window={window} align="right" />
      </div>
    </div>
  );
}

function Row({
  k,
  home,
  away,
  window,
}: {
  k: string;
  home: TeamSheet;
  away: TeamSheet;
  window: number;
}) {
  const h = home.averages[k];
  const a = away.averages[k];
  if (!h || !a) return null;
  const hf = home.form[k];
  const af = away.form[k];
  // Neither side is called better. Higher fouls is not worse, it is just more,
  // and which one a reader wants depends on what they came here for.
  const lead = h.value !== null && a.value !== null && h.value !== a.value
    ? (h.value > a.value ? "home" : "away")
    : null;

  return (
    <tr>
      <td className={`${s.val} ${lead === "home" ? s.lead : ""}`}>
        {h.value ?? "—"}
      </td>
      <td className={s.formCell}>
        <span className={s.form}>
          {hf && <Dots hits={hf.hits} window={window} label={`${h.label} over ${hf.line}`} />}
          {hf && <span className={s.line}>over {hf.line}</span>}
        </span>
      </td>
      <th scope="row" className={s.metric}>
        {h.label}
      </th>
      <td className={s.formCell}>
        <span className={`${s.form} ${s.rightForm}`}>
          {af && <span className={s.line}>over {af.line}</span>}
          {af && <Dots hits={af.hits} window={window} label={`${a.label} over ${af.line}`} />}
        </span>
      </td>
      <td className={`${s.val} ${s.right} ${lead === "away" ? s.lead : ""}`}>
        {a.value ?? "—"}
      </td>
    </tr>
  );
}

function Players({
  side,
  name,
  window,
  align,
}: {
  side: TeamSheet;
  name: string;
  window: number;
  align?: "right";
}) {
  if (!side.players.defensive.length && !side.players.offensive.length) {
    return (
      <section className={align ? `${s.players} ${s.right}` : s.players}>
        <h3 className={s.teamName}>{name}</h3>
        <p className={s.absent}>
          No player numbers for {name}. Second-tier data covers matches but not
          individual players, and it is not published anywhere at any price, so a club
          promoted this summer has a team record and no player record. The averages
          above are real; this part is genuinely missing rather than hidden.
        </p>
      </section>
    );
  }

  return (
    <section className={align ? `${s.players} ${s.right}` : s.players}>
      <h3 className={s.teamName}>{name}</h3>

      <h4 className={s.group}>Gives fouls away</h4>
      <div className={s.scroller}>
        <table className={s.playerTable}>
          <thead>
            <tr>
              <th className={s.left}>Player</th>
              <th>Mins</th>
              <th>Fouls</th>
              <th>Tackles</th>
              <th>Cards</th>
              <th className={s.left}>Last {window}</th>
            </tr>
          </thead>
          <tbody>
            {side.players.defensive.map((p) => (
              <tr key={p.player}>
                <td className={s.left}>
                  <span className={s.pName}>{p.player}</span>
                  {p.watch.length > 0 && (
                    <span className={s.watch}>
                      opposite {p.watch.join(", ")}
                    </span>
                  )}
                </td>
                <td>{p.minutes}&apos;</td>
                <td className={s.strong}>{p.foulsPer90}</td>
                <td>{p.tacklesPer90}</td>
                <td>{p.yellows}</td>
                <td className={s.left}>
                  <Dots hits={p.form.hits} window={window} label={`${p.player} 1+ fouls`} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h4 className={s.group}>Wins fouls</h4>
      <div className={s.scroller}>
        <table className={s.playerTable}>
          <thead>
            <tr>
              <th className={s.left}>Player</th>
              <th>Mins</th>
              <th>Won</th>
              <th className={s.left}>1+ won</th>
              <th className={s.left}>2+ won</th>
            </tr>
          </thead>
          <tbody>
            {side.players.offensive.map((p) => (
              <tr key={p.player}>
                <td className={s.left}>
                  <span className={s.pName}>{p.player}</span>
                </td>
                <td>{p.minutes}&apos;</td>
                <td className={s.strong}>{p.wonPer90}</td>
                <td className={s.left}>
                  <Dots hits={p.form.hits} window={window} label={`${p.player} 1+ fouls won`} />
                </td>
                <td className={s.left}>
                  <Dots hits={p.formTwo.hits} window={window} label={`${p.player} 2+ fouls won`} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
