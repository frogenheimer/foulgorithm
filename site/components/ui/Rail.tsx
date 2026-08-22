import Link from "next/link";
import ThemeToggle from "./ThemeToggle";
import type { ReactNode } from "react";
import s from "./rail.module.css";

/** Safer-gambling links live in ONE place. See docs/13-legal-and-ethics.md */
export const SUPPORT = {
  helpline: "0808 8020 133",
  helplineName: "National Gambling Helpline",
  gamcare: "https://www.gamcare.org.uk",
  gamstop: "https://www.gamstop.co.uk",
};

/**
 * A narrow icon rail rather than a top nav.
 *
 * Frees the full width for content, which matters when the content is tables,
 * and it scales as sections are added. The top nav already overflowed once on a
 * narrow screen with only four links.
 *
 * Icons are inline SVG rather than a font or a library: four shapes do not
 * justify a dependency, and these inherit currentColor so theming is free.
 */

const NAV = [
  { href: "/", label: "This round", icon: Grid },
  { href: "/players", label: "Players", icon: Grid },
  { href: "/characters", label: "The five", icon: Users },
  { href: "/record", label: "Track record", icon: Chart },
  { href: "/history", label: "History", icon: Chart },
  { href: "/methodology", label: "Methodology", icon: Book },
];

export function Rail({ children }: { children: ReactNode }) {
  return (
    <div className={s.shell}>
      <nav className={s.rail} aria-label="Primary">
        <Link href="/" className={s.mark} aria-label="Foulgorithm home">
          <span className={s.markGlyph}>F</span>
        </Link>
        <ul className={s.items}>
          {NAV.map(({ href, label, icon: Icon }) => (
            <li key={href}>
              <Link href={href} className={s.item}>
                <Icon />
                <span className={s.tip}>{label}</span>
                <span className={s.srOnly}>{label}</span>
              </Link>
            </li>
          ))}
        </ul>
        <ThemeToggle />
      </nav>

      <div className={s.main}>
        <div className={s.content}>{children}</div>
        <footer className={s.footer}>
          <p>
            Statistical estimates for research. <strong>Not betting advice.</strong> No outcome is
            guaranteed and past performance does not predict future results.
          </p>
          <p>
            18+. Support: {SUPPORT.helplineName} on {SUPPORT.helpline},{" "}
            <a href={SUPPORT.gamcare}>GamCare</a>, or self-exclude via{" "}
            <a href={SUPPORT.gamstop}>GamStop</a>.
          </p>
        </footer>
      </div>
    </div>
  );
}

function Grid() {
  return (
    <svg viewBox="0 0 20 20" width="19" height="19" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">
      <rect x="2.5" y="2.5" width="6" height="6" rx="1.5" />
      <rect x="11.5" y="2.5" width="6" height="6" rx="1.5" />
      <rect x="2.5" y="11.5" width="6" height="6" rx="1.5" />
      <rect x="11.5" y="11.5" width="6" height="6" rx="1.5" />
    </svg>
  );
}
function Users() {
  return (
    <svg viewBox="0 0 20 20" width="19" height="19" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">
      <circle cx="7.5" cy="6.5" r="3" />
      <path d="M2 16.5c0-3 2.5-5 5.5-5s5.5 2 5.5 5" />
      <path d="M13.5 4.2a3 3 0 0 1 0 4.6M15 11.8c2 .6 3.4 2.4 3.4 4.7" />
    </svg>
  );
}
function Chart() {
  return (
    <svg viewBox="0 0 20 20" width="19" height="19" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">
      <path d="M3 16.5V9M8 16.5V4M13 16.5v-5M18 16.5V7" strokeLinecap="round" />
    </svg>
  );
}
function Book() {
  return (
    <svg viewBox="0 0 20 20" width="19" height="19" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">
      <path d="M3.5 4.5h5a2.5 2.5 0 0 1 2.5 2.5v9a2 2 0 0 0-2-2h-5.5z" />
      <path d="M16.5 4.5h-5A2.5 2.5 0 0 0 9 7v9a2 2 0 0 1 2-2h5.5z" />
    </svg>
  );
}
