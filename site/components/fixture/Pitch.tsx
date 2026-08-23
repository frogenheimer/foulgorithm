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
}: {
  home: Side;
  away: Side;
  selected: Selected;
  onChange: (next: Selected) => void;
  onReset: () => void;
  market: Market;
  onMarket: (m: Market) => void;
}) {
  const [dragging, setDragging] = useState<{ club: string; key: string } | null>(null);
  const swaps = Object.keys(selected).length;
  const confirmed = !(home.shape.predicted || away.shape.predicted);

  return (
    <div className={s.wrap}>
      <div className={s.head}>
        <span className={s.club}>
          {home.club} <span className={s.formation}>{home.shape.formation ?? "by position"}</span>
        </span>
        <span className={s.versus}>{confirmed ? "confirmed elevens" : "predicted elevens"}</span>
        <span className={s.clubAway}>
          <span className={s.formation}>{away.shape.formation ?? "by position"}</span> {away.club}
        </span>
      </div>

      {swaps > 0 && (
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
        <span className={s.marketNote}>expected in this match, per player</span>
      </div>

      <div className={s.squad}>
        <Bench
          side={home}
          selected={selected}
          market={market}
          dragging={dragging}
          onDragStart={(key) => setDragging({ club: home.club, key })}
          onDragEnd={() => setDragging(null)}
        />

        <div className={s.pitch}>
          {/* The grass is a layer of its own so the pitch itself can let an
              open dropdown overhang the touchline instead of clipping it. */}
          <div className={s.turf} aria-hidden>
            <Markings />
          </div>
          <Half
            side={home}
            selected={selected}
            onChange={onChange}
            market={market}
            dragging={dragging}
            onDrop={() => setDragging(null)}
            onDragStart={(key) => setDragging({ club: home.club, key })}
          />
          <Half
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

        <Bench
          side={away}
          selected={selected}
          market={market}
          dragging={dragging}
          onDragStart={(key) => setDragging({ club: away.club, key })}
          onDragEnd={() => setDragging(null)}
        />
      </div>
    </div>
  );
}

/* ---------- who is where ---------- */


function Bench({
  side,
  selected,
  market,
  dragging,
  onDragStart,
  onDragEnd,
}: {
  side: Side;
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
    occupancyOf(side.shape, side.squad, selected, findPlayer)
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
              draggable
              onDragStart={() => onDragStart(key)}
              onDragEnd={onDragEnd}
              className={
                dragging?.key === key ? `${s.benchPlayer} ${s.dragging}` : s.benchPlayer
              }
              title={`${r.fullName} · drag onto the pitch`}
            >
              <span>{r.player}</span>
              <span className={s.benchPos}>
                {shortPosition(r.position)} {r.expected[market].toFixed(2)}
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
}: {
  side: Side;
  selected: Selected;
  onChange: (next: Selected) => void;
  market: Market;
  dragging: { club: string; key: string } | null;
  onDrop: () => void;
  onDragStart: (key: string) => void;
  mirrored?: boolean;
}) {
  const [open, setOpen] = useState<string | null>(null);
  const here = occupancyOf(side.shape, side.squad, selected, findPlayer);
  const byKey = new Map(here.map((o) => [o.key, o]));
  const shirts = useMemo(() => shirtIndex(side.shape), [side.shape]);

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
    <div className={mirrored ? `${s.half} ${s.away}` : s.half}>
      {shape.map((line, i) => (
        <div key={i} className={s.line}>
          {line.map((o) => {
            const swapped = Boolean(selected[o.key]);
            const misplaced = outOfPosition(o.row, o.spot);
            const isOpen = open === o.key;
            const receiving = Boolean(dragging && dragging.club === side.club);
            return (
              <div
                key={o.key}
                className={[
                  s.slot,
                  swapped ? s.swapped : "",
                  misplaced ? s.misplaced : "",
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
                <span
                  className={s.shirt}
                  draggable
                  onDragStart={() => onDragStart(o.key)}
                  title={
                    misplaced
                      ? `${o.name} is a ${shortPosition(o.row!.position)} standing ${positionName(o.spot.position)}`
                      : o.name
                  }
                >
                  {markerFor(shirts, o.row, o.spot)}
                </span>
                <div className={s.picker}>
                  <Combobox
                    value={o.name}
                    options={optionsFor(byName, o.spot, market)}
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
                        title={`${o.row?.fullName ?? o.name}. Change.`}
                      >
                        <span className={s.name}>{o.name}</span>
                        <Chevron />
                      </button>
                    )}
                  />
                </div>
                <span className={s.rate}>
                  {o.row ? o.row.expected[market].toFixed(2) : "—"}
                </span>
              </div>
            );
          })}
        </div>
      ))}
    </div>
  );
}

/** Options for one slot: players who fit the position first, everyone else after. */
function optionsFor(rows: ExplorerRow[], spot: Spot, market: Market): Option[] {
  return rows.map((row) => ({
    value: who(row.fullName),
    label: row.player,
    meta: `${shortPosition(row.position)} · ${row.expected[market].toFixed(2)}`,
    group: samePosition(row.position, spot.position)
      ? `Plays ${positionName(spot.position)}`
      : undefined,
  }));
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
