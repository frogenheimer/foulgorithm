import Link from "next/link";
import Signature from "@/components/characters/Signature";
import type { Settings } from "@/components/characters/Signature";
import { Callout, DataTable, Note, PageHeader, SectionHead } from "@/components/kit";
import { getCharacters, getPlayers } from "@/lib/data";
import { modelName } from "@/lib/names";
import c from "./characters.module.css";

export const metadata = { title: "The five · Foulgorithm" };

export default function Characters() {
  const d = getCharacters();
  const players = getPlayers();
  const settings = players.picks;
  const standings = players.standings ?? [];
  const slates = players.slates;
  const confirmed = new Set(slates.confirmedFixtures ?? []);
  const named = (id: string) => d.characters.find((c) => c.id === id)?.name ?? modelName(id);
  const anyPlayed = standings.some((r) => r.played > 0);
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
          title="The table"
          note="Every gameweek all five commit to the same three bets: six players at 1+, three at 2+, and a mixed two-and-two. Identical shapes, so this measures which players they pick and not how hard a bet they chose. Every leg lands is a win, all but one is a draw. FD is foul difference: a landed leg counts +1, and a miss counts how far it missed by, so a 2+ shout that never came is -2 while one foul short is -1."
        />
        {anyPlayed ? (
          <DataTable
            rows={standings}
            rowKey={(r) => r.id}
            columns={[
              { key: "name", head: "", cell: (r) => named(r.id) },
              { key: "played", head: "P", numeric: true, cell: (r) => r.played },
              { key: "won", head: "W", numeric: true, cell: (r) => r.won },
              { key: "drawn", head: "D", numeric: true, cell: (r) => r.drawn },
              { key: "lost", head: "L", numeric: true, cell: (r) => r.lost },
              { key: "landed", head: "Legs", numeric: true, cell: (r) => `${r.legsLanded}/${r.legsLanded + r.legsMissed}` },
              { key: "fd", head: "FD", numeric: true, cell: (r) => (r.difference > 0 ? `+${r.difference}` : r.difference) },
              { key: "points", head: "Pts", numeric: true, cell: (r) => r.points },
            ]}
          />
        ) : (
          <Note>
            Nothing has settled yet. A slate is only scored once every leg in it has an
            outcome, because counting an unsettled leg as a miss would turn &ldquo;we do not
            know&rdquo; into &ldquo;they got it wrong&rdquo;. The table fills in as rounds
            finish.
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
