import Explorer from "@/components/explorer/Explorer";
import GameShouts from "@/components/explorer/GameShouts";
import { Callout } from "@/components/kit";
import { getExplorer, getPlayers } from "@/lib/data";
import s from "../round.module.css";

export const metadata = { title: "Players · Foulgorithm" };

export default function Players() {
  const d = getExplorer();
  const meta = getPlayers();

  return (
    <div className="stack">
      <section className={s.intro}>
        <h1 className={s.h1}>Look up any player</h1>
        <p className={s.lede}>
          The other pages choose for you. This one does not: {d.rows.length} players across
          the round, every market and every line, with all five models side by side and the
          full shape behind any number you open. Filter by game, position, or how many fouls
          you care about.
        </p>
      </section>

      <Callout>
        <strong>Start simple.</strong> The table opens on one model and one question: how often
        does this happen in 100 matches like this one. Turn off Simple when you want the other
        four models and the spread between them, which is the more interesting view once you
        trust the first one.
      </Callout>

      <GameShouts data={d} />

      <Explorer data={d} />

      <section className={s.footNote}>
        <p>
          Prices are what a bet would need to pay to be worth taking, with no bookmaker margin
          in them. Nobody is offering these. {meta.lineups.confirmed > 0
            ? `${meta.lineups.confirmed} lineups are confirmed; the rest are predicted from current squads.`
            : "No lineups are confirmed yet, so every eleven here is predicted from current squads."}
        </p>
        <p>
          <strong>Thin</strong> means we have too little history on that player to be confident.
          The number is still our honest best guess, it just rests on less.
        </p>
      </section>
    </div>
  );
}
