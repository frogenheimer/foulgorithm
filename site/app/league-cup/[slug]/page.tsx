import TiePage, { tieSlugs } from "@/components/cup/TiePage";

export const metadata = { title: "League Cup tie · Foulgorithm" };

export function generateStaticParams() {
  return tieSlugs("League Cup");
}

export default async function LeagueCupTie({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  return <TiePage competition="League Cup" slug={slug} />;
}
