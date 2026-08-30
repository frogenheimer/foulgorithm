"use client";

/**
 * The matchday squad: both elevens on one pitch, both benches beside it.
 *
 * The formation arrives as lines of player ids from the league, so this draws
 * the real shape rather than inferring one from position codes.
 *
 * **Everything keys off `who()`, never a display string.** The lineup feed says
 * "Luka Vuskovic", the explorer's full name is "Luka Vušković" and its short
 * name is "Vuskovic". Keying on any one of those put Boscagli on the pitch
 * three times, because the dropdown offered a short name into a slot holding a
 * long one and nothing noticed they were the same man.
 *
 * A player can only be in one place. Dragging or selecting someone already on
 * the pitch EXCHANGES the two rather than cloning him.
 */

import { useMemo, useState } from "react";
import type { ExplorerRow, Spot, TeamShape } from "@/lib/data";
import { Combobox, MicroLabel, Toggle } from "@/components/kit";
import { MARKET_LABEL, type Market } from "@/lib/markets";
import type { Option } from "@/components/kit";
import { findPlayer, who } from "@/lib/who";
import {
  benchFrom,
  lines as formationLines,
  markerFor,
  occupancy as occupancyOf,
  outOfPosition,
  placeInto,
  samePosition,
  shirtIndex,
} from "@/lib/pitch";
import s from "./pitch.module.css";

export type { Market } from "@/lib/markets";
export { MARKET_LABEL } from "@/lib/markets";

/**
 * Two figures on every marker (docs/51): his real rate per 90 across every
 * match we hold, then what the model expects here allowing for minutes and
 * opponent. Where they disagree the gap is the model's opinion: a substitute
 * averaging 1.37 fouls per 90 is expected to give away 0.59 in a match he is
 * likely to watch most of. Cup rows carry no "expected" and show the one
 * figure they have.
 */
export function figuresFor(
  row: ExplorerRow | undefined,
  market: Market
): { real: number | null; expected: number | null } {
  if (!row) return { real: null, expected: null };
  return { real: row.career?.[market] ?? null, expected: row.expected?.[market] ?? null };
}

/** The one number to sort or rank by: expected here, else the real rate. */
export function valueFor(row: ExplorerRow | undefined, market: Market) {
  const f = figuresFor(row, market);
  return f.expected ?? f.real;
}

function Figures({ row, market }: { row: ExplorerRow | undefined; market: Market }) {
  const f = figuresFor(row, market);
  if (f.real == null && f.expected == null) return <>—</>;
  if (f.expected == null) return <>{f.real!.toFixed(2)}</>;
  return (
    <>
      {f.real != null && <span className={s.real}>{f.real.toFixed(2)} / </span>}
      <span className={s.expected}>{f.expected.toFixed(2)}</span>
    </>
  );
}

export type Side = {
  club: string;
  shape: TeamShape;
  squad: ExplorerRow[];
};

/** slot key -> whoever is standing in it, as a canonical key. */
export type Selected = Record<string, string>;

export default function Pitch({
  home,
  away,
  selected,
  onChange,
  onReset,
  market,
  onMarket,
  readOnly = false,
}: {
  home: Side;
  away: Side;
  selected: Selected;
  onChange: (next: Selected) => void;
  onReset: () => void;
  market: Market;
  onMarket: (m: Market) => void;
  /**
   * No swapping, no dragging, no reset.
   *
   * The cup pages use this. Swapping recomputes a house sheet from whoever is
   * standing there, and a cup tie involving a Championship club has no model
   * behind it to recompute, so the control would promise something it cannot
   * do. Same pitch, same styles, one capability withheld.
   */
  readOnly?: boolean;
}) {
  const [dragging, setDragging] = useState<{ club: string; key: string } | null>(null);
  const swaps = Object.keys(selected).length;
  const confirmed = !(home.shape.predicted || away.shape.predicted);

  // Phones show one team at a time, goalkeeper at the foot, striker at the
  // top: a map, not a squeezed broadcast graphic. Desktop never reads this;
  // both halves render side by side there regardless.
  const [shown, setShown] = useState<"home" | "away">("home");

  return (
    <div className={`${s.wrap} ${shown === "home" ? s.showHome : s.showAway}`}>
      <div className={s.head}>
        <span className={s.club}>
          {home.club} <span className={s.formation}>{home.shape.formation ?? "by position"}</span>
        </span>
        <span className={s.versus}>{confirmed ? "confirmed elevens" : "predicted elevens"}</span>
        <span className={s.clubAway}>
          <span className={s.formation}>{away.shape.formation ?? "by position"}</span> {away.club}
        </span>
      </div>

      {swaps > 0 && !readOnly && (
        <div className={s.changed}>
          <span>
            <strong>Not the {confirmed ? "confirmed" : "predicted"} eleven.</strong> You have
            made {swaps} change{swaps === 1 ? "" : "s"}, and every number below reflects them.
            Nothing here is graded: the record only holds what we published before kickoff.
          </span>
          <button type="button" className={s.restore} onClick={onReset}>
            Restore {confirmed ? "confirmed lineup" : "predicted eleven"}
          </button>
        </div>
      )}

      <div className={s.controls}>
        <PitchKey readOnly={readOnly} />
        <Toggle
          value={market}
          onChange={onMarket}
          label="Which number to show"
          options={(Object.keys(MARKET_LABEL) as Market[]).map((m) => ({
            value: m,
            label: MARKET_LABEL[m],
          }))}
        />
      </div>

      <div className={s.sideToggle} role="tablist" aria-label="Which team to show">
        {([["home", home.club], ["away", away.club]] as const).map(([key, club]) => (
          <button
            key={key}
            type="button"
            role="tab"
            aria-selected={shown === key}
            className={shown === key ? s.sideOn : s.sideOff}
            onClick={() => setShown(key)}
          >
            {club}
          </button>
        ))}
      </div>

      <div className={s.squad}>
        <div className={s.homeSide}>
        <Bench
          side={home}
          readOnly={readOnly}
          selected={selected}
          market={market}
          dragging={dragging}
          onDragStart={(key) => setDragging({ club: home.club, key })}
          onDragEnd={() => setDragging(null)}
        />
        </div>

        <div className={s.pitch}>
          {/* The grass is a layer of its own so the pitch itself can let an
              open dropdown overhang the touchline instead of clipping it. */}
          <div className={s.turf} aria-hidden>
            <Markings />
          </div>
          <Half
            className={s.homeSide}
            readOnly={readOnly}
            side={home}
            selected={selected}
            onChange={onChange}
            market={market}
            dragging={dragging}
            onDrop={() => setDragging(null)}
            onDragStart={(key) => setDragging({ club: home.club, key })}
          />
          <Half
            className={s.awaySide}
            readOnly={readOnly}
            side={away}
            selected={selected}
            onChange={onChange}
            market={market}
            dragging={dragging}
            onDrop={() => setDragging(null)}
            onDragStart={(key) => setDragging({ club: away.club, key })}
            mirrored
          />
        </div>

        <div className={s.awaySide}>
        <Bench
          side={away}
          readOnly={readOnly}
          selected={selected}
          market={market}
          dragging={dragging}
          onDragStart={(key) => setDragging({ club: away.club, key })}
          onDragEnd={() => setDragging(null)}
        />
        </div>
      </div>
    </div>
  );
}

/* ---------- who is where ---------- */


function Bench({
  side,
  readOnly = false,
  selected,
  market,
  dragging,
  onDragStart,
  onDragEnd,
}: {
  side: Side;
  readOnly?: boolean;
  selected: Selected;
  market: Market;
  dragging: { club: string; key: string } | null;
  onDragStart: (key: string) => void;
  onDragEnd: () => void;
}) {
  // Anyone in the squad who is not currently on the pitch. That is the bench
  // whether the league named them substitutes or a swap put them there.
  const off = benchFrom(
    side.squad,
    occupancyOf(side.shape, side.squad, selected, findPlayer, side.club)
  );

  return (
    <div className={s.bench}>
      <MicroLabel>{side.club} bench</MicroLabel>
      <div className={s.benchList}>
        {off.length === 0 && <span className={s.note}>Everyone is on the pitch.</span>}
        {off.map((r) => {
          const key = `bench:${who(r.fullName)}`;
          return (
            <button
              key={r.fullName}
              type="button"
              draggable={!readOnly}
              onDragStart={() => !readOnly && onDragStart(key)}
              onDragEnd={onDragEnd}
              className={
                dragging?.key === key ? `${s.benchPlayer} ${s.dragging}` : s.benchPlayer
              }
              title={
                readOnly
                  ? r.fullName
                  : `${r.fullName} \u00b7 drag onto the pitch`
              }
            >
              <span className={s.benchName}>{r.player}</span>
              <span className={s.benchPos}>
                {shortPosition(r.position)} <Figures row={r} market={market} />
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

function Half({
  side,
  selected,
  onChange,
  market,
  dragging,
  onDrop,
  onDragStart,
  mirrored = false,
  className = "",
  readOnly = false,
}: {
  side: Side;
  className?: string;
  readOnly?: boolean;
  selected: Selected;
  onChange: (next: Selected) => void;
  market: Market;
  dragging: { club: string; key: string } | null;
  onDrop: () => void;
  onDragStart: (key: string) => void;
  mirrored?: boolean;
}) {
  const [open, setOpen] = useState<string | null>(null);
  const here = occupancyOf(side.shape, side.squad, selected, findPlayer, side.club);
  const byKey = new Map(here.map((o) => [o.key, o]));
  const shirts = useMemo(() => shirtIndex(side.shape), [side.shape]);

  // Whoever is not currently standing on the pitch. A substitution means
  // bringing one of these on, so they lead the dropdown; a player already out
  // there can still be picked, but choosing him swaps two positions rather than
  // making a substitution, and the list now says which is which.
  const benched = useMemo(
    () => new Set(benchFrom(side.squad, here).map((r) => who(r.fullName))),
    [side.squad, here]
  );

  const byName = useMemo(
    () => [...side.squad].sort((a, b) => a.player.localeCompare(b.player)),
    [side.squad]
  );

  /**
   * Put a player into a slot.
   *
   * If he is already on the pitch the two EXCHANGE places, because a player can
   * only be in one place and cloning him was the bug this replaced.
   */
  function place(targetKey: string, incoming: string) {
    onChange(placeInto(selected, here, targetKey, incoming));
  }

  const shape = useMemo(
    () => formationLines(side.shape, here, mirrored),
    [side.shape, here, mirrored]
  );

  return (
    <div className={`${mirrored ? `${s.half} ${s.away}` : s.half} ${className}`}>
      {shape.map((line, i) => (
        <div key={i} className={s.line}>
          {line.map((o) => {
            const swapped = Boolean(selected[o.key]);
            const misplaced = outOfPosition(o.row, o.spot);
            const isOpen = open === o.key;
            const receiving = !readOnly && Boolean(dragging && dragging.club === side.club);
            return (
              <div
                key={o.key}
                className={[
                  s.slot,
                  swapped ? s.swapped : "",
                  misplaced ? s.misplaced : "",
                  o.vacant ? s.vacant : "",
                  isOpen ? s.slotOpen : "",
                  receiving ? s.dropTarget : "",
                ]
                  .filter(Boolean)
                  .join(" ")}
                onDragOver={(e) => receiving && e.preventDefault()}
                onDrop={(e) => {
                  e.preventDefault();
                  if (!dragging || dragging.club !== side.club) return;
                  const incoming = dragging.key.startsWith("bench:")
                    ? dragging.key.slice("bench:".length)
                    : byKey.get(dragging.key)?.row && who(byKey.get(dragging.key)!.row!.fullName);
                  if (incoming) place(o.key, incoming);
                  onDrop();
                }}
              >
                {/* Three independent things to say about one marker, so three
                    channels: the FILL is which team, the RING is out of
                    position, the BADGE is that you changed it. They used to
                    share fill and border, so a swapped away player lost his
                    team colour and a swap looked identical to a misplacement. */}
                <span className={s.marker}>
                  <span
                    className={s.shirt}
                    draggable={!readOnly}
                    onDragStart={() => onDragStart(o.key)}
                    title={
                      o.vacant
                        ? "Nobody in this position. Pick someone."
                        : misplaced
                          ? `${o.name} is a ${shortPosition(o.row!.position)} standing ${positionName(o.spot.position)}`
                          : o.name
                    }
                  >
                    {o.vacant ? "" : markerFor(shirts, o.row, o.spot)}
                  </span>
                  {swapped && !o.vacant && (
                    <span className={s.swapMark} aria-hidden title="You changed this one">
                      &#8646;
                    </span>
                  )}
                </span>
                <div className={s.picker}>
                  {readOnly ? (
                    <span className={s.nameStatic} title={o.row?.fullName ?? o.name}>
                      <span className={s.name}>{o.name}</span>
                    </span>
                  ) : (
                  <Combobox
                    value={o.name}
                    options={optionsFor(byName, o.spot, market, benched)}
                    onChange={(v) => {
                      place(o.key, v);
                      setOpen(null);
                    }}
                    onOpenChange={(isNowOpen) => setOpen(isNowOpen ? o.key : null)}
                    label={`${o.spot.detail || o.spot.position} for ${side.club}`}
                    placeholder="Search squad"
                    trigger={(openIt) => (
                      <button
                        type="button"
                        className={s.nameButton}
                        onClick={openIt}
                        title={
                          o.vacant ? "Pick a player" : `${o.row?.fullName ?? o.name}. Change.`
                        }
                      >
                        <span className={s.name}>{o.name || "Pick a player"}</span>
                        <Chevron />
                      </button>
                    )}
                  />
                  )}
                </div>
                <span className={s.rate}>
                  <Figures row={o.row} market={market} />
                </span>
              </div>
            );
          })}
        </div>
      ))}
    </div>
  );
}

/**
 * Options for one slot, bench first.
 *
 * The list used to group only on position, so it offered starters already on
 * the pitch above substitutes, under a heading that said they play in midfield.
 * Both are true and neither is what someone making a substitution is looking
 * for. A player out there can still be chosen and the two exchange places,
 * which is a different act and now says so.
 */
function optionsFor(
  rows: ExplorerRow[], spot: Spot, market: Market, bench: Set<string>
): Option[] {
  const ranked = [...rows].sort((a, b) => {
    const onBench = Number(bench.has(who(b.fullName))) - Number(bench.has(who(a.fullName)));
    if (onBench) return onBench;
    const fits =
      Number(samePosition(b.position, spot.position)) -
      Number(samePosition(a.position, spot.position));
    if (fits) return fits;
    return a.player.localeCompare(b.player);
  });

  return ranked.map((row) => {
    const isBenched = bench.has(who(row.fullName));
    const fits = samePosition(row.position, spot.position);
    return {
      value: who(row.fullName),
      label: row.player,
      meta: `${shortPosition(row.position)} · ${valueFor(row, market)?.toFixed(2) ?? "—"}`,
      group: isBenched
        ? fits
          ? `On the bench, plays ${positionName(spot.position)}`
          : "On the bench"
        : "Already on the pitch, swaps places",
    };
  });
}


/** Both penalty areas, both six-yard boxes, halfway line, centre circle. */
/**
 * What the marks mean.
 *
 * Three things are being said about each marker and none of them were labelled,
 * so an orange ring and a pale marker both read as "something is odd with this
 * player" without saying what.
 */
function PitchKey({ readOnly = false }: { readOnly?: boolean }) {
  return (
    <ul className={s.key}>
      <li className={s.keyItem}>
        <span className={`${s.keyDot} ${s.keyHome}`} aria-hidden />
        <span className={`${s.keyDot} ${s.keyAway}`} aria-hidden />
        Home and away
      </li>
      <li className={s.keyItem}>
        <span className={s.keyFigures} aria-hidden>
          0.9 / <strong>1.1</strong>
        </span>
        Real per 90, then expected here
      </li>
      <li className={s.keyItem}>
        <span className={`${s.keyDot} ${s.keyMisplaced}`} aria-hidden />
        Out of position for this slot
      </li>
      {!readOnly && (
        <li className={s.keyItem}>
          <span className={`${s.keyDot} ${s.keySwapped}`} aria-hidden>
            &#8646;
          </span>
          Changed by you
        </li>
      )}
    </ul>
  );
}

function Markings() {
  return (
    <svg className={s.markings} viewBox="0 0 1050 680" preserveAspectRatio="none" aria-hidden>
      <g fill="none" stroke="currentColor" strokeWidth="2" vectorEffect="non-scaling-stroke">
        <rect x="6" y="6" width="1038" height="668" />
        <line x1="525" y1="6" x2="525" y2="674" />
        <circle cx="525" cy="340" r="91" />
        <circle cx="525" cy="340" r="4" fill="currentColor" />
        <rect x="6" y="139" width="165" height="402" />
        <rect x="6" y="249" width="55" height="182" />
        <rect x="879" y="139" width="165" height="402" />
        <rect x="989" y="249" width="55" height="182" />
      </g>
    </svg>
  );
}

function Chevron() {
  return (
    <svg viewBox="0 0 12 12" width="10" height="10" aria-hidden>
      <path d="M3 4.5 6 7.5 9 4.5" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}


function shortPosition(code: string): string {
  return { G: "GK", D: "DEF", M: "MID", F: "FWD" }[(code || "").charAt(0).toUpperCase()] ?? "—";
}

function positionName(code: string): string {
  return { G: "in goal", D: "in defence", M: "in midfield", F: "up front" }[code] ?? "here";
}
