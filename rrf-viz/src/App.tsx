import { useState } from 'react';
import { FormulaHeader } from './components/FormulaHeader';
import { NeedForSmoothing } from './components/NeedForSmoothing';
import { WhySharpDropIsAProblem } from './components/WhySharpDropIsAProblem';
import { CurveSmoothingChart } from './components/CurveSmoothingChart';
import { SweetSpotWhy60 } from './components/SweetSpotWhy60';
import { FusionSandbox } from './components/FusionSandbox';
import { KeyTakeaways } from './components/KeyTakeaways';

export function App() {
  const [globalK, setGlobalK] = useState<number>(60);
  const [activeTab, setActiveTab] = useState<'all' | 'need' | 'curves' | 'why60' | 'sandbox'>('all');

  return (
    <div className="min-h-screen bg-[#07090e] text-slate-100 selection:bg-cyan-500 selection:text-slate-950 font-sans">
      {/* Top Navbar */}
      <header className="border-b border-slate-800/80 bg-slate-950/70 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-cyan-500 to-indigo-500 flex items-center justify-center font-black text-slate-950 text-sm shadow-md shadow-cyan-500/20">
              RRF
            </div>
            <span className="font-bold text-slate-200 text-sm sm:text-base tracking-tight">
              Reciprocal Rank Fusion <span className="text-cyan-400 font-mono text-xs ml-1.5 px-2 py-0.5 rounded-full bg-cyan-950/80 border border-cyan-800/50">k = {globalK}</span>
            </span>
          </div>

          {/* Quick Nav Tabs */}
          <nav className="flex items-center gap-1 bg-slate-900/90 p-1 rounded-xl border border-slate-800 text-xs">
            <button
              onClick={() => setActiveTab('all')}
              className={`px-3 py-1.5 rounded-lg transition-all ${
                activeTab === 'all'
                  ? 'bg-cyan-500 text-slate-950 font-bold shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              All Sections
            </button>
            <button
              onClick={() => setActiveTab('need')}
              className={`px-3 py-1.5 rounded-lg transition-all hidden sm:block ${
                activeTab === 'need'
                  ? 'bg-rose-500 text-white font-bold shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Need for Smoothing
            </button>
            <button
              onClick={() => setActiveTab('curves')}
              className={`px-3 py-1.5 rounded-lg transition-all hidden sm:block ${
                activeTab === 'curves'
                  ? 'bg-cyan-500 text-slate-950 font-bold shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Curve Smoothing
            </button>
            <button
              onClick={() => setActiveTab('why60')}
              className={`px-3 py-1.5 rounded-lg transition-all hidden sm:block ${
                activeTab === 'why60'
                  ? 'bg-cyan-500 text-slate-950 font-bold shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Why k = 60?
            </button>
            <button
              onClick={() => setActiveTab('sandbox')}
              className={`px-3 py-1.5 rounded-lg transition-all hidden sm:block ${
                activeTab === 'sandbox'
                  ? 'bg-cyan-500 text-slate-950 font-bold shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Ranker Sandbox
            </button>
          </nav>
        </div>
      </header>

      {/* Main Container */}
      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
        {/* Core Formula & Motivation */}
        <FormulaHeader k={globalK} setK={setGlobalK} />

        {/* The Fundamental Need for Smoothing */}
        {(activeTab === 'all' || activeTab === 'need') && (
          <>
            <NeedForSmoothing />
            <WhySharpDropIsAProblem />
          </>
        )}

        {/* 1. Gap Smoothing Chart */}
        {(activeTab === 'all' || activeTab === 'curves') && (
          <CurveSmoothingChart activeK={globalK} setActiveK={setGlobalK} />
        )}

        {/* 2. Why k=60 Theoretical & Empirical Analysis */}
        {(activeTab === 'all' || activeTab === 'why60') && (
          <SweetSpotWhy60 />
        )}

        {/* 3. Interactive Multi-Ranker Playground */}
        {(activeTab === 'all' || activeTab === 'sandbox') && (
          <FusionSandbox k={globalK} setK={setGlobalK} />
        )}

        {/* 4. Practical Cheat-Sheet & Code */}
        {activeTab === 'all' && (
          <KeyTakeaways />
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 py-6 text-center text-xs text-slate-500">
        Reciprocal Rank Fusion visualizer for Information Retrieval, RAG & Hybrid Search systems.
      </footer>
    </div>
  );
}

export default App;
