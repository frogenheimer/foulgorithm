/**
 * The competition switcher: Premier League or the cups, beta.
 *
 * Cup ties are exhibition: predicted by the same engine, shown on the same
 * fixture template, but recorded nowhere and scored in no league. They are
 * reachable only through this switcher, so the league pages stay the league.
 */

import Link from "next/link";
import s from "./switcher.module.css";

export default function CompetitionSwitcher({ active }: { active: "league" | "cup" }) {
  return (
    <nav className={s.row} aria-label="Competition">
      <Link href="/" className={active === "league" ? s.on : s.chip}>
        Premier League
      </Link>
      <Link href="/cup" className={active === "cup" ? s.on : s.chip}>
        Cups <span className={s.beta}>beta</span>
      </Link>
    </nav>
  );
}
