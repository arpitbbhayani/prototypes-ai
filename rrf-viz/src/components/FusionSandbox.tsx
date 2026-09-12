import React, { useState } from 'react';
import { RotateCcw, ArrowUpDown } from 'lucide-react';

interface DocumentItem {
  id: string;
  title: string;
  bm25Rank: number;
  vectorRank: number;
  spladeRank: number;
}

const DEFAULT_DOCS: DocumentItem[] = [
  {
    id: 'doc-1',
    title: 'Postgres vs MySQL for Vector Search',
    bm25Rank: 1,
    vectorRank: 45,
    spladeRank: 30,
  },
  {
    id: 'doc-2',
    title: 'HNSW Index Tuning & Memory Optimization',
    bm25Rank: 6,
    vectorRank: 4,
    spladeRank: 5,
  },
  {
    id: 'doc-3',
    title: 'Hybrid Search Architecture & Benchmarks',
    bm25Rank: 4,
    vectorRank: 7,
    spladeRank: 2,
  },
  {
    id: 'doc-4',
    title: 'Sparse vs Dense Embeddings Explained',
    bm25Rank: 12,
    vectorRank: 2,
    spladeRank: 15,
  },
  {
    id: 'doc-5',
    title: 'Lexical Keyword Matching with BM25',
    bm25Rank: 2,
    vectorRank: 80,
    spladeRank: 18,
  },
  {
    id: 'doc-6',
    title: 'Vector Quantization (IVF-PQ) Deep Dive',
    bm25Rank: 25,
    vectorRank: 3,
    spladeRank: 40,
  },
];

export const FusionSandbox: React.FC<{ k: number; setK: (k: number) => void }> = ({
  k,
  setK,
}) => {
  const [docs, setDocs] = useState<DocumentItem[]>(DEFAULT_DOCS);
  const [useSplade, setUseSplade] = useState<boolean>(true);

  // Calculate RRF scores and rank
  const scoredDocs = docs.map((doc) => {
    const sBm25 = 1 / (k + doc.bm25Rank);
    const sVector = 1 / (k + doc.vectorRank);
    const sSplade = useSplade ? 1 / (k + doc.spladeRank) : 0;

    const totalScore = sBm25 + sVector + sSplade;
    return {
      ...doc,
      sBm25,
      sVector,
      sSplade,
      totalScore,
    };
  });

  scoredDocs.sort((a, b) => b.totalScore - a.totalScore);

  const handleRankChange = (
    id: string,
    field: 'bm25Rank' | 'vectorRank' | 'spladeRank',
    value: number
  ) => {
    setDocs((prev) =>
      prev.map((d) => (d.id === id ? { ...d, [field]: Math.max(1, Math.min(200, value)) } : d))
    );
  };

  const handleReset = () => {
    setDocs(DEFAULT_DOCS);
    setK(60);
  };

  const setPreset = (preset: 'rogue' | 'balanced') => {
    if (preset === 'rogue') {
      setDocs([
        {
          id: 'p-1',
          title: 'Keyword Spammer (Rank #1 in BM25, awful in Vector)',
          bm25Rank: 1,
          vectorRank: 100,
          spladeRank: 85,
        },
        {
          id: 'p-2',
          title: 'High Consensus Relevant Doc (Rank #4 everywhere)',
          bm25Rank: 4,
          vectorRank: 5,
          spladeRank: 4,
        },
        {
          id: 'p-3',
          title: 'Solid Semantic Match',
          bm25Rank: 8,
          vectorRank: 6,
          spladeRank: 7,
        },
      ]);
    } else if (preset === 'balanced') {
      setDocs(DEFAULT_DOCS);
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-8 shadow-xl mb-8">
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 pb-6 border-b border-slate-800">
        <div>
          <div className="inline-flex items-center gap-2 text-cyan-400 text-xs font-semibold uppercase tracking-wider mb-1">
            <ArrowUpDown className="w-4 h-4" /> Interactive Multi-Ranker Playground
          </div>
          <h2 className="text-2xl font-bold text-white tracking-tight">
            Reciprocal Rank Fusion Sandbox
          </h2>
          <p className="text-slate-400 text-sm mt-1 max-w-2xl">
            Tweak document ranks across BM25, Dense Vector, and SPLADE. Slide <span className="font-mono text-cyan-300">k</span> and observe how the final fused leaderboard shifts live.
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={() => setUseSplade(!useSplade)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all border ${
              useSplade
                ? 'bg-purple-500/20 text-purple-300 border-purple-500/40'
                : 'bg-slate-800 text-slate-400 border-slate-700'
            }`}
          >
            {useSplade ? '3 Rankers (BM25 + Dense + SPLADE)' : '2 Rankers (BM25 + Dense)'}
          </button>
          <button
            onClick={handleReset}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition-all"
          >
            <RotateCcw className="w-3.5 h-3.5" /> Reset
          </button>
        </div>
      </div>

      {/* Preset Buttons */}
      <div className="flex items-center gap-2 my-4 text-xs">
        <span className="text-slate-400 font-medium">Quick Scenarios:</span>
        <button
          onClick={() => setPreset('rogue')}
          className="px-2.5 py-1 rounded-md bg-slate-950 border border-slate-800 hover:border-cyan-500/50 text-cyan-300 transition-all font-mono"
        >
          Rogue BM25 vs Consensus
        </button>
        <button
          onClick={() => setPreset('balanced')}
          className="px-2.5 py-1 rounded-md bg-slate-950 border border-slate-800 hover:border-slate-700 text-slate-300 transition-all font-mono"
        >
          Default Multi-Doc Set
        </button>
      </div>

      {/* Leaderboard Table */}
      <div className="overflow-x-auto mt-2">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="border-b border-slate-800 bg-slate-950 text-slate-400 uppercase font-mono tracking-wider">
              <th className="py-3 px-3 w-16 text-center">Final Rank</th>
              <th className="py-3 px-4">Document Title</th>
              <th className="py-3 px-3 text-cyan-300">BM25 Rank (r₁)</th>
              <th className="py-3 px-3 text-emerald-300">Vector Rank (r₂)</th>
              {useSplade && <th className="py-3 px-3 text-purple-300">SPLADE Rank (r₃)</th>}
              <th className="py-3 px-4 text-right text-amber-300">RRF Score ∑ 1/(k+r)</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 font-mono">
            {scoredDocs.map((doc, index) => {
              const isFirst = index === 0;
              return (
                <tr
                  key={doc.id}
                  className={`transition-colors ${
                    isFirst
                      ? 'bg-cyan-950/20 hover:bg-cyan-950/30'
                      : 'hover:bg-slate-800/30'
                  }`}
                >
                  <td className="py-3 px-3 text-center">
                    <span
                      className={`inline-flex items-center justify-center w-7 h-7 rounded-full font-bold text-xs ${
                        isFirst
                          ? 'bg-amber-400 text-slate-950 shadow-md shadow-amber-400/30'
                          : index === 1
                          ? 'bg-slate-700 text-slate-200'
                          : index === 2
                          ? 'bg-amber-900/50 text-amber-300 border border-amber-800'
                          : 'text-slate-500'
                      }`}
                    >
                      {index + 1}
                    </span>
                  </td>
                  <td className="py-3 px-4 font-sans font-medium text-slate-200">
                    {doc.title}
                  </td>
                  <td className="py-3 px-3">
                    <input
                      type="number"
                      min="1"
                      max="200"
                      value={doc.bm25Rank}
                      onChange={(e) =>
                        handleRankChange(doc.id, 'bm25Rank', parseInt(e.target.value) || 1)
                      }
                      className="w-16 bg-slate-950 border border-slate-800 rounded px-2 py-1 text-cyan-300 font-bold focus:outline-none focus:border-cyan-500"
                    />
                    <span className="text-[10px] text-slate-500 ml-1.5">
                      (+{(doc.sBm25 * 1000).toFixed(1)}m)
                    </span>
                  </td>
                  <td className="py-3 px-3">
                    <input
                      type="number"
                      min="1"
                      max="200"
                      value={doc.vectorRank}
                      onChange={(e) =>
                        handleRankChange(doc.id, 'vectorRank', parseInt(e.target.value) || 1)
                      }
                      className="w-16 bg-slate-950 border border-slate-800 rounded px-2 py-1 text-emerald-300 font-bold focus:outline-none focus:border-emerald-500"
                    />
                    <span className="text-[10px] text-slate-500 ml-1.5">
                      (+{(doc.sVector * 1000).toFixed(1)}m)
                    </span>
                  </td>
                  {useSplade && (
                    <td className="py-3 px-3">
                      <input
                        type="number"
                        min="1"
                        max="200"
                        value={doc.spladeRank}
                        onChange={(e) =>
                          handleRankChange(doc.id, 'spladeRank', parseInt(e.target.value) || 1)
                        }
                        className="w-16 bg-slate-950 border border-slate-800 rounded px-2 py-1 text-purple-300 font-bold focus:outline-none focus:border-purple-500"
                      />
                      <span className="text-[10px] text-slate-500 ml-1.5">
                        (+{(doc.sSplade * 1000).toFixed(1)}m)
                      </span>
                    </td>
                  )}
                  <td className="py-3 px-4 text-right">
                    <span className="font-bold text-amber-300 text-sm">
                      {doc.totalScore.toFixed(5)}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
