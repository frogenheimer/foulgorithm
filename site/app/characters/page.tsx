import Link from "next/link";
import Signature from "@/components/characters/Signature";
import type { Settings } from "@/components/characters/Signature";
import { Callout, PageHeader, SectionHead } from "@/components/kit";
import { getCharacters, getPlayers } from "@/lib/data";
import c from "./characters.module.css";

export const metadata = { title: "The five · Foulgorithm" };

export default function Characters() {
  const d = getCharacters();
  const settings = getPlayers().picks;
  const peers = settings.map((p) => p.settings as unknown as Settings);

  return (
    <div className="stack">
      <PageHeader
        title="The five"
        lede="Five ways of reading the same match. They see identical evidence and differ only in how far they trust it, which is a smaller difference than five names suggest and is worth saying plainly."
      />

      <Callout>
        <strong>They separate by about 2%.</strong> Backtested over 13,993 predictions on
        fouls committed, the gap between best and worst is two points. All five beat a model
        knowing nothing but position and minutes, by roughly 4%, so the history genuinely
        matters. But these are five slightly different readings, not five sharply different
        opinions, and the bars below are the whole of the difference.
      </Callout>

      <section>
        <SectionHead
          title="What separates them"
          note="Four dials. How far back each looks, how hard it shrinks a thin sample, how much it reads the matchup, and how far it pushes a deviation from average. The faint marks show where the other four sit."
        />
        <div className={c.grid}>
          {d.characters.map((ch) => {
            const own = settings.find((p) => p.id === ch.id);
            return (
              <Link
                key={ch.id}
                href={`/characters/${ch.id}`}
                className={c.card}
                style={{ ["--char" as string]: `var(--ch-${ch.id})` }}
              >
                <div>
                  <div className={c.emotion}>{ch.emotion}</div>
                  <div className={c.name}>{ch.name}</div>
                </div>

                <p className={c.tagline}>{ch.tagline}</p>

                {own && (
                  <Signature
                    id={ch.id}
                    settings={own.settings as unknown as Settings}
                    peers={peers}
                  />
                )}

                <span className={c.foot}>
                  <span>{ch.weakness.split(".")[0]}</span>
                  <span className={c.go}>Open &rarr;</span>
                </span>
              </Link>
            );
          })}
        </div>
      </section>
    </div>
  );
}
