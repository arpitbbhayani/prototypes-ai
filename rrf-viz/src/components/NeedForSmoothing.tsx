import React, { useState } from 'react';
import { AlertOctagon, ShieldAlert, CheckCircle2, Split } from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
} from 'recharts';

export const NeedForSmoothing: React.FC = () => {
  const [selectedExample, setSelectedExample] = useState<'cliff' | 'hallucination' | 'consensus'>('cliff');

  // Cliff data: Difference in score between consecutive ranks
  const cliffDataNoSmooth = [
    { rank: 'Rank 1', score: 1.0, drop: 0, label: '1/1 = 1.000' },
    { rank: 'Rank 2', score: 0.5, drop: 50, label: '1/2 = 0.500 (-50%)' },
    { rank: 'Rank 3', score: 0.333, drop: 33.3, label: '1/3 = 0.333 (-33%)' },
    { rank: 'Rank 4', score: 0.25, drop: 25, label: '1/4 = 0.250 (-25%)' },
    { rank: 'Rank 5', score: 0.2, drop: 20, label: '1/5 = 0.200 (-20%)' },
    { rank: 'Rank 10', score: 0.1, drop: 10, label: '1/10 = 0.100' },
    { rank: 'Rank 20', score: 0.05, drop: 5, label: '1/20 = 0.050' },
  ];

  const cliffDataSmoothed = [
    { rank: 'Rank 1', score: 0.01639, relative: 100, label: '1/61 = 0.0164 (100%)' },
    { rank: 'Rank 2', score: 0.01613, relative: 98.4, label: '1/62 = 0.0161 (98.4%)' },
    { rank: 'Rank 3', score: 0.01587, relative: 96.8, label: '1/63 = 0.0159 (96.8%)' },
    { rank: 'Rank 4', score: 0.01563, relative: 95.3, label: '1/64 = 0.0156 (95.3%)' },
    { rank: 'Rank 5', score: 0.01538, relative: 93.8, label: '1/65 = 0.0154 (93.8%)' },
    { rank: 'Rank 10', score: 0.01428, relative: 87.1, label: '1/70 = 0.0143 (87.1%)' },
    { rank: 'Rank 20', score: 0.01250, relative: 76.3, label: '1/80 = 0.0125 (76.3%)' },
  ];

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-8 shadow-xl mb-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-slate-800">
        <div>
          <div className="inline-flex items-center gap-2 text-rose-400 text-xs font-semibold uppercase tracking-wider mb-1">
            <AlertOctagon className="w-4 h-4" /> Fundamental Problem Statement
          </div>
          <h2 className="text-2xl font-bold text-white tracking-tight">
            The Need For Smoothing: Why Raw Reciprocal Rank Fails
          </h2>
          <p className="text-slate-400 text-sm mt-1 max-w-3xl">
            Why can't we just use the naive formula <span className="font-mono text-rose-400 font-bold">1 / r</span>?
            Because the raw harmonic sequence creates a <strong>brutal cliff effect</strong> that breaks ranker fairness and makes search systems vulnerable to single-ranker errors.
          </p>
        </div>

        {/* Tab switcher */}
        <div className="flex items-center gap-1.5 bg-slate-950 p-1.5 rounded-xl border border-slate-800 text-xs">
          <button
            onClick={() => setSelectedExample('cliff')}
            className={`px-3 py-1.5 rounded-lg font-medium transition-all ${
              selectedExample === 'cliff'
                ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40 font-semibold'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            1. The Hyperbolic Cliff
          </button>
          <button
            onClick={() => setSelectedExample('hallucination')}
            className={`px-3 py-1.5 rounded-lg font-medium transition-all ${
              selectedExample === 'hallucination'
                ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40 font-semibold'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            2. Hallucination Dictator
          </button>
          <button
            onClick={() => setSelectedExample('consensus')}
            className={`px-3 py-1.5 rounded-lg font-medium transition-all ${
              selectedExample === 'consensus'
                ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40 font-semibold'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            3. Consensus Breakdown
          </button>
        </div>
      </div>

      {/* Visualizer Body based on selected tab */}
      {selectedExample === 'cliff' && (
        <div className="mt-6 space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Without Smoothing */}
            <div className="bg-slate-950/70 border border-rose-900/40 rounded-xl p-5 relative overflow-hidden">
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm font-bold text-rose-400 flex items-center gap-1.5">
                  <ShieldAlert className="w-4 h-4" /> Without Smoothing: Score = 1 / r
                </span>
                <span className="text-[11px] font-mono bg-rose-950/80 text-rose-300 border border-rose-800/60 px-2 py-0.5 rounded">
                  Brutal Cliff
                </span>
              </div>
              <p className="text-xs text-slate-400 mb-4">
                Rank 1 gets <span className="font-mono text-white font-bold">1.000</span>. Rank 2 drops immediately to <span className="font-mono text-rose-300 font-bold">0.500</span>. That single step loses <span className="text-rose-400 font-bold">50%</span> of the maximum possible score!
              </p>

              {/* Chart */}
              <div className="h-56 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={cliffDataNoSmooth} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <XAxis dataKey="rank" stroke="#64748b" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                    <YAxis stroke="#64748b" tick={{ fill: '#94a3b8', fontSize: 11 }} domain={[0, 1.0]} />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#090d16', borderColor: '#334155', borderRadius: '0.5rem', fontSize: '11px' }}
                      formatter={(val: any) => [val, 'Raw Score']}
                    />
                    <Bar dataKey="score" radius={[4, 4, 0, 0]}>
                      {cliffDataNoSmooth.map((_, index) => (
                        <Cell key={`cell-${index}`} fill={index === 0 ? '#f43f5e' : index === 1 ? '#fb7185' : '#fda4af'} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-3 text-center text-xs font-mono text-rose-400 font-bold bg-rose-950/30 py-1.5 rounded border border-rose-900/30">
                Δ(Rank 1 → Rank 2) = -0.500 (Cliff Drop: 50.0%)
              </div>
            </div>

            {/* With Smoothing */}
            <div className="bg-slate-950/70 border border-cyan-900/40 rounded-xl p-5 relative overflow-hidden">
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm font-bold text-cyan-400 flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4" /> With Smoothing: Score = 1 / (60 + r)
                </span>
                <span className="text-[11px] font-mono bg-cyan-950/80 text-cyan-300 border border-cyan-800/60 px-2 py-0.5 rounded">
                  Graceful Decay
                </span>
              </div>
              <p className="text-xs text-slate-400 mb-4">
                Rank 1 is <span className="font-mono text-white font-bold">100%</span>. Rank 2 retains <span className="font-mono text-cyan-300 font-bold">98.4%</span> of Rank 1's score. Even Rank 10 still preserves <span className="text-cyan-400 font-bold">87.1%</span> value!
              </p>

              {/* Chart */}
              <div className="h-56 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={cliffDataSmoothed} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <XAxis dataKey="rank" stroke="#64748b" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                    <YAxis stroke="#64748b" tick={{ fill: '#94a3b8', fontSize: 11 }} domain={[0, 100]} unit="%" />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#090d16', borderColor: '#334155', borderRadius: '0.5rem', fontSize: '11px' }}
                      formatter={(val: any) => [`${val}%`, 'Relative to #1']}
                    />
                    <Bar dataKey="relative" radius={[4, 4, 0, 0]}>
                      {cliffDataSmoothed.map((_, index) => (
                        <Cell key={`cell-smooth-${index}`} fill={index === 0 ? '#06b6d4' : '#22d3ee'} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-3 text-center text-xs font-mono text-cyan-400 font-bold bg-cyan-950/30 py-1.5 rounded border border-cyan-900/30">
                Δ(Rank 1 → Rank 2) = -0.00026 (Smooth Drop: 1.6%)
              </div>
            </div>
          </div>

          {/* Core Takeaway Box */}
          <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 flex items-start gap-3">
            <Split className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
            <div className="text-xs text-slate-300 space-y-1">
              <span className="font-bold text-white">Mathematical Reality of the Hyperbola:</span>
              <p className="text-slate-400 leading-relaxed">
                The derivative of <span className="font-mono text-cyan-300">f(x) = 1/x</span> is <span className="font-mono text-rose-400">-1/x²</span>. At <span className="font-mono">x=1</span>, the slope is <span className="font-mono font-bold text-rose-400">-1.0</span> (a steep plunge). By substituting <span className="font-mono text-cyan-300">x = 60 + r</span>, the slope at <span className="font-mono">r=1</span> becomes <span className="font-mono text-cyan-300">-1/(61)² ≈ -0.000268</span>. Smoothing literally flattens the violent vertical drop into a usable ranking scale.
              </p>
            </div>
          </div>
        </div>
      )}

      {selectedExample === 'hallucination' && (
        <div className="mt-6 space-y-6">
          <div className="p-4 bg-rose-950/20 border border-rose-900/50 rounded-xl">
            <h3 className="text-sm font-bold text-rose-400 mb-1 flex items-center gap-1.5">
              <ShieldAlert className="w-4 h-4" /> The "Hallucination Dictator" Problem
            </h3>
            <p className="text-xs text-slate-300 leading-relaxed">
              Suppose a user queries <span className="text-amber-300 italic">"PostgreSQL indexing performance"</span>.
              A spam blog with high keyword stuffing achieves BM25 Rank #1, but dense vector embeddings correctly identify it as spam and place it at Rank #100.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Left: Unsmoothed */}
            <div className="bg-slate-950/70 border border-rose-900/40 rounded-xl p-5">
              <span className="text-xs font-bold text-rose-400 uppercase tracking-wider block mb-3">
                Naive Fusion (k = 0, No Smoothing)
              </span>
              <div className="space-y-3 font-mono text-xs">
                <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800">
                  <div className="font-sans font-bold text-slate-200">Doc 1: Keyword Spam Document</div>
                  <div className="text-slate-400 mt-1">BM25 Rank #1, Vector Rank #100</div>
                  <div className="text-rose-400 font-bold mt-1">
                    Score = (1 / 1) + (1 / 100) = 1.000 + 0.010 = <span className="text-sm">1.010</span>
                  </div>
                </div>

                <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800">
                  <div className="font-sans font-bold text-slate-200">Doc 2: High-Quality Postgres Guide</div>
                  <div className="text-slate-400 mt-1">BM25 Rank #2, Vector Rank #2</div>
                  <div className="text-slate-400 font-bold mt-1">
                    Score = (1 / 2) + (1 / 2) = 0.500 + 0.500 = <span className="text-sm text-slate-300">1.000</span>
                  </div>
                </div>
              </div>
              <div className="mt-4 p-2.5 rounded bg-rose-950/50 border border-rose-900/60 text-xs text-rose-300 font-semibold">
                🚨 Failure: The keyword spam doc wins Rank #1 over the genuine consensus document!
              </div>
            </div>

            {/* Right: Smoothed */}
            <div className="bg-slate-950/70 border border-cyan-900/40 rounded-xl p-5">
              <span className="text-xs font-bold text-cyan-400 uppercase tracking-wider block mb-3">
                Smoothed Fusion (k = 60)
              </span>
              <div className="space-y-3 font-mono text-xs">
                <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800">
                  <div className="font-sans font-bold text-slate-200">Doc 1: Keyword Spam Document</div>
                  <div className="text-slate-400 mt-1">BM25 Rank #1, Vector Rank #100</div>
                  <div className="text-slate-400 font-bold mt-1">
                    Score = (1/61) + (1/160) = 0.01639 + 0.00625 = <span className="text-sm text-slate-300">0.02264</span>
                  </div>
                </div>

                <div className="p-3 rounded-lg bg-cyan-950/30 border border-cyan-800/40">
                  <div className="font-sans font-bold text-cyan-200">Doc 2: High-Quality Postgres Guide (WINNER 🏆)</div>
                  <div className="text-slate-400 mt-1">BM25 Rank #2, Vector Rank #2</div>
                  <div className="text-cyan-300 font-bold mt-1">
                    Score = (1/62) + (1/62) = 0.01613 + 0.01613 = <span className="text-sm">0.03226</span>
                  </div>
                </div>
              </div>
              <div className="mt-4 p-2.5 rounded bg-cyan-950/50 border border-cyan-900/60 text-xs text-cyan-300 font-semibold">
                ✅ Fixed: The genuine consensus document wins easily (+42.5% higher score)!
              </div>
            </div>
          </div>
        </div>
      )}

      {selectedExample === 'consensus' && (
        <div className="mt-6 space-y-6">
          <div className="p-4 bg-slate-950 rounded-xl border border-slate-800">
            <h3 className="text-sm font-bold text-white mb-1 flex items-center gap-1.5">
              <Split className="w-4 h-4 text-indigo-400" /> Multi-System Agreement (The Consensus Test)
            </h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              In an ensemble with 3 models (e.g., BM25 + Dense + ColBERT/SPLADE), what should happen if all 3 models place a document in their top 5, while a single model places a completely different document at #1?
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="p-5 rounded-xl bg-slate-950/80 border border-slate-800">
              <span className="text-xs font-mono font-bold text-amber-400 uppercase tracking-wider block mb-2">
                Document X (One #1, Missing from others)
              </span>
              <ul className="text-xs font-mono text-slate-300 space-y-1">
                <li>BM25 Rank: <strong className="text-white">#1</strong></li>
                <li>Dense Vector Rank: <strong className="text-slate-500">Not in top 100</strong></li>
                <li>SPLADE Rank: <strong className="text-slate-500">Not in top 100</strong></li>
              </ul>
              <div className="mt-4 pt-3 border-t border-slate-800 font-mono text-xs space-y-1">
                <div>At k=0: Score = <span className="text-rose-400 font-bold">1.000</span></div>
                <div>At k=60: Score = <span className="text-cyan-400 font-bold">0.01639</span></div>
              </div>
            </div>

            <div className="p-5 rounded-xl bg-slate-950/80 border border-slate-800">
              <span className="text-xs font-mono font-bold text-cyan-400 uppercase tracking-wider block mb-2">
                Document Y (Ranks #4, #4, #5 across all 3)
              </span>
              <ul className="text-xs font-mono text-slate-300 space-y-1">
                <li>BM25 Rank: <strong className="text-white">#4</strong></li>
                <li>Dense Vector Rank: <strong className="text-white">#4</strong></li>
                <li>SPLADE Rank: <strong className="text-white">#5</strong></li>
              </ul>
              <div className="mt-4 pt-3 border-t border-slate-800 font-mono text-xs space-y-1">
                <div>At k=0: 1/4 + 1/4 + 1/5 = <span className="text-rose-400 font-bold">0.700 (LOSES!)</span></div>
                <div>At k=60: 1/64 + 1/64 + 1/65 = <span className="text-cyan-400 font-bold">0.04663 (WINS by 2.8x!)</span></div>
              </div>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-indigo-950/20 border border-indigo-800/40 text-xs text-indigo-200">
            <strong>Key Insight:</strong> Without smoothing, a document backed unanimously by 3 independent AI models at ranks 4 & 5 loses to a document with 1 lucky hit in a single retriever. Smoothing restores democratic wisdom of the crowd.
          </div>
        </div>
      )}
    </div>
  );
};
