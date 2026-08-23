import Link from "next/link";
import { Card, DataTable, Metric, MetricRow, Note, PageHeader, SectionHead } from "@/components/kit";
import { getTeams } from "@/lib/data";
import type { TeamPlayer } from "@/lib/data";
import { fixtureSlug } from "@/lib/slug";
import s from "../teams.module.css";

export function generateStaticParams() {
  return getTeams().table.map((t) => ({ slug: fixtureSlug(t.team) }));
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const t = getTeams().table.find((x) => fixtureSlug(x.team) === slug);
  return { title: t ? `${t.team} · Foulgorithm` : "Foulgorithm" };
}

export default async function Team({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const data = getTeams();
  const t = data.table.find((x) => fixtureSlug(x.team) === slug);
  if (!t) return null;

  const ranked = [...data.table].sort((a, b) => b.points - a.points || b.goalDifference - a.goalDifference);
  const position = ranked.findIndex((x) => x.team === t.team) + 1;

  // Where the club sits on each discipline column, which is more useful than the
  // rate alone: 11 fouls a match means nothing without knowing 20 clubs' spread.
  const rankOn = (key: "foulsPerMatch" | "foulsWonPerMatch" | "cardsPerMatch") => {
    const withValue = data.table.filter((x) => x[key] !== null);
    const order = [...withValue].sort((a, b) => (b[key] ?? 0) - (a[key] ?? 0));
    const i = order.findIndex((x) => x.team === t.team);
    return i < 0 ? null : `${i + 1} of ${withValue.length}`;
  };

  return (
    <div className="stack">
      <div>
        <Link href="/teams" className={s.back}>
          &larr; Teams
        </Link>
        <PageHeader
          title={t.team}
          lede={`${position ? `${position}th` : "Unplaced"} on ${t.points} points from ${t.played} played. Foul rates cover ${data.rateSeasons}.`}
        />
      </div>

      <MetricRow>
        <Metric
          label="Fouls conceded"
          value={t.foulsPerMatch !== null ? t.foulsPerMatch.toFixed(2) : "—"}
          tone={1}
          note={t.foulsPerMatch !== null ? `${rankOn("foulsPerMatch")} in the league` : "No top-flight record yet"}
        />
        <Metric
          label="Fouls won"
          value={t.foulsWonPerMatch !== null ? t.foulsWonPerMatch.toFixed(2) : "—"}
          tone={2}
          note={t.foulsWonPerMatch !== null ? `${rankOn("foulsWonPerMatch")} in the league` : undefined}
        />
        <Metric
          label="Cards"
          value={t.cardsPerMatch !== null ? t.cardsPerMatch.toFixed(2) : "—"}
          tone={3}
          note={t.cardsPerMatch !== null ? `${rankOn("cardsPerMatch")} in the league` : undefined}
        />
      </MetricRow>

      <section>
        <SectionHead
          title="The squad"
          note="Current players only, so anyone who left is not in a table about this season. Ranked by fouls conceded per 90, and anyone under three full matches of playing time is left out rather than shown as a rate built on noise."
        />
        {t.players.length > 0 ? (
          <DataTable
            rows={t.players}
            rowKey={(p: TeamPlayer) => p.player}
            columns={[
              { key: "player", head: "Player", cell: (p) => <span className={s.strong}>{p.player}</span> },
              { key: "pos", head: "Pos", cell: (p) => p.position || "—" },
              { key: "matches", head: "Matches", numeric: true, cell: (p) => p.matches },
              { key: "minutes", head: "Minutes", numeric: true, cell: (p) => p.minutes.toLocaleString() },
              { key: "fouls", head: "Fouls /90", numeric: true, cell: (p) => <span className={s.strong}>{p.foulsPer90}</span> },
              { key: "won", head: "Won /90", numeric: true, cell: (p) => p.wonPer90 },
              { key: "tackles", head: "Tackles /90", numeric: true, cell: (p) => p.tacklesPer90 },
              { key: "cards", head: "Cards", numeric: true, cell: (p) => p.cards },
            ]}
          />
        ) : (
          <Card>
            <Note>
              No player record for {t.team}. Second-tier player data covers matches but not
              individuals and is not published anywhere at any price, so a club promoted this
              summer has a team record and no squad table. The rates above are real; this part
              is genuinely missing rather than hidden.
            </Note>
          </Card>
        )}
      </section>
    </div>
  );
}
