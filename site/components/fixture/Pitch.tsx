"use client";

/**
 * The confirmed eleven, on a pitch, with every slot swappable.
 *
 * The shape is the league's own: it publishes the formation as lines of player
 * ids, goalkeeper first, so this draws the real 4-2-3-1 rather than inferring a
 * shape from position codes. Codes cannot tell a back three from a back four.
 *
 * Swapping a player is not decoration. The five characters' combinations are
 * rebuilt from whoever is on the pitch, so a reader can ask "what if he is
 * rested" and see the answer rather than being told to wait for team news.
 */

import { useMemo } from "react";
import type { ExplorerRow, Spot, TeamShape } from "@/lib/data";
import { MicroLabel } from "@/components/kit";
import s from "./pitch.module.css";

export default function Pitch({
  club,
  shape,
  squad,
  selected,
  onSwap,
  onReset,
  rateOf,
}: {
  club: string;
  shape: TeamShape;
  /** Everyone available to this club in this fixture, for the dropdowns. */
  squad: ExplorerRow[];
  /** slot key -> player name, when swapped away from the published eleven */
  selected: Record<string, string>;
  onSwap: (slotKey: string, player: string) => void;
  onReset: () => void;
  /** What to show under each name. Expected fouls, usually. */
  rateOf: (player: string) => string;
}) {
  const options = useMemo(
    () => [...squad].sort((a, b) => a.player.localeCompare(b.player)),
    [squad]
  );
  const swaps = Object.keys(selected).length;

  return (
    <div className={s.wrap}>
      <div className={s.head}>
        <span className={s.club}>{club}</span>
        <span className={s.formation}>{shape.formation ?? "shape unknown"}</span>
        {swaps > 0 && (
          <button type="button" className={s.reset} onClick={onReset}>
            Reset {swaps} change{swaps === 1 ? "" : "s"}
          </button>
        )}
      </div>

      <div className={s.pitch}>
        <Markings />
        {/* Drawn attack-first, so the pitch reads the way a fan looks at it. */}
        {[...shape.lines].reverse().map((line, i) => (
          <div key={i} className={s.line}>
            {line.map((spot, j) => {
              const key = `${club}|${shape.lines.length - 1 - i}|${j}`;
              const player = selected[key] ?? spot.player;
              const swapped = Boolean(selected[key]);
              return (
                <div key={key} className={swapped ? `${s.slot} ${s.swapped}` : s.slot}>
                  <span className={s.shirt}>{spot.shirt ?? spot.position}</span>
                  <span className={s.name} title={`${player} · ${spot.detail || spot.position}`}>
                    {player}
                  </span>
                  <span className={s.rate}>{rateOf(player)}</span>
                  <select
                    className={s.picker}
                    value={player}
                    onChange={(e) => onSwap(key, e.target.value)}
                    aria-label={`${spot.detail || spot.position} for ${club}`}
                  >
                    {options.some((o) => o.player === player) ? null : (
                      <option value={player}>{player}</option>
                    )}
                    {options.map((o) => (
                      <option key={o.fullName} value={o.player}>
                        {o.player}
                      </option>
                    ))}
                  </select>
                </div>
              );
            })}
          </div>
        ))}
      </div>

      {shape.bench.length > 0 && (
        <div>
          <MicroLabel>Bench</MicroLabel>
          <p className={s.note}>{shape.bench.map((b: Spot) => b.player).join(" · ")}</p>
        </div>
      )}
    </div>
  );
}

/** Halfway line, centre circle, penalty box. Enough to read as a pitch. */
function Markings() {
  return (
    <svg className={s.markings} viewBox="0 0 100 140" preserveAspectRatio="none" aria-hidden>
      <g fill="none" stroke="currentColor" strokeWidth="0.4" vectorEffect="non-scaling-stroke">
        <rect x="2" y="2" width="96" height="136" />
        <line x1="2" y1="70" x2="98" y2="70" />
        <circle cx="50" cy="70" r="12" />
        <rect x="28" y="2" width="44" height="18" />
        <rect x="28" y="120" width="44" height="18" />
      </g>
    </svg>
  );
}
