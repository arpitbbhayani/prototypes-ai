import React, { useState } from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
} from 'recharts';
import { TrendingDown, Sliders, Zap } from 'lucide-react';

interface CurveSmoothingChartProps {
  activeK: number;
  setActiveK: (k: number) => void;
}

export const CurveSmoothingChart: React.FC<CurveSmoothingChartProps> = ({
  activeK,
  setActiveK,
}) => {
  const [maxRank, setMaxRank] = useState<number>(30);
  const [metricMode, setMetricMode] = useState<'normalized' | 'raw' | 'penalty'>('normalized');

  // Generate chart data up to maxRank
  const kOptions = [0, 1, 10, 60, 150];

  const data = Array.from({ length: maxRank }, (_, i) => {
    const rank = i + 1;
    const row: Record<string, number> = { rank };

    kOptions.forEach((k) => {
      const rawScore = 1 / (k + rank);
      const topScore = 1 / (k + 1);
      const normalizedScore = (rawScore / topScore) * 100; // Percentage of Rank 1 score
      const dropFromTop = (1 - rawScore / topScore) * 100; // Drop % from Rank 1

      if (metricMode === 'normalized') {
        row[`k_${k}`] = Number(normalizedScore.toFixed(2));
      } else if (metricMode === 'raw') {
        row[`k_${k}`] = Number(rawScore.toFixed(5));
      } else {
        row[`k_${k}`] = Number(dropFromTop.toFixed(2));
      }
    });

    // Custom slider activeK value if not in standard list
    if (!kOptions.includes(activeK)) {
      const rawScore = 1 / (activeK + rank);
      const topScore = 1 / (activeK + 1);
      const normalizedScore = (rawScore / topScore) * 100;
      const dropFromTop = (1 - rawScore / topScore) * 100;
      if (metricMode === 'normalized') {
        row[`k_active`] = Number(normalizedScore.toFixed(2));
      } else if (metricMode === 'raw') {
        row[`k_active`] = Number(rawScore.toFixed(5));
      } else {
        row[`k_active`] = Number(dropFromTop.toFixed(2));
      }
    }

    return row;
  });

  const getKColor = (k: number) => {
    switch (k) {
      case 0:
        return '#ef4444'; // Red (harsh drop)
      case 1:
        return '#f97316'; // Orange
      case 10:
        return '#eab308'; // Yellow
      case 60:
        return '#06b6d4'; // Cyan (the hero)
      case 150:
        return '#a855f7'; // Purple (too flat)
      default:
        return '#10b981'; // Green for custom
    }
  };

  // Helper stats for table comparison
  const statsTable = [0, 1, 10, 60, 100, 200].map((k) => {
    const s1 = 1 / (k + 1);
    const s2 = 1 / (k + 2);
    const s5 = 1 / (k + 5);
    const s10 = 1 / (k + 10);
    const s20 = 1 / (k + 20);

    const dropRank2 = ((1 - s2 / s1) * 100).toFixed(1);
    const dropRank10 = ((1 - s10 / s1) * 100).toFixed(1);
    const ratio1to10 = (s1 / s10).toFixed(2);
    const ratio5to20 = (s5 / s20).toFixed(2);

    return {
      k,
      s1: s1.toFixed(4),
      s2: s2.toFixed(4),
      dropRank2: `${dropRank2}%`,
      dropRank10: `${dropRank10}%`,
      ratio1to10: `${ratio1to10}x`,
      ratio5to20: `${ratio5to20}x`,
      isHero: k === 60,
    };
  });

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-8 shadow-xl mb-8">
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 pb-6 border-b border-slate-800">
        <div>
          <div className="inline-flex items-center gap-2 text-cyan-400 text-xs font-semibold uppercase tracking-wider mb-1">
            <TrendingDown className="w-4 h-4" /> The Smoothing Effect Visualized
          </div>
          <h2 className="text-2xl font-bold text-white tracking-tight">
            How Adding <span className="font-mono text-cyan-300">k</span> "Smoothens the Gap"
          </h2>
          <p className="text-slate-400 text-sm mt-1 max-w-2xl">
            Without smoothing (<span className="font-mono text-red-400">k=0</span>), finishing #2 drops your score by an immediate 50%. With <span className="font-mono text-cyan-300">k=60</span>, finishing #2 retains 98.4% of #1's score.
          </p>
        </div>

        {/* View mode toggle buttons */}
        <div className="flex items-center gap-1 bg-slate-950 p-1.5 rounded-xl border border-slate-800 text-xs">
          <button
            onClick={() => setMetricMode('normalized')}
            className={`px-3 py-1.5 rounded-lg font-medium transition-all ${
              metricMode === 'normalized'
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 font-semibold'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Relative Value (% of #1)
          </button>
          <button
            onClick={() => setMetricMode('penalty')}
            className={`px-3 py-1.5 rounded-lg font-medium transition-all ${
              metricMode === 'penalty'
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 font-semibold'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Penalty Drop (% Lost)
          </button>
          <button
            onClick={() => setMetricMode('raw')}
            className={`px-3 py-1.5 rounded-lg font-medium transition-all ${
              metricMode === 'raw'
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 font-semibold'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Raw 1/(k+r) Score
          </button>
        </div>
      </div>

      {/* Chart Section */}
      <div className="mt-6">
        <div className="h-80 sm:h-96 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 10, right: 30, left: 10, bottom: 25 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis
                dataKey="rank"
                stroke="#64748b"
                tick={{ fill: '#94a3b8', fontSize: 12 }}
                label={{
                  value: 'Document Rank (r) →',
                  position: 'insideBottom',
                  offset: -15,
                  fill: '#94a3b8',
                  fontSize: 13,
                }}
              />
              <YAxis
                stroke="#64748b"
                tick={{ fill: '#94a3b8', fontSize: 12 }}
                domain={metricMode === 'raw' ? [0, 'auto'] : [0, 100]}
                tickFormatter={(val) =>
                  metricMode === 'raw' ? val.toFixed(3) : `${val}%`
                }
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#090d16',
                  borderColor: '#334155',
                  borderRadius: '0.75rem',
                  color: '#e2e8f0',
                  fontSize: '12px',
                  boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.5)',
                }}
                formatter={(value: any, name: any) => {
                  const labelMap: Record<string, string> = {
                    k_0: 'k = 0 (No smoothing - Pure 1/r)',
                    k_1: 'k = 1',
                    k_10: 'k = 10',
                    k_60: 'k = 60 (Industry Standard)',
                    k_150: 'k = 150 (Heavily flattened)',
                    k_active: `Active k = ${activeK}`,
                  };
                  const suffix = metricMode === 'raw' ? '' : '%';
                  return [`${value}${suffix}`, labelMap[String(name)] || String(name)];
                }}
                labelFormatter={(label) => `Document Rank #${label}`}
              />
              <Legend
                verticalAlign="top"
                height={36}
                wrapperStyle={{ paddingBottom: '10px', fontSize: '12px' }}
                formatter={(val) => {
                  const map: Record<string, string> = {
                    k_0: 'k = 0 (Steep dropoff)',
                    k_1: 'k = 1',
                    k_10: 'k = 10',
                    k_60: '★ k = 60 (Standard)',
                    k_150: 'k = 150',
                    k_active: `Custom k = ${activeK}`,
                  };
                  return <span className="font-mono font-medium text-slate-300">{map[val] || val}</span>;
                }}
              />

              {kOptions.map((kVal) => (
                <Line
                  key={kVal}
                  type="monotone"
                  dataKey={`k_${kVal}`}
                  stroke={getKColor(kVal)}
                  strokeWidth={kVal === 60 ? 3.5 : 2}
                  strokeDasharray={kVal === 0 ? '4 4' : undefined}
                  dot={false}
                  activeDot={{ r: 5, strokeWidth: 2 }}
                />
              ))}

              {!kOptions.includes(activeK) && (
                <Line
                  type="monotone"
                  dataKey="k_active"
                  stroke="#10b981"
                  strokeWidth={3}
                  dot={false}
                />
              )}
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Dynamic Controls Bar */}
        <div className="mt-4 flex flex-wrap items-center justify-between gap-4 p-4 bg-slate-950/60 rounded-xl border border-slate-800">
          <div className="flex items-center gap-3">
            <Sliders className="w-4 h-4 text-cyan-400" />
            <span className="text-xs font-semibold text-slate-300">Max Rank Depth:</span>
            <input
              type="range"
              min="10"
              max="100"
              step="5"
              value={maxRank}
              onChange={(e) => setMaxRank(Number(e.target.value))}
              className="w-32 accent-cyan-500 cursor-pointer"
            />
            <span className="text-xs font-mono text-cyan-400 font-bold">Top {maxRank}</span>
          </div>

          <div className="flex items-center gap-3">
            <span className="text-xs font-semibold text-slate-300">Test Custom k:</span>
            <input
              type="range"
              min="0"
              max="200"
              step="1"
              value={activeK}
              onChange={(e) => setActiveK(Number(e.target.value))}
              className="w-40 accent-cyan-500 cursor-pointer"
            />
            <span className="text-xs font-mono text-cyan-400 font-bold bg-cyan-950/50 px-2 py-0.5 rounded border border-cyan-800/40">
              k = {activeK}
            </span>
          </div>
        </div>
      </div>

      {/* Quantitative Matrix: The Concrete Numbers */}
      <div className="mt-8">
        <h3 className="text-base font-semibold text-white flex items-center gap-2 mb-3">
          <Zap className="w-4 h-4 text-amber-400" /> Numerical Proof: The Immediate Dropoff Gap
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300 border-collapse">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-950/80 text-slate-400 uppercase tracking-wider font-mono">
                <th className="py-2.5 px-3">k value</th>
                <th className="py-2.5 px-3">Score Rank #1</th>
                <th className="py-2.5 px-3">Score Rank #2</th>
                <th className="py-2.5 px-3">#1 → #2 Drop</th>
                <th className="py-2.5 px-3">#1 → #10 Drop</th>
                <th className="py-2.5 px-3">Ratio (Rank #1 / #10)</th>
                <th className="py-2.5 px-3">Ratio (Rank #5 / #20)</th>
                <th className="py-2.5 px-3">Practical Behavior</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {statsTable.map((row) => (
                <tr
                  key={row.k}
                  className={`hover:bg-slate-800/30 transition-colors ${
                    row.isHero ? 'bg-cyan-950/30 text-cyan-200 border-l-2 border-cyan-400' : ''
                  }`}
                >
                  <td className="py-2.5 px-3 font-bold flex items-center gap-1.5">
                    {row.isHero && <span className="text-cyan-400">★</span>}
                    k = {row.k}
                  </td>
                  <td className="py-2.5 px-3 text-slate-400">{row.s1}</td>
                  <td className="py-2.5 px-3 text-slate-400">{row.s2}</td>
                  <td className={`py-2.5 px-3 font-semibold ${row.k === 0 ? 'text-red-400' : 'text-slate-300'}`}>
                    {row.dropRank2}
                  </td>
                  <td className={`py-2.5 px-3 font-semibold ${row.k === 0 ? 'text-red-400' : 'text-slate-300'}`}>
                    {row.dropRank10}
                  </td>
                  <td className="py-2.5 px-3 text-amber-300 font-bold">{row.ratio1to10}</td>
                  <td className="py-2.5 px-3 text-indigo-300 font-bold">{row.ratio5to20}</td>
                  <td className="py-2.5 px-3 font-sans text-slate-400 text-xs">
                    {row.k === 0 && 'Catastrophic cliff. Missing #1 destroys document chance.'}
                    {row.k === 1 && 'Very steep cliff. Rank 1 dominates completely.'}
                    {row.k === 10 && 'Moderate smoothing, but still biased heavily towards #1.'}
                    {row.k === 60 && 'Sweet spot: 1.6% drop between #1 & #2, 13% drop across top 10.'}
                    {row.k === 100 && 'Higher tolerance, useful when retrievers have large noise.'}
                    {row.k === 200 && 'Approaching uniform counting; rank differences washed out.'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
