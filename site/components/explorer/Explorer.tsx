"use client";

/**
 * The filterable view of every prediction.
 *
 * This is the one place on the site that ships JavaScript. Everything else is a
 * server component rendering static HTML, and that stays deliberate. Filtering a
 * few hundred rows on every keystroke is the case where a round trip is worse
 * than the bundle.
 *
 * The three markets are one table, not three pages. A player who concedes two
 * and wins two was in four incidents, and "who is involved in the most fouls"
 * cannot be answered by reading two tables side by side.
 */

import { Fragment, useMemo, useState } from "react";
import type { Explorer as Data, ExplorerRow } from "@/lib/data";
import { DataTable } from "@/components/kit";
import Bars from "./Bars";
import Shape from "./Shape";
import { MARKET_LABEL } from "@/lib/markets";
import s from "./explorer.module.css";

type Market = "committed" | "drawn" | "involvements";
type Sort = "prob" | "expected" | "minutes" | "name";


const MARKET_HINT: Record<Market, string> = {
  committed: "Fouls he gives away",
  drawn: "Fouls he draws out of opponents",
  involvements: "Both together, how often he is in the middle of one",
};

const MARKET_NOUN: Record<Market, string> = {
  committed: "fouls",
  drawn: "fouls won",
  involvements: "involvements",
};

const POSITIONS = ["GK", "DF", "MF", "FW"];

export default function Explorer({ data }: { data: Data }) {
  const [market, setMarket] = useState<Market>("committed");
  const [line, setLine] = useState(0);
  const [model, setModel] = useState(data.house);
  const [fixture, setFixture] = useState("");
  const [position, setPosition] = useState("");
  const [query, setQuery] = useState("");
  const [hideThin, setHideThin] = useState(false);
  const [sort, setSort] = useState<Sort>("prob");
  const [simple, setSimple] = useState(true);
  const [open, setOpen] = useState<string | null>(null);

  const modelIndex = Math.max(0, data.models.indexOf(simple ? data.house : model));
  const fixtures = useMemo(
    () => Array.from(new Set(data.rows.map((r) => r.fixture))).sort(),
    [data.rows]
  );

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    const out = data.rows.filter((r) => {
      if (fixture && r.fixture !== fixture) return false;
      if (position && !r.position.startsWith(position)) return false;
      if (hideThin && r.thin) return false;
      if (q && !r.fullName.toLowerCase().includes(q) && !r.team.toLowerCase().includes(q))
        return false;
      return true;
    });
    const p = (r: ExplorerRow) => r[market][line][modelIndex];
    const by: Record<Sort, (a: ExplorerRow, b: ExplorerRow) => number> = {
      prob: (a, b) => p(b) - p(a),
      expected: (a, b) => b.expected[market] - a.expected[market],
      minutes: (a, b) => b.minutes - a.minutes,
      name: (a, b) => a.fullName.localeCompare(b.fullName),
    };
    return [...out].sort(by[sort]);
  }, [data.rows, market, line, modelIndex, fixture, position, query, hideThin, sort]);

  const lineLabel = `${data.lines[line] + 0.5}+`;

  return (
    <div className={s.wrap}>
      <div className={s.tabs} role="tablist" aria-label="Market">
        {(Object.keys(MARKET_LABEL) as Market[]).map((m) => (
          <button
            key={m}
            role="tab"
            type="button"
            aria-selected={market === m}
            className={market === m ? s.tabOn : s.tab}
            onClick={() => setMarket(m)}
          >
            <span className={s.tabLabel}>{MARKET_LABEL[m]}</span>
            <span className={s.tabHint}>{MARKET_HINT[m]}</span>
          </button>
        ))}
      </div>

      <div className={s.controls}>
        <label className={s.field}>
          <span className={s.fieldLabel}>Search</span>
          <input
            className={s.input}
            type="search"
            value={query}
            placeholder="Player or club"
            onChange={(e) => setQuery(e.target.value)}
          />
        </label>

        <label className={s.field}>
          <span className={s.fieldLabel}>Game</span>
          <select className={s.select} value={fixture} onChange={(e) => setFixture(e.target.value)}>
            <option value="">Every game</option>
            {fixtures.map((f) => (
              <option key={f} value={f}>
                {f}
              </option>
            ))}
          </select>
        </label>

        <label className={s.field}>
          <span className={s.fieldLabel}>Position</span>
          <select
            className={s.select}
            value={position}
            onChange={(e) => setPosition(e.target.value)}
          >
            <option value="">Any</option>
            {POSITIONS.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </label>

        <div className={s.field}>
          <span className={s.fieldLabel}>How many</span>
          <div className={s.segment}>
            {data.lines.map((l, i) => (
              <button
                key={l}
                type="button"
                className={line === i ? s.segOn : s.seg}
                onClick={() => setLine(i)}
                aria-pressed={line === i}
              >
                {l + 0.5}+
              </button>
            ))}
          </div>
        </div>

        {!simple && (
          <label className={s.field}>
            <span className={s.fieldLabel}>Model</span>
            <select className={s.select} value={model} onChange={(e) => setModel(e.target.value)}>
              {data.models.map((m) => (
                <option key={m} value={m}>
                  {m === data.house ? `${m} (house)` : m}
                </option>
              ))}
            </select>
          </label>
        )}

        <div className={s.toggles}>
          <label className={s.check}>
            <input
              type="checkbox"
              checked={simple}
              onChange={(e) => setSimple(e.target.checked)}
            />
            Simple
          </label>
          <label className={s.check}>
            <input
              type="checkbox"
              checked={hideThin}
              onChange={(e) => setHideThin(e.target.checked)}
            />
            Hide thin evidence
          </label>
        </div>
      </div>

      <p className={s.count}>
        {rows.length} of {data.rows.length} players. Click a row for the whole shape.{" "}
        {simple
          ? "One model, the cautious one. Turn off Simple to see all five and how far apart they are."
          : `Showing ${model}, with every model plotted in the spread column.`}
      </p>

      <DataTable
        rows={rows}
        rowKey={(r) => r.fullName + r.fixture}
        sortKey={sort}
        onSort={(k) => setSort(k as Sort)}
        onRowClick={(r) => {
          const id = r.fullName + r.fixture;
          setOpen(open === id ? null : id);
        }}
        expanded={open}
        renderExpanded={(r) => (
          <Shape
            pmf={r.pmf[market]}
            lines={data.lines}
            published={r[market].map((probs) => probs[modelIndex])}
            selected={line}
            noun={MARKET_NOUN[market]}
          />
        )}
        empty="Nothing matches those filters. Widen the search, rather than reading this as a prediction that nobody fouls."
        columns={[
          {
            key: "name",
            head: "Player",
            sort: () => 0,
            cell: (r) => (
              <>
                <span className={s.name}>{r.player}</span>
                <span className={s.meta}>
                  {r.position && r.position !== "?" ? `${r.position} · ` : ""}
                  {r.team}
                  {r.confirmed && (
                    <span className={s.confirmed} title="Named in the confirmed eleven.">
                      <span className={s.dotMark} aria-hidden />
                      named
                    </span>
                  )}
                  {r.thin && (
                    <span className={s.thinTag} title="Too little history to be confident.">
                      thin
                    </span>
                  )}
                </span>
              </>
            ),
          },
          { key: "game", head: "Game", cell: (r) => <span className={s.fixture}>{r.fixture}</span> },
          { key: "minutes", head: "Mins", numeric: true, sort: () => 0, cell: (r) => `${Math.round(r.minutes)}'` },
          {
            key: "expected",
            head: "Expected",
            numeric: true,
            sort: () => 0,
            cell: (r) => r.expected[market].toFixed(2),
          },
          {
            key: "prob",
            head: `${lineLabel} in 100 games`,
            sort: () => 0,
            cell: (r) => <Bars p={r[market][line][modelIndex]} />,
          },
          ...(simple
            ? []
            : [
                {
                  key: "spread",
                  head: "Where the five sit",
                  cell: (r: ExplorerRow) => (
                    <Spread
                      probs={r[market][line]}
                      models={data.models}
                      active={modelIndex}
                    />
                  ),
                },
              ]),
          {
            key: "fair",
            head: "Fair price",
            numeric: true,
            cell: (r) => {
              const p = r[market][line][modelIndex];
              return p > 0 ? (1 / p).toFixed(2) : "—";
            },
          },
        ]}
      />
    </div>
  );
}

/** Where the five models sit relative to each other, on their own shared scale. */
function Spread({ probs, models, active }: { probs: number[]; models: string[]; active: number }) {
  const lo = Math.min(...probs);
  const hi = Math.max(...probs);
  const span = Math.max(hi - lo, 0.02);
  return (
    <span
      className={s.spread}
      title={models.map((m, i) => `${m} ${(probs[i] * 100).toFixed(0)}%`).join("\n")}
    >
      <span className={s.spreadTrack} />
      {probs.map((p, i) => (
        <span
          key={models[i]}
          className={i === active ? s.dotOn : s.dot}
          style={
            {
              left: `${((p - lo) / span) * 100}%`,
              "--char": `var(--ch-${models[i]})`,
            } as React.CSSProperties
          }
          aria-hidden
        />
      ))}
      <span className={s.spreadRange}>
        {(lo * 100).toFixed(0)}–{(hi * 100).toFixed(0)}%
      </span>
    </span>
  );
}
