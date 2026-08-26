import CupRoute, { cupParams } from "@/components/cup/CupRoute";

export const metadata = { title: "League Cup · Foulgorithm" };

export function generateStaticParams() {
  return cupParams("League Cup");
}

export default async function LeagueCup({
  params,
}: {
  params: Promise<{ slug?: string[] }>;
}) {
  const { slug } = await params;
  return <CupRoute competition="League Cup" slug={slug} />;
}
