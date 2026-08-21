import LineExplorer from "@/components/charts/LineExplorer";
import { Badge } from "@/components/ui";
import type { FixturePrediction } from "@/lib/data";
import { fouls, kickoff, odds, pct } from "@/lib/format";
import styles from "./fixture.module.css";

export default function FixtureCard({ fixture }: { fixture: FixturePrediction }) {
  const thin = fixture.thinEvidence.length > 0;

  return (
    <article className={styles.card}>
      <header className={styles.head}>
        <div>
          <h3 className={styles.teams}>
            {fixture.home} <span className={styles.v}>v</span> {fixture.away}
          </h3>
          <p className={styles.meta}>
            {kickoff(fixture.kickoff)}
            {fixture.referee && <> · {fixture.referee}</>}
          </p>
        </div>
        <div className={styles.expected}>
          <span className={styles.expectedLabel}>Expected fouls</span>
          <span className={styles.expectedValue}>{fouls(fixture.expectedFouls)}</span>
        </div>
      </header>

      {thin && (
        <div className={styles.warnRow}>
          <Badge tone="warn">Thin evidence</Badge>
          <span className={styles.warnText}>
            Leaning on the league average for {fixture.thinEvidence.join(", ")}. Treat this
            fixture as less certain than the others.
          </span>
        </div>
      )}

      <LineExplorer fixture={fixture} />

      <div className={styles.tableWrap}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Line</th>
              <th className={styles.num}>Over</th>
              <th className={styles.num}>Fair</th>
              <th className={styles.num}>Under</th>
              <th className={styles.num}>Fair</th>
            </tr>
          </thead>
          <tbody>
            {fixture.lines.map((l) => (
              <tr key={l.line}>
                <td>{l.line.toFixed(1)}</td>
                <td className={styles.num}>{pct(l.probOver)}</td>
                <td className={styles.num}>{odds(l.fairOddsOver)}</td>
                <td className={styles.num}>{pct(1 - l.probOver)}</td>
                <td className={styles.num}>{odds(l.fairOddsUnder)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </article>
  );
}
