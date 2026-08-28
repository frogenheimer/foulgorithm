/**
 * The clock. GitHub's schedule trigger ran this repo's jobs about two hours
 * late and, on 28 August 2026, not at all. Its dispatch API is immediate. So
 * the jobs stay on GitHub Actions (free on a public repo) and the CLOCK moves
 * here: every 30 minutes, read the season's fixture list from the repo, and
 * dispatch whichever workflow is due.
 *
 * Due means:
 *   lineups    a kickoff sits 60 to 130 minutes ahead (the watcher then waits
 *              until T-65 and polls). Dispatched at most once per window.
 *   settle     a matchday's last kickoff was 4h00 to 4h30 ago.
 *   reschedule Tuesday, 04:00 to 04:30 UTC.
 *
 * Nothing here can cost money: the Free plan has no payment method and stops
 * rather than bills, and 48 runs a day is 0.05% of its allowance.
 */

export interface Env {
  REPO: string;
  SEASON_URL: string;
  GITHUB_TOKEN: string;
}

type Fixture = { home: string; away: string; kickoff: string };

const MIN = 60_000;

export function due(fixtures: Fixture[], now: Date): { lineups: boolean; settle: boolean; reschedule: boolean } {
  const t = now.getTime();
  const kickoffs = fixtures.map((f) => new Date(f.kickoff).getTime()).filter((k) => !Number.isNaN(k));

  const lineups = kickoffs.some((k) => k - t > 60 * MIN && k - t <= 130 * MIN);

  const lastPerDay = new Map<string, number>();
  for (const k of kickoffs) {
    const day = new Date(k).toISOString().slice(0, 10);
    lastPerDay.set(day, Math.max(lastPerDay.get(day) ?? 0, k));
  }
  const settle = [...lastPerDay.values()].some((k) => t - k > 240 * MIN && t - k <= 270 * MIN);

  const reschedule = now.getUTCDay() === 2 && now.getUTCHours() === 4 && now.getUTCMinutes() < 30;

  return { lineups, settle, reschedule };
}

async function dispatch(env: Env, workflow: string, inputs: Record<string, unknown> = {}): Promise<string> {
  const res = await fetch(`https://api.github.com/repos/${env.REPO}/actions/workflows/${workflow}/dispatches`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${env.GITHUB_TOKEN}`,
      Accept: "application/vnd.github+json",
      "User-Agent": "foulgorithm-clock",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ ref: "main", inputs }),
  });
  return `${workflow}: ${res.status}`;
}

export default {
  async scheduled(_event: ScheduledEvent, env: Env, ctx: ExecutionContext): Promise<void> {
    const now = new Date();
    const res = await fetch(env.SEASON_URL, { headers: { "User-Agent": "foulgorithm-clock" } });
    if (!res.ok) {
      console.log(`season.json unavailable: ${res.status}`);
      return;
    }
    const season = (await res.json()) as { fixtures?: Fixture[] };
    const what = due(season.fixtures ?? [], now);
    const jobs: Promise<string>[] = [];
    if (what.lineups) jobs.push(dispatch(env, "lineups.yml", { force: false }));
    if (what.settle) jobs.push(dispatch(env, "settle.yml"));
    if (what.reschedule) jobs.push(dispatch(env, "reschedule.yml"));
    if (jobs.length === 0) {
      console.log(`${now.toISOString()} nothing due`);
      return;
    }
    ctx.waitUntil(Promise.all(jobs).then((lines) => console.log(lines.join(" | "))));
  },
};
