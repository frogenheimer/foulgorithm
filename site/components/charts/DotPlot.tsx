"use client";

import styles from "./charts.module.css";

import { useState } from "react";

export type Row = { label: string; value: number; sub: string };

/**
 * Ranked values against a reference line.
 *
 * A dot plot rather than bars, deliberately. Referee foul rates cluster between
 * about 20 and 25, so bars on a zero baseline would all look the same length and
 * the differences that matter would be invisible. Bars imply a zero baseline;
 * dots do not, so a dot plot can start the axis near the data honestly.
 */
export default function DotPlot({
  rows,
  reference,
  referenceLabel,
  unit,
}: {
  rows: Row[];
  reference: number;
  referenceLabel: string;
  unit: string;
}) {
  const [hover, setHover] = useState<string | null>(null);

  const rowH = 25;
  const labelW = 128;
  const valueW = 52;
  const W = 900;
  const H = rows.length * rowH + 44;
  const plotW = W - labelW - valueW - 16;

  const values = rows.map((r) => r.value);
  const pad = (Math.max(...values) - Math.min(...values)) * 0.18 || 1;
  const lo = Math.min(...values, reference) - pad;
  const hi = Math.max(...values, reference) + pad;
  const x = (v: number) => labelW + ((v - lo) / (hi - lo)) * plotW;

  const ticks: number[] = [];
  const start = Math.ceil(lo);
  for (let v = start; v <= hi; v += 1) ticks.push(v);

  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Ranked by ${unit} against the ${referenceLabel}`}>
        {ticks.map((t) => (
          <g key={t}>
            <line className={styles.grid} x1={x(t)} x2={x(t)} y1={14} y2={rows.length * rowH + 18} />
            <text className={styles.tick} x={x(t)} y={H - 8} textAnchor="middle">
              {t}
            </text>
          </g>
        ))}

        <line
          x1={x(reference)}
          x2={x(reference)}
          y1={6}
          y2={rows.length * rowH + 18}
          stroke="var(--series-2)"
          strokeWidth={1.5}
          strokeDasharray="4 3"
        />
        <text
          x={x(reference)}
          y={0}
          dy={-0}
          textAnchor="middle"
          style={{ fontSize: 11, fill: "var(--series-2)" }}
        >
          <tspan x={x(reference)} dy={10}>
            {referenceLabel} {reference.toFixed(1)}
          </tspan>
        </text>

        {rows.map((r, i) => {
          const cy = i * rowH + rowH / 2 + 18;
          const on = hover === r.label;
          return (
            <g
              key={r.label}
              onMouseEnter={() => setHover(r.label)}
              onMouseLeave={() => setHover(null)}
            >
              <rect x={0} y={cy - rowH / 2} width={W} height={rowH} fill="transparent" />
              <text
                x={labelW - 12}
                y={cy + 4}
                textAnchor="end"
                style={{ fontSize: 12.5, fill: on ? "var(--text-primary)" : "var(--text-secondary)" }}
              >
                {r.label}
              </text>
              {/* connector from the reference makes the deviation readable at a glance */}
              <line
                x1={x(reference)}
                x2={x(r.value)}
                y1={cy}
                y2={cy}
                stroke="var(--grid)"
                strokeWidth={2}
              />
              <circle
                cx={x(r.value)}
                cy={cy}
                r={on ? 6 : 5}
                fill="var(--seq-450)"
                stroke="var(--surface-1)"
                strokeWidth={2}
              />
              <text
                x={W - valueW + 4}
                y={cy + 4}
                className={styles.tick}
                style={{ fontSize: 12, fill: on ? "var(--text-primary)" : "var(--text-secondary)" }}
              >
                {r.value.toFixed(2)}
              </text>
            </g>
          );
        })}
      </svg>

      <div style={{ minHeight: 30, marginTop: 8, fontSize: 12.5 }}>
        {hover ? (
          <span style={{ color: "var(--text-secondary)" }}>
            <strong style={{ color: "var(--text-primary)" }}>{hover}</strong>{" "}
            {rows.find((r) => r.label === hover)!.sub}
          </span>
        ) : (
          <span style={{ color: "var(--text-muted)" }}>
            Hover a referee for appearances and card rate.
          </span>
        )}
      </div>
    </div>
  );
}
