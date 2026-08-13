import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { PerformanceHistoryOut } from "../lib/types";

interface Props {
  history: PerformanceHistoryOut | null;
}

// Categorical slots validated CVD-safe (all-pairs, dark surface) together —
// see the dataviz palette check run for this feature. Index 0 is always the
// portfolio; the rest map to benchmark_labels in server-returned order.
const SERIES_COLORS = ["#3987e5", "#d95926", "#199e70"];

const CHART_HEIGHT = 260;
const MARGIN = { top: 12, right: 16, bottom: 24, left: 46 };

function formatPct(value: number | null): string {
  if (value === null) return "—";
  const pct = (value * 100).toFixed(1);
  return `${value >= 0 ? "+" : ""}${pct}%`;
}

function formatUsd(value: number): string {
  return value.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
}

function niceTicks(min: number, max: number, count = 4): number[] {
  if (min === max) {
    min -= 0.05;
    max += 0.05;
  }
  const rawStep = (max - min) / count;
  const mag = Math.pow(10, Math.floor(Math.log10(rawStep)));
  const norm = rawStep / mag;
  const step = norm < 1.5 ? mag : norm < 3 ? 2 * mag : norm < 7 ? 5 * mag : 10 * mag;
  const niceMin = Math.floor(min / step) * step;
  const niceMax = Math.ceil(max / step) * step;
  const ticks: number[] = [];
  for (let v = niceMin; v <= niceMax + step * 0.5; v += step) ticks.push(v);
  return ticks;
}

function buildPathSegments(values: (number | null)[], xAt: (i: number) => number, yAt: (v: number) => number): string {
  const segments: string[] = [];
  let current = "";
  values.forEach((v, i) => {
    if (v === null) {
      if (current) segments.push(current);
      current = "";
      return;
    }
    current += `${current ? "L" : "M"}${xAt(i).toFixed(2)},${yAt(v).toFixed(2)}`;
  });
  if (current) segments.push(current);
  return segments.join(" ");
}

export default function PerformanceChart({ history }: Props) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(640);
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);

  useEffect(() => {
    const measure = () => {
      if (wrapRef.current) setWidth(wrapRef.current.clientWidth);
    };
    measure();
    window.addEventListener("resize", measure);
    return () => window.removeEventListener("resize", measure);
  }, []);

  const points = history?.points ?? [];
  const benchmarkTickers = useMemo(
    () => Object.keys(history?.benchmark_labels ?? {}),
    [history]
  );

  const series = useMemo(() => {
    const list = [
      {
        key: "portfolio",
        label: "Your Portfolio",
        color: SERIES_COLORS[0],
        values: points.map((p) => p.portfolio_return_pct),
      },
    ];
    benchmarkTickers.forEach((ticker, i) => {
      list.push({
        key: ticker,
        label: history?.benchmark_labels[ticker] ?? ticker,
        color: SERIES_COLORS[(i + 1) % SERIES_COLORS.length],
        values: points.map((p) => p.benchmark_return_pct[ticker] ?? null),
      });
    });
    return list;
  }, [points, benchmarkTickers, history]);

  const plotWidth = Math.max(width - MARGIN.left - MARGIN.right, 10);
  const plotHeight = CHART_HEIGHT - MARGIN.top - MARGIN.bottom;

  const allValues = series.flatMap((s) => s.values).filter((v): v is number => v !== null);
  const hasData = allValues.length > 0;
  const rawMin = hasData ? Math.min(0, ...allValues) : -0.05;
  const rawMax = hasData ? Math.max(0, ...allValues) : 0.05;
  const yTicks = niceTicks(rawMin, rawMax);
  const yMin = yTicks[0];
  const yMax = yTicks[yTicks.length - 1];

  const xAt = useCallback(
    (i: number) => (points.length <= 1 ? MARGIN.left : MARGIN.left + (i / (points.length - 1)) * plotWidth),
    [points.length, plotWidth]
  );
  const yAt = useCallback(
    (v: number) => MARGIN.top + (1 - (v - yMin) / (yMax - yMin)) * plotHeight,
    [yMin, yMax, plotHeight]
  );

  const handleMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (points.length === 0) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const fraction = (e.clientX - rect.left - MARGIN.left) / plotWidth;
    const idx = Math.round(fraction * (points.length - 1));
    setHoverIndex(Math.min(Math.max(idx, 0), points.length - 1));
  };

  if (!history || points.length === 0) {
    return (
      <section className="ledger performance-panel">
        <h2 className="panel-title">RETURNS VS. BENCHMARK</h2>
        <p className="panel-subtitle">
          Return per dollar contributed, tracked since your first deposit, vs. the same money put into the
          S&amp;P 500 and Nasdaq 100 instead.
        </p>
        <p className="empty-state">No deposits or trades recorded yet — this chart fills in once money starts moving.</p>
      </section>
    );
  }

  const activeIndex = hoverIndex;
  const activePoint = activeIndex !== null ? points[activeIndex] : null;
  const tooltipLeft = activeIndex !== null ? Math.min(Math.max(xAt(activeIndex), 90), width - 90) : 0;

  return (
    <section className="ledger performance-panel">
      <h2 className="panel-title">RETURNS VS. BENCHMARK</h2>
      <p className="panel-subtitle">
        Return per dollar contributed since {points[0].date}, vs. the same contribution schedule replayed into
        each benchmark. Not a raw value chart — deposits made later don&apos;t create a fake dip.
      </p>

      <div className="performance-stats">
        {series.map((s) => {
          const latest = s.values[s.values.length - 1];
          return (
            <div className="performance-stat" key={s.key}>
              <span className="performance-stat-label">
                <span className="performance-line-key" style={{ background: s.color }} />
                {s.label}
              </span>
              <span className={`performance-stat-value ${latest !== null && latest >= 0 ? "accent-green" : "accent-red"}`}>
                {formatPct(latest)}
              </span>
            </div>
          );
        })}
        <div className="performance-stat">
          <span className="performance-stat-label">Net Contributed</span>
          <span className="performance-stat-value">{formatUsd(history.net_contributions)}</span>
        </div>
      </div>

      <div
        className="performance-chart-wrap"
        ref={wrapRef}
        onMouseMove={handleMove}
        onMouseLeave={() => setHoverIndex(null)}
      >
        <svg width="100%" height={CHART_HEIGHT} viewBox={`0 0 ${width} ${CHART_HEIGHT}`}>
          {yTicks.map((t) => (
            <g key={t}>
              <line
                x1={MARGIN.left}
                x2={width - MARGIN.right}
                y1={yAt(t)}
                y2={yAt(t)}
                stroke={t === 0 ? "var(--border-strong)" : "var(--border)"}
                strokeWidth={1}
              />
              <text x={MARGIN.left - 8} y={yAt(t)} dy="0.32em" textAnchor="end" className="performance-axis-label">
                {(t * 100).toFixed(0)}%
              </text>
            </g>
          ))}

          {series.map((s) => (
            <path
              key={s.key}
              d={buildPathSegments(s.values, xAt, yAt)}
              fill="none"
              stroke={s.color}
              strokeWidth={2}
              strokeLinejoin="round"
              strokeLinecap="round"
            />
          ))}

          {activeIndex !== null && (
            <line
              x1={xAt(activeIndex)}
              x2={xAt(activeIndex)}
              y1={MARGIN.top}
              y2={CHART_HEIGHT - MARGIN.bottom}
              stroke="var(--text-faint)"
              strokeWidth={1}
            />
          )}

          {activeIndex !== null &&
            series.map((s) => {
              const v = s.values[activeIndex];
              if (v === null) return null;
              return (
                <circle key={s.key} cx={xAt(activeIndex)} cy={yAt(v)} r={4} fill={s.color} stroke="var(--panel-bg)" strokeWidth={2} />
              );
            })}

          <text x={MARGIN.left} y={CHART_HEIGHT - 6} className="performance-axis-label" textAnchor="start">
            {points[0].date}
          </text>
          <text x={width - MARGIN.right} y={CHART_HEIGHT - 6} className="performance-axis-label" textAnchor="end">
            {points[points.length - 1].date}
          </text>
        </svg>

        {activePoint && (
          <div className="performance-tooltip" style={{ left: tooltipLeft }}>
            <div className="performance-tooltip-date">{activePoint.date}</div>
            {series.map((s) => {
              const v = s.values[activeIndex as number];
              return (
                <div className="performance-tooltip-row" key={s.key}>
                  <span className="performance-line-key" style={{ background: s.color }} />
                  <span className="performance-tooltip-label">{s.label}</span>
                  <span className={`performance-tooltip-value ${v !== null && v >= 0 ? "accent-green" : "accent-red"}`}>
                    {formatPct(v)}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </section>
  );
}
