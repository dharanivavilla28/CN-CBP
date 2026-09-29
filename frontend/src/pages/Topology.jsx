import React, { useState, useEffect, useMemo, useCallback } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  Handle,
  Position,
  useNodesState,
  useEdgesState,
  MarkerType,
} from 'reactflow';
import 'reactflow/dist/style.css';

import {
  Shield,
  Cross,
  Building,
  DoorOpen,
  DoorClosed,
  Radio,
  Server,
  Zap,
  AlertTriangle,
  Send,
  Plus,
  Trash2,
  RotateCcw,
  CheckCircle2,
  Flame,
  ArrowRight,
  RefreshCw,
  Sliders,
  XCircle,
  HelpCircle,
  Layers,
} from 'lucide-react';
import { api } from '../services/api';

// ────────────────────────── Custom Node Components ────────────────────── //

function HostNode({ data }) {
  const iconMap = {
    Shield: <Shield className="w-5 h-5 text-cyan-400" />,
    Cross: <Cross className="w-5 h-5 text-red-400" />,
    Building: <Building className="w-5 h-5 text-amber-400" />,
    DoorOpen: <DoorOpen className="w-5 h-5 text-emerald-400" />,
    DoorClosed: <DoorClosed className="w-5 h-5 text-emerald-400" />,
    Radio: <Radio className="w-5 h-5 text-purple-400" />,
  };

  const isSelected = data.isSelected;
  const isInPath = data.isInPath;

  return (
    <div
      className={`px-3 py-2.5 rounded-xl border transition-all cursor-pointer shadow-lg min-w-[140px] ${
        isInPath
          ? 'bg-cyan-950/90 border-cyan-400 ring-2 ring-cyan-500/50 shadow-cyan-500/20'
          : isSelected
          ? 'bg-slate-900 border-purple-500 ring-2 ring-purple-500/50'
          : 'bg-slate-900/90 border-slate-700/80 hover:border-slate-500'
      }`}
    >
      <Handle type="target" position={Position.Top} className="!bg-cyan-500 !w-2 !h-2" />
      <Handle type="source" position={Position.Bottom} className="!bg-cyan-500 !w-2 !h-2" />
      <Handle type="target" position={Position.Left} id="left" className="!bg-cyan-500 !w-2 !h-2" />
      <Handle type="source" position={Position.Right} id="right" className="!bg-cyan-500 !w-2 !h-2" />

      <div className="flex items-center gap-2">
        <div className="p-1.5 rounded-lg bg-slate-950/80 border border-slate-800">
          {iconMap[data.icon] || <Shield className="w-5 h-5 text-cyan-400" />}
        </div>
        <div>
          <div className="text-xs font-bold text-slate-100 flex items-center gap-1">
            {data.label}
          </div>
          <div className="text-[10px] font-mono text-cyan-300 font-semibold">{data.ip}</div>
        </div>
      </div>
      {isInPath && (
        <div className="mt-1 text-[9px] font-mono text-cyan-300 bg-cyan-950/80 px-1 py-0.5 rounded text-center border border-cyan-800">
          ● ROUTE HOP
        </div>
      )}
    </div>
  );
}

function SwitchNode({ data }) {
  const isInPath = data.isInPath;
  const isSelected = data.isSelected;

  return (
    <div
      className={`px-4 py-3 rounded-2xl border transition-all cursor-pointer shadow-xl min-w-[150px] ${
        isInPath
          ? 'bg-emerald-950/90 border-emerald-400 ring-2 ring-emerald-500/50 shadow-emerald-500/20'
          : isSelected
          ? 'bg-slate-900 border-purple-500 ring-2 ring-purple-500/50'
          : 'bg-slate-900/95 border-slate-700/90 hover:border-slate-500'
      }`}
    >
      <Handle type="target" position={Position.Top} className="!bg-emerald-500 !w-2.5 !h-2.5" />
      <Handle type="source" position={Position.Bottom} className="!bg-emerald-500 !w-2.5 !h-2.5" />
      <Handle type="target" position={Position.Left} id="left" className="!bg-emerald-500 !w-2.5 !h-2.5" />
      <Handle type="source" position={Position.Right} id="right" className="!bg-emerald-500 !w-2.5 !h-2.5" />

      <div className="flex items-center gap-2.5">
        <div className="p-2 rounded-xl bg-slate-950 border border-slate-800 text-emerald-400">
          <Server className="w-5 h-5" />
        </div>
        <div>
          <div className="text-xs font-black text-slate-100 uppercase tracking-wider font-mono">
            {data.id}
          </div>
          <div className="text-[10px] text-slate-400 truncate max-w-[90px]">{data.label}</div>
          <div className="text-[9px] font-mono text-emerald-400">DPID: {data.dpid?.slice(-4) || '0001'}</div>
        </div>
      </div>
      {isInPath && (
        <div className="mt-1 text-[9px] font-mono text-emerald-300 bg-emerald-950/80 px-1 py-0.5 rounded text-center border border-emerald-800">
          ● OPENFLOW FORWARDING
        </div>
      )}
    </div>
  );
}

const nodeTypes = {
  hostNode: HostNode,
  switchNode: SwitchNode,
};

const DEFAULT_POSITIONS = {
  // Switches in central core
  S1: { x: 260, y: 180 },
  S2: { x: 480, y: 80 },
  S3: { x: 300, y: 380 },
  S4: { x: 620, y: 260 },
  // Surrounding Emergency Hosts
  Security: { x: 60, y: 140 },
  ControlRoom: { x: 120, y: 260 },
  Medical: { x: 480, y: -40 },
  MainGate: { x: 180, y: 480 },
  Admin: { x: 800, y: 180 },
  BackGate: { x: 800, y: 340 },
};

const DEFAULT_ROUTE = {
  path: ['Security', 'S1', 'S2', 'Medical'],
  path_str: 'Security → S1 → S2 → Medical',
  cost: 4.0,
  hop_count: 3,
};

// ────────────────────────── Main Topology Page ────────────────────────── //

export default function Topology({ networkState }) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  const [selectedItem, setSelectedItem] = useState(null); // Node or Link
  const [selectedItemType, setSelectedItemType] = useState(null); // 'node' or 'link'

  // Emergency Message Form State
  const [msgSource, setMsgSource] = useState('Security');
  const [msgDest, setMsgDest] = useState('Medical');
  const [msgText, setMsgText] = useState('FIRE ALERT AT MAIN GATE');
  const [msgPriority, setMsgPriority] = useState('CRITICAL');
  const [isSending, setIsSending] = useState(false);
  const [lastDelivery, setLastDelivery] = useState(null);

  // Link Failure / Recovery State
  const [selectedLinkToFail, setSelectedLinkToFail] = useState('S1-S2');
  const [routeChangeAlert, setRouteChangeAlert] = useState(null);
  const [sendError, setSendError] = useState(null);

  // Custom Topology Creation Form
  const [showAddNodeModal, setShowAddNodeModal] = useState(false);
  const [showAddLinkModal, setShowAddLinkModal] = useState(false);
  const [newNodeId, setNewNodeId] = useState('');
  const [newNodeLabel, setNewNodeLabel] = useState('');
  const [newNodeType, setNewNodeType] = useState('switch');
  const [newNodeIp, setNewNodeIp] = useState('10.0.0.10');

  const [newLinkSrc, setNewLinkSrc] = useState('S1');
  const [newLinkDst, setNewLinkDst] = useState('S4');
  const [newLinkCost, setNewLinkCost] = useState(2.0);
  const [newLinkBw, setNewLinkBw] = useState(1000);

  // Packet Flow Animation state
  const [animatingPacket, setAnimatingPacket] = useState(false);
  const [packetProgressIndex, setPacketProgressIndex] = useState(0);

  // Link Parameter Editing State (Requirement 7: Set Link Weight, Bandwidth, Delay, Loss)
  const [editCost, setEditCost] = useState(2.0);
  const [editBw, setEditBw] = useState(1000);
  const [editDelay, setEditDelay] = useState(5.0);
  const [editLoss, setEditLoss] = useState(0.0);
  const [savingLink, setSavingLink] = useState(false);

  // Current active route path
  const currentRoute = networkState?.routes?.['Security→Medical'] || DEFAULT_ROUTE;
  const isNoPath = currentRoute.status === 'NO_PATH';
  const activePath = (!isNoPath && currentRoute.path) ? currentRoute.path : DEFAULT_ROUTE.path;
  const activePathStr = currentRoute.path_str || DEFAULT_ROUTE.path_str;
  const selectedNodeId = selectedItemType === 'node' ? selectedItem?.id : null;

  // Build React Flow nodes & edges from backend topology
  useEffect(() => {
    if (!networkState?.topology) return;

    const rawNodes = networkState.topology.nodes || [];
    const rawLinks = networkState.topology.links || [];

    const flowNodes = rawNodes.map((n, idx) => {
      const pos = DEFAULT_POSITIONS[n.id] || {
        x: 200 + (idx % 3) * 220,
        y: 100 + Math.floor(idx / 3) * 160,
      };

      const isInPath = activePath.includes(n.id);
      const isSelected = selectedNodeId === n.id;

      return {
        id: n.id,
        type: n.type === 'switch' ? 'switchNode' : 'hostNode',
        position: pos,
        data: {
          ...n,
          isInPath,
          isSelected,
        },
      };
    });

    const flowEdges = rawLinks.map((l) => {
      const isFailed = l.status === 'failed';
      const isPathEdge =
        activePath.length > 1 &&
        activePath.some((node, i) => {
          if (i === activePath.length - 1) return false;
          const next = activePath[i + 1];
          return (
            (l.source === node && l.target === next) ||
            (l.source === next && l.target === node)
          );
        });

      let strokeColor = '#334155'; // default slate
      let strokeWidth = 2;
      let strokeDasharray = undefined;
      let animated = false;

      if (isFailed) {
        strokeColor = '#ef4444'; // Red for failed
        strokeWidth = 3;
        strokeDasharray = '6 6';
      } else if (isPathEdge) {
        strokeColor = '#38bdf8'; // Cyan for active route
        strokeWidth = 4;
        animated = true;
      } else if (l.ml_risk > 0.5) {
        strokeColor = '#f59e0b'; // Amber for high risk
        strokeWidth = 2.5;
      }

      return {
        id: l.id || `${l.source}-${l.target}`,
        source: l.source,
        target: l.target,
        animated,
        style: {
          stroke: strokeColor,
          strokeWidth,
          strokeDasharray,
        },
        label: isFailed ? '✕ FAILED' : `c:${l.cost || l.base_cost} (r:${Math.round((l.ml_risk || 0) * 100)}%)`,
        labelStyle: {
          fill: isFailed ? '#f87171' : isPathEdge ? '#38bdf8' : '#94a3b8',
          fontSize: 10,
          fontFamily: 'monospace',
          fontWeight: 700,
        },
        labelBgStyle: {
          fill: '#090d16',
          fillOpacity: 0.85,
        },
        data: l,
      };
    });

    setNodes(flowNodes);
    setEdges(flowEdges);
  }, [networkState?.topology, activePathStr, selectedNodeId, setNodes, setEdges]);

  // Click on node
  const onNodeClick = useCallback(
    (_, node) => {
      setSelectedItem(node.data);
      setSelectedItemType('node');
    },
    []
  );

  // Click on edge
  const onEdgeClick = useCallback(
    (_, edge) => {
      setSelectedItem(edge.data);
      setSelectedItemType('link');
      if (edge.data) {
        setEditCost(edge.data.cost || edge.data.base_cost || 2.0);
        setEditBw(edge.data.bandwidth || 1000);
        setEditDelay(edge.data.latency || 5.0);
        setEditLoss(edge.data.packet_loss || 0.0);
      }
    },
    []
  );

  // Apply Link Parameters (Requirement 7)
  const handleSaveLinkSettings = async () => {
    if (!selectedItem) return;
    setSavingLink(true);
    try {
      const linkId = selectedItem.id || `${selectedItem.source}-${selectedItem.target}`;
      await api.updateLink({
        id: linkId,
        cost: parseFloat(editCost),
        bandwidth: parseInt(editBw, 10),
        latency: parseFloat(editDelay),
        packet_loss: parseFloat(editLoss),
      });
      setSelectedItem((prev) => ({
        ...prev,
        cost: parseFloat(editCost),
        base_cost: parseFloat(editCost),
        bandwidth: parseInt(editBw, 10),
        latency: parseFloat(editDelay),
        packet_loss: parseFloat(editLoss),
      }));
    } catch (err) {
      console.error('Error saving link settings:', err);
    } finally {
      setSavingLink(false);
    }
  };

  // Send Emergency Message handler
  const handleSendMessage = async (e) => {
    e.preventDefault();
    setIsSending(true);
    setSendError(null);

    try {
      const res = await api.sendMessage({
        source: msgSource,
        destination: msgDest,
        message: msgText,
        priority: msgPriority,
      });

      if (res.status === 'SENT') {
        setLastDelivery(res.delivery);
        setSendError(null);

        // Start traveling packet animation
        setAnimatingPacket(true);
        setPacketProgressIndex(0);
        const pathLen = res.route?.path?.length || 4;
        for (let i = 0; i < pathLen; i++) {
          setPacketProgressIndex(i);
          await new Promise((r) => setTimeout(r, 450));
        }
        setAnimatingPacket(false);
      } else {
        setSendError(`Transmission failed: ${res.detail || 'Unknown error'}`);
      }
    } catch (err) {
      console.error('Failed to send message:', err);
      // Parse error detail from backend 400 response
      let errMsg = 'No path exists from source to destination — all links may be failed.';
      try {
        const errJson = await err?.response?.json?.();
        if (errJson?.detail) errMsg = errJson.detail;
      } catch (_) {}
      setSendError(errMsg);
    } finally {
      setIsSending(false);
    }
  };

  // Fail Link handler
  const handleFailLink = async () => {
    // Split only on the first '-' so IDs with dashes are handled correctly
    const dashIdx = selectedLinkToFail.indexOf('-');
    const source = selectedLinkToFail.slice(0, dashIdx);
    const target = selectedLinkToFail.slice(dashIdx + 1);
    const prevPath = currentRoute.path_str;

    try {
      await api.failLink(source, target);
      setRouteChangeAlert({
        previous: prevPath,
        reason: `Trunk link ${source}-${target} failed / unavailable`,
      });
    } catch (err) {
      console.error('Error failing link:', err);
    }
  };

  // Restore Link handler
  const handleRestoreLink = async () => {
    const [source, target] = selectedLinkToFail.split('-');
    try {
      await api.restoreLink(source, target);
      setRouteChangeAlert(null);
    } catch (err) {
      console.error('Error restoring link:', err);
    }
  };

  // Add custom node
  const handleAddNode = async (e) => {
    e.preventDefault();
    try {
      await api.addNode({
        id: newNodeId,
        label: newNodeLabel || newNodeId,
        type: newNodeType,
        ip: newNodeIp,
        mac: `00:00:00:00:00:${Math.floor(Math.random() * 89 + 10)}`,
        icon: newNodeType === 'switch' ? 'Server' : 'Shield',
      });
      setShowAddNodeModal(false);
      setNewNodeId('');
      setNewNodeLabel('');
    } catch (err) {
      alert(`Error adding node: ${err.message}`);
    }
  };

  // Add custom link
  const handleAddLink = async (e) => {
    e.preventDefault();
    try {
      await api.addLink({
        source: newLinkSrc,
        target: newLinkDst,
        cost: parseFloat(newLinkCost),
        bandwidth: parseInt(newLinkBw, 10),
        latency: 4.5,
        packet_loss: 0.0,
      });
      setShowAddLinkModal(false);
    } catch (err) {
      alert(`Error adding link: ${err.message}`);
    }
  };

  // Delete selected item
  const handleDeleteSelected = async () => {
    if (!selectedItem) return;
    if (selectedItemType === 'node') {
      await api.deleteNode(selectedItem.id);
    } else if (selectedItemType === 'link') {
      await api.deleteLink(selectedItem.id || `${selectedItem.source}-${selectedItem.target}`);
    }
    setSelectedItem(null);
  };

  return (
    <div className="space-y-6 pb-12">
      {/* ────────────────── Header Bar ────────────────── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-5 rounded-2xl bg-slate-900/60 border border-slate-800 backdrop-blur-md">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-black tracking-tight text-white flex items-center gap-2">
              <Layers className="w-6 h-6 text-cyan-400" />
              Emergency Topology & Dynamic Routing
            </h1>
            <span className="px-2.5 py-0.5 rounded text-xs font-mono font-bold bg-cyan-950 text-cyan-400 border border-cyan-800">
              Interactive Graph
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Visualise OpenFlow switches, emergency hosts, link-state costs, and ML-governed Dijkstra paths
          </p>
        </div>

        {/* Custom Topology Creation Buttons */}
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => setShowAddNodeModal(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-slate-950 text-xs font-bold transition shadow-sm"
          >
            <Plus className="w-3.5 h-3.5" /> Add Node
          </button>
          <button
            onClick={() => setShowAddLinkModal(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition"
          >
            <Plus className="w-3.5 h-3.5" /> Connect Nodes
          </button>
          <button
            onClick={() => api.resetTopology()}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200 text-xs font-semibold border border-slate-700 transition"
            title="Reset to default campus layout"
          >
            <RotateCcw className="w-3.5 h-3.5" /> Reset Topology
          </button>
        </div>
      </div>

      {/* ────────────────── Route Changed Alert Banner (Requirement 14) ────────────────── */}
      {routeChangeAlert && (
        <div className="p-4 rounded-xl bg-amber-950/40 border border-amber-600/60 flex items-start justify-between gap-4 animate-pulse-slow">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-400 mt-0.5" />
            <div>
              <div className="text-xs font-bold text-amber-300 uppercase tracking-wider font-mono">
                ROUTE CHANGED • AUTOMATIC FAULT RECOVERY ACTIVE
              </div>
              <div className="text-xs text-slate-300 mt-1 font-mono">
                <span className="text-slate-500 line-through mr-2">Previous: {routeChangeAlert.previous}</span>
                <span className="text-emerald-400 font-bold">New: {currentRoute.path_str}</span>
              </div>
              <div className="text-[11px] text-amber-200/80 mt-0.5">
                Reason: {routeChangeAlert.reason} • Dijkstra ignored failed trunk link and selected next available lowest-cost path.
              </div>
            </div>
          </div>
          <button
            onClick={() => setRouteChangeAlert(null)}
            className="text-slate-400 hover:text-slate-200 text-xs"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* ────────────────── Main Graph & Inspector Grid ────────────────── */}
      <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
        {/* React Flow Topology Visualizer (3 Cols) */}
        <div className="xl:col-span-3 h-[580px] rounded-2xl bg-slate-950 border border-slate-800 relative overflow-hidden shadow-2xl">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={onNodeClick}
            onEdgeClick={onEdgeClick}
            nodeTypes={nodeTypes}
            fitView
            attributionPosition="bottom-left"
          >
            <Background color="#1e293b" gap={20} size={1} />
            <Controls className="!bg-slate-900 !border-slate-800 !text-slate-300" />
            <MiniMap
              nodeColor={(n) => (n.type === 'switchNode' ? '#10b981' : '#38bdf8')}
              className="!bg-slate-900/90 !border-slate-800"
            />
          </ReactFlow>

          {/* Active Route Overlay Badge */}
          <div className="absolute top-4 left-4 z-10 p-3 rounded-xl bg-slate-950/85 border border-cyan-500/40 backdrop-blur-md font-mono text-xs shadow-xl">
            {isNoPath ? (
              <>
                <div className="flex items-center gap-2 text-red-400 font-bold mb-1">
                  <span className="w-2 h-2 rounded-full bg-red-500 animate-ping" />
                  ROUTING FAILURE:
                </div>
                <div className="text-red-300 font-black text-sm flex items-center gap-1.5">
                  ⚠ NO PATH EXISTS
                </div>
                <div className="text-[10px] text-red-400/80 mt-1">
                  All links between {currentRoute.source || 'Security'} and {currentRoute.destination || 'Medical'} are failed or unreachable.
                </div>
              </>
            ) : (
              <>
                <div className="flex items-center gap-2 text-cyan-400 font-bold mb-1">
                  <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
                  ACTIVE DIJKSTRA ROUTE:
                </div>
                <div className="text-slate-200 font-bold flex items-center gap-1.5">
                  {activePathStr}
                </div>
                <div className="text-[10px] text-slate-400 mt-1 flex items-center justify-between gap-4">
                  <span>Total Cost: <b className="text-cyan-300">{currentRoute.cost}</b></span>
                  <span>Hops: <b className="text-emerald-300">{currentRoute.hop_count || activePath.length - 1}</b></span>
                </div>
              </>
            )}
          </div>

          {/* Packet Flow Animation Indicator (Requirement 27) */}
          {animatingPacket && (
            <div className="absolute bottom-4 left-4 z-10 px-4 py-2 rounded-xl bg-purple-950/90 border border-purple-500/50 backdrop-blur-md font-mono text-xs shadow-xl flex items-center gap-2 text-purple-200 animate-pulse">
              <Zap className="w-4 h-4 text-purple-400" />
              <span>PACKET TRAVELING: {activePath[packetProgressIndex]} → {activePath[packetProgressIndex + 1] || 'DESTINATION'}</span>
            </div>
          )}

          {/* Legend */}
          <div className="absolute bottom-4 right-4 z-10 p-2.5 rounded-xl bg-slate-950/85 border border-slate-800 backdrop-blur-md font-mono text-[10px] space-y-1 text-slate-400">
            <div className="flex items-center gap-2"><span className="w-3 h-1 bg-cyan-400" /> Active Dijkstra Path</div>
            <div className="flex items-center gap-2"><span className="w-3 h-1 bg-red-500 border-dashed" /> Failed Link (S1-X-S2)</div>
            <div className="flex items-center gap-2"><span className="w-3 h-1 bg-amber-400" /> High ML Congestion Risk</div>
            <div className="flex items-center gap-2"><span className="w-2.5 h-2.5 rounded-sm bg-emerald-500" /> OpenFlow Switch</div>
            <div className="flex items-center gap-2"><span className="w-2.5 h-2.5 rounded-sm bg-cyan-500" /> Emergency Host</div>
          </div>
        </div>

        {/* Right Sidebar: Details & Controls (1 Col) */}
        <div className="space-y-4">
          {/* Selected Item Inspector (Host IP / Link Details) */}
          <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold text-slate-300 uppercase tracking-wider font-mono">
                {selectedItemType === 'node' ? 'Host / Switch Info' : selectedItemType === 'link' ? 'Link Details' : 'Inspector'}
              </span>
              {selectedItem && (
                <button
                  onClick={handleDeleteSelected}
                  className="text-red-400 hover:text-red-300 text-xs flex items-center gap-1 font-mono"
                  title="Delete element from topology"
                >
                  <Trash2 className="w-3 h-3" /> Delete
                </button>
              )}
            </div>

            {selectedItem ? (
              selectedItemType === 'node' ? (
                <div className="space-y-2 font-mono text-xs">
                  <div className="flex justify-between py-1 border-b border-slate-800"><span className="text-slate-400">Name:</span> <span className="text-white font-bold">{selectedItem.label}</span></div>
                  <div className="flex justify-between py-1 border-b border-slate-800"><span className="text-slate-400">ID:</span> <span className="text-cyan-300">{selectedItem.id}</span></div>
                  <div className="flex justify-between py-1 border-b border-slate-800"><span className="text-slate-400">Type:</span> <span className="text-slate-300 uppercase">{selectedItem.type}</span></div>
                  {selectedItem.ip && <div className="flex justify-between py-1 border-b border-slate-800"><span className="text-slate-400">IP Address:</span> <span className="text-emerald-400 font-bold">{selectedItem.ip}</span></div>}
                  {selectedItem.mac && <div className="flex justify-between py-1 border-b border-slate-800"><span className="text-slate-400">MAC Address:</span> <span className="text-slate-300">{selectedItem.mac}</span></div>}
                  <div className="flex justify-between py-1"><span className="text-slate-400">Status:</span> <span className="text-emerald-400 uppercase font-bold">{selectedItem.status || 'ACTIVE'}</span></div>
                </div>
              ) : (
                <div className="space-y-3 font-mono text-xs">
                  <div className="space-y-1.5 pb-2 border-b border-slate-800">
                    <div className="flex justify-between py-0.5"><span className="text-slate-400">Link:</span> <span className="text-cyan-400 font-bold">{selectedItem.source} ↔ {selectedItem.target}</span></div>
                    <div className="flex justify-between py-0.5"><span className="text-slate-400">Current Cost:</span> <span className="text-cyan-300 font-bold">{selectedItem.cost}</span></div>
                    <div className="flex justify-between py-0.5"><span className="text-slate-400">ML Risk:</span> <span className="text-purple-400 font-bold">{Math.round((selectedItem.ml_risk || 0) * 100)}%</span></div>
                    <div className="flex justify-between py-0.5"><span className="text-slate-400">Status:</span> <span className={selectedItem.status === 'failed' ? 'text-red-400 font-bold' : 'text-emerald-400 font-bold'}>{selectedItem.status?.toUpperCase() || 'ACTIVE'}</span></div>
                  </div>

                  {/* Set Link Parameters (Requirement 7) */}
                  <div className="space-y-2 pt-1">
                    <div className="text-[11px] font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1">
                      <Sliders className="w-3.5 h-3.5 text-cyan-400" />
                      Configure Link Parameters:
                    </div>

                    <div>
                      <div className="flex justify-between text-[11px] text-slate-400 mb-0.5">
                        <span>Set Link Weight (Cost):</span>
                        <span className="text-cyan-300">{editCost}</span>
                      </div>
                      <input
                        type="number"
                        step="0.5"
                        min="0.5"
                        max="20"
                        value={editCost}
                        onChange={(e) => setEditCost(e.target.value)}
                        className="w-full bg-slate-950 border border-slate-700 rounded p-1.5 text-xs text-white"
                      />
                    </div>

                    <div>
                      <div className="flex justify-between text-[11px] text-slate-400 mb-0.5">
                        <span>Set Bandwidth (Mbps):</span>
                        <span className="text-emerald-300">{editBw} Mbps</span>
                      </div>
                      <input
                        type="number"
                        step="50"
                        min="10"
                        max="10000"
                        value={editBw}
                        onChange={(e) => setEditBw(e.target.value)}
                        className="w-full bg-slate-950 border border-slate-700 rounded p-1.5 text-xs text-white"
                      />
                    </div>

                    <div>
                      <div className="flex justify-between text-[11px] text-slate-400 mb-0.5">
                        <span>Set Delay / Latency (ms):</span>
                        <span className="text-amber-300">{editDelay} ms</span>
                      </div>
                      <input
                        type="number"
                        step="0.5"
                        min="0.5"
                        max="200"
                        value={editDelay}
                        onChange={(e) => setEditDelay(e.target.value)}
                        className="w-full bg-slate-950 border border-slate-700 rounded p-1.5 text-xs text-white"
                      />
                    </div>

                    <div>
                      <div className="flex justify-between text-[11px] text-slate-400 mb-0.5">
                        <span>Set Packet Loss (%):</span>
                        <span className="text-rose-300">{editLoss}%</span>
                      </div>
                      <input
                        type="number"
                        step="0.1"
                        min="0"
                        max="50"
                        value={editLoss}
                        onChange={(e) => setEditLoss(e.target.value)}
                        className="w-full bg-slate-950 border border-slate-700 rounded p-1.5 text-xs text-white"
                      />
                    </div>

                    <button
                      onClick={handleSaveLinkSettings}
                      disabled={savingLink}
                      className="w-full mt-2 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-slate-950 text-xs font-bold transition flex items-center justify-center gap-1 shadow-sm disabled:opacity-50"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      {savingLink ? 'Updating...' : 'APPLY LINK SETTINGS'}
                    </button>
                  </div>
                </div>
              )
            ) : (
              <div className="py-6 text-center text-xs text-slate-500 font-mono">
                Click any Node or Link to inspect IP addresses, OpenFlow ports, and live link metrics.
              </div>
            )}
          </div>

          {/* Fault Tolerance & Link Failure Controls (Requirement 13 & 21) */}
          <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800">
            <span className="text-xs font-bold text-slate-300 uppercase tracking-wider font-mono flex items-center gap-1.5 mb-3">
              <Flame className="w-4 h-4 text-red-400" />
              Fault Injection & Recovery
            </span>

            <div className="space-y-3">
              <div>
                <label className="text-[11px] font-mono text-slate-400 block mb-1">Target Trunk Link:</label>
                <select
                  value={selectedLinkToFail}
                  onChange={(e) => setSelectedLinkToFail(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 text-xs font-mono text-slate-200 rounded-lg p-2 focus:outline-none focus:border-red-500"
                >
                  <option value="S1-S2">S1 ↔ S2 (Primary Backbone)</option>
                  <option value="S1-S3">S1 ↔ S3 (West to South)</option>
                  <option value="S2-S4">S2 ↔ S4 (North to East)</option>
                  <option value="S3-S4">S3 ↔ S4 (Alternate Backbone)</option>
                  <option value="S2-S3">S2 ↔ S3 (Cross Trunk)</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={handleFailLink}
                  className="w-full py-2 rounded-lg bg-red-600/90 hover:bg-red-500 text-white font-mono text-xs font-bold transition shadow-md shadow-red-950 flex items-center justify-center gap-1"
                >
                  <XCircle className="w-3.5 h-3.5" /> FAIL LINK
                </button>
                <button
                  onClick={handleRestoreLink}
                  className="w-full py-2 rounded-lg bg-emerald-600/90 hover:bg-emerald-500 text-white font-mono text-xs font-bold transition shadow-md shadow-emerald-950 flex items-center justify-center gap-1"
                >
                  <RotateCcw className="w-3.5 h-3.5" /> RESTORE
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ────────────────── Send Emergency Message Panel (Requirement 15, 16, 17) ────────────────── */}
      <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Radio className="w-5 h-5 text-red-500 animate-pulse" />
            <h2 className="text-lg font-bold text-white">Send Emergency Message (Real TCP Socket Protocol)</h2>
          </div>
          <span className="text-xs font-mono text-slate-400 bg-slate-950 px-2.5 py-1 rounded border border-slate-800">
            Transport: Python AF_INET TCP Socket Handshake
          </span>
        </div>

        <form onSubmit={handleSendMessage} className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {/* Source Dropdown */}
          <div>
            <label className="text-xs font-mono text-slate-400 block mb-1">Source Node:</label>
            <select
              value={msgSource}
              onChange={(e) => setMsgSource(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 text-xs font-mono text-cyan-300 rounded-lg p-2.5 focus:outline-none focus:border-cyan-500"
            >
              <option value="Security">Security (10.0.0.1)</option>
              <option value="ControlRoom">Emergency Control (10.0.0.6)</option>
              <option value="Medical">Medical Room (10.0.0.2)</option>
              <option value="MainGate">Main Gate (10.0.0.4)</option>
              <option value="Admin">Admin Building (10.0.0.3)</option>
              <option value="BackGate">Back Gate (10.0.0.5)</option>
            </select>
          </div>

          {/* Destination Dropdown */}
          <div>
            <label className="text-xs font-mono text-slate-400 block mb-1">Destination Node:</label>
            <select
              value={msgDest}
              onChange={(e) => setMsgDest(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 text-xs font-mono text-red-300 rounded-lg p-2.5 focus:outline-none focus:border-red-500"
            >
              <option value="Medical">Medical Room (10.0.0.2)</option>
              <option value="Security">Security (10.0.0.1)</option>
              <option value="ControlRoom">Emergency Control (10.0.0.6)</option>
              <option value="Admin">Admin Building (10.0.0.3)</option>
              <option value="MainGate">Main Gate (10.0.0.4)</option>
              <option value="BackGate">Back Gate (10.0.0.5)</option>
            </select>
          </div>

          {/* Message Text Input */}
          <div>
            <label className="text-xs font-mono text-slate-400 block mb-1">Emergency Payload:</label>
            <input
              type="text"
              value={msgText}
              onChange={(e) => setMsgText(e.target.value)}
              placeholder="e.g. FIRE ALERT AT MAIN GATE"
              className="w-full bg-slate-950 border border-slate-700 text-xs font-mono text-white rounded-lg p-2.5 focus:outline-none focus:border-cyan-500"
            />
          </div>

          {/* Priority & Send Button */}
          <div className="flex items-end gap-2">
            <div className="w-1/2">
              <label className="text-xs font-mono text-slate-400 block mb-1">Priority:</label>
              <select
                value={msgPriority}
                onChange={(e) => setMsgPriority(e.target.value)}
                className={`w-full bg-slate-950 border text-xs font-mono rounded-lg p-2.5 focus:outline-none ${
                  msgPriority === 'CRITICAL' ? 'border-red-600 text-red-400' : 'border-slate-700 text-amber-300'
                }`}
              >
                <option value="NORMAL">Normal</option>
                <option value="EMERGENCY">Emergency</option>
                <option value="CRITICAL">Critical</option>
              </select>
            </div>
            <button
              type="submit"
              disabled={isSending}
              className="w-1/2 py-2.5 rounded-lg bg-red-600 hover:bg-red-500 text-white font-bold text-xs font-mono uppercase tracking-wide transition shadow-lg shadow-red-900/40 flex items-center justify-center gap-1.5 disabled:opacity-50"
            >
              <Send className="w-3.5 h-3.5" />
              {isSending ? 'Sending...' : 'SEND'}
            </button>
          </div>
        </form>

        {/* Socket Delivery Receipt Display */}
        {lastDelivery && (
          <div className="mt-4 p-3.5 rounded-xl bg-slate-950 border border-emerald-500/40 font-mono text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span className="text-emerald-300 font-bold">TCP SOCKET TRANSMISSION CONFIRMED:</span>
              <span className="text-slate-300">
                "{lastDelivery.message}" from <b className="text-cyan-300">{lastDelivery.source}</b> to <b className="text-red-300">{lastDelivery.destination}</b>
              </span>
            </div>
            <div className="flex items-center gap-3 text-[11px] text-slate-400">
              <span>Path: <b className="text-slate-200">{(lastDelivery.route_path || []).join(' → ')}</b></span>
              <span>RTT: <b className="text-emerald-400">{lastDelivery.rtt_ms} ms</b></span>
              <span className="px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800">DELIVERED</span>
            </div>
          </div>
        )}

        {/* No Path Error Display */}
        {sendError && (
          <div className="mt-4 p-3.5 rounded-xl bg-red-950/60 border border-red-600/60 font-mono text-xs flex items-start gap-3">
            <XCircle className="w-4 h-4 text-red-400 mt-0.5 shrink-0" />
            <div>
              <div className="text-red-300 font-bold uppercase tracking-wide">TRANSMISSION FAILED — NO PATH EXISTS</div>
              <div className="text-red-400/80 mt-0.5">{sendError}</div>
              <div className="text-slate-400 mt-1 text-[11px]">Restore failed links using the Fault Injection panel above, then retry.</div>
            </div>
          </div>
        )}
      </div>

      {/* ────────────────── Add Node Modal ────────────────── */}
      {showAddNodeModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-md w-full p-6 shadow-2xl">
            <h3 className="text-lg font-bold text-white mb-4">Add Custom Network Node</h3>
            <form onSubmit={handleAddNode} className="space-y-4 text-xs font-mono">
              <div>
                <label className="text-slate-400 block mb-1">Node Identifier (e.g. S5 or GuardPost):</label>
                <input
                  type="text"
                  required
                  value={newNodeId}
                  onChange={(e) => setNewNodeId(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-white"
                />
              </div>
              <div>
                <label className="text-slate-400 block mb-1">Display Label:</label>
                <input
                  type="text"
                  value={newNodeLabel}
                  onChange={(e) => setNewNodeLabel(e.target.value)}
                  placeholder="e.g. East Wing Switch"
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-white"
                />
              </div>
              <div>
                <label className="text-slate-400 block mb-1">Type:</label>
                <select
                  value={newNodeType}
                  onChange={(e) => setNewNodeType(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-white"
                >
                  <option value="switch">SDN OpenFlow Switch</option>
                  <option value="host">Emergency Host Station</option>
                </select>
              </div>
              {newNodeType === 'host' && (
                <div>
                  <label className="text-slate-400 block mb-1">IP Address:</label>
                  <input
                    type="text"
                    value={newNodeIp}
                    onChange={(e) => setNewNodeIp(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-white"
                  />
                </div>
              )}
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddNodeModal(false)}
                  className="px-4 py-2 rounded-lg bg-slate-800 text-slate-300 font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg bg-cyan-500 text-slate-950 font-bold"
                >
                  Create Node
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ────────────────── Add Link Modal ────────────────── */}
      {showAddLinkModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-md w-full p-6 shadow-2xl">
            <h3 className="text-lg font-bold text-white mb-4">Connect Nodes (Create Link)</h3>
            <form onSubmit={handleAddLink} className="space-y-4 text-xs font-mono">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-slate-400 block mb-1">Source Node:</label>
                  <input
                    type="text"
                    required
                    value={newLinkSrc}
                    onChange={(e) => setNewLinkSrc(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-white"
                  />
                </div>
                <div>
                  <label className="text-slate-400 block mb-1">Target Node:</label>
                  <input
                    type="text"
                    required
                    value={newLinkDst}
                    onChange={(e) => setNewLinkDst(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-white"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-slate-400 block mb-1">Base Cost / Weight:</label>
                  <input
                    type="number"
                    step="0.5"
                    value={newLinkCost}
                    onChange={(e) => setNewLinkCost(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-white"
                  />
                </div>
                <div>
                  <label className="text-slate-400 block mb-1">Bandwidth (Mbps):</label>
                  <input
                    type="number"
                    value={newLinkBw}
                    onChange={(e) => setNewLinkBw(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-white"
                  />
                </div>
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddLinkModal(false)}
                  className="px-4 py-2 rounded-lg bg-slate-800 text-slate-300 font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg bg-cyan-500 text-slate-950 font-bold"
                >
                  Establish Link
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
