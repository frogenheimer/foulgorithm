import { betsCopy, isPriced, scoringCopy } from "@/lib/contract";
import Link from "next/link";
import Signature from "@/components/characters/Signature";
import type { Settings } from "@/components/characters/Signature";
import SlipRail from "@/components/five/SlipRail";
import Vidiprinter from "@/components/home/Vidiprinter";
import Standings from "@/components/five/Standings";
import { Callout, Note, PageHeader, SectionHead } from "@/components/kit";
import { getArchivedFixtures, getCharacters, getPlayers } from "@/lib/data";
import { gameOrder } from "@/lib/bets";
import { vidiprinterLines } from "@/lib/vidiprinter";
import c from "./characters.module.css";

export const metadata = { title: "The five · Foulgorithm" };

/**
 * The league between the models. The table leads, because this page answers
 * "who is winning the game between the five"; the week's bets follow, game
 * by game, three slips per character on every one of them (docs/38); and
 * the dials at the bottom say what actually separates the temperaments.
 */
export default function Characters() {
  const d = getCharacters();
  const players = getPlayers();
  const settings = players.picks;
  const slates = players.slates;
  const confirmed = new Set(slates.confirmedFixtures ?? []);
  const peers = settings.map((p) => p.settings as unknown as Settings);
  const games = gameOrder(Object.keys(slates.byGame ?? {}), players.board);
  const printer = vidiprinterLines(getArchivedFixtures(), 12);

  // The summary strip's numbers, so a closed game still says what it holds.
  const gameMeta = (g: string) => {
    let bets = 0;
    let hot = 0;
    for (const shapes of Object.values(slates.byGame[g] ?? {})) {
      for (const bet of Object.values(shapes ?? {})) {
        if (!bet) continue;
        bets += 1;
        hot += bet.legs.filter((l) => l.hotTake).length;
      }
    }
    return { bets, hot };
  };
  const columns = d.characters.map((ch) => ({ id: ch.id, name: ch.name, generation: ch.generation }));
  // The top three of the table wear their medals on every slip.
  const medals = Object.fromEntries(
    (players.standings ?? [])
      .filter((r) => r.played > 0)
      .slice(0, 3)
      .map((r, i) => [r.id, (i + 1) as 1 | 2 | 3])
  );
  const names = Object.fromEntries(columns.map((ch) => [ch.id, ch.name]));

  return (
    <div className="stack">
      <PageHeader
        title="The five"
        lede="The five, and the 6~7 who joined to beat them. Eleven readings of the same match, playing the same game: three bets each, on every fixture, scored like a league. Generation 1 bets on pure temperament; generation 2 on bounded logic with one guaranteed hot take."
      />

      <Callout>
        <strong>They separate by about 2%.</strong> Backtested over 13,993 predictions on
        fouls committed, the gap between the five's best and worst is two points, and all
        of them beat a model knowing nothing but position and minutes by roughly 4%, so
        the history genuinely matters. The challengers run the same evidence through new
        dials and stricter betting rules, and the league below is the test of whether
        that helps.
      </Callout>

      <Standings standings={players.standings ?? []} names={names}
          priced={isPriced(players.slates.shapes)}
        />

      {printer.length > 0 && <Vidiprinter lines={printer} />}

      <section>
        <SectionHead
          title="This week's bets"
          note={`${betsCopy(isPriced(players.slates.shapes))} ${scoringCopy(isPriced(players.slates.shapes))} Hot is a leg where a character parts company with the pack.`}
        />
        {games.length ? (
          <div className={c.betGames}>
            {games.map((g) => {
              const meta = gameMeta(g);
              return (
                <details key={g} className={c.betsGame}>
                  <summary className={c.betsSummary}>
                    <span className={c.gameLabel}>
                      {g}
                      {!confirmed.has(g) ? " *" : ""}
                    </span>
                    <span className={c.swatchRow} aria-hidden>
                      {columns.map((ch) => (
                        <span
                          key={ch.id}
                          className={c.dot}
                          style={{ ["--char" as string]: `var(--ch-${ch.id})` }}
                        />
                      ))}
                    </span>
                    <span className={c.betsMeta}>
                      {meta.bets} bets · {meta.hot} hot
                    </span>
                  </summary>
                  <SlipRail bets={slates.byGame[g]} characters={columns} shapes={slates.shapes} medals={medals} />
                </details>
              );
            })}
          </div>
        ) : (
          <Note>
            No bets are on the board yet. They appear when the round&rsquo;s slates are
            published.
          </Note>
        )}
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
