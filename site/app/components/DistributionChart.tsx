"use client";

import { useState } from "react";

type Bin = { fouls: number; matches: number; share: number };

/**
 * The empirical distribution of total fouls in a match.
 *
 * This is the chart that justifies the modelling approach: it is a discrete,
 * right-skewed count, which is why the model fits count distributions rather
 * than the truncated normal the 2025 version used.
 */
export default function DistributionChart({ bins }: { bins: Bin[] }) {
  const [hover, setHover] = useState<number | null>(null);

  const W = 760;
  const H = 260;
  const M = { top: 16, right: 16, bottom: 34, left: 40 };
  const iw = W - M.left - M.right;
  const ih = H - M.top - M.bottom;

  const max = Math.max(...bins.map((b) => b.share));
  const bw = iw / bins.length;
  const y = (v: number) => M.top + ih - (v / max) * ih;

  const mean = bins.reduce((a, b) => a + b.fouls * b.share, 0);
  const ticks = [0, 0.02, 0.04, 0.06];

  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Distribution of total fouls per match">
        {ticks.map((t) => (
          <g key={t}>
            <line className="gridline" x1={M.left} x2={W - M.right} y1={y(t)} y2={y(t)} />
            <text className="tick" x={M.left - 8} y={y(t) + 4} textAnchor="end">
              {(t * 100).toFixed(0)}%
            </text>
          </g>
        ))}

        {bins.map((b, i) => {
          const h = Math.max(1, M.top + ih - y(b.share));
          const on = hover === b.fouls;
          return (
            <rect
              key={b.fouls}
              x={M.left + i * bw + 1}
              y={y(b.share)}
              width={Math.max(1, bw - 2)}
              height={h}
              rx={3}
              fill={on ? "var(--seq-600)" : "var(--seq-450)"}
              onMouseEnter={() => setHover(b.fouls)}
              onMouseLeave={() => setHover(null)}
            />
          );
        })}

        <line className="axisline" x1={M.left} x2={W - M.right} y1={M.top + ih} y2={M.top + ih} />

        {bins.map((b, i) =>
          b.fouls % 5 === 0 ? (
            <text key={b.fouls} className="tick" x={M.left + i * bw + bw / 2} y={H - 12} textAnchor="middle">
              {b.fouls}
            </text>
          ) : null
        )}

        {(() => {
          const mx = M.left + (mean - bins[0].fouls) * bw + bw / 2;
          return <line className="axisline" x1={mx} x2={mx} y1={M.top} y2={M.top + ih} strokeDasharray="3 3" />;
        })()}
      </svg>

      <div style={{ minHeight: 34, marginTop: 8, fontSize: 13 }}>
        {hover !== null ? (
          <span style={{ color: "var(--text-secondary)" }}>
            <strong style={{ color: "var(--text-primary)" }}>{hover} fouls</strong> in{" "}
            {(bins.find((b) => b.fouls === hover)!.share * 100).toFixed(1)}% of matches (
            {bins.find((b) => b.fouls === hover)!.matches.toLocaleString()} matches)
          </span>
        ) : (
          <span style={{ color: "var(--text-muted)" }}>
            Dashed line marks the mean, {mean.toFixed(1)} fouls. Hover a bar for its share.
          </span>
        )}
      </div>
    </div>
  );
}
