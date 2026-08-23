import Link from "next/link";
import Timeline from "@/components/fixture/Timeline";
import { Card, Metric, MetricRow, PageHeader, SectionHead } from "@/components/kit";
import { getPlayers, getSeason, getTrackRecord } from "@/lib/data";
import { count } from "@/lib/format";

export default function Today() {
  const d = getPlayers();
  const record = getTrackRecord();
  const season = getSeason();
  const t = d.trainedOn;
  const lead = d.topFoulers[0];

  // Expected total fouls per fixture: the likely eleven from each side, added.
  //
  // Eleven PER TEAM, not twenty-two off a combined list. A confirmed fixture
  // carries exactly eleven a side and an unconfirmed one carries fourteen, so
  // slicing the flattened list took fourteen from the home side and eight from
  // the away side and made every unconfirmed fixture look quiet.
  const expected: Record<string, number> = {};
  for (const f of d.board) {
    const label = `${f.home} v ${f.away}`;
    expected[label] = Object.values(f.teams).reduce(
      (total, squad) =>
        total +
        squad
          .slice(0, 11)
          .reduce((a, p) => a + (p.committed?.why?.expected_fouls ?? 0), 0),
      0
    );
  }

  const house = record?.models?.house;

  return (
    <div className="stack">
      <PageHeader
        title="Today"
        lede={
          <>
            Calibrated probabilities for Premier League fouls, published before kickoff and
            graded afterwards. Pick a fixture for both clubs&apos; records side by side and
            what each of the five makes of it.
          </>
        }
      />

      <section>
        <Timeline
          fixtures={season.fixtures}
          matchweeks={season.matchweeks}
          currentMatchweek={season.currentMatchweek}
          expected={expected}
          hasPage={new Set(Object.keys(d.fixtureSlips))}
        />
      </section>

      <section>
        <SectionHead
          title="Where we stand"
          note={
            <>
              Foul rates from {count(t.playerMatches)} player-matches, {t.from} to {t.to}.
              Squads are today&apos;s, taken live from the league&apos;s own data, so
              transfers and injuries are already accounted for.
            </>
          }
        />
        <MetricRow>
          <Metric
            label="Strongest read"
            value={`${lead.committed.outOf100}/100`}
            tone={1}
            note={`${lead.player} commits at least one foul, ${lead.fixture}`}
          />
          <Metric
            label="Lineups confirmed"
            value={`${d.lineups.confirmed} of ${d.board.length}`}
            tone={2}
            note="Confirmed elevens land about an hour before kickoff"
          />
          {house ? (
            <Metric
              label="Graded so far"
              value={String(house.n)}
              note={
                <>
                  We said {(house.claimed * 100).toFixed(0)}%, it happened{" "}
                  {(house.actual * 100).toFixed(0)}%.{" "}
                  <Link href="/record">Track record</Link>
                </>
              }
            />
          ) : (
            <Metric
              label="Graded so far"
              value="0"
              note="Nothing has settled yet. It will, and the losses stay up."
            />
          )}
        </MetricRow>
      </section>

      <section>
        <Card
          title="What this is, and what it is not"
          subtitle="Worth reading once before trusting a number on this site."
        >
          <div style={{ display: "grid", gap: "var(--s3)", maxWidth: "var(--w-prose)", fontSize: "var(--t-sm)", color: "var(--ink-2)", lineHeight: 1.7 }}>
            <p>
              Every price here is <strong>our own</strong>. No archive of real odds for
              player foul markets exists to buy, and no bookmaker publishes one we can
              reach, so we never claim to have beaten a market. Where a bookmaker price is
              shown it is an estimate with the margin stated.
            </p>
            <p>
              The five characters see identical evidence and separate by about{" "}
              <strong>2%</strong> on player markets. They are five slightly different
              readings, not five sharply different opinions, and we would rather say so
              than let five portraits imply otherwise.
            </p>
            <p>
              Every prediction is graded once the match settles and{" "}
              <Link href="/record">the record</Link> keeps the bad weeks. That is most of
              what separates this from a tipster account.
            </p>
          </div>
        </Card>
      </section>
    </div>
  );
}
