import DistributionChart from "./components/DistributionChart";
import DotPlot from "./components/DotPlot";
import TrendChart from "./components/TrendChart";
import { getOverview } from "./lib/data";

export default function Home() {
  const d = getOverview();
  const h = d.headline;
  const cardsThen = d.seasons[0].cardsPerMatch;
  const cardsNow = d.seasons[d.seasons.length - 1].cardsPerMatch;
  const cardsChange = ((cardsNow - cardsThen) / cardsThen) * 100;
  const leagueMean = d.referees.reduce((a, r) => a + r.foulsPerMatch * r.matches, 0) /
    d.referees.reduce((a, r) => a + r.matches, 0);

  return (
    <div className="wrap">
      <header className="masthead">
        <div className="brand">
          <h1>Foulgorithm</h1>
          <span className="pill">Pre-alpha</span>
        </div>
        <p className="lede">
          Statistical models for Premier League fouls, cards and tackles. No model is running yet.
          What follows is the historical picture the model will be built on, drawn from{" "}
          {d.coverage.matches.toLocaleString()} matches across {d.coverage.seasons} seasons.
        </p>
      </header>

      <section>
        <div className="tiles">
          <div className="tile">
            <div className="label">Fouls per match now</div>
            <div className="value">{h.foulsPerMatchNow}</div>
            <div className="note">
              <span className="delta-down">{h.changePct}%</span> since {d.coverage.firstSeason}
            </div>
          </div>
          <div className="tile">
            <div className="label">Cards per match now</div>
            <div className="value">{cardsNow}</div>
            <div className="note">
              <span className="delta-up">+{cardsChange.toFixed(1)}%</span> since {d.coverage.firstSeason}
            </div>
          </div>
          <div className="tile">
            <div className="label">Matches analysed</div>
            <div className="value">{d.coverage.matches.toLocaleString()}</div>
            <div className="note">
              {d.coverage.firstSeason} to {d.coverage.lastSeason}
            </div>
          </div>
          <div className="tile">
            <div className="label">Away yellow card penalty</div>
            <div className="value">
              +{(((d.homeAway.awayYellows - d.homeAway.homeYellows) / d.homeAway.homeYellows) * 100).toFixed(0)}%
            </div>
            <div className="note">
              {d.homeAway.awayYellows} away vs {d.homeAway.homeYellows} home
            </div>
          </div>
        </div>
      </section>

      <section>
        <div className="section-head">
          <h2>Fouls are falling. Cards are not.</h2>
          <p>
            Both measures indexed to 100 in {d.coverage.firstSeason}, because fouls run at around 22 a
            match and cards at around 4. Putting them on one axis without indexing would flatten cards
            into a line along the floor, and giving them separate axes would let the scales be chosen to
            tell any story we liked.
          </p>
        </div>
        <div className="card">
          <TrendChart seasons={d.seasons} />
        </div>
        <p className="note-box" style={{ marginTop: 16 }}>
          Referees are calling {Math.abs(h.changePct)}% fewer fouls than in {d.coverage.firstSeason},
          while booking players {cardsChange.toFixed(0)}% more often. A foul in 2026 is more likely to be
          punished than a foul in 2000. That gap matters: a model trained on old seasons as though they
          were equal evidence would be wrong about both markets, which is why the model applies
          exponential time decay.
        </p>
      </section>

      <section>
        <div className="section-head">
          <h2>What a match actually looks like</h2>
          <p>
            Total fouls per match across all {d.coverage.matches.toLocaleString()} matches. Discrete,
            right-skewed and bounded at zero, which is why the model fits count distributions rather
            than a normal curve.
          </p>
        </div>
        <div className="card">
          <DistributionChart bins={d.distribution} />
        </div>
      </section>

      <section>
        <div className="section-head">
          <h2>Referees, {d.recentWindow}</h2>
          <p>
            Raw fouls per match, minimum 20 appearances. Treat this as an observation, not as a rating:
            these numbers are confounded by which teams each referee was assigned. Separating the
            referee from the fixture needs a model that estimates both at once, which is exactly what
            the 2025 version got wrong by dividing one average by another.
          </p>
        </div>
        <div className="card">
          <div className="chart-title">Fouls per match by referee</div>
          <div className="chart-sub">
            All {d.referees.length} referees with 20 or more appearances, against the league mean
          </div>
          <DotPlot
            unit="fouls per match"
            reference={leagueMean}
            referenceLabel="league mean"
            rows={d.referees.map((r) => ({
              label: r.referee,
              value: r.foulsPerMatch,
              sub: `${r.matches} matches · ${r.cardsPerMatch} yellows per match · ${
                r.vsLeague >= 1 ? "+" : ""
              }${((r.vsLeague - 1) * 100).toFixed(1)}% vs league mean`,
            }))}
          />
        </div>
      </section>

      <section>
        <div className="section-head">
          <h2>Teams, {d.recentWindow}</h2>
          <p>Fouls committed and fouls drawn per match, minimum 20 matches in the window.</p>
        </div>
        <div className="card scroll-x">
          <table>
            <thead>
              <tr>
                <th>Team</th>
                <th className="num">Matches</th>
                <th className="num">Fouls committed</th>
                <th className="num">Fouls drawn</th>
                <th className="num">Net</th>
              </tr>
            </thead>
            <tbody>
              {d.teams.map((t) => (
                <tr key={t.team}>
                  <td>{t.team}</td>
                  <td className="num">{t.matches}</td>
                  <td className="num">{t.committedPerMatch.toFixed(2)}</td>
                  <td className="num">{t.drawnPerMatch.toFixed(2)}</td>
                  <td className="num">
                    {(t.committedPerMatch - t.drawnPerMatch > 0 ? "+" : "") +
                      (t.committedPerMatch - t.drawnPerMatch).toFixed(2)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <footer>
        <p>
          Data from football-data.co.uk, generated {d.generatedAt.slice(0, 10)}. No model predictions are
          published yet. When they are, every one will be published before kickoff and graded afterwards,
          including the wrong ones.
        </p>
        <p>
          For entertainment and research. Not betting advice, and no outcome is guaranteed. 18+. Support
          is available from the National Gambling Helpline on 0808 8020 133.
        </p>
      </footer>
    </div>
  );
}
