"use client";

/**
 * The match players table (docs/46): every player from both squads, one
 * table, every column sortable, real and expected per-90 side by side,
 * actuals as their own columns once played, the house's tier on the rows
 * its slips use, the eleven marked and the bench folded away once the
 * sheets are confirmed. On phones a column chooser replaces the sideways
 * scroll. Built on DataTable; nothing here is a second table.
 */

import { useEffect, useMemo, useState } from "react";
import type { Bet, Explorer, ExplorerRow, Formations } from "@/lib/data";
import type { Outcomes } from "@/lib/graded";
import { buildRows, compare, per90, type MatchRow, type SortKey } from "@/lib/matchplayers";
import { Column, DataTable, Thin, Toggle } from "@/components/kit";
import ClubChip from "@/components/kit/ClubChip";
import s from "./matchplayers.module.css";

type Metric = "fouls" | "fouled" | "involvements" | "mins";

const fmt = (v: number | null | undefined, places = 2) => (v == null ? "—" : v.toFixed(places));

export default function MatchPlayers({
  label,
  explorer,
  shapes,
  houseSlips,
  outcomes,
  played = false,
}: {
  label: string;
  explorer: Explorer;
  shapes?: Formations[string];
  houseSlips?: Record<string, Bet> | null;
  outcomes?: Outcomes;
  played?: boolean;
}) {
  const fixtureRows = useMemo(
    () => explorer.rows.filter((r) => r.fixture === label),
    [explorer.rows, label]
  );
  const { rows, confirmed } = useMemo(
    () => buildRows(fixtureRows, shapes, houseSlips, outcomes),
    [fixtureRows, shapes, houseSlips, outcomes]
  );

  const [sortKey, setSortKey] = useState<SortKey>("fouls");
  const [open, setOpen] = useState<string | null>(null);
  const [metric, setMetric] = useState<Metric>("fouls");
  const [narrow, setNarrow] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(max-width: 760px)");
    const sync = () => setNarrow(mq.matches);
    sync();
    mq.addEventListener("change", sync);
    return () => mq.removeEventListener("change", sync);
  }, []);

  const sorted = useMemo(() => [...rows].sort(compare(sortKey)), [rows, sortKey]);
  const eleven = confirmed ? sorted.filter((x) => x.xi) : sorted;
  const bench = confirmed ? sorted.filter((x) => !x.xi) : [];

  const houseIdx = explorer.models.indexOf(explorer.house);
  const lineIdx = (line: number) => explorer.lines.indexOf(line - 0.5);
  const price = (r: ExplorerRow, market: "committed" | "drawn", line: number) => {
    const li = lineIdx(line);
    const p = li >= 0 ? r[market]?.[li]?.[houseIdx] : undefined;
    return p == null ? "—" : `${Math.round(p * 100)}/100`;
  };

  const pair = (real: number | null, expected: number | null) => (
    <span className={s.pair}>
      <span className={s.real}>{fmt(real)}</span>
      <span className={s.sep} aria-hidden>
        ·
      </span>
      <span className={s.expected}>{fmt(expected)}</span>
    </span>
  );

  const playerCol: Column<MatchRow> = {
    key: "player",
    head: "Player",
    sort: compare("player"),
    cell: (x) => (
      <span className={s.player}>
        <ClubChip name={x.r.team} size="sm" />
        <span className={s.name}>
          {x.r.player}
          {x.r.thin && (
            <>
              {" "}
              <Thin />
            </>
          )}
        </span>
        <span className={s.meta}>
          {x.r.position}
          {narrow && x.tier ? ` · ${x.tier}` : ""}
        </span>
      </span>
    ),
  };
  const metricCols: Record<Metric, Column<MatchRow>> = {
    mins: { key: "mins", head: "Mins", numeric: true, sort: compare("mins"), cell: (x) => `${Math.round(x.r.minutes)}'` },
    fouls: {
      key: "fouls",
      head: <span title="real per 90 · expected this match">Fouls/90</span>,
      numeric: true,
      sort: compare("fouls"),
      cell: (x) => pair(per90(x.r, "committed"), (x.r.expected?.committed ?? null)),
    },
    fouled: {
      key: "fouled",
      head: <span title="real per 90 · expected this match">Fouled/90</span>,
      numeric: true,
      sort: compare("fouled"),
      cell: (x) => pair(per90(x.r, "drawn"), (x.r.expected?.drawn ?? null)),
    },
    involvements: {
      key: "involvements",
      head: <span title="real per 90 · expected this match">Inv/90</span>,
      numeric: true,
      sort: compare("involvements"),
      cell: (x) => pair(per90(x.r, "involvements"), (x.r.expected?.involvements ?? null)),
    },
  };
  const xiCol: Column<MatchRow> = {
    key: "xi",
    head: "XI",
    sort: compare("xi"),
    cell: (x) => (x.xi ? <span className={s.xi} title={confirmed ? "confirmed eleven" : "predicted eleven"}>{confirmed ? "✓" : "○"}</span> : ""),
  };
  const houseCol: Column<MatchRow> = {
    key: "house",
    head: "House",
    sort: compare("house"),
    cell: (x) => (x.tier ? <span className={`${s.tier} ${s[x.tier]}`}>{x.tier}</span> : ""),
  };
  const actualCols: Column<MatchRow>[] = played
    ? [
        { key: "actualFouls", head: "Fouls", numeric: true, sort: compare("actualFouls"), cell: (x) => fmt(x.actualFouls, 0) },
        { key: "actualFouled", head: "Fouled", numeric: true, sort: compare("actualFouled"), cell: (x) => fmt(x.actualFouled, 0) },
      ]
    : [];

  const columns: Column<MatchRow>[] = narrow
    ? [playerCol, metricCols[metric]]
    : [playerCol, xiCol, metricCols.mins, metricCols.fouls, metricCols.fouled, metricCols.involvements, ...actualCols, houseCol];

  const expanded = (x: MatchRow) => (
    <div className={s.expanded}>
      <div className={s.prices}>
        <span className={s.pricesHead}>Fouls</span>
        {[1, 2, 3].map((n) => (
          <span key={`c${n}`}>
            {n}+ <strong>{price(x.r, "committed", n)}</strong>
          </span>
        ))}
        <span className={s.pricesHead}>Fouled</span>
        {[1, 2, 3].map((n) => (
          <span key={`d${n}`}>
            {n}+ <strong>{price(x.r, "drawn", n)}</strong>
          </span>
        ))}
      </div>
      <p className={s.note}>
        {x.r.career
          ? `${x.r.career.nineties.toFixed(0)} full matches on record. Real figures are his per 90 across everything we hold; expected figures are this match, allowing for minutes and opponent.`
          : "No matches on record: every figure here is an estimate from position and club."}
        {x.r.priorFrom && x.r.priorFrom !== "own-record" ? ` Prior: ${x.r.priorFrom}.` : ""}
      </p>
    </div>
  );

  const table = (list: MatchRow[]) => (
    <DataTable
      rows={list}
      rowKey={(x) => x.r.fullName + x.r.team}
      columns={columns}
      sortKey={sortKey}
      onSort={(k) => setSortKey(k as SortKey)}
      expanded={open}
      renderExpanded={expanded}
      onRowClick={(x) => setOpen(open === x.r.fullName + x.r.team ? null : x.r.fullName + x.r.team)}
    />
  );

  return (
    <div className={s.wrap}>
      {narrow && (
        <Toggle
          value={metric}
          onChange={setMetric}
          label="Which figure to show"
          options={[
            { value: "fouls", label: "Fouls" },
            { value: "fouled", label: "Fouled" },
            { value: "involvements", label: "Inv" },
            { value: "mins", label: "Mins" },
          ]}
        />
      )}
      <p className={s.legend}>
        Each figure is <span className={s.real}>real</span> per 90 then <span className={s.expected}>expected</span> this match.{" "}
        {confirmed ? "Confirmed elevens; the bench is below." : "Elevens predicted until the sheets land, marked ○."} Click a row for the prices.
      </p>
      {table(eleven)}
      {bench.length > 0 && (
        <details className={s.bench}>
          <summary className={s.benchHead}>Show bench ({bench.length})</summary>
          {table(bench)}
        </details>
      )}
    </div>
  );
}
