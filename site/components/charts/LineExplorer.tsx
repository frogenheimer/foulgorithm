"use client";

import { useMemo, useState } from "react";
import type { FixturePrediction } from "@/lib/data";
import { odds, pct } from "@/lib/format";
import styles from "./charts.module.css";

/**
 * The predicted distribution for one fixture, with a movable line.
 *
 * This is why models return distributions rather than point estimates: one fit
 * prices every line. Drag or hover anywhere on the curve and the probability
 * and fair odds follow. See docs/decisions/ADR-005.
 */
export default function LineExplorer({ fixture }: { fixture: FixturePrediction }) {
  // The published pmf is truncated to a readable range, so it sums to slightly
  // under 1. Renormalise, otherwise the explorer and the line table disagree in
  // the first decimal place and one of them is wrong.
  const bars = useMemo(() => {
    const total = fixture.pmf.reduce((a, b) => a + b, 0);
    return fixture.pmf.map((p, i) => ({ fouls: fixture.pmfFrom + i, p: p / total }));
  }, [fixture]);
  const defaultLine = 22.5;
  const [line, setLine] = useState(defaultLine);

  const W = 560;
  const H = 150;
  const M = { top: 10, right: 8, bottom: 24, left: 8 };
  const iw = W - M.left - M.right;
  const ih = H - M.top - M.bottom;

  const max = Math.max(...bars.map((b) => b.p));
  const bw = iw / bars.length;
  const x = (fouls: number) => M.left + (fouls - fixture.pmfFrom) * bw;
  const y = (p: number) => M.top + ih - (p / max) * ih;

  const probOver = bars.filter((b) => b.fouls > line).reduce((a, b) => a + b.p, 0);
  const fairOver = probOver > 0 ? 1 / probOver : Infinity;
  const fairUnder = probOver < 1 ? 1 / (1 - probOver) : Infinity;

  const lineMin = fixture.pmfFrom + 0.5;
  const lineMax = fixture.pmfFrom + bars.length - 1.5;
  const clamp = (v: number) => Math.min(Math.max(v, lineMin), lineMax);

  function moveTo(clientX: number, target: SVGSVGElement) {
    const box = target.getBoundingClientRect();
    const ratio = (clientX - box.left) / box.width;
    const fouls = fixture.pmfFrom + ratio * bars.length;
    setLine(clamp(Math.round(fouls) - 0.5));
  }

  // The chart is the control: a slider over the distribution's lines. Arrow
  // keys move it a line at a time, so a keyboard prices the market too.
  function onKey(e: React.KeyboardEvent) {
    const step =
      e.key === "ArrowLeft" || e.key === "ArrowDown" ? -1
      : e.key === "ArrowRight" || e.key === "ArrowUp" ? 1
      : null;
    if (step !== null) setLine(clamp(line + step));
    else if (e.key === "Home") setLine(lineMin);
    else if (e.key === "End") setLine(lineMax);
    else return;
    e.preventDefault();
  }

  return (
    <div>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        role="slider"
        tabIndex={0}
        aria-label={`Line for total fouls, ${fixture.home} against ${fixture.away}`}
        aria-valuemin={lineMin}
        aria-valuemax={lineMax}
        aria-valuenow={line}
        aria-valuetext={`over ${line.toFixed(1)}: ${pct(probOver)}, under: ${pct(1 - probOver)}`}
        onKeyDown={onKey}
        onClick={(e) => moveTo(e.clientX, e.currentTarget)}
        onMouseMove={(e) => moveTo(e.clientX, e.currentTarget)}
        onTouchMove={(e) => moveTo(e.touches[0].clientX, e.currentTarget)}
        style={{ touchAction: "pan-y" }}
      >
        {bars.map((b) => {
          const over = b.fouls > line;
          return (
            <rect
              key={b.fouls}
              x={x(b.fouls) + 0.75}
              y={y(b.p)}
              width={Math.max(1, bw - 1.5)}
              height={Math.max(1, M.top + ih - y(b.p))}
              rx={2}
              fill={over ? "var(--seq-3)" : "var(--seq-1)"}
              className={styles.bar}
            />
          );
        })}

        <line
          x1={x(line + 0.5)}
          x2={x(line + 0.5)}
          y1={M.top - 6}
          y2={M.top + ih}
          stroke="var(--c3)"
          strokeWidth={2}
        />

        <line
          className={styles.axis}
          x1={M.left}
          x2={W - M.right}
          y1={M.top + ih}
          y2={M.top + ih}
        />

        {bars
          .filter((b) => b.fouls % 5 === 0)
          .map((b) => (
            <text key={b.fouls} className={styles.tick} x={x(b.fouls) + bw / 2} y={H - 8} textAnchor="middle">
              {b.fouls}
            </text>
          ))}
      </svg>

      <div className={styles.explorerReadout}>
        <div>
          <span className={styles.readoutLabel}>Over {line.toFixed(1)}</span>
          <span className={styles.readoutValue}>{pct(probOver)}</span>
          <span className={styles.readoutOdds}>fair {odds(fairOver)}</span>
        </div>
        <div>
          <span className={styles.readoutLabel}>Under {line.toFixed(1)}</span>
          <span className={styles.readoutValue}>{pct(1 - probOver)}</span>
          <span className={styles.readoutOdds}>fair {odds(fairUnder)}</span>
        </div>
        {line !== defaultLine && (
          <button className={styles.reset} onClick={() => setLine(defaultLine)}>
            Reset
          </button>
        )}
      </div>
      <p className={styles.hint}>
        Move across the chart, or focus it and use the arrow keys, to price a different line.
      </p>
    </div>
  );
}
