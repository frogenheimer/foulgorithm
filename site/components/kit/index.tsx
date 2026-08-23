/**
 * The primitives. Mandatory: docs/brandbook.md, enforced by
 * scripts/audit-ui.sh.
 *
 * These exist because nine pages produced twenty-two CSS modules, eight
 * separate implementations of one table, thirty-nine uppercase label rules and
 * thirteen hand-built card shells. Not one of those was a disagreement about
 * design. Reuse simply was not the cheap path.
 */

import type { ReactNode } from "react";
import s from "./kit.module.css";

/* ---------- headers ---------- */

export function PageHeader({ title, lede }: { title: string; lede?: ReactNode }) {
  return (
    <header className={s.page}>
      <h1 className={s.h1}>{title}</h1>
      {lede && <p className={s.lede}>{lede}</p>}
    </header>
  );
}

export function SectionHead({ title, note }: { title: string; note?: ReactNode }) {
  return (
    <div className={s.section}>
      <h2 className={s.h2}>{title}</h2>
      {note && <p className={s.note}>{note}</p>}
    </div>
  );
}

/** Uppercase tracked label above a figure. There were thirty-nine of these. */
export function MicroLabel({ children }: { children: ReactNode }) {
  return <span className={s.micro}>{children}</span>;
}

/* ---------- card ---------- */

export function Card({
  children,
  title,
  subtitle,
  flush = false,
}: {
  children: ReactNode;
  title?: string;
  subtitle?: ReactNode;
  /** No padding, for a card whose whole body is a table. */
  flush?: boolean;
}) {
  return (
    <section className={flush ? s.cardFlush : s.card}>
      {title && (
        <header className={s.cardHead}>
          <h3 className={s.cardTitle}>{title}</h3>
          {subtitle && <p className={s.cardSub}>{subtitle}</p>}
        </header>
      )}
      {children}
    </section>
  );
}

/* ---------- metric ---------- */

type Tone = "neutral" | 1 | 2 | 3 | 4;

export function Metric({
  label,
  value,
  note,
  tone = "neutral",
}: {
  label: string;
  value: string;
  note?: ReactNode;
  tone?: Tone;
}) {
  const toneClass = tone === "neutral" ? "" : s[`tone${tone}`];
  return (
    <div className={s.metric}>
      <MicroLabel>{label}</MicroLabel>
      <div className={`${s.metricValue} ${toneClass}`}>{value}</div>
      {note && <div className={s.metricNote}>{note}</div>}
    </div>
  );
}

export function MetricRow({ children }: { children: ReactNode }) {
  return <div className={s.metrics}>{children}</div>;
}

/* ---------- scroller ---------- */

/**
 * Wide content scrolls inside its own box; the page body never scrolls.
 *
 * `min-width: 0` on this is load-bearing and easy to leave off: a grid or flex
 * item defaults to `min-width: auto` and refuses to shrink below its contents,
 * so the table pushes the whole page wider while the scroller looks correct.
 * That bug shipped once already.
 */
export function Scroller({ children }: { children: ReactNode }) {
  return <div className={s.tableWrap}>{children}</div>;
}

/* ---------- table ---------- */

export type Column<T> = {
  key: string;
  head: ReactNode;
  /** Right-aligns and applies tabular figures, matching pro convention. */
  numeric?: boolean;
  sort?: (a: T, b: T) => number;
  cell: (row: T) => ReactNode;
};

export function DataTable<T>({
  rows,
  columns,
  rowKey,
  sortKey,
  onSort,
  onRowClick,
  empty = "Nothing matches.",
}: {
  rows: T[];
  columns: Column<T>[];
  rowKey: (row: T) => string;
  sortKey?: string;
  onSort?: (key: string) => void;
  onRowClick?: (row: T) => void;
  empty?: ReactNode;
}) {
  return (
    <Scroller>
      <table className={s.dataTable}> {/* audit-ignore B7: this IS the DataTable */}
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c.key} className={c.numeric ? s.num : undefined} scope="col">
                {c.sort && onSort ? (
                  <button type="button" className={s.sortable} onClick={() => onSort(c.key)}>
                    {c.head}
                    {sortKey === c.key && <span className={s.sortMark}>&darr;</span>}
                  </button>
                ) : (
                  c.head
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr
              key={rowKey(row)}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
              style={onRowClick ? { cursor: "pointer" } : undefined}
            >
              {columns.map((c) => (
                <td key={c.key} className={c.numeric ? s.num : undefined}>
                  {c.cell(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length === 0 && <p className={s.empty}>{empty}</p>}
    </Scroller>
  );
}

/* ---------- odds ---------- */

/**
 * A decimal price. Monospace, because a price is a readout rather than prose.
 *
 * `muted` is for a price we are estimating rather than asserting, which is
 * every bookmaker figure on this site: we have never observed a player-fouls
 * price and the estimate is a stated assumption.
 */
export function Odds({ value, muted = false }: { value: number | null; muted?: boolean }) {
  if (value === null || !Number.isFinite(value)) {
    return <span className={s.oddsMuted}>&mdash;</span>;
  }
  return <span className={muted ? s.oddsMuted : s.odds}>{value.toFixed(2)}</span>;
}

/* ---------- dots: the fingerprint ---------- */

/**
 * Did the line land, in each of the last few matches. Most recent on the left.
 *
 * Filled against hollow rather than two colours, so it survives greyscale and
 * colour blindness without a legend. Missing matches are drawn as dashed gaps,
 * not as misses: fewer matches played is not a run of failures.
 */
export function Dots({
  hits,
  window,
  label,
}: {
  hits: boolean[];
  window: number;
  label: string;
}) {
  const missing = Math.max(0, window - hits.length);
  return (
    <span
      className={s.dots}
      role="img"
      aria-label={`${label}: ${hits.filter(Boolean).length} of ${hits.length}`}
    >
      {hits.map((hit, i) => (
        <span key={i} className={hit ? s.hit : s.miss} />
      ))}
      {Array.from({ length: missing }, (_, i) => (
        <span key={`gap${i}`} className={s.gap} />
      ))}
    </span>
  );
}

/* ---------- badge ---------- */

export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "good" | "warn" | "bad";
}) {
  const map = { neutral: "", good: s.badgeGood, warn: s.badgeWarn, bad: s.badgeBad };
  return <span className={`${s.badge} ${map[tone]}`}>{children}</span>;
}

/* ---------- skeleton ---------- */

export function Skeleton({ width = "100%", height = "1em" }: { width?: string; height?: string }) {
  return <span className={s.skeleton} style={{ display: "block", width, height }} aria-hidden />;
}
