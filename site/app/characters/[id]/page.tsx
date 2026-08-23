import Link from "next/link";
import Signature from "@/components/characters/Signature";
import type { Settings } from "@/components/characters/Signature";
import { Callout, Card, MicroLabel, SectionHead } from "@/components/kit";
import { getCharacters, getPlayers, getTrackRecord } from "@/lib/data";
import { fixtureSlug } from "@/lib/slug";
import c from "../characters.module.css";

export function generateStaticParams() {
  return getCharacters().characters.map((ch) => ({ id: ch.id }));
}

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const ch = getCharacters().characters.find((x) => x.id === id);
  return { title: ch ? `${ch.name} · Foulgorithm` : "Foulgorithm" };
}

export default async function Character({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const ch = getCharacters().characters.find((x) => x.id === id);
  const data = getPlayers();
  const own = data.picks.find((p) => p.id === id);
  if (!ch || !own) return null;

  const peers = data.picks.map((p) => p.settings as unknown as Settings);
  const record = getTrackRecord()?.models?.[id];

  // This character's ladder for the first fixture that has one, so the page
  // shows what it actually does rather than only what it believes.
  const found = Object.entries(data.fixtureSlips).find(([, byChar]) => byChar[id]?.length);
  const fixture = found?.[0];
  const ladder = found?.[1][id];

  return (
    <div className="stack" style={{ ["--char" as string]: `var(--ch-${id})` }}>
      <div>
        <Link href="/characters" className={c.back}>
          &larr; The five
        </Link>
        <header className={c.hero}>
          <div className={c.heroEmotion}>{ch.emotion}</div>
          <div className={c.heroName}>{ch.name}</div>
          <p className={c.heroTagline}>{ch.tagline}</p>
        </header>
      </div>

      <div className={c.two}>
        <section>
          <SectionHead title="How it reads a match" />
          <div className={c.prose}>
            <p>{ch.philosophy}</p>
            <p>
              <strong>When it loses.</strong> {ch.onLosing}
            </p>
          </div>
        </section>

        <section>
          <SectionHead
            title="Its settings"
            note="The faint marks are where the other four sit, so each bar reads as a position among five rather than a score out of ten."
          />
          <Signature id={id} settings={own.settings as unknown as Settings} peers={peers} big />
        </section>
      </div>

      <Callout>
        <strong>Where it is wrong.</strong> {ch.weakness}
      </Callout>

      {ladder && fixture && (
        <section>
          <SectionHead
            title={`What it likes in ${fixture}`}
            note={
              <>
                Its own ladder, built inside one fixture.{" "}
                <Link href={`/fixture/${fixtureSlug(fixture)}`}>See all five side by side</Link>.
              </>
            }
          />
          <Card>
            <div className={c.tiers}>
              {ladder.map((t) => (
                <div key={t.targetLabel} className={c.tier}>
                  <span className={c.tierPrice}>{t.targetLabel}</span>
                  <span className={c.tierLegs}>
                    {t.legs
                      .map((l) => `${l.player} ${l.fouls}+ ${l.market === "drawn" ? "won" : "fouls"}`)
                      .join(" + ")}
                  </span>
                  <span className={c.tierOdds}>{t.outOf100}/100</span>
                </div>
              ))}
            </div>
          </Card>
        </section>
      )}

      <section>
        <SectionHead title="Its record" />
        <Card>
          {record && record.n > 0 ? (
            <div className={c.prose}>
              <p>
                <MicroLabel>{record.n} graded claims</MicroLabel>
              </p>
              <p>
                It said <strong>{(record.claimed * 100).toFixed(0)}%</strong> on average and{" "}
                <strong>{(record.actual * 100).toFixed(0)}%</strong> happened.
                {record.n < 100 && (
                  <>
                    {" "}
                    At {record.n} claims that gap is noise, not evidence. It takes a few hundred
                    before either number means anything, and this page will keep saying so until
                    it does.
                  </>
                )}
              </p>
              <p>
                <Link href="/record">The full record</Link>, every character, including the bad
                weeks.
              </p>
            </div>
          ) : (
            <div className={c.prose}>
              <p>
                Nothing of its own has settled yet. When it does it appears here and on the{" "}
                <Link href="/record">track record</Link>, wins and losses alike.
              </p>
            </div>
          )}
        </Card>
      </section>
    </div>
  );
}
