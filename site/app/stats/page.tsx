import Sheet from "@/components/matchday/Sheet";
import { getMatchday } from "@/lib/data";
import s from "../round.module.css";

export const metadata = { title: "Stats sheet · Foulgorithm" };

export default function Stats() {
  const d = getMatchday();

  return (
    <div className="stack">
      <section className={s.intro}>
        <h1 className={s.h1}>The stats sheet</h1>
        <p className={s.lede}>
          What actually happened, both clubs side by side. No model, no
          suggestions, no prices. Every number here can be checked against a
          scoreboard, which is the whole point of the page.
        </p>
      </section>

      <Sheet data={d} />

      <section className={s.footNote}>
        <p>
          Averages are per match across {d.seasons.join(" and ")}. The dots show whether
          the line landed in each of the last {d.window} matches, most recent on the
          left. Hollow means it did not; a dashed outline means that match has not been
          played yet.
        </p>
        <p>
          Lines are set at the middle of each club&apos;s own record rather than at a
          bookmaker&apos;s number, so the dots split roughly evenly and actually tell you
          something. A line nothing ever clears would just draw five identical dots.
        </p>
        <p>
          <strong>Want a view instead of the facts?</strong> The players page has the
          model&apos;s probabilities and the five competing versions of them.
        </p>
      </section>
    </div>
  );
}
