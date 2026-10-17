import type { SpreadPoint } from "./api";

const SECTOR_PALETTE = ["#2451d6", "#6690ea", "#a8b8d8", "#d8dde8"];

export function SpreadLineChart({ points }: { points: SpreadPoint[] }) {
  if (points.length < 2) return null;

  const W = 480;
  const H = 180;
  const padL = 36;
  const padR = 12;
  const padT = 14;
  const padB = 24;
  const plotW = W - padL - padR;
  const plotH = H - padT - padB;

  const allValues = points.flatMap((p) => [p.wacr_pct, p.bond_yield_pct]);
  const min = Math.min(...allValues) - 0.3;
  const max = Math.max(...allValues) + 0.3;
  const span = max - min || 1;

  const x = (i: number) => padL + (i / (points.length - 1)) * plotW;
  const y = (v: number) => padT + plotH - ((v - min) / span) * plotH;

  const wacrPath = points.map((p, i) => `${i === 0 ? "M" : "L"} ${x(i)} ${y(p.wacr_pct)}`).join(" ");
  const bondPath = points
    .map((p, i) => `${i === 0 ? "M" : "L"} ${x(i)} ${y(p.bond_yield_pct)}`)
    .join(" ");
  const areaPath =
    points.map((p, i) => `${i === 0 ? "M" : "L"} ${x(i)} ${y(p.wacr_pct)}`).join(" ") +
    " " +
    points
      .slice()
      .reverse()
      .map((p, i) => `L ${x(points.length - 1 - i)} ${y(p.bond_yield_pct)}`)
      .join(" ") +
    " Z";

  const gridLines = [min, (min + max) / 2, max];

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="Cap rate versus bond yield over time">
      {gridLines.map((v) => (
        <g key={v}>
          <line
            x1={padL}
            x2={W - padR}
            y1={y(v)}
            y2={y(v)}
            className="stroke-zinc-200 dark:stroke-zinc-800"
            strokeWidth={1}
          />
          <text x={padL - 6} y={y(v) + 3} textAnchor="end" className="fill-zinc-400 font-mono text-[9px]">
            {v.toFixed(1)}%
          </text>
        </g>
      ))}

      <path d={areaPath} style={{ fill: "var(--accent)", opacity: 0.08 }} />
      <path d={bondPath} className="fill-none stroke-zinc-400 dark:stroke-zinc-600" strokeWidth={1.5} strokeDasharray="3 3" />
      <path d={wacrPath} style={{ stroke: "var(--accent)" }} className="fill-none" strokeWidth={2} />

      {points.map((p, i) => (
        <g key={p.as_of}>
          <circle cx={x(i)} cy={y(p.wacr_pct)} r={3} style={{ fill: "var(--accent)" }} />
          <circle cx={x(i)} cy={y(p.bond_yield_pct)} r={2.5} className="fill-zinc-400 dark:fill-zinc-600" />
          <text
            x={x(i)}
            y={H - 4}
            textAnchor="middle"
            className="fill-zinc-400 font-mono text-[9px]"
          >
            {p.period}
          </text>
        </g>
      ))}
    </svg>
  );
}

export function SectorDonut({ sectors }: { sectors: { sector: string; pct: number }[] }) {
  const size = 96;
  const strokeWidth = 16;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;

  let cumulative = 0;
  const arcs = sectors.map((s, i) => {
    const arcLength = (s.pct / 100) * circumference;
    const offset = cumulative;
    cumulative += arcLength;
    return { ...s, arcLength, offset, color: SECTOR_PALETTE[i % SECTOR_PALETTE.length] };
  });

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="shrink-0" role="img" aria-label="Sector split">
      <g transform={`rotate(-90 ${size / 2} ${size / 2})`}>
        {arcs.map((a) => (
          <circle
            key={a.sector}
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={a.color}
            strokeWidth={strokeWidth}
            strokeDasharray={`${a.arcLength} ${circumference - a.arcLength}`}
            strokeDashoffset={-a.offset}
          />
        ))}
      </g>
    </svg>
  );
}

export function RiskBarChart({
  rows,
}: {
  rows: { ticker: string; pct_change_per_1pct_cap_rate_rise: number; gearing_pct: number }[];
}) {
  const W = 560;
  const rowH = 32;
  const padL = 48;
  const padR = 56;
  const H = rows.length * rowH + 20;
  const plotW = W - padL - padR;
  const maxMag = Math.max(...rows.map((r) => Math.abs(r.pct_change_per_1pct_cap_rate_rise)));

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="Leverage risk ranking">
      {rows.map((r, i) => {
        const barW = (Math.abs(r.pct_change_per_1pct_cap_rate_rise) / maxMag) * plotW;
        const cy = 14 + i * rowH;
        return (
          <g key={r.ticker}>
            <text x={padL - 8} y={cy + 4} textAnchor="end" className="fill-zinc-700 dark:fill-zinc-300 font-mono text-[11px] font-medium">
              {r.ticker}
            </text>
            <rect x={padL} y={cy - 7} width={plotW} height={14} className="fill-zinc-100 dark:fill-zinc-900" rx={2} />
            <rect
              x={padL}
              y={cy - 7}
              width={barW}
              height={14}
              className="fill-[#c23b3b] dark:fill-[#e05a5a]"
              rx={2}
            />
            <text
              x={padL + plotW + 8}
              y={cy + 4}
              className="fill-zinc-500 dark:fill-zinc-400 font-mono text-[10px]"
            >
              {r.pct_change_per_1pct_cap_rate_rise.toFixed(1)}%
            </text>
          </g>
        );
      })}
    </svg>
  );
}

export { SECTOR_PALETTE };
