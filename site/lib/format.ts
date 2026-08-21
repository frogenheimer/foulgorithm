/**
 * All number and date formatting lives here.
 *
 * A `toFixed` in a component is a bug: it is how two places end up disagreeing
 * about decimal places. See docs/ui-styleguide.md.
 */

export const pct = (p: number, dp = 1) => `${(p * 100).toFixed(dp)}%`;

export const odds = (o: number) => (Number.isFinite(o) ? o.toFixed(2) : "—");

export const fouls = (n: number) => n.toFixed(2);

export const count = (n: number) => n.toLocaleString("en-GB");

export const signed = (n: number, dp = 2) => `${n >= 0 ? "+" : ""}${n.toFixed(dp)}`;

export const signedPct = (n: number, dp = 1) => `${n >= 0 ? "+" : ""}${n.toFixed(dp)}%`;

export function kickoff(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString("en-GB", {
    weekday: "short",
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Europe/London",
  });
}

export function kickoffDay(iso: string): string {
  return new Date(iso).toLocaleDateString("en-GB", {
    weekday: "long",
    day: "numeric",
    month: "long",
    timeZone: "Europe/London",
  });
}

export function shortDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}
