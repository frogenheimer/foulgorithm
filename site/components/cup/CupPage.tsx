/**
 * Both cup index pages, which differ only in which file they read.
 *
 * Written once because they are the same page. The competition switcher, the
 * header and the exhibition warning are identical; the FA Cup and the League
 * Cup are two routes so that a pairing meeting in both gets two pages, not
 * because the pages themselves want to be different.
 */

import CompetitionSwitcher from "@/components/home/CompetitionSwitcher";
import CupBoard from "@/components/cup/CupBoard";
import { PageHeader } from "@/components/kit";
import { getCupData } from "@/lib/data";
import { cupFile } from "@/lib/cups";
import type { Competition } from "@/lib/cups";

export default function CupPage({ competition }: { competition: Competition }) {
  const data = getCupData(cupFile(competition));
  const ties = data?.ties ?? [];
  const full = ties.filter((t) => t.kind === "full").length;

  return (
    <div className="stack">
      <CompetitionSwitcher active={competition} />
      <PageHeader
        kicker="Exhibition · beta"
        title={`The ${competition}`}
        lede={
          <>
            Every tie where we hold match history for both clubs, which means
            Premier League and Championship sides. Each page is the two clubs&rsquo;
            raw record, measured the same way from the same source, plus one
            expected total.{" "}
            {full > 0 && (
              <>
                {full === ties.length ? "Every tie here is" : `${full} of these are`}{" "}
                between top-flight clubs and carries the full model as well.{" "}
              </>
            )}
            Exhibition only: nothing here is recorded, graded or scored in the
            league table.
          </>
        }
      />
      <CupBoard ties={ties} />
    </div>
  );
}
