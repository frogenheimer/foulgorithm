import { getTeams } from "@/lib/data";
import { TeamsTable } from "./Table";

export const metadata = { title: "Teams · Foulgorithm" };

export default function Teams() {
  return <TeamsTable data={getTeams()} />;
}
