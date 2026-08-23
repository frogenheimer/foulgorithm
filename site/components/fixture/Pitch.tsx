"use client";

/**
 * Both elevens, on one pitch, in the shape the league published.
 *
 * The formation arrives as lines of player ids, goalkeeper first, so this draws
 * the real 4-2-3-1 rather than inferring one from position codes. Codes cannot
 * tell a back three from a back four.
 *
 * Home occupies the left half attacking right, away the right half attacking
 * left, which is how a fixture is written and how a broadcast frames it. The
 * pitch is 105 by 68 metres, held as an aspect ratio so the shape stays right at
 * any width.
 *
 * Swapping a player is not decoration: the five characters' combinations rebuild
 * from whoever is standing on it.
 */

import { useMemo } from "react";
import type { ExplorerRow, Spot, TeamShape } from "@/lib/data";
import { Combobox, MicroLabel, Toggle } from "@/components/kit";
import type { Option } from "@/components/kit";
import s from "./pitch.module.css";

export type Market = "committed" | "drawn" | "involvements";

export const MARKET_LABEL: Record<Market, string> = {
  committed: "Fouls conceded",
  drawn: "Fouls won",
  involvements: "Involvements",
};

export type Side = {
  club: string;
  shape: TeamShape;
  squad: ExplorerRow[];
};

export default function Pitch({
  home,
  away,
  selected,
  onSwap,
  onReset,
  rateOf,
  market,
  onMarket,
}: {
  home: Side;
  away: Side;
  /** slot key -> player, when swapped away from the published eleven */
  selected: Record<string, string>;
  onSwap: (slotKey: string, player: string) => void;
  onReset: () => void;
  rateOf: (club: string, player: string) => string;
  /** Which number sits under each name. */
  market: Market;
  onMarket: (m: Market) => void;
}) {
  const swaps = Object.keys(selected).length;
  // A predicted eleven is right about 78% of the time. The page says which it
  // is looking at rather than letting a guess read as a team sheet.
  const predicted = Boolean(home.shape.predicted || away.shape.predicted);

  return (
    <div className={s.wrap}>
      <div className={s.head}>
        <span className={s.club}>
          {home.club}{" "}
          <span className={s.formation}>
            {home.shape.formation ?? "by position"}
          </span>
        </span>
        <span className={s.versus}>
          {swaps > 0 ? (
            <button type="button" className={s.reset} onClick={onReset}>
              Reset {swaps} change{swaps === 1 ? "" : "s"}
            </button>
          ) : predicted ? (
            "predicted elevens, grouped by position"
          ) : (
            "confirmed elevens"
          )}
        </span>
        <span className={s.clubAway}>
          <span className={s.formation}>
            {away.shape.formation ?? "by position"}
          </span>{" "}
          {away.club}
        </span>
      </div>

      <div className={s.markets}>
        <Toggle
          value={market}
          onChange={onMarket}
          label="Which number to show"
          options={(Object.keys(MARKET_LABEL) as Market[]).map((m) => ({
            value: m,
            label: MARKET_LABEL[m],
          }))}
        />
        <span className={s.marketNote}>
          expected in this match, per player
        </span>
      </div>

      <div className={s.pitch}>
        <Markings />
        {/* Home: goalkeeper at the left edge, attack running right. */}
        <Half side={home} selected={selected} onSwap={onSwap} rateOf={rateOf} market={market} />
        {/* Away: mirrored, so the two face each other. */}
        <Half
          side={away}
          selected={selected}
          onSwap={onSwap}
          rateOf={rateOf}
          market={market}
          mirrored
        />
      </div>

      <div className={s.benches}>
        {[home, away].map((side) => (
          <div key={side.club}>
            <MicroLabel>{side.club} bench</MicroLabel>
            <p className={s.note}>
              {side.shape.bench.map((b: Spot) => b.player).join(" · ") || "None named"}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

function Half({
  side,
  selected,
  onSwap,
  rateOf,
  market,
  mirrored = false,
}: {
  side: Side;
  selected: Record<string, string>;
  onSwap: (key: string, player: string) => void;
  rateOf: (club: string, player: string) => string;
  market: Market;
  mirrored?: boolean;
}) {
  const byName = useMemo(
    () => [...side.squad].sort((a, b) => a.player.localeCompare(b.player)),
    [side.squad]
  );

  /**
   * Players who actually play the slot's position are offered first. Everyone
   * else stays one keystroke away rather than hidden, because a manager can
   * field whoever he likes and a dropdown should not argue.
   */
  const onPitchNames = new Set(
    side.shape.lines.flatMap((line, i) =>
      line.map((spot, j) => selected[`${side.club}|${i}|${j}`] ?? spot.player)
    )
  );

  const optionsFor = (spot: Spot): Option[] =>
    byName.map((row) => {
      const available = !onPitchNames.has(row.player);
      const fits = samePosition(row.position, spot.position);
      return {
        value: row.player,
        label: row.player,
        // Position first, because "who plays here" is the question being asked.
        // The rate is secondary and both fit.
        meta: `${shortPosition(row.position)} · ${row.expected[market].toFixed(2)}`,
        // Available and in position first, then anyone else off the pitch. A
        // player already on it is still selectable, because a manager can
        // reorganise, but he is not what "sub someone in" means.
        group: available
          ? fits
            ? `On the bench, plays ${positionName(spot.position)}`
            : "Off the pitch"
          : undefined,
      };
    });

  const shape = useMemo(
    () => regroup(side, selected),
    [side, selected]
  );
  const lines = mirrored ? [...shape].reverse() : shape;

  return (
    <div className={mirrored ? `${s.half} ${s.away}` : s.half}>
      {lines.map((line, i) => {
        const lineIndex = mirrored ? side.shape.lines.length - 1 - i : i;
        return (
          <div key={i} className={s.line}>
            {line.map((spot, j) => {
              const key = `${side.club}|${lineIndex}|${j}`;
              const player = selected[key] ?? spot.player;
              const swapped = Boolean(selected[key]);
              return (
                <div key={key} className={swapped ? `${s.slot} ${s.swapped}` : s.slot}>
                  <span className={s.shirt}>{spot.shirt ?? spot.position}</span>
                  <div className={s.picker}>
                    <Combobox
                      value={player}
                      options={optionsFor(spot)}
                      onChange={(v) => onSwap(key, v)}
                      label={`${spot.detail || spot.position} for ${side.club}`}
                      placeholder="Search squad"
                      trigger={(open) => (
                        <button
                          type="button"
                          className={s.nameButton}
                          onClick={open}
                          title={`${player} · ${spot.detail || spot.position}. Change.`}
                        >
                          <span className={s.name}>{player}</span>
                          <Chevron />
                        </button>
                      )}
                    />
                  </div>
                  <span className={s.rate}>{rateOf(side.club, player)}</span>
                </div>
              );
            })}
          </div>
        );
      })}
    </div>
  );
}

/**
 * Rebuild the lines from whoever is on the pitch now.
 *
 * The published shape places the published eleven. Swap a midfielder into a
 * defender's slot and leaving the shape alone stands a midfielder at left-back,
 * which is not what the manager who made that change meant. Regrouping by the
 * players' own positions is the honest re-jig: one goalkeeper, then defenders,
 * midfielders and forwards in the order they were selected.
 *
 * Untouched sides keep the league's published shape exactly, because that is a
 * real formation and this is only a grouping.
 */
function regroup(side: Side, selected: Record<string, string>): Spot[][] {
  const mine = Object.keys(selected).some((k) => k.startsWith(`${side.club}|`));
  if (!mine) return side.shape.lines;

  const byName = new Map(side.squad.map((r) => [r.player, r]));
  const current: Spot[] = side.shape.lines.flatMap((line, i) =>
    line.map((spot, j) => {
      const name = selected[`${side.club}|${i}|${j}`] ?? spot.player;
      const row = byName.get(name);
      return row
        ? { ...spot, player: name, position: row.position.charAt(0).toUpperCase(), detail: row.position }
        : { ...spot, player: name };
    })
  );

  const buckets: Record<string, Spot[]> = { G: [], D: [], M: [], F: [] };
  for (const spot of current) {
    const code = (spot.position || "M").charAt(0).toUpperCase();
    buckets[code in buckets ? code : "M"].push(spot);
  }
  return ["G", "D", "M", "F"].map((k) => buckets[k]).filter((line) => line.length > 0);
}

function shortPosition(code: string): string {
  const c = (code || "").charAt(0).toUpperCase();
  return { G: "GK", D: "DEF", M: "MID", F: "FWD" }[c] ?? "—";
}

/** Both penalty areas, both six-yard boxes, halfway line, centre circle. */
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
      <path
        d="M3 4.5 6 7.5 9 4.5"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/** FPL codes a squad GKP/DEF/MID/FWD; the league codes a slot G/D/M/F. */
function samePosition(squadPosition: string, slotPosition: string): boolean {
  const a = (squadPosition || "").trim().charAt(0).toUpperCase();
  const b = (slotPosition || "").trim().charAt(0).toUpperCase();
  return a === b;
}

function positionName(code: string): string {
  return { G: "in goal", D: "in defence", M: "in midfield", F: "up front" }[code] ?? "here";
}
