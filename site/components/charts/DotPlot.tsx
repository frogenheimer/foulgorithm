"use client";

import { useState } from "react";
import styles from "./charts.module.css";

export type Row = { label: string; value: number; sub: string };

/**
 * Ranked values against a reference line.
 *
 * A dot plot rather than bars, deliberately. Referee foul rates cluster between
 * about 20 and 25, so bars on a zero baseline would all look the same length and
 * the differences that matter would be invisible. Bars imply a zero baseline;
 * dots do not, so a dot plot can start the axis near the data honestly.
 *
 * HTML rows rather than one big SVG, also deliberately. An SVG drawn at 900
 * units and scaled to a phone renders its labels at about 5px. Here every
 * position is a percentage of the track, so the geometry scales and the type
 * does not. Each row is a button: hover previews, tap or Enter pins, and the
 * details sit in the row's accessible name rather than behind a hover.
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
  const [pinned, setPinned] = useState<string | null>(null);

  const values = rows.map((r) => r.value);
  const pad = (Math.max(...values) - Math.min(...values)) * 0.18 || 1;
  const lo = Math.min(...values, reference) - pad;
  const hi = Math.max(...values, reference) + pad;
  const x = (v: number) => `${(((v - lo) / (hi - lo)) * 100).toFixed(2)}%`;

  const ticks: number[] = [];
  for (let v = Math.ceil(lo); v <= hi; v += 1) ticks.push(v);

  const activeLabel = pinned ?? hover;
  const active = activeLabel ? rows.find((r) => r.label === activeLabel) : undefined;

  return (
    <div className={styles.dp}>
      <div className={styles.dpRefHead}>
        <span style={{ left: x(reference) }}>
          {referenceLabel} {reference.toFixed(1)}
        </span>
      </div>

      <div className={styles.dpBody}>
        <div className={styles.dpGrid} aria-hidden>
          {ticks.map((t) => (
            <span key={t} className={styles.dpGridline} style={{ left: x(t) }} />
          ))}
          <span className={styles.dpRefLine} style={{ left: x(reference) }} />
        </div>

        {rows.map((r) => {
          const on = activeLabel === r.label;
          const from = Math.min(r.value, reference);
          const to = Math.max(r.value, reference);
          return (
            <button
              key={r.label}
              type="button"
              className={on ? styles.dpRowOn : styles.dpRow}
              aria-pressed={pinned === r.label}
              aria-label={`${r.label}: ${r.value.toFixed(2)} ${unit}. ${r.sub}`}
              onMouseEnter={() => setHover(r.label)}
              onMouseLeave={() => setHover(null)}
              onClick={() => setPinned(pinned === r.label ? null : r.label)}
            >
              <span className={styles.dpLabel}>{r.label}</span>
              <span className={styles.dpTrack}>
                <span
                  className={styles.dpConnector}
                  style={{ left: x(from), width: `calc(${x(to)} - ${x(from)})` }}
                />
                <span className={styles.dpDot} style={{ left: x(r.value) }} />
              </span>
              <span className={styles.dpValue}>{r.value.toFixed(2)}</span>
            </button>
          );
        })}

        <div className={styles.dpScale} aria-hidden>
          {ticks.map((t) => (
            <span key={t} style={{ left: x(t) }}>
              {t}
            </span>
          ))}
        </div>
      </div>

      <div className={styles.readout}>
        {active ? (
          <span>
            <strong>{active.label}</strong> {active.sub}
          </span>
        ) : (
          <span className={styles.readoutIdle}>
            Hover or tap a referee for appearances and card rate.
          </span>
        )}
      </div>
    </div>
  );
}
