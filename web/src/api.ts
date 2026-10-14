const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

export type FundSummary = {
  id: string;
  name: string;
  ticker: string;
};

export type FundSector = {
  sector: string;
  wale_years: number;
  cap_rate_pct: number;
};

export type FundSnapshot = {
  period: string;
  as_of: string;
  nta_per_security: number;
  wacr_pct: number | null;
  gearing_pct: number | null;
  sectors: FundSector[];
  wale_years?: number | null;
  occupancy_pct?: number | null;
  source: string;
};

export type Fund = FundSummary & {
  snapshots: FundSnapshot[];
};

export type SensitivityResult = {
  base_nta_per_security: number;
  new_nta_per_security: number;
  pct_change: number;
  base_cap_rate_pct: number;
  new_cap_rate_pct: number;
  gearing_pct: number | null;
};

export async function listFunds(): Promise<FundSummary[]> {
  const res = await fetch(`${API_BASE}/funds`);
  if (!res.ok) throw new Error("Failed to load funds");
  return res.json();
}

export async function getFund(id: string): Promise<Fund> {
  const res = await fetch(`${API_BASE}/funds/${id}`);
  if (!res.ok) throw new Error("Failed to load fund");
  return res.json();
}

export async function getSensitivity(
  id: string,
  newCapRatePct: number,
): Promise<SensitivityResult> {
  const res = await fetch(
    `${API_BASE}/funds/${id}/sensitivity?new_cap_rate_pct=${newCapRatePct}`,
  );
  if (!res.ok) throw new Error("Failed to compute sensitivity");
  return res.json();
}

export type CompareRow = {
  id: string;
  name: string;
  ticker: string;
  period: string;
  as_of: string;
  nta_per_security: number;
  wacr_pct: number | null;
  gearing_pct: number | null;
  wale_years: number | null;
  occupancy_pct: number | null;
};

export async function compareFunds(): Promise<CompareRow[]> {
  const res = await fetch(`${API_BASE}/compare`);
  if (!res.ok) throw new Error("Failed to load comparison");
  return res.json();
}

export type SpreadPoint = {
  period: string;
  as_of: string;
  wacr_pct: number;
  bond_yield_pct: number;
  bond_yield_period: string;
  spread_pct: number;
};

export type SpreadResponse = {
  fund_id: string;
  points: SpreadPoint[];
  bond_source: string;
};

export async function getSpread(id: string): Promise<SpreadResponse> {
  const res = await fetch(`${API_BASE}/funds/${id}/spread`);
  if (!res.ok) throw new Error("Failed to load spread");
  return res.json();
}

export type SectorExposureFund = {
  id: string;
  as_of: string;
  sectors: { sector: string; pct: number }[];
  basis: string;
  note: string;
};

export type SectorExposureResponse = {
  funds: SectorExposureFund[];
  coverage_note: string;
};

export async function getSectorExposure(): Promise<SectorExposureResponse> {
  const res = await fetch(`${API_BASE}/sector-exposure`);
  if (!res.ok) throw new Error("Failed to load sector exposure");
  return res.json();
}

export type RiskRankingRow = {
  id: string;
  name: string;
  ticker: string;
  wacr_pct: number;
  gearing_pct: number;
  pct_change_per_1pct_cap_rate_rise: number;
};

export type RiskRankingResponse = {
  rows: RiskRankingRow[];
  coverage_note: string;
};

export async function getRiskRanking(): Promise<RiskRankingResponse> {
  const res = await fetch(`${API_BASE}/risk-ranking`);
  if (!res.ok) throw new Error("Failed to load risk ranking");
  return res.json();
}

export type MonteCarloResult = {
  base_nta_per_security: number;
  base_cap_rate_pct: number;
  shift_std_dev_pct: number;
  simulations: number;
  p10: number;
  p25: number;
  p50: number;
  p75: number;
  p90: number;
};

export async function getMonteCarlo(id: string): Promise<MonteCarloResult> {
  const res = await fetch(`${API_BASE}/funds/${id}/monte-carlo`);
  if (!res.ok) throw new Error("Failed to load simulation");
  return res.json();
}
