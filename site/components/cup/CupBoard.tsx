/**
 * One cup's slate: a card per tie, linking to its own page.
 *
 * The cards no longer flip to a set of picks. Most ties cannot have picks at
 * all now that the Championship is in, and a card that turns for two ties out
 * of ten reads as a bug rather than a feature. The front carries what every
 * tie has: who, when, and each side's fouls per match against its own
 * division.
 */

import Link from "next/link";
import ClubChip from "@/components/kit/ClubChip";
import { Callout } from "@/components/kit";
import { cupHref, sideNote, totalHeadline } from "@/lib/cups";
import type { CupTie } from "@/lib/cups";
import s from "./cup.module.css";

export default function CupBoard({ ties }: { ties: CupTie[] }) {
  if (!ties.length) {
    return (
      <Callout>
        <strong>No ties on the slate.</strong> This page fills itself in when
        the draw sends two clubs we hold match history for against each other,
        which means Premier League and Championship sides.
      </Callout>
    );
  }

  return (
    <div className={s.grid}>
      {ties.map((tie) => (
        <TieCard key={tie.slug} tie={tie} />
      ))}
    </div>
  );
}

function TieCard({ tie }: { tie: CupTie }) {
  const kickoff = new Date(tie.kickoff).toLocaleString("en-GB", {
    weekday: "short",
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Europe/London",
  });
  const headline = totalHeadline(tie);

  return (
    <Link href={cupHref(tie)} className={s.card}>
      <span className={s.day}>
        {tie.round ? `${tie.round} · ` : ""}
        {kickoff}
      </span>

      <span className={s.clubs} aria-hidden>
        <ClubChip name={tie.home} />
        <ClubChip name={tie.away} />
      </span>
      <span className={s.title}>
        {tie.home} v {tie.away}
      </span>

      <span className={s.sides}>
        <Side name={tie.home} tie={tie} which="home" />
        <Side name={tie.away} tie={tie} which="away" />
      </span>

      {headline && <span className={s.note}>{headline}</span>}

      <span className={s.foot}>
        {tie.kind === "full" ? "Full model" : "Match total and record only"}
      </span>
    </Link>
  );
}

/** Fouls per match, with the division the number belongs to. */
function Side({ name, tie, which }: { name: string; tie: CupTie; which: "home" | "away" }) {
  const fouls = tie.compare[0]?.rows[0];
  const value = fouls ? fouls[which] : null;
  const rank = fouls ? fouls[which === "home" ? "homeRank" : "awayRank"] : null;

  return (
    <span className={s.side}>
      <span className={s.sideName}>{name}</span>
      <span className={s.sideValue}>{value ?? "no data"}</span>
      <span className={s.sideNote}>{rank ?? sideNote(tie.record[which])}</span>
    </span>
  );
}
