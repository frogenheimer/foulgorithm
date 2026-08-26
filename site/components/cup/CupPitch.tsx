"use client";

/**
 * Both elevens on one pitch, the same picture the league fixture pages draw.
 *
 * Read-only, and that is the whole difference. The league's `Pitch` lets you
 * swap a player and recomputes the house sheet from whoever is standing there,
 * which needs the explorer's model rows. Most cup ties have no model rows and
 * never will, so a swap here would have nothing to recompute and the numbers on
 * the shirts would have to be invented. Same styles, same shape, no fiction.
 *
 * The number on a shirt is the player's own fouls per 90 across the matches we
 * hold. It is a fact about him, not a forecast for this game, and the key says
 * so.
 */

import { useState } from "react";
import { MicroLabel } from "@/components/kit";
import type { CupEleven, CupPlayer } from "@/lib/cups";
import s from "@/components/fixture/pitch.module.css";
import c from "./cup.module.css";

export default function CupPitch({
  home,
  away,
}: {
  home: CupEleven;
  away: CupEleven;
}) {
  // Phones show one team at a time, goalkeeper at the foot. Desktop renders
  // both halves side by side and never reads this.
  const [shown, setShown] = useState<"home" | "away">("home");
  const confirmed = home.confirmed && away.confirmed;

  return (
    <div className={`${s.wrap} ${shown === "home" ? s.showHome : s.showAway}`}>
      <div className={s.head}>
        <span className={s.club}>
          {home.team} <span className={s.formation}>{shapeLabel(home)}</span>
        </span>
        <span className={s.versus}>
          {confirmed ? "confirmed elevens" : "predicted elevens"}
        </span>
        <span className={s.clubAway}>
          <span className={s.formation}>{shapeLabel(away)}</span> {away.team}
        </span>
      </div>

      <div className={c.pitchKey}>
        <MicroLabel>On each shirt</MicroLabel>
        <span className={c.pitchKeyText}>
          Fouls per 90 across every match we hold for that player. His own rate,
          not a forecast for this game.
        </span>
      </div>

      <div className={s.sideToggle} role="tablist" aria-label="Which team to show">
        {([["home", home.team], ["away", away.team]] as const).map(([key, club]) => (
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
          <Bench eleven={home} />
        </div>

        <div className={s.pitch}>
          <div className={s.turf} aria-hidden>
            <Markings />
          </div>
          <Half eleven={home} className={s.homeSide} />
          <Half eleven={away} className={s.awaySide} mirrored />
        </div>

        <div className={s.awaySide}>
          <Bench eleven={away} />
        </div>
      </div>
    </div>
  );
}

/** "4-3-3" from a club's sheet, or our own grouping, never confused. */
function shapeLabel(eleven: CupEleven): string {
  if (eleven.formation) return eleven.formation;
  return eleven.grouping ? `${eleven.grouping} by position` : "by position";
}

function Half({
  eleven,
  className = "",
  mirrored = false,
}: {
  eleven: CupEleven;
  className?: string;
  mirrored?: boolean;
}) {
  const lines = mirrored ? [...eleven.lines].reverse() : eleven.lines;

  return (
    <div className={`${mirrored ? `${s.half} ${s.away}` : s.half} ${className}`}>
      {lines.map((line, i) => (
        <div key={i} className={s.line}>
          {line.map((p) => (
            <div key={`${p.player}-${p.shirt ?? "x"}`} className={s.slot}>
              <span className={s.marker}>
                <span
                  className={s.shirt}
                  title={`${p.player} · ${p.foulsPer90 ?? "no rate"} fouls per 90 · ${p.spell}`}
                >
                  {p.foulsPer90 ?? "—"}
                </span>
              </span>
              <span className={c.pitchName}>{surname(p.player)}</span>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

function Bench({ eleven }: { eleven: CupEleven }) {
  if (!eleven.bench.length) return null;
  return (
    <div className={s.bench}>
      <MicroLabel>{eleven.team} squad</MicroLabel>
      <div className={s.benchList}>
        {eleven.bench.map((p) => (
          <span key={p.player} className={c.benchRow}>
            <span className={s.benchPos}>{p.position}</span>
            <span className={c.benchName}>{surname(p.player)}</span>
            <span className={c.benchValue}>{p.foulsPer90 ?? "—"}</span>
          </span>
        ))}
      </div>
    </div>
  );
}

/** Shirts carry surnames. "Gabriel Magalhães" is "Magalhães" on a pitch. */
function surname(name: string): string {
  const parts = name.trim().split(/\s+/);
  return parts.length > 1 ? parts[parts.length - 1] : name;
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
