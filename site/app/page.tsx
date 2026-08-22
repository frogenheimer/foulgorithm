import Link from "next/link";
import FixtureGrid from "@/components/FixtureGrid";
import LeagueRail from "@/components/LeagueRail";
import { DotArray } from "@/components/charts/pack";
import Portrait, { CHARACTER_COLOUR } from "@/components/characters/Portrait";
import Disagreement from "@/components/charts/Disagreement";
import { getCharacters, getPlayers } from "@/lib/data";
import { count, kickoff, odds } from "@/lib/format";
import s from "./today.module.css";

export default function Today() {
  const d = getPlayers();
  const t = d.trainedOn;
  const lead = d.topFoulers[0];
  const chars = getCharacters();

  return (
    <div className={s.page}>
      <section className={s.hero}>
        <p className={s.eyebrow}>The next matchday</p>
        <h1 className={s.h1}>Who gives away fouls</h1>
        <p className={s.answer}>
          Calibrated probabilities for Premier League fouls, published before kickoff and
          graded afterwards. Nothing is hidden when it goes wrong, which is most of what
          separates this from a tipster account.
        </p>
        <p className={s.sub}>
          Squads are today&apos;s, taken live from the league&apos;s own data, so transfers and
          injuries are already accounted for. Foul rates come from {count(t.playerMatches)}{" "}
          player-matches, {t.from} to {t.to}. Every price is what a bet would need to pay to be
          worth taking, not a price anyone is offering.
        </p>
      </section>

      {/* Three ways in, because they answer different questions and a reader
          arriving cold cannot tell which one they want from a nav icon. */}
      <nav className={s.routes} aria-label="Where to start">
        <Link href="/stats" className={s.route}>
          <span className={s.routeLabel}>Just the numbers</span>
          <span className={s.routeBody}>
            Both clubs side by side, fouls, cards, shots, referee. No model anywhere near it.
          </span>
          <span className={s.routeGo}>The stats sheet</span>
        </Link>
        <Link href="/players" className={s.route}>
          <span className={s.routeLabel}>What we think will happen</span>
          <span className={s.routeBody}>
            Every player, fouls conceded, won and both together. Filter it however you like.
          </span>
          <span className={s.routeGo}>Players</span>
        </Link>
        <Link href="/record" className={s.route}>
          <span className={s.routeLabel}>Whether we have been right</span>
          <span className={s.routeBody}>
            Every published call, graded. Including the ones that lost.
          </span>
          <span className={s.routeGo}>Track record</span>
        </Link>
      </nav>

      <div className={s.split}>
        <div className={s.mainCol}>
      <section>
        <h2 className={s.h2}>Most likely to commit a foul</h2>
        <p className={s.note}>
          Ranked across every fixture in the round. The strongest read is{" "}
          <strong>{lead.player}</strong>: in {lead.committed.outOf100} of 100 matches like this
          one he commits at least one foul, and in the other {100 - lead.committed.outOf100} he
          does not.
        </p>
        <ol className={s.leaders}>
          {d.topFoulers.slice(0, 8).map((r, i) => (
            <li key={r.player + r.fixture} className={s.leader} style={{ "--i": i } as React.CSSProperties}>
              <span className={s.rank}>{i + 1}</span>
              <span className={s.who}>
                <span className={s.name}>{r.player}</span>
                <span className={s.meta}>
                  {r.position && `${r.position} · `}{r.fixture} ·{" "}
                  {Math.round(r.expectedMinutes)}&apos;
                </span>
              </span>
              <span className={s.freq}>
                <DotArray p={r.committed.p1plus} label={`${r.player} commits a foul`} />
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
        <h2 className={s.h2}>Where the models disagree</h2>
        <p className={s.note}>
          All five see identical evidence. Agreement tells you nothing; the gaps are the
          interesting part, and by Tuesday one of them will have been closer.
        </p>
        <Disagreement
          rows={chars.disagreement}
          characters={chars.characters.map((c) => ({ id: c.id, name: c.name }))}
        />
      </section>

        </div>
        <LeagueRail data={d.leagueLeaders} />
      </div>

      <section>
        <h2 className={s.h2}>Five readings of the same evidence</h2>
        <p className={s.note}>
          Five algorithms with five temperaments, seeing the same players and the same history.
          Each builds a slip at <strong>2/1, 3/1, 5/1 and 10/1</strong>, so they are compared at
          matched risk rather than at whatever risk their temperament happened to produce. A
          cautious one cannot look better by picking near-certainties, and a bold one cannot look
          better by reaching. <strong>vs pack</strong> is the gap between this character and the
          other four.
          <br />
          <br />
          Those prices are <strong>our own</strong>, not a bookmaker&apos;s. No archive of real odds
          for these markets exists to buy, so we cannot compare against the market and do not
          pretend to.
          <br />
          <br />
          Worth being straight about the size of that gap. Backtested over 13,993 predictions, the
          five separate by only <strong>1.9%</strong> on fouls committed. They all beat a model
          knowing nothing but position and minutes, by about 4%, so the history genuinely matters.
          But they are five slightly different readings, not five sharply different opinions, and
          we would rather say so than let the portraits imply otherwise.
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
              <div className={s.tierList}>
                {c.tiers.map((t) => (
                  <details key={t.target} className={s.tier}>
                    <summary className={s.tierSummary}>
                      <span className={s.chev} aria-hidden="true">›</span>
                      <span className={s.tierTarget}>{t.target.toFixed(0)}/1</span>
                      <span className={s.tierLegs}>{t.legs.length} legs</span>
                      <span className={s.tierProb}>{t.outOf100}/100</span>
                    </summary>
                    <ul className={s.tierBody}>
                      {t.legs.map((l) => (
                        <li key={l.player}>
                          <span className={s.legName}>
                            {l.player}
                            {l.thin && <span className={s.thin}>thin</span>}
                          </span>
                          <span className={s.legMarket}>
                            {l.fouls}+ {l.market === "committed" ? "fouls" : "won"}
                          </span>
                          <span className={s.legProb}>
                            {l.outOf100}
                            <span className={s.pack}> vs {Math.round(l.packProb * 100)}</span>
                          </span>
                        </li>
                      ))}
                    </ul>
                  </details>
                ))}
              </div>
            </article>
          ))}
        </div>
      </section>

      <section>
        <h2 className={s.h2}>Every player, every fixture</h2>
        <p className={s.note}>
          Pick a day, then a fixture. Each opens a head-to-head comparison, the full squads with
          search and sorting, and the likeliest combination reaching 4, 5 or 6 fouls.
        </p>
        <FixtureGrid fixtures={d.board} />
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
          <p>
            {d.lineups.confirmed > 0
              ? `${d.lineups.confirmed} confirmed team sheets are in, taken from the ${d.lineups.source}. `
              : `No team sheets are confirmed yet. `}
            {d.lineups.note} A fixture showing <em>XI confirmed</em> is predicted from the actual
            eleven; every other fixture is predicted from the current squad, which is a weaker thing
            and is marked as such.
          </p>
          <p className={s.muted}>
            Generated {d.generatedAt.slice(0, 10)}. Every call published here is graded once the
            match settles, and the results are on the <Link href="/record">track record</Link>,
            good weeks and bad.
          </p>
        </div>
      </details>
    </div>
  );
}
