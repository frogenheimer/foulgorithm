"use client";

/**
 * The structured game sheet (docs/39): two tiers under the pitch.
 *
 * Tier one is the clubs face to face, every metric we hold as a mirrored
 * bar pair in kit colours with league ranks on the ends. Tier two is the
 * players who will actually be on it: the likely eleven first, re-tied to
 * the confirmed eleven when the sheets land, the rest in a drawer. All
 * three foul columns show at once; the one toggle is Expected (our model,
 * for this match) against Actual (their history, checkable against a
 * scoreboard), and the copy says which is which because an estimate must
 * never sit beside a measurement looking identical.
 */

import { useState } from "react";
import type { ExplorerRow, MatchdayFixture } from "@/lib/data";
import { clubIdentity } from "@/lib/clubs";
import { mirrorShares, xiSplit } from "@/lib/gamesheet";
import { DataTable } from "@/components/kit";
import ClubChip from "@/components/kit/ClubChip";
import s from "./gamesheet.module.css";

const METRIC_ORDER = [
  "foulsFor", "foulsAgainst", "cardsFor", "cardsAgainst",
  "shotsFor", "shotsAgainst", "cornersFor", "cornersAgainst",
];

export default function GameSheet({
  fixture,
  rows,
}: {
  fixture: MatchdayFixture;
  rows: ExplorerRow[];
}) {
  const [mode, setMode] = useState<"expected" | "actual">("expected");
  const home = fixture.home;
  const away = fixture.away;
  const homeSheet = fixture.teams[home];
  const awaySheet = fixture.teams[away];
  const ref = fixture.referee;
  const { eleven, drawer } = xiSplit(rows);

  const value = (r: ExplorerRow, market: "committed" | "drawn" | "involvements") => {
    if (mode === "expected") return r.expected[market].toFixed(2);
    const held = r.career?.[market];
    return held == null ? "—" : held.toFixed(2);
  };

  const columns = [
    {
      key: "player",
      head: "Player",
      cell: (r: ExplorerRow) => (
        <span className={s.playerCell}>
          <ClubChip name={r.team} size="sm" />
          {r.player}
          {!r.confirmed && r.startProbability != null && r.startProbability < 0.6 && (
            <span className={s.doubt}>doubt</span>
          )}
        </span>
      ),
    },
    { key: "mins", head: "Mins", numeric: true, cell: (r: ExplorerRow) => `${Math.round(r.minutes)}'` },
    { key: "committed", head: "Fouls", numeric: true, cell: (r: ExplorerRow) => value(r, "committed") },
    { key: "drawn", head: "Won", numeric: true, cell: (r: ExplorerRow) => value(r, "drawn") },
    { key: "involvements", head: "Both", numeric: true, cell: (r: ExplorerRow) => value(r, "involvements") },
  ];

  return (
    <div className={s.sheet}>
      {ref && ref.name && (
        <p className={s.refStrip}>
          Referee {ref.name}
          {ref.matches > 0 &&
            ` · ${ref.foulsPerMatch} fouls · ${ref.yellowsPerMatch} cards · ${ref.matches} matches`}
          {ref.foulsVsLeague != null &&
            ` · ${ref.foulsVsLeague >= 0 ? "+" : ""}${ref.foulsVsLeague}% vs league`}
          {ref.foulsBooked != null && ` · books ${ref.foulsBooked}% of fouls`}
        </p>
      )}

      {homeSheet && awaySheet && (
        <div className={s.mirror}>
          {METRIC_ORDER.map((key) => {
            const h = homeSheet.averages[key];
            const a = awaySheet.averages[key];
            if (!h || !a || (h.value == null && a.value == null)) return null;
            const [left, right] = mirrorShares(h.value, a.value);
            return (
              <div key={key} className={s.metricRow}>
                <span className={s.val}>
                  {h.value ?? "—"}
                  {h.rank != null && <span className={s.rank}>{h.rank}/{h.rankOf}</span>}
                </span>
                <span className={s.bars} aria-hidden>
                  <span className={s.trackLeft}>
                    <span
                      className={s.barLeft}
                      style={{ width: `${left}%`, background: clubIdentity(home).primary }}
                    />
                  </span>
                  <span className={s.metricLabel}>{h.label}</span>
                  <span className={s.trackRight}>
                    <span
                      className={s.barRight}
                      style={{ width: `${right}%`, background: clubIdentity(away).primary }}
                    />
                  </span>
                </span>
                <span className={`${s.val} ${s.right}`}>
                  {a.rank != null && <span className={s.rank}>{a.rank}/{a.rankOf}</span>}
                  {a.value ?? "—"}
                </span>
              </div>
            );
          })}
        </div>
      )}

      <div className={s.playerTier}>
        <div className={s.toggleRow}>
          <span className={s.tierTitle}>The players</span>
          <span className={s.toggle} role="group" aria-label="Numbers shown">
            <button
              type="button"
              className={mode === "expected" ? s.toggleOn : s.toggleOff}
              onClick={() => setMode("expected")}
            >
              Expected
            </button>
            <button
              type="button"
              className={mode === "actual" ? s.toggleOn : s.toggleOff}
              onClick={() => setMode("actual")}
            >
              Actual
            </button>
          </span>
        </div>
        <p className={s.modeNote}>
          {mode === "expected"
            ? "Our model's numbers for THIS match: fouls, fouls won, and both together."
            : "Their history, per 90 minutes, checkable against a scoreboard. No model in these numbers."}
        </p>
        <DataTable rows={eleven} rowKey={(r) => r.fullName + r.team} columns={columns} />
        {drawer.length > 0 && (
          <details className={s.drawer}>
            <summary className={s.drawerHead}>
              Bench and the rest ({drawer.length})
            </summary>
            <DataTable rows={drawer} rowKey={(r) => r.fullName + r.team} columns={columns} />
          </details>
        )}
      </div>
    </div>
  );
}
