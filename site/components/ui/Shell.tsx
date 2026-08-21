import Link from "next/link";
import type { ReactNode } from "react";
import styles from "./shell.module.css";

/** Safer-gambling links live in ONE place, because the charity landscape is
 *  shifting and a dead link should be a one-line fix. See docs/13-legal-and-ethics.md */
export const SUPPORT = {
  helpline: "0808 8020 133",
  helplineName: "National Gambling Helpline",
  gamcare: "https://www.gamcare.org.uk",
  gamstop: "https://www.gamstop.co.uk",
};

const NAV = [
  { href: "/", label: "This round" },
  { href: "/characters", label: "The five" },
  { href: "/history", label: "History" },
  { href: "/methodology", label: "Methodology" },
];

export function Shell({ children }: { children: ReactNode }) {
  return (
    <>
      <header className={styles.masthead}>
        <div className={styles.mastheadInner} style={{ maxWidth: 1100, margin: "0 auto" }}>
          <Link href="/" className={styles.brand}>
            Foulgorithm
            <span className={styles.pill}>Pre-alpha</span>
          </Link>
          <nav className={styles.nav} aria-label="Primary">
            {NAV.map((item) => (
              <Link key={item.href} href={item.href} className={styles.navLink}>
                {item.label}
              </Link>
            ))}
          </nav>
        </div>
      </header>

      <main className="wrap">{children}</main>

      <footer className={styles.footer}>
        <div className="wrap">
          <p>
            Statistical estimates for research and entertainment. <strong>Not betting advice.</strong>{" "}
            No outcome is guaranteed and past performance does not predict future results.
          </p>
          <p>
            18+. Support: {SUPPORT.helplineName} on {SUPPORT.helpline},{" "}
            <a href={SUPPORT.gamcare} className={styles.footerLink}>
              GamCare
            </a>
            , or self-exclude via{" "}
            <a href={SUPPORT.gamstop} className={styles.footerLink}>
              GamStop
            </a>
            .
          </p>
        </div>
      </footer>
    </>
  );
}
