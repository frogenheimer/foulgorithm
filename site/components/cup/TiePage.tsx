/**
 * One cup tie's page.
 *
 * Both cups share this, and so do both kinds of tie. A Premier League tie adds
 * the house sheet above the record; every other tie simply does not have one,
 * and the page says which it is rather than leaving a reader to notice the
 * absence.
 */

import { notFound } from "next/navigation";
import Link from "next/link";
import HouseSheet from "@/components/fixture/HouseSheet";
import TieStats from "@/components/cup/TieStats";
import { Note, PageHeader } from "@/components/kit";
import { getCupData } from "@/lib/data";
import { cupFile, cupPath, showsHouseSheet } from "@/lib/cups";
import type { Competition } from "@/lib/cups";

export function tieFor(competition: Competition, slug: string) {
  const data = getCupData(cupFile(competition));
  return data?.ties.find((t) => t.slug === slug) ?? null;
}

export function tieSlugs(competition: Competition) {
  const data = getCupData(cupFile(competition));
  return (data?.ties ?? []).map((t) => ({ slug: t.slug }));
}

export default function TiePage({
  competition,
  slug,
}: {
  competition: Competition;
  slug: string;
}) {
  const tie = tieFor(competition, slug);
  if (!tie) notFound();

  const kickoff = new Date(tie.kickoff).toLocaleString("en-GB", {
    weekday: "long",
    day: "numeric",
    month: "long",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Europe/London",
  });

  return (
    <div className="stack">
      <Link href={cupPath(competition)}>&larr; {competition}</Link>

      <PageHeader
        kicker={`${competition}${tie.round ? ` · ${tie.round}` : ""} · ${kickoff}`}
        title={`${tie.home} v ${tie.away}`}
        lede={
          tie.kind === "full" ? (
            <>
              Both clubs are top-flight, so this tie carries the full model as
              well as the record. Exhibition: nothing here is graded or scored.
            </>
          ) : (
            <>
              Raw record and one expected total. No player picks, because no
              player-level foul data exists for the Championship at any price
              and a pick built without it would be a positional average wearing
              a probability. Exhibition: nothing here is graded or scored.
            </>
          )
        }
      />

      {showsHouseSheet(tie) && <HouseSheet sheet={tie.houseSheet as never} />}

      <TieStats tie={tie} />

      <Note>
        Team rates come from football-data.co.uk for both divisions, so each
        side is measured the same way by the same source. Nothing on this page
        is recorded, graded or carried into the track record.
      </Note>
    </div>
  );
}
