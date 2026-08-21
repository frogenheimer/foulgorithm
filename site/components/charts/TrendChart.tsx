"use client";

import styles from "./charts.module.css";

import { useState } from "react";
import type { SeasonRow } from "@/lib/data";

/**
 * Fouls and cards indexed to 100 at the first season.
 *
 * Indexed deliberately: fouls run around 22 a match and cards around 4, so a
 * shared raw axis would flatten cards into a line along the floor. Indexing puts
 * both on one axis, which is the only honest way to show two different measures
 * together. A second y-axis would not be.
 */
export default function TrendChart({ seasons }: { seasons: SeasonRow[] }) {
  const [hover, setHover] = useState<number | null>(null);

  const W = 760;
  const H = 300;
  const M = { top: 16, right: 20, bottom: 34, left: 40 };
  const iw = W - M.left - M.right;
  const ih = H - M.top - M.bottom;

  const base = seasons[0];
  const pts = seasons.map((s, i) => ({
    ...s,
    i,
    fouls: (s.foulsPerMatch / base.foulsPerMatch) * 100,
    cards: (s.cardsPerMatch / base.cardsPerMatch) * 100,
  }));

  const all = pts.flatMap((p) => [p.fouls, p.cards]);
  const lo = Math.floor(Math.min(...all) / 10) * 10 - 5;
  const hi = Math.ceil(Math.max(...all) / 10) * 10 + 5;

  const x = (i: number) => M.left + (i / (pts.length - 1)) * iw;
  const y = (v: number) => M.top + ih - ((v - lo) / (hi - lo)) * ih;
  const line = (key: "fouls" | "cards") =>
    pts.map((p, i) => `${i === 0 ? "M" : "L"}${x(p.i)},${y(p[key])}`).join(" ");

  const ticks: number[] = [];
  for (let v = lo; v <= hi; v += 10) ticks.push(v);

  const active = hover === null ? null : pts[hover];

  return (
    <div>
      <div className={styles.legend}>
        <span>
          <i className={styles.swatch} style={{ background: "var(--series-1)" }} /> Fouls per match
        </span>
        <span>
          <i className={styles.swatch} style={{ background: "var(--series-2)" }} /> Cards per match
        </span>
      </div>

      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Fouls and cards per match by season, indexed to 100 at 2000-01">
        {ticks.map((t) => (
          <g key={t}>
            <line className={styles.grid} x1={M.left} x2={W - M.right} y1={y(t)} y2={y(t)} />
            <text className={styles.tick} x={M.left - 8} y={y(t) + 4} textAnchor="end">
              {t}
            </text>
          </g>
        ))}

        {/* The index baseline: everything is relative to this */}
        <line className={styles.axis} x1={M.left} x2={W - M.right} y1={y(100)} y2={y(100)} strokeDasharray="3 3" />

        {pts.map((p, i) =>
          i % 5 === 0 || i === pts.length - 1 ? (
            <text key={p.season} className={styles.tick} x={x(p.i)} y={H - 12} textAnchor="middle">
              {p.season.slice(2)}
            </text>
          ) : null
        )}

        <path d={line("fouls")} fill="none" stroke="var(--series-1)" strokeWidth={2} strokeLinejoin="round" />
        <path d={line("cards")} fill="none" stroke="var(--series-2)" strokeWidth={2} strokeLinejoin="round" />

        {active && (
          <>
            <line className={styles.axis} x1={x(active.i)} x2={x(active.i)} y1={M.top} y2={M.top + ih} />
            {(["fouls", "cards"] as const).map((k) => (
              <circle
                key={k}
                cx={x(active.i)}
                cy={y(active[k])}
                r={4.5}
                fill={k === "fouls" ? "var(--series-1)" : "var(--series-2)"}
                stroke="var(--surface-1)"
                strokeWidth={2}
              />
            ))}
          </>
        )}

        {pts.map((p) => (
          <rect
            key={p.season}
            x={x(p.i) - iw / (pts.length - 1) / 2}
            y={M.top}
            width={iw / (pts.length - 1)}
            height={ih}
            fill="transparent"
            onMouseEnter={() => setHover(p.i)}
            onMouseLeave={() => setHover(null)}
          />
        ))}
      </svg>

      <div style={{ minHeight: 46, marginTop: 10, fontSize: 13 }}>
        {active ? (
          <span style={{ color: "var(--text-secondary)" }}>
            <strong style={{ color: "var(--text-primary)" }}>{active.season}</strong>
            {" · "}
            {active.foulsPerMatch} fouls per match ({active.fouls.toFixed(0)} indexed)
            {" · "}
            {active.cardsPerMatch} cards per match ({active.cards.toFixed(0)} indexed)
          </span>
        ) : (
          <span style={{ color: "var(--text-muted)" }}>Hover a season for its numbers.</span>
        )}
      </div>
    </div>
  );
}
