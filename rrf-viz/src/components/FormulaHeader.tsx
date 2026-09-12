import React from 'react';
import { Sparkles, Layers } from 'lucide-react';

interface FormulaHeaderProps {
  k: number;
  setK: (k: number) => void;
}

export const FormulaHeader: React.FC<FormulaHeaderProps> = ({ k, setK }) => {
  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 sm:p-8 backdrop-blur-xl shadow-2xl relative overflow-hidden mb-8">
      <div className="absolute -right-20 -top-20 w-80 h-80 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute -left-20 -bottom-20 w-80 h-80 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />

      <div className="relative z-10 flex flex-col md:flex-row items-start md:items-center justify-between gap-6 pb-6 border-b border-slate-800/80">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 text-xs font-semibold uppercase tracking-wider mb-3">
            <Sparkles className="w-3.5 h-3.5" /> Interactive Guide & Sandbox
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
            Reciprocal Rank Fusion <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-indigo-400">(RRF)</span>
          </h1>
          <p className="text-slate-400 mt-2 text-base max-w-2xl">
            Why does <span className="font-mono text-cyan-300 font-bold">k = 60</span> dominate hybrid search (BM25 + Vector)? How does this simple constant smooth the ranking penalty and balance consensus?
          </p>
        </div>

        {/* Quick K-Selector Pill */}
        <div className="flex flex-col items-end bg-slate-950/80 p-3 rounded-xl border border-slate-800 w-full md:w-auto">
          <span className="text-xs font-medium text-slate-400 mb-1 flex items-center gap-1.5">
            Global Smoothing Constant <span className="font-mono text-cyan-400 font-bold text-sm">k = {k}</span>
          </span>
          <div className="flex items-center gap-1.5 flex-wrap">
            {[0, 1, 10, 60, 100, 200].map((val) => (
              <button
                key={val}
                onClick={() => setK(val)}
                className={`px-2.5 py-1 rounded-md text-xs font-mono font-semibold transition-all ${
                  k === val
                    ? 'bg-cyan-500 text-slate-950 shadow-md shadow-cyan-500/30'
                    : 'bg-slate-800/60 hover:bg-slate-800 text-slate-300'
                }`}
              >
                {val === 60 ? 'k=60 (default)' : `k=${val}`}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Formula Component Breakdown */}
      <div className="mt-6 grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
        {/* The Math display */}
        <div className="lg:col-span-6 bg-slate-950/60 p-5 rounded-xl border border-slate-800/80 font-mono text-center flex flex-col justify-center">
          <div className="text-xs text-slate-500 uppercase tracking-wider mb-2 flex items-center justify-center gap-1">
            <Layers className="w-3.5 h-3.5" /> Cormack, Clarke & Büttcher (SIGIR 2009)
          </div>
          <div className="text-2xl sm:text-3xl text-slate-200 font-medium tracking-wide py-2">
            <span className="text-indigo-400 font-bold">RRF_Score</span>
            <span className="text-slate-500">(d)</span> ={' '}
            <span className="text-slate-400">∑</span>
            <span className="text-xs text-slate-500 mx-1">m ∈ M</span>
            <span className="inline-flex flex-col text-center align-middle mx-2 text-xl sm:text-2xl">
              <span className="border-b border-slate-700 pb-0.5 text-cyan-300 font-bold">1</span>
              <span className="pt-0.5">
                <span className="text-amber-400 font-bold">{k}</span>
                <span className="text-slate-500"> + </span>
                <span className="text-purple-400 font-bold">r<sub className="text-xs">m</sub>(d)</span>
              </span>
            </span>
          </div>
          <div className="text-xs text-slate-400 mt-2">
            Sum of reciprocals over each retrieval model <span className="text-slate-300">m</span> (e.g. BM25, Dense Vector, SPLADE).
          </div>
        </div>

        {/* Intuition Callouts */}
        <div className="lg:col-span-6 grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="p-3.5 rounded-xl bg-slate-800/40 border border-slate-800">
            <div className="flex items-center gap-1.5 text-cyan-400 text-xs font-bold mb-1">
              <span className="w-2 h-2 rounded-full bg-cyan-400"></span>
              Rank, Not Score
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Vector cosines (0.7-0.9) & BM25 log-odds (0-35) have completely incompatible scales. RRF operates purely on ordinal ranks <span className="font-mono text-purple-300">r</span>, eliminating calibration mismatch.
            </p>
          </div>

          <div className="p-3.5 rounded-xl bg-slate-800/40 border border-slate-800">
            <div className="flex items-center gap-1.5 text-amber-400 text-xs font-bold mb-1">
              <span className="w-2 h-2 rounded-full bg-amber-400"></span>
              The Smoothing <span className="font-mono">k</span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Without <span className="font-mono text-amber-300">k</span>, rank 1 gets 1.0 and rank 2 gets 0.5 (a catastrophic 50% drop). <span className="font-mono text-amber-300">k</span> prevents rank 1 from monopolizing the fused score.
            </p>
          </div>

          <div className="p-3.5 rounded-xl bg-slate-800/40 border border-slate-800">
            <div className="flex items-center gap-1.5 text-indigo-400 text-xs font-bold mb-1">
              <span className="w-2 h-2 rounded-full bg-indigo-400"></span>
              Democratic Consensus
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Allows agreement among multiple rankers (e.g. #3 + #4) to safely beat a single model's isolated #1 fluke hallucination.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
