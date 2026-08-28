import Link from "next/link";
import CompetitionSwitcher from "@/components/home/CompetitionSwitcher";
import Timeline from "@/components/fixture/Timeline";
import Vidiprinter from "@/components/home/Vidiprinter";
import { Card, Metric, MetricRow, PageHeader, SectionHead } from "@/components/kit";
import { getArchivedFixtures, getPlayers, getSeason, getTrackRecord } from "@/lib/data";
import { count } from "@/lib/format";
import { vidiprinterLines } from "@/lib/vidiprinter";

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
  // What we said, from the permanent record rather than the current board.
  //
  // It was summed off the board, which only holds the fixtures being predicted
  // now. The moment the pipeline moved to predicting the round that is COMING,
  // every played card lost its claim and "We said 22" quietly disappeared from
  // the comparison that is the whole point of showing a result.
  const expected: Record<string, number> = Object.fromEntries(
    Object.entries(d.expectedTotals ?? {}).map(([label, held]) => [label, held.expected])
  );

  const house = record?.models?.house;

  // The house engine's strongest single call per fixture, for the card front.
  const houseCalls = Object.fromEntries(
    d.board
      .filter((f) => f.summary?.topFouler)
      .map((f) => [
        `${f.home} v ${f.away}`,
        { player: f.summary!.topFouler.player, outOf100: f.summary!.topFouler.outOf100 },
      ])
  );
  // The house sheet's starred picks per fixture, for the card backs.
  const sheets = Object.fromEntries(
    d.board
      .map((f) => [
        `${f.home} v ${f.away}`,
        (f.houseSheet?.groups ?? []).flatMap((g) =>
          g.picks
            .filter((p) => p.star)
            .map((p) => ({ player: p.player, outOf100: p.outOf100, line: g.line, market: g.market, tier: p.tier ?? null }))
        ),
      ])
      .filter(([, stars]) => (stars as unknown[]).length > 0)
  );

  const settledLines = vidiprinterLines(getArchivedFixtures());
  // TEMPORARY, remove next deploy: sample lines so the vidiprinter can be
  // seen in place before the first per-game round settles this weekend.
  const printer = settledLines.length > 0 ? settledLines : SAMPLE_PRINTER;

  return (
    <div className="stack">
      <CompetitionSwitcher active="league" />
      <PageHeader
        kicker={`Today · Matchweek ${season.currentMatchweek}`}
        title="Today"
        lede={
          <>
            Calibrated probabilities for Premier League fouls, published before kickoff and
            graded afterwards. Pick a fixture for both clubs&apos; records side by side and
            what each of the eleven makes of it.
          </>
        }
      />

      {printer.length > 0 && <Vidiprinter lines={printer} />}

      <section>
        <Timeline
          fixtures={season.fixtures}
          matchweeks={season.matchweeks}
          currentMatchweek={season.currentMatchweek}
          expected={expected}
          house={houseCalls}
          sheets={sheets}
          hasPage={
            // The current round's pages, plus every played game the archive
            // kept a page for. See publish/archive.py.
            new Set([
              ...Object.keys(d.fixtureSlips),
              // Cup archives share a league fixture's label but live at their
              // own slug; linking a league card to a cup page misfiled a
              // played league game once already.
              ...Object.values(getArchivedFixtures())
                .filter((a) => !a.competition)
                .map((a) => a.label),
            ])
          }
          options={d.fixtureOptions}
          settled={d.settledCards ?? {}}
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
              The competitors see identical evidence and separate by about{" "}
              <strong>2%</strong> on player markets. They are slightly different
              readings, not sharply different opinions, and we would rather say so
              than let eleven portraits imply otherwise.
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

// TEMPORARY, remove next deploy: a realistic feed so the vidiprinter is
// visible in place before anything has settled under the contract.
const SAMPLE_PRINTER = [
  { text: "NFO v LEE \u00b7 MAGICIAN \u00b7 SIX AT 1+ \u00b7 ALL SIX (6) LANDED", tone: "won" as const },
  { text: "NFO v LEE \u00b7 ALAN \u00b7 THREE AT 2+ \u00b7 NO", tone: "lost" as const },
  { text: "NFO v LEE \u00b7 JUSTINE \u00b7 TWO AND TWO \u00b7 CAME IN", tone: "won" as const },
  { text: "ARS v CHE \u00b7 BDOG \u00b7 SIX AT 1+ \u00b7 NO", tone: "lost" as const },
  { text: "ARS v CHE \u00b7 LILY \u00b7 TWO AND TWO \u00b7 CAME IN", tone: "won" as const },
  { text: "ARS v CHE \u00b7 MABEL \u00b7 THREE AT 2+ \u00b7 CAME IN", tone: "won" as const },
  { text: "LIV v EVE \u00b7 TAYLER \u00b7 SIX AT 1+ \u00b7 ALL SIX (6) LANDED", tone: "won" as const },
  { text: "LIV v EVE \u00b7 DOTTIE \u00b7 THREE AT 2+ \u00b7 NO", tone: "lost" as const },
  { text: "MCI v NEW \u00b7 PAX \u00b7 SIX AT 1+ \u00b7 CAME IN", tone: "won" as const },
  { text: "MCI v NEW \u00b7 DELE \u00b7 TWO AND TWO \u00b7 NO", tone: "lost" as const },
];
