/**
 * The chart pack: a small set of chart types sharing one visual language.
 *
 * Every chart on the site comes from here, so they read as one system rather
 * than as separate experiments. Rules, all from docs/16-design-direction.md:
 *
 *   - Server components. No "use client", so these cost zero client JavaScript
 *     and render at build time into the static export.
 *   - Colour comes from CSS custom properties, so dark mode is free and no
 *     chart carries a hard-coded hex.
 *   - One idea per chart. A chart needing a paragraph of explanation is the
 *     wrong chart.
 *   - Every chart carries a text alternative, because colour and position must
 *     never be the only way to read it.
 */

import s from "./pack.module.css";

const INK = "var(--text-muted)";
const GRID = "var(--grid)";

/* ------------------------------------------------------------------ *
 * Dot array. 20 dots, so a reader COUNTS rather than judging an area.
 * The evidence for this over a bar is the strongest in the field.
 * ------------------------------------------------------------------ */

export function DotArray({
  p,
  label,
  columns = 10,
  size = 6,
}: {
  p: number;
  label: string;
  columns?: number;
  size?: number;
}) {
  const total = 20;
  const filled = Math.round(p * total);
  const gap = 3;
  const rows = Math.ceil(total / columns);
  const w = columns * size + (columns - 1) * gap;
  const h = rows * size + (rows - 1) * gap;

  return (
    <svg
      viewBox={`0 0 ${w} ${h}`}
      width={w}
      height={h}
      role="img"
      aria-label={`${label}: ${filled} of ${total}`}
      className={s.dots}
    >
      {Array.from({ length: total }, (_, i) => (
        <circle
          key={i}
          cx={(i % columns) * (size + gap) + size / 2}
          cy={Math.floor(i / columns) * (size + gap) + size / 2}
          r={size / 2}
          fill={i < filled ? "var(--seq-450)" : GRID}
        />
      ))}
    </svg>
  );
}

/* ------------------------------------------------------------------ *
 * Horizontal bars. For ranked magnitude with named things, where the
 * labels are words and would read badly rotated.
 * ------------------------------------------------------------------ */

export function Bars({
  rows,
  max,
  unit = "",
  height = 18,
  labelWidth = 96,
}: {
  rows: { label: string; value: number; muted?: boolean }[];
  max?: number;
  unit?: string;
  height?: number;
  labelWidth?: number;
}) {
  const ceiling = max ?? Math.max(...rows.map((r) => r.value)) * 1.05;
  const W = 420;
  const barArea = W - labelWidth - 44;
  const H = rows.length * height + 4;

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      className={s.chart}
      role="img"
      aria-label={rows.map((r) => `${r.label} ${r.value}${unit}`).join(", ")}
    >
      {rows.map((r, i) => {
        const y = i * height + 2;
        const w = Math.max(1, (r.value / ceiling) * barArea);
        return (
          <g key={r.label}>
            <text x={labelWidth - 8} y={y + height / 2 + 4} textAnchor="end" className={s.tick}>
              {r.label}
            </text>
            <rect
              x={labelWidth}
              y={y + 3}
              width={w}
              height={height - 8}
              rx={3}
              fill={r.muted ? "var(--seq-100)" : "var(--seq-450)"}
            />
            <text x={labelWidth + w + 7} y={y + height / 2 + 4} className={s.value}>
              {r.value}
              {unit}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

/* ------------------------------------------------------------------ *
 * Distribution. The shape of a count outcome, with the mean marked.
 * ------------------------------------------------------------------ */

export function Distribution({
  pmf,
  from = 0,
  highlightAbove,
  label,
}: {
  pmf: number[];
  from?: number;
  highlightAbove?: number;
  label: string;
}) {
  const W = 420;
  const H = 96;
  const pad = { top: 6, bottom: 18 };
  const max = Math.max(...pmf);
  const bw = W / pmf.length;
  const ih = H - pad.top - pad.bottom;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className={s.chart} role="img" aria-label={label}>
      {pmf.map((v, i) => {
        const value = from + i;
        const h = Math.max(1, (v / max) * ih);
        const on = highlightAbove !== undefined && value > highlightAbove;
        return (
          <rect
            key={value}
            x={i * bw + 0.6}
            y={pad.top + ih - h}
            width={Math.max(1, bw - 1.2)}
            height={h}
            rx={1.5}
            fill={on ? "var(--seq-450)" : "var(--seq-100)"}
          />
        );
      })}
      <line x1={0} x2={W} y1={pad.top + ih} y2={pad.top + ih} stroke={GRID} />
      {pmf.map((_, i) => {
        const value = from + i;
        return value % 5 === 0 ? (
          <text key={value} x={i * bw + bw / 2} y={H - 5} textAnchor="middle" className={s.tick}>
            {value}
          </text>
        ) : null;
      })}
    </svg>
  );
}

/* ------------------------------------------------------------------ *
 * Sparkline. A trend at a glance, no axes, no numbers.
 * ------------------------------------------------------------------ */

export function Sparkline({
  values,
  label,
  width = 120,
  height = 28,
}: {
  values: number[];
  label: string;
  width?: number;
  height?: number;
}) {
  if (values.length < 2) return null;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const step = width / (values.length - 1);
  const path = values
    .map((v, i) => `${i === 0 ? "M" : "L"}${i * step},${height - ((v - min) / span) * (height - 4) - 2}`)
    .join(" ");

  return (
    <svg viewBox={`0 0 ${width} ${height}`} width={width} height={height} role="img" aria-label={label}>
      <path d={path} fill="none" stroke="var(--seq-450)" strokeWidth={1.75} strokeLinejoin="round" />
      <circle
        cx={(values.length - 1) * step}
        cy={height - ((values[values.length - 1] - min) / span) * (height - 4) - 2}
        r={2.5}
        fill="var(--seq-450)"
      />
    </svg>
  );
}

/* ------------------------------------------------------------------ *
 * Comparison strip. One value against a reference, e.g. a player
 * against his position's average.
 * ------------------------------------------------------------------ */

export function VersusStrip({
  value,
  reference,
  max,
  label,
}: {
  value: number;
  reference: number;
  max: number;
  label: string;
}) {
  const W = 160;
  const H = 22;
  const x = (v: number) => Math.min((v / max) * W, W);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className={s.chart} role="img" aria-label={label}>
      <rect x={0} y={H / 2 - 3} width={W} height={6} rx={3} fill={GRID} />
      <rect x={0} y={H / 2 - 3} width={x(value)} height={6} rx={3} fill="var(--seq-450)" />
      <line
        x1={x(reference)}
        x2={x(reference)}
        y1={2}
        y2={H - 2}
        stroke="var(--series-2)"
        strokeWidth={1.75}
      />
    </svg>
  );
}
