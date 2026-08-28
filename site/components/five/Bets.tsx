/**
 * The competitors' bets on one game, as betting slips.
 *
 * Styled after the paper object: a stub header with the character's name, a
 * perforation between bets, dotted leaders running each leg out to its
 * number, and a "we make it" total at the foot of every bet. On a played
 * game every bet carries its verdict and every leg its mark, colour always
 * paired with a word or a sign, and a voided leg is struck through rather
 * than pretending it was ever settled.
 */

import type { Bet, SlateShape, SlipLeg } from "@/lib/data";
import type { BetVerdict, Outcomes } from "@/lib/graded";
import { betVerdict, legMark } from "@/lib/graded";
import { betOutOf100 } from "@/lib/bets";
import { Badge } from "@/components/kit";
import s from "./bets.module.css";

export type SlipCharacter = { id: string; name: string; generation?: number };

/** One character's slip for one game: the unit the grid, the rail and the
 *  focused overlay all render. */
const MEDALS = ["", "1st", "2nd", "3rd"] as const;

export function SlipCard({
  character: ch,
  own,
  shapes,
  outcomes,
  gameOver = false,
  medal,
}: {
  character: SlipCharacter;
  own: Record<string, Bet>;
  shapes: SlateShape[];
  outcomes?: Outcomes;
  gameOver?: boolean;
  /** League position 1-3: the slip wears its medal, word included. */
  medal?: 1 | 2 | 3;
}) {
  const medalClass = medal === 1 ? s.medal1 : medal === 2 ? s.medal2 : s.medal3;
  return (
    <article className={s.slip} style={{ ["--char" as string]: `var(--ch-${ch.id})` }}>
      <header className={s.head}>
        <span className={s.swatch} aria-hidden />
        {ch.name}
        {ch.generation === 2 && <Badge>v2</Badge>}
        {medal && <span className={medalClass}>{MEDALS[medal]}</span>}
      </header>
      {shapes.map((sh) => {
        const bet = own[sh.key];
        const price = bet ? betOutOf100(bet.legs) : null;
        const verdict =
          outcomes && bet ? betVerdict(bet.legs, outcomes, gameOver) : null;
        return (
          <div key={sh.key} className={s.bet}>
            <div className={s.betHead}>
              <span className={s.betLabel}>{sh.label}</span>
              {verdict && <VerdictWord verdict={verdict} />}
            </div>
            {bet ? (
              <>
                <ul className={s.legs}>
                  {bet.legs.map((l) => (
                    <Leg
                      key={`${l.fullName ?? l.player}|${l.market}|${l.line}`}
                      leg={l}
                      outcomes={outcomes}
                      gameOver={gameOver}
                    />
                  ))}
                </ul>
                {price != null && (
                  <div className={s.total}>
                    <span className={s.totalLabel}>
                      {bet.housePrice != null
                        ? `house ${Math.max(1, Math.round(bet.housePrice * 100))}, we make it`
                        : "we make it"}
                    </span>
                    <span className={s.dots} aria-hidden />
                    <span className={s.price}>
                      {price < 1 ? "<1" : price}/100
                    </span>
                  </div>
                )}
              </>
            ) : (
              <p className={s.passed}>passed, could not fill the shape</p>
            )}
          </div>
        );
      })}
    </article>
  );
}

export default function Bets({
  bets,
  characters,
  shapes,
  outcomes,
  gameOver = false,
  medals,
}: {
  /** character id -> slate key -> the bet. One game's fifteen. */
  bets: Record<string, Record<string, Bet>>;
  characters: SlipCharacter[];
  shapes: SlateShape[];
  /** Present on a played game: marks every bet and leg. */
  outcomes?: Outcomes;
  /** Once true, an unmarked leg is void rather than open. */
  gameOver?: boolean;
  /** character id -> league position, for the top three's medals. */
  medals?: Record<string, 1 | 2 | 3>;
}) {
  return (
    <div className={s.grid}>
      {characters.map((ch) => {
        const own = bets[ch.id];
        if (!own) return null;
        return (
          <SlipCard
            key={ch.id}
            character={ch}
            own={own}
            shapes={shapes}
            outcomes={outcomes}
            gameOver={gameOver}
            medal={medals?.[ch.id]}
          />
        );
      })}
    </div>
  );
}

function VerdictWord({ verdict }: { verdict: BetVerdict }) {
  const cls =
    verdict === "came in"
      ? s.verdictWon
      : verdict === "no"
        ? s.verdictLost
        : s.verdictOpen;
  return <span className={cls}>{verdict}</span>;
}

function Leg({
  leg,
  outcomes,
  gameOver,
}: {
  leg: SlipLeg;
  outcomes?: Outcomes;
  gameOver: boolean;
}) {
  const mark = outcomes ? legMark(leg, outcomes) : null;
  const voided = outcomes != null && mark === null && gameOver;
  const cls =
    mark === true ? s.legWon : mark === false ? s.legLost : voided ? s.legVoid : s.leg;
  return (
    <li className={cls}>
      <span className={s.legPlayer}>{leg.player}</span>
      <span className={s.legWhat}>
        {leg.fouls}+ {leg.market === "drawn" ? "won" : "fouls"}
      </span>
      {leg.hotTake && <span className={s.hot}>hot</span>}
      <span className={s.dots} aria-hidden />
      <span className={s.legProb}>{leg.outOf100}</span>
      {outcomes && (
        <span className={s.sign} aria-hidden={mark === null && !voided}>
          {mark === true ? "✓" : mark === false ? "✗" : voided ? "void" : ""}
        </span>
      )}
    </li>
  );
}
