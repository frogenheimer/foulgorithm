/**
 * The primitives. Mandatory: docs/brandbook.md, enforced by
 * scripts/audit-ui.sh.
 *
 * These exist because nine pages produced twenty-two CSS modules, eight
 * separate implementations of one table, thirty-nine uppercase label rules and
 * thirteen hand-built card shells. Not one of those was a disagreement about
 * design. Reuse simply was not the cheap path.
 */

import { Fragment } from "react";
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

export function SectionHead({
  title,
  note,
  children,
}: {
  title: string;
  note?: ReactNode;
  /** Alias for `note`, so a heading and its explanation can be written inline. */
  children?: ReactNode;
}) {
  const body = note ?? children;
  return (
    <div className={s.section}>
      <h2 className={s.h2}>{title}</h2>
      {body && <p className={s.note}>{body}</p>}
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
  expanded,
  renderExpanded,
  rowClass,
  empty = "Nothing matches.",
}: {
  rows: T[];
  columns: Column<T>[];
  rowKey: (row: T) => string;
  sortKey?: string;
  onSort?: (key: string) => void;
  onRowClick?: (row: T) => void;
  /** Key of the row currently open, from `rowKey`. */
  expanded?: string | null;
  /** What to draw underneath an open row, spanning every column. */
  renderExpanded?: (row: T) => ReactNode;
  /** Per-row class, for rows that need muting or marking. */
  rowClass?: (row: T) => string | undefined;
  empty?: ReactNode;
}) {
  return (
    <Scroller>
      <table className={s.dataTable}> {/* audit-ignore B7: this IS the DataTable */}
        <thead>
          <tr>
            {columns.map((c) => (
              <th
                key={c.key}
                className={c.numeric ? s.num : undefined}
                scope="col"
                /* Directions vary by column and the table does not know them,
                   so "other" says "sorted by this" without guessing which way. */
                aria-sort={sortKey === c.key ? "other" : undefined}
              >
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
          {rows.map((row) => {
            const key = rowKey(row);
            const open = expanded === key && Boolean(renderExpanded);
            return (
              <Fragment key={key}>
                <tr
                  onClick={onRowClick ? () => onRowClick(row) : undefined}
                  /* A clickable row is reachable by keyboard too: Tab to it,
                     Enter or Space opens it. Not a perfect control (a row is
                     not a button), but strictly better than mouse-only. */
                  tabIndex={onRowClick ? 0 : undefined}
                  onKeyDown={
                    onRowClick
                      ? (e) => {
                          if (e.key === "Enter" || e.key === " ") {
                            e.preventDefault();
                            onRowClick(row);
                          }
                        }
                      : undefined
                  }
                  className={[open ? s.rowOpen : "", rowClass?.(row) ?? ""]
                    .filter(Boolean)
                    .join(" ") || undefined}
                  aria-expanded={renderExpanded ? open : undefined}
                  style={onRowClick ? { cursor: "pointer" } : undefined}
                >
                  {columns.map((c) => (
                    <td key={c.key} className={c.numeric ? s.num : undefined}>
                      {c.cell(row)}
                    </td>
                  ))}
                </tr>
                {open && (
                  <tr className={s.expandedRow}>
                    <td colSpan={columns.length}>{renderExpanded!(row)}</td>
                  </tr>
                )}
              </Fragment>
            );
          })}
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

/* ---------- callout and prose ---------- */

/** One thing the reader must know first. A page with three of these has none. */
export function Callout({ children }: { children: ReactNode }) {
  return <aside className={s.callout}>{children}</aside>;
}

/** A quiet standalone line. Caveats, sample-size notes, sourcing. */
export function Note({ children }: { children: ReactNode }) {
  return <p className={s.standalone}>{children}</p>;
}

/**
 * A run of sentences rather than data.
 *
 * Constrained to a reading width: a 1240px line of text is unreadable however
 * good the type is, and most of this site's credibility lives in its prose.
 */
export function Prose({ children }: { children: ReactNode }) {
  return <div className={s.prose}>{children}</div>;
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

/**
 * A segmented switch between a small, fixed set of views.
 *
 * Not a checkbox: both options are always visible and named, so nobody has to
 * work out what the off state means.
 *
 * Not tabs either. This used to carry role="tablist" with none of the tab
 * pattern behind it (no panel, no arrow keys, no roving tabindex), so a screen
 * reader announced tabs whose keyboard model then did not work. Plain buttons
 * with aria-pressed say exactly what they are, and Tab plus Enter just works.
 */
export function Toggle<T extends string>({
  value,
  options,
  onChange,
  label,
  narrowOnly = false,
}: {
  value: T;
  options: { value: T; label: string }[];
  onChange: (value: T) => void;
  label: string;
  /** Hide above 900px, where a side-by-side layout fits and a switch is noise. */
  narrowOnly?: boolean;
}) {
  return (
    <div
      className={narrowOnly ? `${s.toggle} ${s.narrowOnly}` : s.toggle}
      role="group"
      aria-label={label}
    >
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          aria-pressed={o.value === value}
          className={o.value === value ? s.toggleOptionOn : s.toggleOption}
          onClick={() => onChange(o.value)}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

export { Combobox } from "./Combobox";
export type { Option } from "./Combobox";

/* ---------- skeleton ---------- */

export function Skeleton({ width = "100%", height = "1em" }: { width?: string; height?: string }) {
  return <span className={s.skeleton} style={{ display: "block", width, height }} aria-hidden />;
}


/**
 * Not enough evidence behind this number to lean on it.
 *
 * Said the same way everywhere. It used to be five separate implementations
 * that disagreed on size and spacing, so the same caveat looked like a
 * different caveat on every page.
 */
export function Thin({ title }: { title?: string }) {
  const why = title ?? "Not much playing time behind this, so the rate is weak evidence";
  return (
    // The title only ever reaches a hovering mouse. The visually hidden copy
    // reaches everyone else.
    <span className={s.thinTag} title={why}>
      thin<span className="sr-only">, {why}</span>
    </span>
  );
}

/** Class for a table row whose numbers rest on thin evidence. */
export const thinRow = s.thinRow;


/**
 * A short list of choices. Four of these were hand-rolled across the explorer
 * and the shouts panel, each styled from its own stylesheet.
 *
 * Deliberately a native select rather than a Combobox. Combobox exists because
 * a native select is hostile at forty options; at five it is the better control,
 * and forcing a search box onto "which of five models" is ceremony. The rule:
 * searchable Combobox when the list is long or unbounded, this when it is short
 * and fixed.
 */
export function Select<T extends string>({
  value,
  options,
  onChange,
  label,
}: {
  value: T;
  options: { value: T; label: string }[];
  onChange: (value: T) => void;
  label: string;
}) {
  return (
    <select
      className={s.select}
      value={value}
      aria-label={label}
      onChange={(e) => onChange(e.target.value as T)}
    >
      {options.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </select>
  );
}


/**
 * This number is a stand-in, not a record.
 *
 * Used where a player has never appeared in this division and is priced from
 * his club's rate in the one below. Deliberately worded and styled like Thin,
 * because both say the same thing to a reader: trust this less.
 */
export function Estimated({ title }: { title?: string }) {
  const why = title ?? "Estimated rather than measured";
  return (
    <span className={s.thinTag} title={why}>
      est<span className="sr-only">, {why}</span>
    </span>
  );
}
