import React, { useState } from 'react';
import { Target, Users, AlertTriangle, ShieldCheck, Scale, Compass } from 'lucide-react';

export const SweetSpotWhy60: React.FC = () => {
  const [interactiveK, setInteractiveK] = useState<number>(60);

  // Scenario:
  // Doc A: Rank 1 in BM25, Rank 60 in Vector (One strong model, one skeptical model)
  // Doc B: Rank 5 in BM25, Rank 6 in Vector (Both models agree it is very strong)
  const calcScore = (r1: number, r2: number, k: number) => {
    return 1 / (k + r1) + 1 / (k + r2);
  };

  const scoreA = calcScore(1, 60, interactiveK);
  const scoreB = calcScore(5, 6, interactiveK);
  const winner = scoreA > scoreB ? 'Doc A (Solo Hero)' : 'Doc B (Consensus Choice)';

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-8 shadow-xl mb-8">
      <div className="flex items-center gap-2 text-indigo-400 text-xs font-semibold uppercase tracking-wider mb-2">
        <Target className="w-4 h-4" /> Theoretical & Empirical Justification
      </div>
      <h2 className="text-2xl font-bold text-white tracking-tight">
        Why <span className="font-mono text-cyan-300">k = 60</span> Works For Almost Every Search System
      </h2>
      <p className="text-slate-400 text-sm mt-1 max-w-3xl">
        In their 2009 landmark paper <em>"Reciprocal Rank Fusion Outperforms Condorcet and Individual Rank Learning Methods"</em>, Gordon Cormack, Charles Clarke, and Stefan Büttcher tested fusion parameters across TREC datasets. Here is why <span className="font-mono text-cyan-300">k = 60</span> became the canonical golden standard.
      </p>

      {/* 3 Core Conceptual Pillars */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-6">
        {/* Pillar 1 */}
        <div className="bg-slate-950/70 border border-slate-800/80 rounded-xl p-5 flex flex-col justify-between">
          <div>
            <div className="w-10 h-10 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 flex items-center justify-center mb-3">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <h3 className="text-base font-bold text-white mb-2">1. The "Dictator" Hazard (Small k)</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              If <span className="font-mono text-amber-300">k &lt; 10</span>, rank #1 gets massive score leverage (<span className="font-mono text-cyan-300">1/(1)=1.0</span> vs <span className="font-mono text-cyan-300">1/(5)=0.2</span>).
              A single noisy retriever (e.g. BM25 matching a random keyword) will unilaterally force an irrelevant document to #1, completely overruling high confidence from other retrievers.
            </p>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-800/80 text-[11px] text-red-400 font-medium">
            Risk: Keyword spoofing & outlier hallucinations dominate.
          </div>
        </div>

        {/* Pillar 2 */}
        <div className="bg-slate-950/70 border border-slate-800/80 rounded-xl p-5 flex flex-col justify-between">
          <div>
            <div className="w-10 h-10 rounded-lg bg-purple-500/10 border border-purple-500/20 text-purple-400 flex items-center justify-center mb-3">
              <Scale className="w-5 h-5" />
            </div>
            <h3 className="text-base font-bold text-white mb-2">2. The "Democracy" Trap (Large k)</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              If <span className="font-mono text-purple-300">k &gt; 200</span>, the difference between rank #1 (<span className="font-mono">1/201 ≈ 0.004975</span>) and rank #50 (<span className="font-mono">1/250 ≈ 0.004000</span>) shrinks to negligible fractions.
              RRF degenerates into pure "borda count" or document frequency: being retrieved at rank #80 by 2 models beats rank #1 by 1 model!
            </p>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-800/80 text-[11px] text-purple-400 font-medium">
            Risk: Top-1 precision is erased; mediocre tail documents flood top results.
          </div>
        </div>

        {/* Pillar 3 */}
        <div className="bg-slate-950/70 border border-cyan-500/30 rounded-xl p-5 bg-gradient-to-b from-cyan-950/20 to-transparent flex flex-col justify-between">
          <div>
            <div className="w-10 h-10 rounded-lg bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 flex items-center justify-center mb-3">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <h3 className="text-base font-bold text-white mb-2">3. The k = 60 Goldilocks Zone</h3>
            <p className="text-xs text-slate-300 leading-relaxed">
              At <span className="font-mono text-cyan-300 font-semibold">k = 60</span>:
              <br />• Rank #1 contributes <span className="font-mono text-cyan-300">0.01639</span>.
              <br />• Rank #10 contributes <span className="font-mono text-cyan-300">0.01428</span>.
              <br />• Rank #60 contributes <span className="font-mono text-cyan-300">0.00833</span> (exactly half of rank 1).
              <br />Two retrievers placing a document in top-10 (<span className="font-mono">~0.030</span>) easily beat one model placing it at rank #1 (<span className="font-mono">0.016</span>).
            </p>
          </div>
          <div className="mt-4 pt-3 border-t border-cyan-800/40 text-[11px] text-cyan-400 font-medium">
            Result: Consensus outvotes outlier noise, while strong precision is preserved.
          </div>
        </div>
      </div>

      {/* Interactive Demonstration: The Rogue vs Consensus Battle */}
      <div className="mt-8 p-6 bg-slate-950/80 rounded-xl border border-slate-800">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-5">
          <div>
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Compass className="w-4 h-4 text-cyan-400" /> Live Simulation: Rogue Outlier vs Strong Consensus
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Drag the <span className="font-mono text-cyan-400">k</span> slider to see how different values change who wins the #1 spot.
            </p>
          </div>

          <div className="flex items-center gap-3 bg-slate-900 px-4 py-2 rounded-xl border border-slate-800">
            <span className="text-xs text-slate-400 font-medium">Smoothing Constant:</span>
            <input
              type="range"
              min="1"
              max="200"
              value={interactiveK}
              onChange={(e) => setInteractiveK(Number(e.target.value))}
              className="w-36 accent-cyan-400 cursor-pointer"
            />
            <span className="text-xs font-mono font-bold text-cyan-400 w-12">k = {interactiveK}</span>
          </div>
        </div>

        {/* The Head-to-Head Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          {/* Doc A */}
          <div
            className={`p-4 rounded-xl border transition-all ${
              winner.includes('Doc A')
                ? 'bg-amber-950/20 border-amber-500/50 shadow-lg shadow-amber-950/20'
                : 'bg-slate-900/40 border-slate-800/60 opacity-80'
            }`}
          >
            <div className="flex justify-between items-center mb-2">
              <span className="font-bold text-sm text-amber-300">Document A (The Rogue Outlier)</span>
              {winner.includes('Doc A') && (
                <span className="text-[10px] uppercase font-bold bg-amber-500/20 text-amber-300 px-2 py-0.5 rounded-full border border-amber-500/40">
                  Winner 🏆
                </span>
              )}
            </div>
            <div className="text-xs text-slate-400 space-y-1 font-mono">
              <div>BM25 Rank: <span className="text-white font-bold">#1</span> (1 / ({interactiveK} + 1) = {(1 / (interactiveK + 1)).toFixed(5)})</div>
              <div>Vector Rank: <span className="text-slate-400">#60</span> (1 / ({interactiveK} + 60) = {(1 / (interactiveK + 60)).toFixed(5)})</div>
              <div className="pt-2 border-t border-slate-800 text-slate-200 font-bold flex justify-between">
                <span>RRF Score:</span>
                <span className="text-amber-300 text-sm">{scoreA.toFixed(5)}</span>
              </div>
            </div>
          </div>

          {/* Doc B */}
          <div
            className={`p-4 rounded-xl border transition-all ${
              winner.includes('Doc B')
                ? 'bg-cyan-950/20 border-cyan-500/50 shadow-lg shadow-cyan-950/20'
                : 'bg-slate-900/40 border-slate-800/60 opacity-80'
            }`}
          >
            <div className="flex justify-between items-center mb-2">
              <span className="font-bold text-sm text-cyan-300">Document B (The Strong Consensus)</span>
              {winner.includes('Doc B') && (
                <span className="text-[10px] uppercase font-bold bg-cyan-500/20 text-cyan-300 px-2 py-0.5 rounded-full border border-cyan-500/40">
                  Winner 🏆
                </span>
              )}
            </div>
            <div className="text-xs text-slate-400 space-y-1 font-mono">
              <div>BM25 Rank: <span className="text-white font-bold">#5</span> (1 / ({interactiveK} + 5) = {(1 / (interactiveK + 5)).toFixed(5)})</div>
              <div>Vector Rank: <span className="text-white font-bold">#6</span> (1 / ({interactiveK} + 6) = {(1 / (interactiveK + 6)).toFixed(5)})</div>
              <div className="pt-2 border-t border-slate-800 text-slate-200 font-bold flex justify-between">
                <span>RRF Score:</span>
                <span className="text-cyan-300 text-sm">{scoreB.toFixed(5)}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Verdict Explanation Box */}
        <div className="p-3.5 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-300 flex items-start gap-3">
          <Users className="w-5 h-5 text-indigo-400 shrink-0 mt-0.5" />
          <div>
            <div className="font-semibold text-white mb-0.5">
              Current Verdict at k = {interactiveK}: <span className={winner.includes('Doc B') ? 'text-cyan-300 font-bold' : 'text-amber-300 font-bold'}>{winner}</span>
            </div>
            <p className="text-slate-400 leading-relaxed">
              {interactiveK <= 15 ? (
                <span>
                  At low <span className="font-mono text-amber-300">k={interactiveK}</span>, the single BM25 #1 rank overwhelmingly dictates the outcome, completely brushing aside the fact that Vector search ranked it way down at #60.
                </span>
              ) : (
                <span>
                  With <span className="font-mono text-cyan-300">k={interactiveK}</span>, the mutual agreement across both models (#5 and #6) comfortably outscores the solitary #1 outlier. This is the exact smoothing defense mechanism that makes RRF robust against retriever failures!
                </span>
              )}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
