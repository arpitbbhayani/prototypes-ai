import React from 'react';
import { CheckCircle2, BookOpen, Code2 } from 'lucide-react';

export const KeyTakeaways: React.FC = () => {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-8 shadow-xl mb-12">
      <div className="flex items-center gap-2 text-cyan-400 text-xs font-semibold uppercase tracking-wider mb-2">
        <BookOpen className="w-4 h-4" /> Practical Engineer Cheat-Sheet
      </div>
      <h2 className="text-2xl font-bold text-white tracking-tight mb-4">
        Summary: Reciprocal Rank Fusion & The Role of <span className="font-mono text-cyan-300">k</span>
      </h2>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 flex gap-3">
          <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
          <div className="text-xs space-y-1">
            <span className="font-bold text-slate-200">Scale Invariant & Zero Calibration</span>
            <p className="text-slate-400 leading-relaxed">
              Unlike linear score combination (<span className="font-mono text-cyan-300">α·ScoreBM25 + (1-α)·ScoreVector</span>), RRF does not require min-max scaling, z-score normalization, or tuning across changing query distributions.
            </p>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 flex gap-3">
          <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
          <div className="text-xs space-y-1">
            <span className="font-bold text-slate-200">The Role of k: Rank Gap Smoother</span>
            <p className="text-slate-400 leading-relaxed">
              In reciprocal functions <span className="font-mono text-cyan-300">1/r</span>, the derivative is highest near <span className="font-mono text-cyan-300">r=1</span>. Adding <span className="font-mono text-cyan-300">k</span> shifts the evaluation origin to <span className="font-mono text-cyan-300">k+1</span>, converting a brutal hyperbolic cliff into a gradual, graceful decline.
            </p>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 flex gap-3">
          <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
          <div className="text-xs space-y-1">
            <span className="font-bold text-slate-200">Why k=60 Specifically?</span>
            <p className="text-slate-400 leading-relaxed">
              TREC experiments proved that <span className="font-mono text-cyan-300">k=60</span> hits the empirical sweet spot across collections: it values top-10 relevance without allowing a single retrieval system to overpower genuine multi-system consensus.
            </p>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 flex gap-3">
          <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
          <div className="text-xs space-y-1">
            <span className="font-bold text-slate-200">When to Change k?</span>
            <p className="text-slate-400 leading-relaxed">
              If your retrievers have very high precision and little noise, slightly lower <span className="font-mono text-cyan-300">k (e.g. 20-30)</span> rewards top hits more. If your retrievers produce noisy tails, higher <span className="font-mono text-cyan-300">k (e.g. 80-100)</span> prevents fluke hits from surfacing.
            </p>
          </div>
        </div>
      </div>

      {/* Production Python Code Snippet */}
      <div className="mt-6 p-4 rounded-xl bg-slate-950 border border-slate-800">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
            <Code2 className="w-4 h-4 text-cyan-400" />
            <span>Python Reference Implementation (Clean & Vectorized)</span>
          </div>
        </div>
        <pre className="text-xs font-mono text-slate-300 bg-slate-900/60 p-4 rounded-lg overflow-x-auto border border-slate-800/80 leading-relaxed">
{`def reciprocal_rank_fusion(ranked_lists: list[list[str]], k: int = 60) -> list[tuple[str, float]]:
    """
    Combines multiple ranked lists into a single consensus ranking.
    :param ranked_lists: List of rankings, e.g. [[docA, docB, ...], [docB, docC, ...]]
    :param k: Smoothing constant (default: 60)
    :return: List of (doc_id, score) sorted in descending order
    """
    scores = {}
    for r_list in ranked_lists:
        for rank, doc_id in enumerate(r_list, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + (1.0 / (k + rank))
            
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)`}
        </pre>
      </div>
    </div>
  );
};
