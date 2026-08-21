/**
 * Layout primitives.
 *
 * Nothing here knows what a foul is. If a component needs domain knowledge it
 * belongs in a page or a chart, not in ui/. See docs/ui-styleguide.md.
 */

import type { ReactNode } from "react";
import styles from "./ui.module.css";

export function Card({
  children,
  title,
  subtitle,
  padded = true,
}: {
  children: ReactNode;
  title?: string;
  subtitle?: string;
  padded?: boolean;
}) {
  return (
    <section className={padded ? styles.card : styles.cardFlush}>
      {title && (
        <header className={styles.cardHead}>
          <h3 className={styles.cardTitle}>{title}</h3>
          {subtitle && <p className={styles.cardSub}>{subtitle}</p>}
        </header>
      )}
      {children}
    </section>
  );
}

export function SectionHead({
  title,
  children,
  id,
}: {
  title: string;
  children?: ReactNode;
  id?: string;
}) {
  return (
    <header className={styles.sectionHead} id={id}>
      <h2 className={styles.sectionTitle}>{title}</h2>
      {children && <p className={styles.sectionBody}>{children}</p>}
    </header>
  );
}

export function StatTile({
  label,
  value,
  note,
  tone = "neutral",
}: {
  label: string;
  value: string;
  note?: ReactNode;
  tone?: "neutral" | "series1" | "series2";
}) {
  return (
    <div className={styles.tile}>
      <div className={styles.tileLabel}>{label}</div>
      <div className={`${styles.tileValue} ${styles[tone]}`}>{value}</div>
      {note && <div className={styles.tileNote}>{note}</div>}
    </div>
  );
}

export function TileGrid({ children }: { children: ReactNode }) {
  return <div className={styles.tileGrid}>{children}</div>;
}

export function Badge({
  children,
  tone = "neutral",
  title,
}: {
  children: ReactNode;
  tone?: "neutral" | "warn";
  title?: string;
}) {
  return (
    <span className={`${styles.badge} ${tone === "warn" ? styles.badgeWarn : ""}`} title={title}>
      {children}
    </span>
  );
}

export function Note({ children }: { children: ReactNode }) {
  return <p className={styles.note}>{children}</p>;
}

export function Callout({ children }: { children: ReactNode }) {
  return <aside className={styles.callout}>{children}</aside>;
}
