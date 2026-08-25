import Link from "next/link";
import Signature from "@/components/characters/Signature";
import type { Settings } from "@/components/characters/Signature";
import Bets from "@/components/five/Bets";
import Standings from "@/components/five/Standings";
import { Callout, Note, PageHeader, SectionHead } from "@/components/kit";
import { getCharacters, getPlayers } from "@/lib/data";
import { gameOrder } from "@/lib/bets";
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
  const columns = d.characters.map((ch) => ({ id: ch.id, name: ch.name }));
  const names = Object.fromEntries(columns.map((ch) => [ch.id, ch.name]));

  return (
    <div className="stack">
      <PageHeader
        title="The five"
        lede="Five ways of reading the same match, playing the same game: three bets each, on every fixture, scored like a league. They see identical evidence and differ only in how far they trust it."
      />

      <Callout>
        <strong>They separate by about 2%.</strong> Backtested over 13,993 predictions on
        fouls committed, the gap between best and worst is two points. All five beat a model
        knowing nothing but position and minutes, by roughly 4%, so the history genuinely
        matters. But these are five slightly different readings, not five sharply different
        opinions, and the league below is where the difference shows.
      </Callout>

      <Standings standings={players.standings ?? []} names={names} />

      <section>
        <SectionHead
          title="This week's bets"
          note="Three bets per character on every game: six players at 1+, three at 2+, and a two-and-two. Identical shapes, so the league measures which players they pick and not how hard a bet they chose. A game marked * has no confirmed eleven yet: those bets regenerate automatically when the team sheets land, an hour before kickoff, and each bet's last version before its own kickoff is the one that scores."
        />
        {games.length ? (
          <div className={c.betGames}>
            {games.map((g) => (
              <div key={g}>
                <div className={c.gameLabel}>
                  {g}
                  {!confirmed.has(g) ? " *" : ""}
                </div>
                <Bets bets={slates.byGame[g]} characters={columns} shapes={slates.shapes} />
              </div>
            ))}
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
