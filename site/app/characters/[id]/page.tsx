import Link from "next/link";
import { notFound } from "next/navigation";
import Portrait, { CHARACTER_COLOUR } from "@/components/characters/Portrait";
import { Callout, Card, SectionHead } from "@/components/ui";
import { getCharacters } from "@/lib/data";
import { count, fouls, kickoff, odds, pct } from "@/lib/format";
import c from "../characters.module.css";

export function generateStaticParams() {
  return getCharacters().characters.map((ch) => ({ id: ch.id }));
}

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const ch = getCharacters().characters.find((x) => x.id === id);
  return { title: ch ? `${ch.name} · Foulgorithm` : "Foulgorithm" };
}

export default async function CharacterPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const data = getCharacters();
  const ch = data.characters.find((x) => x.id === id);
  if (!ch) notFound();

  const colour = CHARACTER_COLOUR[ch.id];
  const ranked = [...ch.fixtures].sort((a, b) => b.expectedFouls - a.expectedFouls);
  const consensus = Object.fromEntries(data.disagreement.map((d) => [d.key, d.consensus]));

  return (
    <div className="stack">
      <section>
        <Link href="/characters" className={c.back}>
          ← All five
        </Link>
        <div className={c.hero}>
          <Portrait id={ch.id} size={132} label={ch.name} />
          <div>
            <h1 className={c.heroName} style={{ color: colour }}>
              {ch.name}
            </h1>
            <p className={c.heroEmotion}>{ch.emotion}</p>
            <p className={c.heroTagline}>&ldquo;{ch.tagline}&rdquo;</p>
          </div>
        </div>
      </section>

      <section>
        <SectionHead title="How he reads a game">
          <span className={c.prose}>{ch.philosophy}</span>
        </SectionHead>
        <div className={c.traits}>
          <div className={c.trait} style={{ borderLeftColor: colour }}>
            <div className={c.traitLabel}>Edge</div>
            <p className={c.traitBody}>{ch.edge}</p>
          </div>
          <div className={c.trait} style={{ borderLeftColor: colour }}>
            <div className={c.traitLabel}>Blind spot</div>
            <p className={c.traitBody}>{ch.weakness}</p>
          </div>
          <div className={c.trait} style={{ borderLeftColor: colour }}>
            <div className={c.traitLabel}>When he loses</div>
            <p className={c.traitBody}>{ch.onLosing}</p>
          </div>
        </div>
      </section>

      <section>
        <SectionHead title="This round">
          Every fixture as {ch.name} sees it, against what the five agree on average. A gap is him
          backing his temperament against the room.
        </SectionHead>
        <Card padded={false}>
          <div className="scroll-x">
            <table className={c.table}>
              <thead>
                <tr>
                  <th>Fixture</th>
                  <th>Kickoff</th>
                  <th className={c.num}>{ch.name}</th>
                  <th className={c.num}>The five</th>
                  <th className={c.num}>Gap</th>
                  <th className={c.num}>Over 22.5</th>
                  <th className={c.num}>Fair</th>
                </tr>
              </thead>
              <tbody>
                {ranked.map((f) => {
                  const line = f.lines.find((l) => l.line === 22.5)!;
                  const gap = f.expectedFouls - (consensus[f.key] ?? f.expectedFouls);
                  return (
                    <tr key={f.key}>
                      <td className={c.fixture}>
                        {f.home} v {f.away}
                      </td>
                      <td className="muted">{kickoff(f.kickoff)}</td>
                      <td className={c.num} style={{ color: colour, fontWeight: 600 }}>
                        {fouls(f.expectedFouls)}
                      </td>
                      <td className={`${c.num} secondary`}>{fouls(consensus[f.key] ?? 0)}</td>
                      <td className={c.num} style={{ color: Math.abs(gap) > 0.5 ? colour : "var(--text-muted)" }}>
                        {gap >= 0 ? "+" : ""}
                        {gap.toFixed(2)}
                      </td>
                      <td className={c.num}>{pct(line.probOver)}</td>
                      <td className={`${c.num} secondary`}>{odds(line.fairOddsOver)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      </section>

      <section>
        <SectionHead title="Under the bonnet" />
        <Card>
            <table className={c.table}>
              <tbody>
                <tr>
                  <td>Model</td>
                  <td className={c.num}>
                    {ch.model.id} {ch.model.version}
                  </td>
                </tr>
                <tr>
                  <td>Memory, half-life</td>
                  <td className={c.num}>{Math.round(ch.model.config.half_life_days)} days</td>
                </tr>
                <tr>
                  <td>Confidence, dispersion scale</td>
                  <td className={c.num}>{ch.model.config.dispersion_scale}</td>
                </tr>
                <tr>
                  <td>Trained on</td>
                  <td className={c.num}>
                    {count(data.trainedOn.matches)} matches, {data.trainedOn.firstSeason} to{" "}
                    {data.trainedOn.lastSeason}
                  </td>
                </tr>
              </tbody>
            </table>
        </Card>
        <Callout>
          Frozen at this version on 21 August 2026 and not tuned since. Any change from here has to
          be a new version, so a shift in results can always be attributed. {ch.name} has published
          nothing that has settled yet, so there is no live record to show, and a backtest is not a
          record.
        </Callout>
      </section>
    </div>
  );
}
