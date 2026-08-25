"use client";

/**
 * One cup fixture card, client-side for one reason: the tap flip. Hover
 * turns the card to the house's starred picks on pointer devices; on touch
 * the first tap turns it, a tap on the turned card follows the link (its
 * back foot says so) and a tap anywhere else turns it back, exactly the
 * homepage cards' behaviour.
 */

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import ClubChip from "@/components/kit/ClubChip";
import s from "@/app/cup/cup.module.css";

export type CupStar = { player: string; outOf100: number; line: number; market: string };

export default function CupCard({
  label,
  href,
  competition,
  kickoffLine,
  expected,
  call,
  lineupConfirmed,
  stars,
}: {
  label: string;
  href: string;
  competition: string;
  kickoffLine: string;
  expected?: number;
  call?: { player: string; outOf100: number } | null;
  lineupConfirmed?: boolean;
  stars: CupStar[];
}) {
  const [home, away] = label.split(" v ");
  const [tapped, setTapped] = useState(false);
  const cardRef = useRef<HTMLAnchorElement>(null);
  useEffect(() => {
    if (!tapped) return;
    const off = (e: PointerEvent) => {
      if (cardRef.current && !cardRef.current.contains(e.target as Node)) setTapped(false);
    };
    document.addEventListener("pointerdown", off);
    return () => document.removeEventListener("pointerdown", off);
  }, [tapped]);
  const tapToFlip = (e: React.MouseEvent) => {
    if (!stars.length || tapped) return;
    if (window.matchMedia("(hover: none)").matches) {
      e.preventDefault();
      setTapped(true);
    }
  };

  return (
    <Link
      ref={cardRef}
      href={href}
      className={`${s.card} ${stars.length ? s.flippable : ""} ${tapped ? s.tapped : ""}`}
      onClick={tapToFlip}
    >
      <span className={s.front}>
        <span className={s.day}>
          {competition}
          {" · "}
          {kickoffLine}
        </span>
        <span className={s.clubs} aria-hidden>
          <ClubChip name={home} />
          <ClubChip name={away} />
        </span>
        <span className={s.title}>{label}</span>
        {expected != null && (
          <span className={s.fouls}>
            {Math.round(expected)}
            <em>expected fouls</em>
          </span>
        )}
        {call && (
          <span className={s.call}>
            {call.player} commits 1+ · {call.outOf100}/100
          </span>
        )}
        <span className={s.note}>
          {lineupConfirmed ? "XI confirmed" : "XI predicted from current squads"}
        </span>
      </span>
      {stars.length > 0 && (
        <span className={s.backFace} aria-hidden>
          <span className={s.backTitle}>The house</span>
          <span className={s.backLegs}>
            {stars.slice(0, 5).map((l) => (
              <span key={`${l.player}-${l.market}-${l.line}`} className={s.backLeg}>
                <span className={s.backPlayer}>{l.player}</span>
                <span className={s.backWhat}>
                  {l.line}+ {l.market === "drawn" ? "won" : "fouls"}
                </span>
                <span className={s.backProb}>{l.outOf100}</span>
              </span>
            ))}
          </span>
          <span className={s.backFoot}>open the game &rarr;</span>
        </span>
      )}
    </Link>
  );
}
