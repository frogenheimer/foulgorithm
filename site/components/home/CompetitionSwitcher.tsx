/**
 * The competition switcher: the league, then the two domestic cups.
 *
 * Both cups get their own chip because both get their own page. They shared
 * one until now, which meant the same two clubs meeting in each landed on a
 * single URL and the second tie quietly overwrote the first.
 *
 * Cup ties are exhibition: nothing in them is recorded, graded or scored, and
 * they are reachable only through here, so the league pages stay the league.
 */

import Link from "next/link";
import { COMPETITIONS, cupPath } from "@/lib/cups";
import type { Competition } from "@/lib/cups";
import s from "./switcher.module.css";

export default function CompetitionSwitcher({
  active,
}: {
  active: "league" | Competition;
}) {
  return (
    <nav className={s.row} aria-label="Competition">
      <Link href="/" className={active === "league" ? s.on : s.chip}>
        Premier League
      </Link>
      {COMPETITIONS.map((competition) => (
        <Link
          key={competition}
          href={cupPath(competition)}
          className={active === competition ? s.on : s.chip}
        >
          {competition} <span className={s.beta}>beta</span>
        </Link>
      ))}
    </nav>
  );
}
