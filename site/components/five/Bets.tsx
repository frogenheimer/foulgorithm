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
import { clubIdentity } from "@/lib/clubs";
import { Badge } from "@/components/kit";
import s from "./bets.module.css";

export type SlipCharacter = { id: string; name: string; generation?: number };

/** The slip's look. "standard" is the rail's card; the other three are the
 *  house's variants (docs/47): a thermal till receipt, a boarding-pass
 *  ticket, a betting-shop slip. Same data, different object. */
export type SlipVariant = "standard" | "receipt" | "ticket" | "slip";

const EVENT_WORDS: Record<number, string> = { 4: "Four", 5: "Five", 6: "Six" };
const SHORT_URL = "https://www.youtube.com/shorts/thJjDcikJ7A";

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
  variant = "standard",
}: {
  character: SlipCharacter;
  own: Record<string, Bet>;
  shapes: SlateShape[];
  outcomes?: Outcomes;
  gameOver?: boolean;
  /** League position 1-3: the slip wears its medal, word included. */
  medal?: 1 | 2 | 3;
  variant?: SlipVariant;
}) {
  const medalClass = medal === 1 ? s.medal1 : medal === 2 ? s.medal2 : s.medal3;
  if (variant !== "standard") {
    return (
      <PaperSlip
        variant={variant}
        character={ch}
        own={own}
        shapes={shapes}
        outcomes={outcomes}
        gameOver={gameOver}
      />
    );
  }
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
                      {ch.id === "house"
                        ? "the house makes it"
                        : bet.housePrice != null
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


/**
 * The three paper variants, one bet each (the house's slips are one bet per
 * card). Each is the same object drawn differently: the legs, the count of
 * events, the house's price, and the verdict once the game is played.
 */
function PaperSlip({
  variant,
  character: ch,
  own,
  shapes,
  outcomes,
  gameOver,
}: {
  variant: SlipVariant;
  character: SlipCharacter;
  own: Record<string, Bet>;
  shapes: SlateShape[];
  outcomes?: Outcomes;
  gameOver: boolean;
}) {
  const sh = shapes[0];
  const bet = sh ? own[sh.key] : null;
  const tier = (bet?.tier ?? sh?.key ?? "").toString();
  const price = bet ? betOutOf100(bet.legs) : null;
  const verdict = outcomes && bet ? betVerdict(bet.legs, outcomes, gameOver) : null;
  const events = bet?.units ?? sh?.units;
  const words = events ? `${EVENT_WORDS[events] ?? events} foul events` : sh?.label ?? "";
  const fixture = bet?.legs[0]?.fixture ?? "";
  const stamp =
    verdict === "came in"
      ? "winner"
      : verdict === "no"
        ? "void"
        : tier === "rogue"
          ? "rogue"
          : tier === "safe"
            ? "accepted"
            : "placed";
  const mark = (l: SlipLeg) => (outcomes ? legMark(l, outcomes) : null);
  const legClass = (l: SlipLeg) => {
    const m = mark(l);
    const voided = outcomes != null && m === null && gameOver;
    return m === true ? s.pWon : m === false ? s.pLost : voided ? s.pVoid : "";
  };

  if (!bet) {
    return (
      <article className={`${s.paper} ${s[variant]}`}>
        <p className={s.passed}>passed, could not make the count</p>
      </article>
    );
  }

  if (variant === "receipt") {
    return (
      <article className={`${s.paper} ${s.receipt}`} aria-label={`${ch.name}, ${tier}`}>
        <div className={s.rHead}>
          FOULGORITHM
          <small>
            THE HOUSE · {tier.toUpperCase()} · {price}/100
          </small>
        </div>
        <ul className={s.rLegs}>
          {bet.legs.map((l) => (
            <li key={`${l.fullName ?? l.player}|${l.market}|${l.line}`} className={`${s.rLeg} ${legClass(l)}`}>
              <span>{l.player}</span>
              <span className={s.rWhat}>
                {l.fouls}+ {l.market === "drawn" ? "won" : "fouls"}
              </span>
              <span className={s.rDots} aria-hidden />
              <span>{l.outOf100}</span>
            </li>
          ))}
        </ul>
        <div className={s.rTotal}>
          <span>{words.toUpperCase()}</span>
          <span>{price}/100</span>
        </div>
        <div className={s.rBar} aria-hidden />
        {(tier === "rogue" || verdict) && (
          <span className={s.rStamp}>{verdict ? stamp : "risk"}</span>
        )}
      </article>
    );
  }

  if (variant === "ticket") {
    const [home, away] = fixture.split(" v ");
    const kickoff = (bet.legs[0] as { kickoff?: string }).kickoff;
    const when = kickoff ? new Date(kickoff) : null;
    return (
      <article className={`${s.paper} ${s.ticket} ${s[`band_${tier}`] ?? ""}`} aria-label={`${ch.name}, ${tier}`}>
        <div className={s.tMain}>
          <span className={s.tBand} aria-hidden />
          <span className={s.tKicker}>
            <span>Foulgorithm · boarding pass</span>
            <span>The house</span>
          </span>
          <div className={s.tRoute}>
            <span className={s.tCode}>{clubIdentity(home).code}</span>
            <span className={s.tArrow} aria-hidden>
              →
            </span>
            <span className={s.tCode}>{clubIdentity(away).code}</span>
            <span className={s.tRouteNames}>{fixture}</span>
          </div>
          <div className={s.tFields}>
            <span className={s.tField}>
              <span className={s.tFieldLabel}>Date</span>
              <span className={s.tFieldValue}>
                {when ? when.toLocaleDateString("en-GB", { day: "numeric", month: "short", timeZone: "Europe/London" }) : "—"}
              </span>
            </span>
            <span className={s.tField}>
              <span className={s.tFieldLabel}>KO</span>
              <span className={s.tFieldValue}>
                {when ? when.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", timeZone: "Europe/London" }) : "—"}
              </span>
            </span>
            <span className={s.tField}>
              <span className={s.tFieldLabel}>Events</span>
              <span className={s.tFieldValue}>{events ?? "—"}</span>
            </span>
            <span className={s.tField}>
              <span className={s.tFieldLabel}>Price</span>
              <span className={s.tFieldValue}>{price}/100</span>
            </span>
          </div>
          <ol className={s.tRows}>
            {bet.legs.map((l, i) => (
              <li key={`${l.fullName ?? l.player}|${l.market}|${l.line}`} className={`${s.tRow} ${legClass(l)}`}>
                <span className={s.tSeat}>{String(i + 1).padStart(2, "0")}</span>
                <span className={s.tName}>{l.player}</span>
                <span className={s.tWhat}>
                  {l.fouls}+ {l.market === "drawn" ? "won" : "fouls"}
                </span>
                <span className={s.tPrice}>{l.outOf100}</span>
              </li>
            ))}
          </ol>
          {verdict && <span className={s.tVerdict}>{stamp}</span>}
        </div>
        <div className={s.tStub}>
          <span className={s.tTier}>{tier}</span>
          <a className={s.tQr} href={SHORT_URL} target="_blank" rel="noreferrer" title="Scan me">
            {/* Generated once with the qrcode CLI; it encodes SHORT_URL. */}
            <img src="/qr-short.svg" alt="QR code" />
          </a>
          <span className={s.tScan}>scan</span>
          <span className={s.tStubPrice}>{price}/100</span>
        </div>
      </article>
    );
  }

  return (
    <article className={`${s.paper} ${s.slipPaper}`} aria-label={`${ch.name}, ${tier}`}>
      <div className={s.sHead}>
        <span>Foulgorithm</span>
        <span>{tier}</span>
      </div>
      <ul className={s.sRows}>
        {bet.legs.map((l) => (
          <li key={`${l.fullName ?? l.player}|${l.market}|${l.line}`} className={`${s.sRow} ${legClass(l)}`}>
            <span className={s.ink}>{l.player}</span>
            <span className={`${s.ink} ${s.sWhat}`}>
              {l.fouls}+ {l.market === "drawn" ? "won" : "fouls"}
            </span>
            <span className={`${s.ink} ${s.sPrice}`}>{l.outOf100}</span>
          </li>
        ))}
      </ul>
      <div className={s.sTotal}>
        <span>{words}</span>
        <span>{price}/100</span>
      </div>
      <div className={s.sFoot}>
        <span>{fixture}</span>
        <span>the house</span>
      </div>
      <span className={s.sStamp}>{stamp}</span>
    </article>
  );
}
