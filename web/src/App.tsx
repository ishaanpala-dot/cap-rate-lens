import { useEffect, useMemo, useState } from "react";
import { CaretDown, CaretUp, Buildings, ChartLineUp, ArrowSquareOut } from "@phosphor-icons/react";
import {
  getFund,
  getSensitivity,
  listFunds,
  compareFunds,
  getSpread,
  getSectorExposure,
  getRiskRanking,
  getMonteCarlo,
  getCovenant,
  getCovenantRanking,
  getHeatmap,
  getCommentary,
  type Fund,
  type FundSummary,
  type SensitivityResult,
  type CompareRow,
  type SpreadResponse,
  type SectorExposureResponse,
  type RiskRankingResponse,
  type MonteCarloResult,
  type CovenantResult,
  type CovenantRankingResponse,
  type HeatmapResponse,
  type CommentaryResponse,
} from "./api";
import {
  SpreadLineChart,
  SectorDonut,
  RiskBarChart,
  CovenantBarChart,
  Heatmap,
  SECTOR_PALETTE,
} from "./Charts";
import About from "./About";
import Portfolio from "./Portfolio";

function formatPct(n: number | null | undefined, digits = 2) {
  if (n === null || n === undefined) return "n/a";
  return `${n.toFixed(digits)}%`;
}

function formatDollar(n: number) {
  return `$${n.toFixed(2)}`;
}

function formatBp(deltaPct: number) {
  const bp = Math.round(deltaPct * 100);
  return `${bp >= 0 ? "+" : ""}${bp}bp`;
}

const NOT_SOURCED_HINT =
  "Not yet sourced: this may exist in the fund's full report, but hasn't been manually or automatically extracted yet.";

function NotSourced() {
  return (
    <span
      title={NOT_SOURCED_HINT}
      className="cursor-help border-b border-dotted border-zinc-400 text-zinc-400 dark:border-zinc-600 dark:text-zinc-500"
    >
      n/a
    </span>
  );
}

function SourceLine({ text, url }: { text: string | null | undefined; url?: string | null }) {
  if (!text) return null;
  if (!url) {
    return <p className="mt-6 text-xs text-zinc-400 dark:text-zinc-500">{text}</p>;
  }
  return (
    <p className="mt-6 text-xs text-zinc-400 dark:text-zinc-500">
      <a
        href={url}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-start gap-1 underline decoration-dotted underline-offset-2 hover:text-zinc-600 dark:hover:text-zinc-300"
      >
        <span>{text}</span>
        <ArrowSquareOut weight="bold" size={11} className="mt-0.5 shrink-0" />
      </a>
    </p>
  );
}

type View = "detail" | "compare" | "sectors" | "portfolio" | "about";
type SortKey = keyof Pick<
  CompareRow,
  "ticker" | "nta_per_security" | "wacr_pct" | "gearing_pct" | "wale_years" | "as_of"
>;

export default function App() {
  const [view, setView] = useState<View>("detail");
  const [fundList, setFundList] = useState<FundSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [fund, setFund] = useState<Fund | null>(null);
  const [capRate, setCapRate] = useState<number>(6);
  const [sensitivity, setSensitivity] = useState<SensitivityResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [compareRows, setCompareRows] = useState<CompareRow[]>([]);
  const [sortKey, setSortKey] = useState<SortKey>("wacr_pct");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [spread, setSpread] = useState<SpreadResponse | null>(null);
  const [sectorExposure, setSectorExposure] = useState<SectorExposureResponse | null>(null);
  const [riskRanking, setRiskRanking] = useState<RiskRankingResponse | null>(null);
  const [monteCarlo, setMonteCarlo] = useState<MonteCarloResult | null>(null);
  const [covenant, setCovenant] = useState<CovenantResult | null>(null);
  const [covenantRanking, setCovenantRanking] = useState<CovenantRankingResponse | null>(null);
  const [heatmap, setHeatmap] = useState<HeatmapResponse | null>(null);
  const [commentary, setCommentary] = useState<CommentaryResponse | null>(null);

  useEffect(() => {
    listFunds()
      .then((funds) => {
        setFundList(funds);
        if (funds.length > 0) setSelectedId(funds[0].id);
      })
      .catch(() => setError("Could not reach the valuation API. Is it running on localhost:8000?"));
    // Fetched eagerly (not gated to the compare tab) so staleness badges can be
    // shown on the Fund detail tab too, without waiting for a tab switch.
    compareFunds()
      .then(setCompareRows)
      .catch(() => setError("Could not load the market comparison."));
    getRiskRanking()
      .then(setRiskRanking)
      .catch(() => setRiskRanking(null));
    getCovenantRanking()
      .then(setCovenantRanking)
      .catch(() => setCovenantRanking(null));
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    getFund(selectedId).then((f) => {
      setFund(f);
      const base = f.snapshots[0]?.wacr_pct;
      if (base) setCapRate(base);
    });
    getSpread(selectedId)
      .then(setSpread)
      .catch(() => setSpread(null));
    getMonteCarlo(selectedId)
      .then(setMonteCarlo)
      .catch(() => setMonteCarlo(null));
    getCovenant(selectedId)
      .then(setCovenant)
      .catch(() => setCovenant(null));
    getHeatmap(selectedId)
      .then(setHeatmap)
      .catch(() => setHeatmap(null));
    getCommentary(selectedId)
      .then(setCommentary)
      .catch(() => setCommentary(null));
  }, [selectedId]);

  useEffect(() => {
    if (view !== "sectors") return;
    getSectorExposure()
      .then(setSectorExposure)
      .catch(() => setError("Could not load sector exposure."));
  }, [view]);

  const snapshot = fund?.snapshots[0];
  const hasModel = snapshot?.wacr_pct != null && snapshot?.gearing_pct != null;

  useEffect(() => {
    if (!selectedId || !hasModel) {
      setSensitivity(null);
      return;
    }
    getSensitivity(selectedId, capRate)
      .then(setSensitivity)
      .catch(() => setSensitivity(null));
  }, [selectedId, capRate, hasModel]);

  const sliderRange = useMemo(() => {
    const base = snapshot?.wacr_pct ?? 6;
    return { min: Math.max(2, base - 2.5), max: base + 2.5, base };
  }, [snapshot]);

  const sortedRows = useMemo(() => {
    const withValue = compareRows.filter((r) => r[sortKey] !== null);
    const withoutValue = compareRows.filter((r) => r[sortKey] === null);
    withValue.sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      const diff = typeof av === "string" && typeof bv === "string" ? av.localeCompare(bv) : (av as number) - (bv as number);
      return sortDir === "asc" ? diff : -diff;
    });
    return [...withValue, ...withoutValue];
  }, [compareRows, sortKey, sortDir]);

  const latestAsOf = useMemo(() => {
    if (compareRows.length === 0) return null;
    return compareRows.reduce((max, r) => (r.as_of > max ? r.as_of : max), compareRows[0].as_of);
  }, [compareRows]);

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  }

  return (
    <div className="min-h-[100dvh] bg-[#fafaf9] text-zinc-900 dark:bg-[#0a0b0d] dark:text-zinc-100">
      <nav className="sticky top-0 z-10 border-b border-zinc-200 bg-[#fafaf9]/90 backdrop-blur dark:border-zinc-800 dark:bg-[#0a0b0d]/90">
        <div className="mx-auto flex h-14 max-w-5xl items-center gap-2 px-5">
          <span
            className="flex h-6 w-6 items-center justify-center rounded text-white"
            style={{ background: "var(--accent)" }}
          >
            <ChartLineUp weight="bold" size={14} />
          </span>
          <span className="font-display text-sm font-semibold">Cap Rate Lens</span>
        </div>
      </nav>

      <div className="mx-auto max-w-5xl px-5 py-10 md:py-12">
        <header className="mb-10">
          <h1 className="font-display text-2xl md:text-3xl font-semibold tracking-tight max-w-[22ch]">
            How cap rate moves reshape ASX property trust valuations
          </h1>
          <p className="mt-3 max-w-[60ch] text-zinc-600 dark:text-zinc-400">
            Compare WACR, gearing and NTA across major ASX-listed property trusts, or pick one
            fund and move its cap rate to see net tangible assets respond. Figures are sourced
            from each fund's public ASX announcements.
          </p>
        </header>

        {error && (
          <div className="mb-8 rounded-md border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300">
            {error}
          </div>
        )}

        <div className="mb-8 flex gap-2 border-b border-zinc-200 dark:border-zinc-800">
          <TabButton active={view === "detail"} onClick={() => setView("detail")}>
            Fund detail
          </TabButton>
          <TabButton active={view === "compare"} onClick={() => setView("compare")}>
            Market comparison
          </TabButton>
          <TabButton active={view === "sectors"} onClick={() => setView("sectors")}>
            Sector exposure
          </TabButton>
          <TabButton active={view === "portfolio"} onClick={() => setView("portfolio")}>
            Portfolio builder
          </TabButton>
          <TabButton active={view === "about"} onClick={() => setView("about")}>
            About
          </TabButton>
        </div>

        {view === "detail" && (
          <>
            <div className="mb-10 flex flex-wrap gap-2">
              {fundList.map((f) => (
                <button
                  key={f.id}
                  onClick={() => setSelectedId(f.id)}
                  style={selectedId === f.id ? { background: "var(--accent)", borderColor: "var(--accent)" } : undefined}
                  className={`tabular rounded-full border px-4 py-2 text-sm font-medium transition-colors ${
                    selectedId === f.id
                      ? "text-white"
                      : "border-zinc-300 bg-white text-zinc-700 hover:border-zinc-400 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-300"
                  }`}
                >
                  {f.ticker}
                </button>
              ))}
            </div>

            {fund && snapshot && (
              <div className="grid gap-10 md:grid-cols-[1.1fr_1fr]">
                <section>
                  <h2 className="font-display text-xl font-semibold">{fund.name}</h2>
                  <p className="text-sm text-zinc-500 dark:text-zinc-400">
                    {snapshot.period}, as of {snapshot.as_of}
                    <StaleBadge asOf={snapshot.as_of} latestAsOf={latestAsOf} />
                  </p>

                  <div className="mt-6 grid grid-cols-2 gap-px overflow-hidden rounded-lg border border-zinc-200 bg-zinc-200 dark:border-zinc-800 dark:bg-zinc-800">
                    <Metric label="NTA per security" value={formatDollar(snapshot.nta_per_security)} />
                    <Metric
                      label="WACR"
                      value={snapshot.wacr_pct !== null ? formatPct(snapshot.wacr_pct) : <NotSourced />}
                    />
                    <Metric
                      label="Gearing"
                      value={snapshot.gearing_pct !== null ? formatPct(snapshot.gearing_pct) : <NotSourced />}
                    />
                    <Metric
                      label="WALE"
                      value={
                        snapshot.wale_years ? (
                          `${snapshot.wale_years.toFixed(1)}y`
                        ) : snapshot.computed_wale ? (
                          <span
                            title={`Value-weighted across ${snapshot.computed_wale.coverage_pct}% of the portfolio (sectors with both a WALE and a known exposure %)`}
                            className="cursor-help border-b border-dotted border-zinc-400"
                          >
                            ~{snapshot.computed_wale.value.toFixed(1)}y
                          </span>
                        ) : (
                          <NotSourced />
                        )
                      }
                    />
                  </div>

                  {snapshot.sectors.length > 0 && (
                    <div className="mt-6">
                      <h3 className="text-sm font-medium text-zinc-500 dark:text-zinc-400">
                        Sector cap rates
                      </h3>
                      <div className="mt-2 divide-y divide-zinc-200 dark:divide-zinc-800">
                        {snapshot.sectors.map((s) => (
                          <div key={s.sector} className="flex items-center justify-between py-2 text-sm">
                            <span>{s.sector}</span>
                            <span className="tabular flex gap-4 text-zinc-600 dark:text-zinc-400">
                              <span>{s.wale_years.toFixed(1)}y WALE</span>
                              <span className="font-medium text-zinc-900 dark:text-zinc-100">
                                {formatPct(s.cap_rate_pct)}
                              </span>
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  <SourceLine text={snapshot.source} url={snapshot.source_url} />

                  {spread && spread.points.length >= 2 && (
                    <div className="mt-8">
                      <h3 className="text-sm font-medium text-zinc-500 dark:text-zinc-400">
                        Cap rate risk premium
                      </h3>
                      <p className="mt-1 text-xs text-zinc-400 dark:text-zinc-500">
                        Solid line is WACR, dashed line is the 10-year Australian government bond
                        yield. The shaded gap is the risk premium.
                      </p>
                      <div className="mt-3">
                        <SpreadLineChart points={spread.points} />
                      </div>
                      <div className="mt-1 flex gap-4 text-xs text-zinc-500 dark:text-zinc-400">
                        <span className="inline-flex items-center gap-1.5">
                          <span className="h-0.5 w-3" style={{ background: "var(--accent)" }} />
                          WACR
                        </span>
                        <span className="inline-flex items-center gap-1.5">
                          <span className="h-0.5 w-3 border-t-2 border-dashed border-zinc-400" />
                          10y bond yield
                        </span>
                      </div>
                      <p className="mt-3 text-xs text-zinc-500 dark:text-zinc-400">
                        {spread.points[spread.points.length - 1].spread_pct < spread.points[0].spread_pct
                          ? "The premium has compressed over this period, bond yields moved up faster than this fund's cap rate."
                          : "The premium has widened over this period, this fund's cap rate moved up faster than bond yields."}
                        {spread.points.length === 2 &&
                          " Based on only two data points so far, treat this as indicative rather than a confirmed trend."}
                      </p>
                      <p className="mt-2 text-xs text-zinc-400 dark:text-zinc-500">{spread.bond_source}</p>
                    </div>
                  )}
                </section>

                <section className="rounded-xl border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-950">
                  <h3 className="text-sm font-medium text-zinc-500 dark:text-zinc-400">
                    Cap rate sensitivity
                  </h3>

                  {!hasModel ? (
                    <p className="mt-4 text-sm text-zinc-500 dark:text-zinc-400">
                      This fund's latest snapshot doesn't report both WACR and gearing, so the
                      sensitivity model can't run for it yet.
                    </p>
                  ) : (
                    <>
                      <div className="mt-4">
                        <div className="flex items-baseline justify-between">
                          <span className="tabular text-4xl font-semibold">
                            {capRate.toFixed(2)}%
                          </span>
                          <span className="tabular text-sm text-zinc-500 dark:text-zinc-400">
                            base {formatPct(sliderRange.base)}
                            {Math.abs(capRate - sliderRange.base) > 0.001 && (
                              <span className="ml-1.5">({formatBp(capRate - sliderRange.base)})</span>
                            )}
                          </span>
                        </div>
                        <input
                          type="range"
                          min={sliderRange.min}
                          max={sliderRange.max}
                          step={0.05}
                          value={capRate}
                          onChange={(e) => setCapRate(Number(e.target.value))}
                          style={{ accentColor: "var(--accent)" }}
                          className="mt-3 w-full"
                        />
                        <div className="mt-1 flex justify-between text-xs text-zinc-400">
                          <span>{sliderRange.min.toFixed(1)}%</span>
                          <span>{sliderRange.max.toFixed(1)}%</span>
                        </div>
                      </div>

                      {sensitivity && (
                        <div className="mt-6 border-t border-zinc-200 pt-6 dark:border-zinc-800">
                          <div className="flex items-end justify-between">
                            <div>
                              <p className="text-sm text-zinc-500 dark:text-zinc-400">
                                Implied NTA per security
                              </p>
                              <p className="tabular text-3xl font-semibold">
                                {formatDollar(sensitivity.new_nta_per_security)}
                              </p>
                            </div>
                            <p
                              className={`tabular flex items-center gap-1 text-lg font-medium ${
                                sensitivity.pct_change >= 0
                                  ? "text-emerald-600 dark:text-emerald-400"
                                  : "text-red-600 dark:text-red-400"
                              }`}
                            >
                              <CaretDown
                                weight="bold"
                                className={sensitivity.pct_change >= 0 ? "rotate-180" : ""}
                              />
                              {Math.abs(sensitivity.pct_change).toFixed(1)}%
                            </p>
                          </div>
                          <p className="mt-3 text-xs text-zinc-500 dark:text-zinc-400">
                            Assumes net operating income is unchanged and debt is fixed, so the full
                            swing in asset value flows through to equity.
                          </p>
                        </div>
                      )}

                      {monteCarlo && (
                        <div className="mt-6 border-t border-zinc-200 pt-6 dark:border-zinc-800">
                          <h4 className="text-sm font-medium text-zinc-500 dark:text-zinc-400">
                            Simulated NTA range (Monte Carlo)
                          </h4>
                          <p className="mt-1 text-xs text-zinc-400 dark:text-zinc-500">
                            {monteCarlo.simulations.toLocaleString()} draws of a cap rate shift
                            (&plusmn;{Math.round(monteCarlo.shift_std_dev_pct * 100)}bp, 1 std.
                            dev., a simplifying assumption) applied to the valuation model.
                          </p>
                          <FanChart result={monteCarlo} />
                        </div>
                      )}
                    </>
                  )}
                </section>
              </div>
            )}

            {commentary && commentary.sentences.length > 0 && (
              <div className="mt-10 rounded-xl border border-zinc-200 p-6 dark:border-zinc-800">
                <h3 className="text-sm font-medium text-zinc-500 dark:text-zinc-400">
                  What the numbers say
                </h3>
                <p className="mt-1 text-xs text-zinc-400 dark:text-zinc-500">
                  Generated from fixed templates filled with the figures above, not free-form text,
                  so nothing here can state a number that isn't backed by the data on this page.
                </p>
                <ul className="mt-3 space-y-2 text-sm text-zinc-700 dark:text-zinc-300">
                  {commentary.sentences.map((s, i) => (
                    <li key={i} className="flex gap-2">
                      <span className="text-zinc-300 dark:text-zinc-700">&bull;</span>
                      <span>{s}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {covenant && (
              <div className="mt-6 rounded-xl border border-zinc-200 p-6 dark:border-zinc-800">
                <h3 className="text-sm font-medium text-zinc-500 dark:text-zinc-400">
                  Covenant headroom
                </h3>
                <p className="mt-1 text-xs text-zinc-400 dark:text-zinc-500">
                  No tracked fund discloses an actual bank-loan gearing covenant, so this assumes a
                  single {covenant.covenant_gearing_pct.toFixed(0)}% gearing threshold applied
                  uniformly to every fund, not a reported figure.
                </p>
                <p className="tabular mt-3 text-2xl font-semibold">
                  {covenant.bp_headroom.toFixed(0)}bp{" "}
                  <span className="text-sm font-normal text-zinc-500 dark:text-zinc-400">
                    of cap rate rise until gearing reaches {covenant.covenant_gearing_pct.toFixed(0)}%
                    (at {covenant.cap_rate_at_breach_pct.toFixed(2)}%)
                  </span>
                </p>
              </div>
            )}

            {heatmap && (
              <div className="mt-6 rounded-xl border border-zinc-200 p-6 dark:border-zinc-800">
                <h3 className="text-sm font-medium text-zinc-500 dark:text-zinc-400">
                  Cap rate vs. rent growth
                </h3>
                <p className="mt-1 text-xs text-zinc-400 dark:text-zinc-500">
                  NTA per security % change for each combination. The 0% row/column is the current
                  position; shows how much rent growth would offset a given cap rate move.
                </p>
                <div className="mt-3 overflow-x-auto">
                  <Heatmap
                    cells={heatmap.cells}
                    xSteps={heatmap.cap_rate_shifts_bp}
                    ySteps={heatmap.noi_growth_steps_pct}
                  />
                </div>
              </div>
            )}
          </>
        )}

        {view === "compare" && (
          <>
            <div className="overflow-x-auto rounded-lg border border-zinc-200 dark:border-zinc-800">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-zinc-200 bg-zinc-50 text-left dark:border-zinc-800 dark:bg-zinc-900">
                    <SortableHeader label="Fund" sortKey="ticker" active={sortKey} dir={sortDir} onSort={toggleSort} />
                    <SortableHeader label="NTA" sortKey="nta_per_security" active={sortKey} dir={sortDir} onSort={toggleSort} />
                    <SortableHeader label="WACR" sortKey="wacr_pct" active={sortKey} dir={sortDir} onSort={toggleSort} />
                    <SortableHeader label="Gearing" sortKey="gearing_pct" active={sortKey} dir={sortDir} onSort={toggleSort} />
                    <SortableHeader label="WALE" sortKey="wale_years" active={sortKey} dir={sortDir} onSort={toggleSort} />
                    <SortableHeader label="As of" sortKey="as_of" active={sortKey} dir={sortDir} onSort={toggleSort} />
                    <th className="px-4 py-3 font-medium text-zinc-500 dark:text-zinc-400">Source</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedRows.map((r) => (
                    <tr
                      key={r.id}
                      onClick={() => {
                        setSelectedId(r.id);
                        setView("detail");
                      }}
                      className="cursor-pointer border-b border-zinc-100 last:border-0 hover:bg-zinc-50 dark:border-zinc-900 dark:hover:bg-zinc-900"
                    >
                      <td className="px-4 py-3">
                        <span className="font-medium">{r.ticker}</span>
                        <span className="ml-2 text-zinc-500 dark:text-zinc-400">{r.name}</span>
                      </td>
                      <td className="tabular px-4 py-3">{formatDollar(r.nta_per_security)}</td>
                      <td className="tabular px-4 py-3">{r.wacr_pct !== null ? formatPct(r.wacr_pct) : <NotSourced />}</td>
                      <td className="tabular px-4 py-3">{r.gearing_pct !== null ? formatPct(r.gearing_pct, 1) : <NotSourced />}</td>
                      <td className="tabular px-4 py-3">
                        {r.wale_years ? (
                          `${r.wale_years.toFixed(1)}y`
                        ) : r.computed_wale ? (
                          <span title={`Value-weighted across ${r.computed_wale.coverage_pct}% of the portfolio (sectors with both a WALE and a known exposure %)`} className="cursor-help border-b border-dotted border-zinc-400">
                            ~{r.computed_wale.value.toFixed(1)}y
                          </span>
                        ) : (
                          <NotSourced />
                        )}
                      </td>
                      <td className="tabular px-4 py-3 text-zinc-500 dark:text-zinc-400">
                        {r.as_of}
                        <StaleBadge asOf={r.as_of} latestAsOf={latestAsOf} />
                      </td>
                      <td className="px-4 py-3">
                        {r.source_url ? (
                          <a
                            href={r.source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            title={r.source ?? undefined}
                            className="inline-flex text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200"
                          >
                            <ArrowSquareOut weight="bold" size={14} />
                          </a>
                        ) : (
                          <span title={r.source ?? NOT_SOURCED_HINT} className="cursor-help text-zinc-300 dark:text-zinc-700">
                            <ArrowSquareOut weight="bold" size={14} />
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {riskRanking && riskRanking.rows.length > 0 && (
              <div className="mt-10">
                <h3 className="text-sm font-medium text-zinc-500 dark:text-zinc-400">
                  Leverage risk ranking
                </h3>
                <p className="mt-1 text-xs text-zinc-400 dark:text-zinc-500">
                  NTA per security change for a +100bp rise in cap rate, worst-affected first.
                  Higher gearing amplifies the same cap rate move into a larger equity swing.
                </p>
                <div className="mt-3">
                  <RiskBarChart rows={riskRanking.rows} />
                </div>
                <p className="mt-3 text-xs text-zinc-400 dark:text-zinc-500">
                  {riskRanking.coverage_note}
                </p>
              </div>
            )}

            {covenantRanking && covenantRanking.rows.length > 0 && (
              <div className="mt-10">
                <h3 className="text-sm font-medium text-zinc-500 dark:text-zinc-400">
                  Covenant headroom ranking
                </h3>
                <p className="mt-1 text-xs text-zinc-400 dark:text-zinc-500">
                  {covenantRanking.assumption_note} Least headroom first.
                </p>
                <div className="mt-3">
                  <CovenantBarChart rows={covenantRanking.rows} />
                </div>
                <p className="mt-3 text-xs text-zinc-400 dark:text-zinc-500">
                  {covenantRanking.coverage_note}
                </p>
              </div>
            )}
          </>
        )}

        {view === "sectors" && sectorExposure && (
          <div>
            <div className="grid gap-6 sm:grid-cols-2">
              {sectorExposure.funds.map((f) => {
                const fundMeta = fundList.find((x) => x.id === f.id);
                return (
                  <div
                    key={f.id}
                    className="rounded-xl border border-zinc-200 p-5 dark:border-zinc-800"
                  >
                    <div className="flex items-start gap-4">
                      <SectorDonut sectors={f.sectors} />
                      <div className="min-w-0">
                        <div className="flex items-center gap-1.5">
                          <Buildings weight="bold" size={14} className="text-zinc-400" />
                          <h3 className="font-display text-sm font-semibold">
                            {fundMeta?.ticker} &middot; {fundMeta?.name}
                          </h3>
                        </div>
                        <p className="mt-0.5 text-xs text-zinc-400 dark:text-zinc-500">as of {f.as_of}</p>
                        <div className="mt-3 space-y-1">
                          {f.sectors.map((s, i) => (
                            <div key={s.sector} className="flex items-center gap-1.5 text-xs text-zinc-600 dark:text-zinc-400">
                              <span
                                className="h-2 w-2 shrink-0 rounded-full"
                                style={{ background: SECTOR_PALETTE[i % SECTOR_PALETTE.length] }}
                              />
                              <span className="tabular">{s.pct}%</span>
                              <span>{s.sector}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                    <p className="mt-4 text-xs text-zinc-400 dark:text-zinc-500">{f.note}</p>
                    {f.source_url && (
                      <a
                        href={f.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="mt-1 inline-flex items-center gap-1 text-xs text-zinc-400 underline decoration-dotted underline-offset-2 hover:text-zinc-600 dark:text-zinc-500 dark:hover:text-zinc-300"
                      >
                        View source <ArrowSquareOut weight="bold" size={11} />
                      </a>
                    )}
                  </div>
                );
              })}
            </div>
            <p className="mt-8 border-t border-zinc-200 pt-4 text-xs text-zinc-400 dark:border-zinc-800 dark:text-zinc-500">
              {sectorExposure.coverage_note}
            </p>
          </div>
        )}

        {view === "portfolio" && <Portfolio fundList={fundList} />}

        {view === "about" && <About />}
      </div>
    </div>
  );
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      style={active ? { borderColor: "var(--accent)" } : undefined}
      className={`border-b-2 px-1 pb-3 text-sm font-medium transition-colors ${
        active
          ? "text-zinc-900 dark:text-zinc-100"
          : "border-transparent text-zinc-600 hover:text-zinc-900 dark:text-zinc-300 dark:hover:text-zinc-100"
      }`}
    >
      {children}
    </button>
  );
}

function StaleBadge({ asOf, latestAsOf }: { asOf: string; latestAsOf: string | null }) {
  if (!latestAsOf || asOf >= latestAsOf) return null;
  return (
    <span
      title={`Latest tracked data is as of ${latestAsOf}. This fund's figures are from ${asOf}.`}
      className="tabular ml-2 cursor-help rounded border border-amber-300 bg-amber-50 px-1.5 py-0.5 text-[10px] font-medium text-amber-700 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-400"
    >
      older data
    </span>
  );
}

function FanChart({ result }: { result: MonteCarloResult }) {
  const values = [result.p10, result.p25, result.p50, result.p75, result.p90];
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const pct = (v: number) => ((v - min) / span) * 100;

  return (
    <div className="mt-4">
      <div className="relative h-10">
        <div className="absolute inset-y-0 left-0 right-0 rounded" style={{ background: "var(--accent-soft)" }} />
        <div
          className="absolute inset-y-0 rounded"
          style={{ left: `${pct(result.p25)}%`, right: `${100 - pct(result.p75)}%`, background: "var(--accent)", opacity: 0.45 }}
        />
        <div
          className="absolute inset-y-0 w-0.5"
          style={{ left: `${pct(result.p50)}%`, background: "var(--accent)" }}
        />
      </div>
      <div className="tabular mt-2 flex justify-between text-xs text-zinc-500 dark:text-zinc-400">
        <span>p10 {formatDollar(result.p10)}</span>
        <span className="font-medium text-zinc-900 dark:text-zinc-100">
          median {formatDollar(result.p50)}
        </span>
        <span>p90 {formatDollar(result.p90)}</span>
      </div>
    </div>
  );
}

function SortableHeader({
  label,
  sortKey,
  active,
  dir,
  onSort,
}: {
  label: string;
  sortKey: SortKey;
  active: SortKey;
  dir: "asc" | "desc";
  onSort: (key: SortKey) => void;
}) {
  const isActive = active === sortKey;
  return (
    <th className="px-4 py-3 font-medium text-zinc-500 dark:text-zinc-400">
      <button
        onClick={() => onSort(sortKey)}
        aria-sort={isActive ? (dir === "asc" ? "ascending" : "descending") : "none"}
        className="inline-flex items-center gap-1 rounded select-none focus-visible:outline-2 focus-visible:outline-offset-2"
        style={{ outlineColor: "var(--accent)" }}
      >
        {label}
        {isActive &&
          (dir === "asc" ? <CaretUp weight="bold" size={12} /> : <CaretDown weight="bold" size={12} />)}
      </button>
    </th>
  );
}

function Metric({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="bg-white p-4 dark:bg-zinc-950">
      <p className="text-xs text-zinc-500 dark:text-zinc-400">{label}</p>
      <p className="tabular mt-1 text-2xl font-semibold">{value}</p>
    </div>
  );
}
