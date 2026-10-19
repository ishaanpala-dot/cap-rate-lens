import type { SpreadPoint, HeatmapCell, PortfolioCurvePoint } from "./api";

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

export function CovenantBarChart({
  rows,
}: {
  rows: { ticker: string; bp_headroom: number }[];
}) {
  const W = 560;
  const rowH = 32;
  const padL = 48;
  const padR = 64;
  const H = rows.length * rowH + 20;
  const plotW = W - padL - padR;
  const maxMag = Math.max(...rows.map((r) => Math.abs(r.bp_headroom)), 1);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="Covenant headroom ranking">
      {rows.map((r, i) => {
        const barW = (Math.abs(r.bp_headroom) / maxMag) * plotW;
        const cy = 14 + i * rowH;
        return (
          <g key={r.ticker}>
            <text x={padL - 8} y={cy + 4} textAnchor="end" className="fill-zinc-700 dark:fill-zinc-300 font-mono text-[11px] font-medium">
              {r.ticker}
            </text>
            <rect x={padL} y={cy - 7} width={plotW} height={14} className="fill-zinc-100 dark:fill-zinc-900" rx={2} />
            <rect x={padL} y={cy - 7} width={barW} height={14} style={{ fill: "var(--accent)" }} rx={2} />
            <text x={padL + plotW + 8} y={cy + 4} className="fill-zinc-500 dark:fill-zinc-400 font-mono text-[10px]">
              {r.bp_headroom.toFixed(0)}bp
            </text>
          </g>
        );
      })}
    </svg>
  );
}

export function Heatmap({
  cells,
  xSteps,
  ySteps,
}: {
  cells: HeatmapCell[];
  xSteps: number[];
  ySteps: number[];
}) {
  const cellW = 52;
  const cellH = 28;
  const padL = 44;
  const padT = 18;
  const padB = 24;
  const W = padL + xSteps.length * cellW + 10;
  const H = padT + ySteps.length * cellH + padB;

  const maxAbs = Math.max(...cells.map((c) => Math.abs(c.pct_change)), 1);
  const colorFor = (v: number) => {
    const t = Math.min(Math.abs(v) / maxAbs, 1);
    if (v >= 0) {
      // positive: accent blue tint
      return `rgba(36,81,214,${0.12 + t * 0.6})`;
    }
    return `rgba(194,59,59,${0.12 + t * 0.6})`;
  };

  const yOrdered = [...ySteps].reverse();

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="Cap rate versus NOI growth NTA sensitivity grid">
      {xSteps.map((x, xi) => (
        <text
          key={x}
          x={padL + xi * cellW + cellW / 2}
          y={padT - 6}
          textAnchor="middle"
          className="fill-zinc-400 font-mono text-[9px]"
        >
          {x >= 0 ? `+${x}` : x}
        </text>
      ))}
      {yOrdered.map((y, yi) => (
        <text
          key={y}
          x={padL - 6}
          y={padT + yi * cellH + cellH / 2 + 3}
          textAnchor="end"
          className="fill-zinc-400 font-mono text-[9px]"
        >
          {y >= 0 ? `+${y}%` : `${y}%`}
        </text>
      ))}
      {yOrdered.map((y, yi) =>
        xSteps.map((x, xi) => {
          const cell = cells.find((c) => c.cap_rate_shift_bp === x && c.noi_growth_pct === y);
          if (!cell) return null;
          return (
            <g key={`${x}-${y}`}>
              <rect
                x={padL + xi * cellW}
                y={padT + yi * cellH}
                width={cellW - 1}
                height={cellH - 1}
                fill={colorFor(cell.pct_change)}
              />
              <text
                x={padL + xi * cellW + cellW / 2}
                y={padT + yi * cellH + cellH / 2 + 3}
                textAnchor="middle"
                className="fill-zinc-700 dark:fill-zinc-200 font-mono text-[9px]"
              >
                {cell.pct_change >= 0 ? "+" : ""}
                {cell.pct_change.toFixed(0)}
              </text>
            </g>
          );
        }),
      )}
      <text
        x={padL + (xSteps.length * cellW) / 2}
        y={H - 6}
        textAnchor="middle"
        className="fill-zinc-400 text-[9px]"
      >
        cap rate shift (bp) &rarr;
      </text>
    </svg>
  );
}

export function SensitivityCurveChart({ points }: { points: PortfolioCurvePoint[] }) {
  const valid = points.filter((p) => p.pct_change !== null) as { cap_rate_shift_bp: number; pct_change: number }[];
  if (valid.length === 0) return null;

  const W = 480;
  const H = 160;
  const padL = 40;
  const padR = 12;
  const padT = 14;
  const padB = 22;
  const plotW = W - padL - padR;
  const plotH = H - padT - padB;

  const xMin = Math.min(...valid.map((p) => p.cap_rate_shift_bp));
  const xMax = Math.max(...valid.map((p) => p.cap_rate_shift_bp));
  const yMin = Math.min(...valid.map((p) => p.pct_change), 0);
  const yMax = Math.max(...valid.map((p) => p.pct_change), 0);
  const ySpan = yMax - yMin || 1;

  const x = (v: number) => padL + ((v - xMin) / (xMax - xMin)) * plotW;
  const y = (v: number) => padT + plotH - ((v - yMin) / ySpan) * plotH;

  const path = valid.map((p, i) => `${i === 0 ? "M" : "L"} ${x(p.cap_rate_shift_bp)} ${y(p.pct_change)}`).join(" ");
  const zeroY = y(0);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="Combined portfolio sensitivity curve">
      <line x1={padL} x2={W - padR} y1={zeroY} y2={zeroY} className="stroke-zinc-300 dark:stroke-zinc-700" strokeWidth={1} />
      <path d={path} style={{ stroke: "var(--accent)" }} className="fill-none" strokeWidth={2} />
      {valid.map((p) => (
        <circle key={p.cap_rate_shift_bp} cx={x(p.cap_rate_shift_bp)} cy={y(p.pct_change)} r={2.5} style={{ fill: "var(--accent)" }} />
      ))}
      {valid.map((p) => (
        <text
          key={`${p.cap_rate_shift_bp}-label`}
          x={x(p.cap_rate_shift_bp)}
          y={H - 4}
          textAnchor="middle"
          className="fill-zinc-400 font-mono text-[8px]"
        >
          {p.cap_rate_shift_bp >= 0 ? `+${p.cap_rate_shift_bp}` : p.cap_rate_shift_bp}
        </text>
      ))}
    </svg>
  );
}

export { SECTOR_PALETTE };
