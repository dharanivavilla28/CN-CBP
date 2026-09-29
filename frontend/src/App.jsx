import React, { useState, useEffect, useCallback } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Navbar from './components/Navbar';
import Dashboard from './pages/Dashboard';
import Topology from './pages/Topology';
import { useNetworkSocket } from './hooks/useNetworkSocket';
import { api } from './services/api';
import { CheckCircle2, RefreshCw, AlertTriangle, ShieldAlert } from 'lucide-react';

export default function App() {
  const [networkState, setNetworkState] = useState({
    topology: null,
    routes: {},
    metrics: null,
    metrics_history: [],
    ml_predictions: {},
    events: [],
    mode: 'SIMULATION',
    traffic_level: 'NORMAL',
  });

  const [isScenarioRunning, setIsScenarioRunning] = useState(false);
  const [scenarioLogs, setScenarioLogs] = useState([]);
  const [showScenarioModal, setShowScenarioModal] = useState(false);

  // Handle incoming WebSocket messages
  const handleWebSocketEvent = useCallback((payload) => {
    const { event, data } = payload;

    if (event === 'INITIAL_STATE') {
      setNetworkState((prev) => ({
        ...prev,
        topology: data.topology,
        routes: data.routes,
        metrics: data.metrics,
        metrics_history: [data.metrics],
        ml_predictions: data.ml_predictions,
        mode: data.mode,
        traffic_level: data.traffic_level,
      }));
    } else if (event === 'TELEMETRY_UPDATE') {
      setNetworkState((prev) => ({
        ...prev,
        metrics: data.stats,
        metrics_history: [...(prev.metrics_history || []), data.stats].slice(-30),
        ml_predictions: data.ml_predictions,
        routes: data.active_routes || prev.routes,
      }));
    } else if (event === 'TOPOLOGY_CHANGED' || event === 'LINK_FAILED' || event === 'LINK_RESTORED') {
      if (data.topology) {
        setNetworkState((prev) => ({
          ...prev,
          topology: data.topology,
          routes: data.routes || prev.routes,
        }));
      }
    } else if (event === 'SCENARIO_STEP') {
      setScenarioLogs((prev) => [...prev, data]);
    }
  }, []);

  const { isConnected } = useNetworkSocket(handleWebSocketEvent);

  // Initial data fetch
  useEffect(() => {
    Promise.all([
      api.getStatus(),
      api.getTopology(),
      api.getRoutes(),
      api.getNetworkStats(),
      api.getMLPredictions(),
      api.getEvents(20),
    ])
      .then(([status, topo, routes, stats, ml, evts]) => {
        setNetworkState({
          topology: topo,
          routes: routes,
          metrics: stats,
          metrics_history: stats.metrics_history || [],
          ml_predictions: ml.predictions || {},
          events: evts,
          mode: status.mode || 'SIMULATION',
          traffic_level: status.traffic_level || 'NORMAL',
        });
      })
      .catch((err) => {
        console.error('Error fetching initial backend state:', err);
      });
  }, []);

  // Handle traffic level injection
  const handleTrafficChange = async (level) => {
    try {
      await api.setTrafficLevel(level);
      setNetworkState((prev) => ({ ...prev, traffic_level: level }));
    } catch (e) {
      console.error(e);
    }
  };

  // Run the 14-Step CBP Emergency Scenario
  const handleRunScenario = async () => {
    setIsScenarioRunning(true);
    setScenarioLogs([]);
    setShowScenarioModal(true);

    try {
      const res = await api.runScenario();
      if (res.steps) {
        setScenarioLogs(res.steps);
      }
    } catch (err) {
      console.error('Scenario run error:', err);
    } finally {
      setIsScenarioRunning(false);
    }
  };

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
        {/* Navigation Bar */}
        <Navbar
          mode={networkState.mode}
          trafficLevel={networkState.traffic_level}
          onTrafficChange={handleTrafficChange}
          onRunScenario={handleRunScenario}
          isScenarioRunning={isScenarioRunning}
        />

        {/* WebSocket Connection Warning Banner if disconnected */}
        {!isConnected && (
          <div className="bg-amber-950/80 border-b border-amber-800 text-amber-300 text-xs px-4 py-1.5 text-center font-mono">
            ⚠️ Live WebSocket stream connecting to backend (ws://localhost:8000/ws/network)...
          </div>
        )}

        {/* Main Application Content */}
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 lg:px-8 py-6">
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<Dashboard networkState={networkState} />} />
            <Route path="/topology" element={<Topology networkState={networkState} />} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </main>

        {/* Footer */}
        <footer className="border-t border-slate-900 bg-slate-950/80 px-4 py-4 text-center text-xs font-mono text-slate-500">
          ML-Enhanced Software Defined Emergency Communication Network with Dynamic Fault-Aware Routing • Academic Computer Networks CBP
        </footer>

        {/* 14-Step Automated Emergency Scenario Modal (Requirement 30) */}
        {showScenarioModal && (
          <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4">
            <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-2xl w-full p-6 shadow-2xl flex flex-col max-h-[85vh]">
              <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                <div className="flex items-center gap-2">
                  <ShieldAlert className="w-5 h-5 text-red-500" />
                  <h3 className="text-base font-bold text-white">
                    14-Step Automated Emergency Demonstration Scenario
                  </h3>
                </div>
                <button
                  onClick={() => setShowScenarioModal(false)}
                  className="text-slate-400 hover:text-white text-xs font-mono"
                >
                  ✕ Close
                </button>
              </div>

              <div className="py-2 text-xs text-slate-400 font-mono">
                Executing automated evaluation protocol: Traffic surge → ML Risk penalty → Dijkstra Alternate Path → Physical Link Failure → Flow Table Rule Recovery.
              </div>

              <div className="flex-1 overflow-y-auto space-y-2 py-3 pr-2 font-mono text-xs">
                {scenarioLogs.map((log, idx) => (
                  <div
                    key={idx}
                    className="p-2.5 rounded-lg bg-slate-950 border border-slate-800/80 flex items-start gap-2.5"
                  >
                    <span className="w-5 h-5 rounded-full bg-cyan-950 text-cyan-400 border border-cyan-800 flex items-center justify-center text-[10px] font-bold shrink-0 mt-0.5">
                      {log.step || idx + 1}
                    </span>
                    <div>
                      <div className="font-bold text-slate-200">{log.action}</div>
                      <div className="text-slate-400 text-[11px] mt-0.5">{log.detail}</div>
                    </div>
                  </div>
                ))}
                {isScenarioRunning && (
                  <div className="flex items-center gap-2 text-cyan-400 py-3 text-xs animate-pulse">
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>Executing scenario steps...</span>
                  </div>
                )}
              </div>

              <div className="pt-3 border-t border-slate-800 flex justify-end">
                <button
                  onClick={() => setShowScenarioModal(false)}
                  className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold"
                >
                  Done
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </BrowserRouter>
  );
}
