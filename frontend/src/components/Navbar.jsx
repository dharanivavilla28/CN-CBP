import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  Activity, 
  Share2, 
  Cpu, 
  ShieldAlert, 
  Radio, 
  Flame, 
  RefreshCw 
} from 'lucide-react';

export default function Navbar({ 
  status, 
  mode = 'SIMULATION', 
  trafficLevel = 'NORMAL', 
  onTrafficChange,
  onRunScenario,
  isScenarioRunning = false 
}) {
  return (
    <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur-md sticky top-0 z-50 px-4 lg:px-8 py-3">
      <div className="flex flex-col md:flex-row items-center justify-between gap-4">
        {/* Left: Branding & CBP Title */}
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400">
            <Radio className="w-5 h-5 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono font-bold tracking-wider uppercase px-2 py-0.5 rounded bg-cyan-950 border border-cyan-800 text-cyan-300">
                SDN + ML ROUTING
              </span>
              <span className={`text-xs font-mono font-bold tracking-wider uppercase px-2 py-0.5 rounded border ${
                mode === 'SIMULATION' 
                  ? 'bg-amber-950/70 border-amber-700 text-amber-300' 
                  : 'bg-emerald-950/70 border-emerald-700 text-emerald-300'
              }`}>
                {mode === 'SIMULATION' ? 'SIMULATION MODE' : 'REAL SDN MODE'}
              </span>
            </div>
            <h1 className="text-base font-extrabold text-slate-100 tracking-tight flex items-center gap-2 mt-0.5">
              Emergency Network Control Center
            </h1>
          </div>
        </div>

        {/* Center: EXACTLY TWO REQUIRED UI PAGES */}
        <nav className="flex items-center p-1 rounded-xl bg-slate-900 border border-slate-800">
          <NavLink
            to="/dashboard"
            className={({ isActive }) =>
              `flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all ${
                isActive
                  ? 'bg-cyan-500 text-slate-950 shadow-md shadow-cyan-500/20'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`
            }
          >
            <Activity className="w-4 h-4" />
            Network Dashboard
          </NavLink>

          <NavLink
            to="/topology"
            className={({ isActive }) =>
              `flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all ${
                isActive
                  ? 'bg-cyan-500 text-slate-950 shadow-md shadow-cyan-500/20'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`
            }
          >
            <Share2 className="w-4 h-4" />
            Topology & Routing
          </NavLink>
        </nav>

        {/* Right: Traffic Level Simulator & Scenario Action */}
        <div className="flex items-center gap-2">
          {/* Traffic Injector */}
          <div className="flex items-center bg-slate-900 border border-slate-800 rounded-lg p-1 text-xs">
            <span className="text-slate-400 font-mono px-2 flex items-center gap-1">
              <Flame className="w-3.5 h-3.5 text-amber-400" />
              Load:
            </span>
            <button
              onClick={() => onTrafficChange('NORMAL')}
              className={`px-2 py-1 rounded font-medium transition ${
                trafficLevel === 'NORMAL' ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Normal
            </button>
            <button
              onClick={() => onTrafficChange('HIGH')}
              className={`px-2 py-1 rounded font-medium transition ${
                trafficLevel === 'HIGH' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              High
            </button>
            <button
              onClick={() => onTrafficChange('CONGESTED')}
              className={`px-2 py-1 rounded font-medium transition ${
                trafficLevel === 'CONGESTED' ? 'bg-red-500/20 text-red-300 border border-red-500/40' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Congested
            </button>
          </div>

          {/* Quick Scenario Run */}
          {onRunScenario && (
            <button
              onClick={onRunScenario}
              disabled={isScenarioRunning}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-600 hover:bg-red-500 text-white text-xs font-bold tracking-wide transition shadow-lg shadow-red-900/30 disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isScenarioRunning ? 'animate-spin' : ''}`} />
              {isScenarioRunning ? 'RUNNING...' : 'DEMO SCENARIO'}
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
