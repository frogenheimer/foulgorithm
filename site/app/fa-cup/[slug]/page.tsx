import TiePage, { tieSlugs } from "@/components/cup/TiePage";

export const metadata = { title: "FA Cup tie · Foulgorithm" };

export function generateStaticParams() {
  return tieSlugs("FA Cup");
}

export default async function FaCupTie({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  return <TiePage competition="FA Cup" slug={slug} />;
}
