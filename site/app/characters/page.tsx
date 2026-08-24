import Link from "next/link";
import Signature from "@/components/characters/Signature";
import type { Settings } from "@/components/characters/Signature";
import FivePicks from "@/components/fixture/FivePicks";
import { Callout, Note, PageHeader, SectionHead } from "@/components/kit";
import { getCharacters, getPlayers } from "@/lib/data";
import { slateFixtures } from "@/lib/fivepicks";
import c from "./characters.module.css";

export const metadata = { title: "The five · Foulgorithm" };

export default function Characters() {
  const d = getCharacters();
  const players = getPlayers();
  const settings = players.picks;
  const slates = players.slates;
  const confirmed = new Set(slates.confirmedFixtures ?? []);
  const peers = settings.map((p) => p.settings as unknown as Settings);
  const games = slateFixtures(slates, players.board);
  const columns = d.characters.map((ch) => ({ id: ch.id, name: ch.name }));

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
          title="Side by side"
          note="The same committed picks as a matrix, one game at a time in kickoff order: rows are players, columns are the five, and a filled cell is a pick at that line in that character's colour. The players they agree on rise to the top. A game marked * has no confirmed eleven yet."
        />
        {games.length ? (
          <div className={c.matrixGames}>
            {games.map((g) => (
              <div key={g}>
                <div className={c.gameLabel}>
                  {g}
                  {!confirmed.has(g) ? " *" : ""}
                </div>
                <FivePicks slates={slates} fixture={g} characters={columns} />
              </div>
            ))}
          </div>
        ) : (
          <Note>
            No committed picks are on the board yet. The matrix appears when the
            round&rsquo;s slates are published.
          </Note>
        )}
      </section>

      <section>
        <SectionHead
          title="This week's picks"
          note="Every committed slate for the current round, in full. A game marked * has no confirmed eleven yet: those picks regenerate automatically when the team sheets land, an hour before kickoff, and the version on the board at the round's first kickoff is the one that scores."
        />
        <div className={c.slates}>
          {d.characters.map((ch) => {
            const own = slates.byCharacter[ch.id];
            if (!own) return null;
            const allLegs = slates.shapes.flatMap((sh) => own[sh.key]?.legs ?? []);
            const games = Array.from(new Set(allLegs.map((l) => l.fixture)));
            const provisional = games.some((g) => !confirmed.has(g));
            return (
              <details
                key={ch.id}
                className={c.slate}
                style={{ ["--char" as string]: `var(--ch-${ch.id})` }}
              >
                <summary className={c.slateHead}>
                  <span className={c.slateWho}>
                    <span className={c.slateSwatch} aria-hidden />
                    {ch.name}
                  </span>
                  <span className={c.slateMeta}>
                    {allLegs.length} legs across {games.length} game
                    {games.length === 1 ? "" : "s"}
                    {provisional ? "\u2009*" : ""}
                  </span>
                </summary>

                {slates.shapes.map((sh) => {
                  const built = own[sh.key];
                  const shapeGames = built
                    ? Array.from(new Set(built.legs.map((l) => l.fixture)))
                    : [];
                  return (
                    <div key={sh.key} className={c.shape}>
                      <div className={c.shapeLabel}>
                        {sh.label}
                        {!built && (
                          <span className={c.passed}> — passed, could not fill the shape</span>
                        )}
                      </div>
                      {shapeGames.map((g) => (
                        <div key={g} className={c.slateGame}>
                          <div className={c.gameLabel}>
                            {g}
                            {!confirmed.has(g) ? "\u2009*" : ""}
                          </div>
                          <ul className={c.slateLegs}>
                            {built!.legs
                              .filter((l) => l.fixture === g)
                              .map((l) => (
                                <li
                                  key={`${l.fullName ?? l.player}-${l.market}-${l.fouls}`}
                                  className={c.slateLeg}
                                >
                                  <span className={c.legPlayer}>{l.player}</span>
                                  <span className={c.legWhat}>
                                    {l.fouls}+ {l.market === "drawn" ? "won" : "fouls"}
                                  </span>
                                  <span className={c.legProb}>{l.outOf100}/100</span>
                                </li>
                              ))}
                          </ul>
                        </div>
                      ))}
                    </div>
                  );
                })}
              </details>
            );
          })}
        </div>
      </section>

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
