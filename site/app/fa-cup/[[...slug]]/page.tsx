import CupRoute, { cupParams } from "@/components/cup/CupRoute";

export const metadata = { title: "FA Cup · Foulgorithm" };

export function generateStaticParams() {
  return cupParams("FA Cup");
}

export default async function FaCup({
  params,
}: {
  params: Promise<{ slug?: string[] }>;
}) {
  const { slug } = await params;
  return <CupRoute competition="FA Cup" slug={slug} />;
}
