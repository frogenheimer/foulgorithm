import { redirect } from "next/navigation";
import { getCupData } from "@/lib/data";

/**
 * The old single cup page. Both cups have their own route now, because the
 * same two clubs can meet in each and this URL put them on one page.
 *
 * Kept as a redirect rather than deleted: anything already linking here should
 * land somewhere sensible. Whichever cup has a tie on the slate wins, and the
 * League Cup is the default when both are quiet.
 */
export default function Cup() {
  const league = getCupData("league-cup.json");
  const fa = getCupData("fa-cup.json");
  redirect(league?.ties?.length || !fa?.ties?.length ? "/league-cup" : "/fa-cup");
}
