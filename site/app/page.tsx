import Portrait, { CHARACTER_COLOUR } from "@/components/characters/Portrait";
import { getPlayers } from "@/lib/data";
import { count, kickoff, odds } from "@/lib/format";
import s from "./today.module.css";

export default function Today() {
  const d = getPlayers();
  const t = d.trainedOn;
  const lead = d.topFoulers[0];

  return (
    <div className={s.page}>
      <section className={s.hero}>
        <p className={s.eyebrow}>The next matchday</p>
        <h1 className={s.h1}>Who gives away fouls</h1>
        {/* Lead with a frequency and its complement, not a bare probability.
            "In 68 of 100" is read correctly far more often than "68% chance". */}
        <p className={s.answer}>
          The model&apos;s strongest read is <strong>{lead.player}</strong>. In{" "}
          <strong>{lead.committed.outOf100} of 100</strong> matches like this one he commits at
          least one foul. In the other {100 - lead.committed.outOf100}, he does not.
        </p>
        <p className={s.sub}>
          Squads are today&apos;s, taken live from the league&apos;s own data, so transfers and
          injuries are already accounted for. Foul rates come from{" "}
          {count(t.playerMatches)} player-matches, {t.from} to {t.to}. Every price is what a bet
          would need to pay to be worth taking, not a price anyone is offering.
        </p>
      </section>

      <section>
        <h2 className={s.h2}>Most likely to commit a foul</h2>
        <p className={s.note}>Ranked across every fixture in the round.</p>
        <ol className={s.leaders}>
          {d.topFoulers.slice(0, 8).map((r, i) => (
            <li key={r.player + r.fixture} className={s.leader} style={{ "--i": i } as React.CSSProperties}>
              <span className={s.rank}>{i + 1}</span>
              <span className={s.who}>
                <span className={s.name}>{r.player}</span>
                <span className={s.meta}>
                  {r.position && `${r.position} · `}{r.team} · {r.fixture} ·{" "}
                  {Math.round(r.expectedMinutes)} min expected
                </span>
              </span>
              <span className={s.freq}>
                <Dots p={r.committed.p1plus} />
                <span className={s.freqText}>
                  <strong>{r.committed.outOf100}</strong> of 100
                </span>
              </span>
              <span className={s.bandCol}>{r.committed.band1}</span>
              <span className={s.floorCol}>
                <span className={s.floorLabel}>take at</span>
                {odds(r.committed.floor1 ?? 0)}+
              </span>
            </li>
          ))}
        </ol>
      </section>

      <section>
        <h2 className={s.h2}>The five, and what each would back</h2>
        <p className={s.note}>
          Five algorithms built around five temperaments, all seeing the same players and the same
          history. Each builds a five-pick slip constrained to a similar combined return, so nobody
          wins simply by picking easier bets. <strong>vs pack</strong> is the gap between what this
          character makes it and what the other four do, which is where it backs its temperament
          against the room.
        </p>
        <div className={s.picksGrid}>
          {d.picks.map((c) => (
            <article key={c.id} className={s.charCard}>
              <header className={s.charHead}>
                <Portrait id={c.id} size={52} label={c.name} />
                <div>
                  <h3 className={s.charName} style={{ color: CHARACTER_COLOUR[c.id] }}>
                    {c.name}
                  </h3>
                  <p className={s.charEmotion}>{c.emotion}</p>
                </div>
                <dl className={s.charStats}>
                  <div>
                    <dt>Average</dt>
                    <dd>{Math.round(c.averageProb * 100)}%</dd>
                  </div>
                  <div>
                    <dt>All five land</dt>
                    <dd>
                      {c.combinedFair ? `${c.combinedFair}/1` : "—"}
                      {!c.inBand && <span className={s.outBand} title="Could not reach the target band">*</span>}
                    </dd>
                  </div>
                  <div>
                    <dt>vs pack</dt>
                    <dd>{c.averageEdge >= 0 ? "+" : ""}{Math.round(c.averageEdge * 100)}</dd>
                  </div>
                </dl>
              </header>
              <ul className={s.pickList}>
                {c.picks.map((p) => (
                  <li key={p.player} className={s.pick}>
                    <span className={s.pickPlayer}>
                      {p.player}
                      {p.thin && <span className={s.thin} title="Thin evidence">thin</span>}
                    </span>
                    <span className={s.pickMarket}>
                      {p.line + 0.5}+ {p.market === "committed" ? "fouls" : "fouls drawn"}
                    </span>
                    <span className={s.pickProb}>
                      {p.outOf100}
                      <span className={s.pack}> vs {Math.round(p.packProb * 100)}</span>
                    </span>
                    <span className={s.pickFloor}>{odds(p.floor)}+</span>
                  </li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </section>

      <section>
        <h2 className={s.h2}>Every player, every fixture</h2>
        <p className={s.note}>
          Both squads side by side. Chance of committing at least 1, 2 or 3 fouls, and the price
          each would need to pay to be worth backing.
        </p>
        {d.board.map((fx) => (
          <details key={fx.key} name="board" className={s.fixture}>
            <summary className={s.summary}>
              <span className={s.chev} aria-hidden="true">›</span>
              <span className={s.fxName}>
                {fx.home} v {fx.away}
              </span>
              <span className={s.fxMeta}>
                {kickoff(fx.kickoff)}
                {fx.referee && ` · ${fx.referee}`}
              </span>
            </summary>
            <div className={s.teams}>
              {Object.entries(fx.teams).map(([team, players]) => (
                <div key={team} className={s.teamCol}>
                  <h4 className={s.teamName}>{team}</h4>
                  <div className="scroll-x">
                    <table className={s.table}>
                      <thead>
                        <tr>
                          <th>Player</th>
                          <th>Pos</th>
                          <th className={s.num}>Min</th>
                          <th className={s.num}>1+</th>
                          <th className={s.num}>2+</th>
                          <th className={s.num}>3+</th>
                          <th className={s.num}>Take 1+ at</th>
                        </tr>
                      </thead>
                      <tbody>
                        {players.map((p) => (
                          <tr key={p.player} className={p.thin ? s.thinRow : undefined}>
                            <td>{p.player}</td>
                            <td className="muted">{p.position ?? ""}</td>
                            <td className={s.num}>{Math.round(p.expectedMinutes)}</td>
                            <td className={s.num}>{Math.round(p.committed.p1plus * 100)}</td>
                            <td className={s.num}>{Math.round(p.committed.p2plus * 100)}</td>
                            <td className={s.num}>{Math.round(p.committed.p3plus * 100)}</td>
                            <td className={s.num}>{odds(p.committed.floor1 ?? 0)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ))}
            </div>
          </details>
        ))}
      </section>

      <details className={s.machinery}>
        <summary className={s.machinerySummary}>
          <span className={s.chev} aria-hidden="true">›</span> How we worked this out
        </summary>
        <div className={s.machineryBody}>
          <p>
            Each player carries a fouls-per-90 rate, weighted so recent matches count more and
            shrunk toward the league average in proportion to how little we know about him. That
            rate is multiplied by his expected minutes, then adjusted for the opponent.
          </p>
          <p>
            Prices are the <strong>minimum</strong> a bet must pay to be worth taking, set{" "}
            {Math.round(d.edgeMargin * 100)}% above break-even. Backing at exactly fair odds returns
            nothing in expectation, so the margin is the point.
          </p>
          <p>
            Band words are pinned: &ldquo;likely&rdquo; always means 55 to 75%, and never anything
            else. Players marked <em>thin</em> have too little recent history to be more than a
            positional average wearing a name. Rates are shrunk toward the player&apos;s position,
            not the league, so a goalkeeper is never assumed to foul like a midfielder.
          </p>
          <p>
            Each character&apos;s five picks are constrained to a similar combined return, so a
            cautious character cannot win by picking near-certainties. A star next to the return
            means that character could not reach the band with picks it actually believed in.
          </p>
          <p>
            Squads come from the {d.squads.source}: {d.squads.players} players across all 20 clubs,
            updated continuously, so a player who has transferred or is injured never reaches a
            prediction. Of those, {d.squads.resolved} are matched to a foul record. The rest are new
            enough to the league that we fall back to their position&apos;s average and mark them
            thin, rather than guessing from a similar name.
          </p>
          <p className={s.muted}>
            Generated {d.generatedAt.slice(0, 10)}. No prediction here has settled yet, so there is
            no accuracy record to show. There will be.
          </p>
        </div>
      </details>
    </div>
  );
}

/** 20 dots. Counting beats judging an area, which is why this is not a bar. */
function Dots({ p }: { p: number }) {
  const filled = Math.round(p * 20);
  return (
    <span className={s.dots} aria-hidden="true">
      {Array.from({ length: 20 }, (_, i) => (
        <i key={i} className={i < filled ? s.dotOn : s.dotOff} />
      ))}
    </span>
  );
}
