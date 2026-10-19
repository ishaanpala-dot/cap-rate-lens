import { useState } from "react";
import { Trash, Plus } from "@phosphor-icons/react";
import { postPortfolio, type FundSummary, type PortfolioResponse, type PortfolioHolding } from "./api";
import { SensitivityCurveChart, SectorDonut, SECTOR_PALETTE } from "./Charts";

function formatPct(n: number | null, digits = 2) {
  if (n === null) return "n/a";
  return `${n.toFixed(digits)}%`;
}

export default function Portfolio({ fundList }: { fundList: FundSummary[] }) {
  const [holdings, setHoldings] = useState<{ fund_id: string; amount: string }[]>([]);
  const [result, setResult] = useState<PortfolioResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  function addHolding() {
    const unused = fundList.find((f) => !holdings.some((h) => h.fund_id === f.id));
    if (!unused) return;
    setHoldings([...holdings, { fund_id: unused.id, amount: "10000" }]);
  }

  function removeHolding(index: number) {
    setHoldings(holdings.filter((_, i) => i !== index));
  }

  function updateHolding(index: number, patch: Partial<{ fund_id: string; amount: string }>) {
    setHoldings(holdings.map((h, i) => (i === index ? { ...h, ...patch } : h)));
  }

  async function compute() {
    setError(null);
    const parsed: PortfolioHolding[] = holdings
      .map((h) => ({ fund_id: h.fund_id, amount: Number(h.amount) }))
      .filter((h) => h.amount > 0);
    if (parsed.length === 0) {
      setError("Add at least one holding with a positive amount.");
      setResult(null);
      return;
    }
    try {
      const res = await postPortfolio(parsed);
      setResult(res);
    } catch {
      setError("Could not compute the portfolio.");
      setResult(null);
    }
  }

  return (
    <div className="max-w-[64ch]">
      <h2 className="font-display text-xl font-semibold">Portfolio builder</h2>
      <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">
        Enter holdings across the tracked funds to see combined gearing, sector exposure, and a
        cap-rate sensitivity curve for the whole portfolio, not just one fund.
      </p>

      <div className="mt-6 space-y-2">
        {holdings.map((h, i) => (
          <div key={i} className="flex items-center gap-2">
            <select
              value={h.fund_id}
              onChange={(e) => updateHolding(i, { fund_id: e.target.value })}
              className="rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
            >
              {fundList.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.ticker} &middot; {f.name}
                </option>
              ))}
            </select>
            <span className="text-sm text-zinc-400">$</span>
            <input
              type="number"
              min={0}
              value={h.amount}
              onChange={(e) => updateHolding(i, { amount: e.target.value })}
              className="tabular w-32 rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
            />
            <button
              onClick={() => removeHolding(i)}
              className="ml-1 text-zinc-400 hover:text-red-600 dark:hover:text-red-400"
              aria-label="Remove holding"
            >
              <Trash weight="bold" size={16} />
            </button>
          </div>
        ))}

        <button
          onClick={addHolding}
          disabled={holdings.length >= fundList.length}
          className="inline-flex items-center gap-1 rounded-full border border-zinc-300 px-3 py-1.5 text-sm font-medium text-zinc-700 hover:border-zinc-400 disabled:opacity-40 dark:border-zinc-700 dark:text-zinc-300"
        >
          <Plus weight="bold" size={14} /> Add holding
        </button>
      </div>

      {holdings.length > 0 && (
        <button
          onClick={compute}
          style={{ background: "var(--accent)" }}
          className="mt-6 rounded-md px-4 py-2 text-sm font-medium text-white"
        >
          Compute portfolio
        </button>
      )}

      {error && <p className="mt-4 text-sm text-red-600 dark:text-red-400">{error}</p>}

      {result && (
        <div className="mt-8 space-y-8">
          <div className="grid grid-cols-2 gap-px overflow-hidden rounded-lg border border-zinc-200 bg-zinc-200 dark:border-zinc-800 dark:bg-zinc-800">
            <div className="bg-white p-4 dark:bg-zinc-950">
              <p className="text-xs text-zinc-500 dark:text-zinc-400">Total holdings</p>
              <p className="tabular mt-1 text-2xl font-semibold">
                ${result.total_amount.toLocaleString()}
              </p>
            </div>
            <div className="bg-white p-4 dark:bg-zinc-950">
              <p className="text-xs text-zinc-500 dark:text-zinc-400">Weighted gearing</p>
              <p className="tabular mt-1 text-2xl font-semibold">{formatPct(result.weighted_gearing_pct, 1)}</p>
            </div>
            <div className="bg-white p-4 dark:bg-zinc-950">
              <p className="text-xs text-zinc-500 dark:text-zinc-400">Weighted WACR</p>
              <p className="tabular mt-1 text-2xl font-semibold">{formatPct(result.weighted_wacr_pct)}</p>
            </div>
            <div className="bg-white p-4 dark:bg-zinc-950">
              <p className="text-xs text-zinc-500 dark:text-zinc-400">Sensitivity model coverage</p>
              <p className="tabular mt-1 text-2xl font-semibold">{formatPct(result.modelled_coverage_pct, 0)}</p>
            </div>
          </div>

          {result.sensitivity_curve.some((p) => p.pct_change !== null) && (
            <div>
              <h3 className="text-sm font-medium text-zinc-500 dark:text-zinc-400">
                Combined sensitivity curve
              </h3>
              <p className="mt-1 text-xs text-zinc-400 dark:text-zinc-500">
                Portfolio NTA % change if every holding's cap rate moved by the same amount at once.
              </p>
              <div className="mt-3">
                <SensitivityCurveChart points={result.sensitivity_curve} />
              </div>
            </div>
          )}

          {result.sector_exposure.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-zinc-500 dark:text-zinc-400">
                Combined sector exposure
              </h3>
              <p className="mt-1 text-xs text-zinc-400 dark:text-zinc-500">
                Covers {formatPct(result.sector_exposure_coverage_pct, 0)} of total holdings by value
                (only funds with sourced sector data are included).
              </p>
              <div className="mt-3 flex items-start gap-4">
                <SectorDonut sectors={result.sector_exposure} />
                <div className="space-y-1">
                  {result.sector_exposure.map((s, i) => (
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
          )}

          <p className="border-t border-zinc-200 pt-4 text-xs text-zinc-400 dark:border-zinc-800 dark:text-zinc-500">
            {result.note}
          </p>
        </div>
      )}
    </div>
  );
}
