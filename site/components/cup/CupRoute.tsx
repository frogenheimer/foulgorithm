/**
 * One route per cup, covering both the index and every tie page.
 *
 * An optional catch-all rather than a separate `[slug]` folder, and for a
 * concrete reason: `output: export` refuses a dynamic route whose
 * generateStaticParams comes back empty, and the FA Cup has no qualifying ties
 * between May and January. A `[slug]` route would have failed the build for
 * eight months of the year. Here the index is itself a param, so the list is
 * never empty and no placeholder page has to be invented to keep the build up.
 */

import { notFound } from "next/navigation";
import CupPage from "@/components/cup/CupPage";
import TiePage, { tieSlugs } from "@/components/cup/TiePage";
import type { Competition } from "@/lib/cups";

/** The index (no segment), then one entry per tie. */
export function cupParams(competition: Competition) {
  return [
    { slug: [] as string[] },
    ...tieSlugs(competition).map((t) => ({ slug: [t.slug] })),
  ];
}

export default function CupRoute({
  competition,
  slug,
}: {
  competition: Competition;
  slug?: string[];
}) {
  if (!slug || slug.length === 0) return <CupPage competition={competition} />;
  if (slug.length > 1) notFound();
  return <TiePage competition={competition} slug={slug[0]} />;
}
