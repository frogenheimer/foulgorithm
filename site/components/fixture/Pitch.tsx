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
import { Combobox, MicroLabel } from "@/components/kit";
import type { Option } from "@/components/kit";
import s from "./pitch.module.css";

export default function Pitch({
  club,
  shape,
  squad,
  selected,
  onSwap,
  onReset,
  rateOf,
  away = false,
  hiddenWhenNarrow = false,
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
  /** The away side attacks left, so its formation is drawn goalkeeper-first. */
  away?: boolean;
  /** Hidden below 900px, where the two sides show one at a time. */
  hiddenWhenNarrow?: boolean;
}) {
  const byName = useMemo(
    () => [...squad].sort((a, b) => a.player.localeCompare(b.player)),
    [squad]
  );

  /**
   * Options for one slot, with players who actually play that position offered
   * first. Everyone else stays one keystroke away rather than hidden: a manager
   * can field whoever he likes and the dropdown should not argue.
   */
  const optionsFor = (spot: Spot): Option[] =>
    byName.map((row) => ({
      value: row.player,
      label: row.player,
      meta: `${row.expected.committed.toFixed(2)}`,
      group: samePosition(row.position, spot.position) ? `Plays ${positionName(spot.position)}` : undefined,
    }));
  const swaps = Object.keys(selected).length;

  return (
    <div className={hiddenWhenNarrow ? `${s.wrap} ${s.hideNarrow}` : s.wrap}>
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
        {/* Lines arrive goalkeeper-first. Home attacks right, so drawn in order
            its keeper sits at the left edge; away attacks left and reverses.
            The two pitches then face each other the way the fixture is written. */}
        {(away ? [...shape.lines].reverse() : [...shape.lines]).map((line, i) => (
          <div key={i} className={s.line}>
            {line.map((spot, j) => {
              const lineIndex = away ? shape.lines.length - 1 - i : i;
              const key = `${club}|${lineIndex}|${j}`;
              const player = selected[key] ?? spot.player;
              const swapped = Boolean(selected[key]);
              return (
                <div key={key} className={swapped ? `${s.slot} ${s.swapped}` : s.slot}>
                  <span className={s.shirt}>{spot.shirt ?? spot.position}</span>
                  <span className={s.name} title={`${player} · ${spot.detail || spot.position}`}>
                    {player}
                  </span>
                  <span className={s.rate}>{rateOf(player)}</span>
                  <div className={s.picker}>
                    <Combobox
                      value={player}
                      options={optionsFor(spot)}
                      onChange={(v) => onSwap(key, v)}
                      label={`${spot.detail || spot.position} for ${club}`}
                      placeholder="Search squad"
                    />
                  </div>
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

/** FPL codes a squad by GKP/DEF/MID/FWD; the league codes a slot G/D/M/F. */
function samePosition(squadPosition: string, slotPosition: string): boolean {
  const first = (squadPosition || "").trim().charAt(0).toUpperCase();
  return first === (slotPosition || "").trim().charAt(0).toUpperCase();
}

function positionName(code: string): string {
  return { G: "in goal", D: "in defence", M: "in midfield", F: "up front" }[code] ?? "here";
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
