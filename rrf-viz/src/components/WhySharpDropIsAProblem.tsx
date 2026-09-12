import { useState } from 'react';
import { HelpCircle, AlertTriangle, ArrowRight, Activity, Users, Scale } from 'lucide-react';

export const WhySharpDropIsAProblem: React.FC = () => {
  const [activeCard, setActiveCard] = useState<number>(0);

  const problems = [
    {
      title: '1. IR Noise: The difference between Rank #1 and #2 is mostly luck',
      badge: 'Uncertainty & Noisy Scores',
      color: 'amber',
      icon: Activity,
      summary: 'In real information retrieval, the difference between the #1 hit and the #2 hit is often statistically insignificant (e.g. cosine 0.891 vs 0.889).',
      detail: (
        <div className="space-y-2 text-xs">
          <p className="text-slate-300">
            Retriever scores are inherently noisy approximations. Document length normalization quirks, minor BM25 term frequency differences, or embedding floating-point drift easily swap Rank #1 and Rank #2.
          </p>
          <div className="p-3 bg-slate-900 rounded-lg border border-slate-800 font-mono">
            <div>Vector Retriever Score:</div>
            <div className="text-emerald-400">Doc A = 0.8912 (Rank #1)</div>
            <div className="text-slate-300">Doc B = 0.8904 (Rank #2)  <span className="text-slate-500">← Difference is only 0.0008!</span></div>
          </div>
          <p className="text-rose-300 font-semibold">
            🚨 The problem with a sharp drop: Punishing Doc B by an immediate 50% score penalty for a 0.0008 score difference is disproportionate and irrational.
          </p>
        </div>
      ),
    },
    {
      title: '2. Dictator Veto: A single rogue model overrules all other models',
      badge: 'Destruction of Hybrid Search',
      color: 'rose',
      icon: AlertTriangle,
      summary: 'Why use hybrid search if one model can unilaterally declare the winner regardless of what other rankers think?',
      detail: (
        <div className="space-y-2 text-xs">
          <p className="text-slate-300">
            We build multi-stage hybrid search (BM25 + Dense + SPLADE) specifically because <em>every individual retriever has known blind spots</em>:
          </p>
          <ul className="list-disc list-inside text-slate-400 space-y-1">
            <li><strong>BM25 fails on:</strong> synonyms, conceptual search, and keyword stuffing/spam.</li>
            <li><strong>Dense vector fails on:</strong> exact SKU/part numbers, acronyms, and rare proper nouns.</li>
          </ul>
          <p className="text-slate-300 mt-2">
            If Rank #1 grants an insurmountable score (<span className="font-mono text-cyan-300">1.0</span> vs <span className="font-mono text-cyan-300">0.5</span>), whenever BM25 trips on keyword spam, its #1 pick <strong>automatically vetoes</strong> the semantic model.
          </p>
        </div>
      ),
    },
    {
      title: '3. Destruction of Ensemble "Wisdom of the Crowd"',
      badge: 'Consensus Deficit',
      color: 'indigo',
      icon: Users,
      summary: 'A sharp drop violates Condorcet and Borda voting principles, where mutual consensus should outperform isolated extremism.',
      detail: (
        <div className="space-y-2 text-xs">
          <p className="text-slate-300">
            Consider 3 retrieval models judging two candidate documents:
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 my-2 font-mono">
            <div className="p-2.5 bg-slate-900 rounded border border-rose-900/40">
              <span className="text-rose-400 font-bold block mb-1">Doc X (Rogue Hit)</span>
              <div>Model 1: #1</div>
              <div>Model 2: #50</div>
              <div>Model 3: #50</div>
              <div className="mt-1 pt-1 border-t border-slate-800 text-rose-300 font-bold">
                Unsmoothed: 1.00 + 0.02 + 0.02 = 1.04
              </div>
            </div>
            <div className="p-2.5 bg-slate-900 rounded border border-cyan-900/40">
              <span className="text-cyan-400 font-bold block mb-1">Doc Y (Consensus Hit)</span>
              <div>Model 1: #2</div>
              <div>Model 2: #2</div>
              <div>Model 3: #2</div>
              <div className="mt-1 pt-1 border-t border-slate-800 text-slate-300 font-bold">
                Unsmoothed: 0.50 + 0.50 + 0.50 = 1.50 (barely ahead)
              </div>
            </div>
          </div>
          <p className="text-slate-300">
            If Doc Y had been ranked #3, #3, #3 (<span className="font-mono">0.33 + 0.33 + 0.33 = 1.00</span>), <strong>Doc X would beat it!</strong> Three separate AI models agreeing a document is top-tier would lose to 1 fluke.
          </p>
        </div>
      ),
    },
    {
      title: '4. Non-Linear Cliff vs Linear Relevance',
      badge: 'Relevance Decay Mismatch',
      color: 'cyan',
      icon: Scale,
      summary: 'Human relevance judgments do not halve between the 1st and 2nd document.',
      detail: (
        <div className="space-y-2 text-xs">
          <p className="text-slate-300">
            TREC relevance assessments and user click-through studies show that while top results are more relevant than bottom results, true document utility degrades smoothly:
          </p>
          <div className="p-3 bg-slate-900 rounded-lg border border-slate-800 font-mono text-slate-300">
            <div>True Relevance: [Doc #1: 95%] → [Doc #2: 92%] → [Doc #3: 88%] ...</div>
            <div className="text-rose-400 mt-1">Raw 1/r Model: [Doc #1: 100%] → [Doc #2: 50%] → [Doc #3: 33%]</div>
            <div className="text-cyan-400 mt-1">k=60 Model:   [Doc #1: 100%] → [Doc #2: 98.4%] → [Doc #3: 96.8%]</div>
          </div>
          <p className="text-slate-400 mt-2">
            The unsmoothed score curve is catastrophically steeper than the true underlying relevance distribution. Smoothing bridges this gap.
          </p>
        </div>
      ),
    },
  ];

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-8 shadow-xl mb-8">
      <div className="flex items-center gap-2 text-amber-400 text-xs font-semibold uppercase tracking-wider mb-2">
        <HelpCircle className="w-4 h-4" /> Core Question
      </div>
      <h2 className="text-2xl font-bold text-white tracking-tight">
        "Why is it actually a problem that rank drops sharply?"
      </h2>
      <p className="text-slate-400 text-sm mt-1 max-w-3xl">
        At first glance, rewarding the #1 rank sounds great. But in search and retrieval engineering, a sharp drop creates <strong>four fatal system flaws</strong>.
      </p>

      {/* Grid of 4 Core Explanations */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-6">
        {problems.map((prob, idx) => {
          const Icon = prob.icon;
          const isSelected = activeCard === idx;
          return (
            <div
              key={idx}
              onClick={() => setActiveCard(idx)}
              className={`cursor-pointer p-5 rounded-xl border transition-all text-left flex flex-col justify-between ${
                isSelected
                  ? 'bg-slate-950 border-cyan-500/60 shadow-lg shadow-cyan-950/30 ring-1 ring-cyan-500/30'
                  : 'bg-slate-950/60 border-slate-800 hover:border-slate-700 hover:bg-slate-950/90'
              }`}
            >
              <div>
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-lg bg-slate-900 border border-slate-800 flex items-center justify-center text-cyan-400">
                      <Icon className="w-4 h-4" />
                    </div>
                    <span className="text-[11px] font-mono uppercase font-bold text-cyan-400/90 bg-cyan-950/40 px-2 py-0.5 rounded border border-cyan-900/40">
                      {prob.badge}
                    </span>
                  </div>
                  <span className="text-xs text-slate-500 font-mono">#{idx + 1}</span>
                </div>
                <h3 className="text-sm font-bold text-white mb-2 leading-snug">{prob.title}</h3>
                <p className="text-xs text-slate-400 leading-relaxed mb-3">{prob.summary}</p>
              </div>

              {isSelected && (
                <div className="mt-4 pt-4 border-t border-slate-800/80 animate-fadeIn">
                  {prob.detail}
                </div>
              )}

              {!isSelected && (
                <div className="text-[11px] text-cyan-400 font-semibold flex items-center gap-1 mt-2">
                  Click to inspect real-world example <ArrowRight className="w-3 h-3" />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
