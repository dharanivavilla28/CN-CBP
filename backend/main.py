"""
FastAPI Backend Server & WebSocket Hub
Part of: ML-Enhanced SDN Emergency Communication Network

Provides:
  - REST API endpoints for SDN controller, routing engine, ML predictor, and sockets
  - WebSocket /ws/network for live UI streaming
  - Background telemetry loop simulating network traffic and ML evaluation
"""
import asyncio
import json
import logging
import os
import sys
import time
from typing import Dict, Any, List, Optional

# Ensure backend root is on sys.path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from network.simulation import simulator
from network.sockets import socket_manager
from sdn.topology import get_default_topology

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EmergencySDN")

app = FastAPI(
    title="ML-Enhanced SDN Emergency Communication System",
    description="SDN Controller + Dijkstra Dynamic Routing + ML Risk Assessment + TCP Sockets",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Active WebSocket client connections
connected_websockets: List[WebSocket] = []


# ─────────────────────────── Pydantic Request Models ─────────────────── #

class SendMessageRequest(BaseModel):
    source: str = "Security"
    destination: str = "Medical"
    message: str = "FIRE ALERT AT MAIN GATE"
    priority: str = "CRITICAL"  # "NORMAL", "EMERGENCY", "CRITICAL"


class LinkActionRequest(BaseModel):
    source: str
    target: str


class AddNodeRequest(BaseModel):
    id: str
    label: str
    type: str = "host"  # "host" or "switch"
    ip: Optional[str] = "10.0.0.10"
    mac: Optional[str] = "00:00:00:00:00:10"
    category: Optional[str] = "custom"
    icon: Optional[str] = "Server"


class AddLinkRequest(BaseModel):
    source: str
    target: str
    cost: float = 1.0
    bandwidth: int = 100
    latency: float = 5.0
    packet_loss: float = 0.0


class RecalculateRouteRequest(BaseModel):
    source: str = "Security"
    destination: str = "Medical"
    ml_adjusted: bool = True


class TrafficLevelRequest(BaseModel):
    level: str = "NORMAL"  # "NORMAL", "HIGH", "CONGESTED"


# ─────────────────────────── WebSocket Hub ─────────────────────────────── #

async def notify_websockets(event_type: str, data: Any):
    if not connected_websockets:
        return
    message = json.dumps({"event": event_type, "data": data, "timestamp": time.time()})
    disconnected = []
    for ws in connected_websockets:
        try:
            await ws.send_text(message)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        if ws in connected_websockets:
            connected_websockets.remove(ws)


@app.websocket("/ws/network")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_websockets.append(websocket)
    logger.info("WebSocket connected. Total clients: %d", len(connected_websockets))

    # Send initial state snapshot
    try:
        initial_data = {
            "topology": {
                "nodes": simulator.routing_engine.nodes,
                "links": simulator.routing_engine.links,
                "failed_links": [list(k) for k in simulator.routing_engine.failed_links],
            },
            "routes": simulator.routing_engine.current_routes,
            "metrics": simulator.update_telemetry_tick(),
            "ml_predictions": simulator.last_ml_predictions,
            "mode": simulator.mode,
            "traffic_level": simulator.traffic_level,
        }
        await websocket.send_text(json.dumps({"event": "INITIAL_STATE", "data": initial_data}))
    except Exception as e:
        logger.error("Failed sending initial WS payload: %s", e)

    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming ping or requests
            try:
                msg = json.loads(data)
                if msg.get("action") == "PING":
                    await websocket.send_text(json.dumps({"event": "PONG", "timestamp": time.time()}))
            except Exception:
                pass
    except WebSocketDisconnect:
        if websocket in connected_websockets:
            connected_websockets.remove(websocket)
        logger.info("WebSocket disconnected. Remaining clients: %d", len(connected_websockets))


# ─────────────────────────── Background Telemetry Task ────────────────── #

telemetry_task = None

async def telemetry_loop():
    logger.info("Starting background telemetry loop (1.5s intervals)...")
    while True:
        try:
            stats = simulator.update_telemetry_tick()
            await notify_websockets("TELEMETRY_UPDATE", {
                "stats": stats,
                "ml_predictions": simulator.last_ml_predictions,
                "active_routes": simulator.routing_engine.current_routes,
            })
        except Exception as e:
            logger.error("Error in telemetry loop: %s", e)
        await asyncio.sleep(1.5)


@app.on_event("startup")
async def startup_event():
    global telemetry_task
    # Start TCP sockets
    socket_manager.start_all()
    # Connect simulator broadcast to WebSockets
    simulator.register_subscriber(notify_websockets)
    # Launch telemetry task
    telemetry_task = asyncio.create_task(telemetry_loop())
    logger.info("Emergency SDN Backend startup sequence complete.")


@app.on_event("shutdown")
async def shutdown_event():
    global telemetry_task
    if telemetry_task:
        telemetry_task.cancel()
    socket_manager.stop_all()
    logger.info("Emergency SDN Backend shut down.")


# ─────────────────────────── REST Endpoints ──────────────────────────── #

@app.get("/api/status")
def get_system_status():
    return {
        "sdn_controller": "ONLINE",
        "network": "ACTIVE",
        "ml_engine": "ONLINE" if simulator.ml_predictor.is_loaded else "HEURISTIC",
        "mode": simulator.mode,
        "traffic_level": simulator.traffic_level,
        "last_update": time.time(),
        "time_str": time.strftime("%H:%M:%S"),
    }


@app.get("/api/topology")
def get_topology():
    return {
        "nodes": simulator.routing_engine.nodes,
        "links": simulator.routing_engine.links,
        "failed_links": [list(k) for k in simulator.routing_engine.failed_links],
    }


@app.get("/api/nodes")
def get_nodes():
    return simulator.routing_engine.nodes


@app.get("/api/links")
def get_links():
    return simulator.routing_engine.links


@app.get("/api/routes")
def get_routes():
    return simulator.routing_engine.current_routes


@app.get("/api/network-stats")
def get_network_stats():
    active_links = [l for l in simulator.routing_engine.links if l.get("status") != "failed"]
    failed = [l for l in simulator.routing_engine.links if l.get("status") == "failed"]
    
    # Calculate live averages
    avg_lat = round(sum(l.get("latency", 5.0) for l in active_links) / max(len(active_links), 1), 2)
    avg_loss = round(sum(l.get("packet_loss", 0.0) for l in active_links) / max(len(active_links), 1), 3)
    avg_risk = round(sum(l.get("ml_risk", 0.0) for l in active_links) / max(len(active_links), 1), 3)

    return {
        "active_nodes": len([n for n in simulator.routing_engine.nodes if n.get("status") == "active"]),
        "active_links": len(active_links),
        "failed_links": len(failed),
        "average_latency_ms": avg_lat,
        "packet_loss_percent": round(avg_loss * 100, 2),
        "ml_risk_percent": round(avg_risk * 100, 1),
        "total_packets": sum(s.get("rx_packets", 0) for s in simulator.controller.stats.values()),
        "current_route": simulator.routing_engine.current_routes.get("Security→Medical", {}).get("path_str", "N/A"),
        "mode": simulator.mode,
        "traffic_level": simulator.traffic_level,
        "metrics_history": simulator.metrics_history[-20:],
    }


@app.get("/api/ml/prediction")
def get_ml_predictions():
    return {
        "predictions": simulator.last_ml_predictions,
        "formula": simulator.routing_engine.ML_RISK_FORMULA,
        "model_used": "RandomForest (CICIDS2017)",
    }


@app.get("/api/ml/info")
def get_ml_info():
    return simulator.ml_predictor.get_model_info()


@app.post("/api/messages/send")
async def send_emergency_message(req: SendMessageRequest):
    # 1. Determine optimal route with Dijkstra
    route = simulator.recalculate_route(req.source, req.destination, ml_adjusted=True)
    if not route.get("path"):
        raise HTTPException(status_code=400, detail=f"No route available from {req.source} to {req.destination}")

    # 2. Transmit via real TCP sockets
    delivery = socket_manager.send_tcp_message(
        source=req.source,
        destination=req.destination,
        message=req.message,
        priority=req.priority,
        route_path=route["path"],
        route_cost=route["cost"],
    )

    # 3. Notify real-time UI
    await notify_websockets("MESSAGE_SENT", delivery)
    return {
        "status": "SENT",
        "delivery": delivery,
        "route": route,
    }


@app.get("/api/messages/history")
def get_message_history(limit: int = 50):
    return list(reversed(socket_manager.message_log[-limit:]))


@app.post("/api/links/fail")
async def fail_link(req: LinkActionRequest):
    result = simulator.fail_link(req.source, req.target)
    await notify_websockets("LINK_FAILED", {
        "source": req.source,
        "target": req.target,
        "topology": get_topology(),
        "routes": simulator.routing_engine.current_routes,
    })
    return result


@app.post("/api/links/restore")
async def restore_link(req: LinkActionRequest):
    result = simulator.restore_link(req.source, req.target)
    await notify_websockets("LINK_RESTORED", {
        "source": req.source,
        "target": req.target,
        "topology": get_topology(),
        "routes": simulator.routing_engine.current_routes,
    })
    return result


@app.post("/api/topology/node")
async def add_node(req: AddNodeRequest):
    node = {
        "id": req.id,
        "label": req.label,
        "type": req.type,
        "ip": req.ip,
        "mac": req.mac,
        "category": req.category,
        "status": "active",
        "icon": req.icon,
    }
    simulator.routing_engine.add_node(node)
    if req.type == "switch":
        simulator.controller.register_switch(req.id)
    else:
        simulator.controller.register_host(req.id, req.ip, req.mac, "S1", 1)

    await notify_websockets("TOPOLOGY_CHANGED", get_topology())
    return {"status": "ADDED", "node": node}


@app.delete("/api/topology/node/{node_id}")
async def delete_node(node_id: str):
    simulator.routing_engine.remove_node(node_id)
    simulator.routing_engine.recalculate_all_routes()
    await notify_websockets("TOPOLOGY_CHANGED", get_topology())
    return {"status": "DELETED", "node_id": node_id}


@app.post("/api/topology/link")
async def add_link(req: AddLinkRequest):
    link = {
        "id": f"{req.source}-{req.target}",
        "source": req.source,
        "target": req.target,
        "cost": req.cost,
        "base_cost": req.cost,
        "bandwidth": req.bandwidth,
        "latency": req.latency,
        "packet_loss": req.packet_loss,
        "ml_risk": 0.05,
        "status": "active",
    }
    try:
        simulator.routing_engine.add_link(link)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    simulator.routing_engine.recalculate_all_routes()
    await notify_websockets("TOPOLOGY_CHANGED", get_topology())
    return {"status": "ADDED", "link": link}


@app.delete("/api/topology/link/{link_id}")
async def delete_link(link_id: str):
    simulator.routing_engine.remove_link(link_id)
    simulator.routing_engine.recalculate_all_routes()
    await notify_websockets("TOPOLOGY_CHANGED", get_topology())
    return {"status": "DELETED", "link_id": link_id}


class UpdateLinkRequest(BaseModel):
    id: str
    cost: Optional[float] = None
    bandwidth: Optional[int] = None
    latency: Optional[float] = None
    packet_loss: Optional[float] = None


@app.post("/api/topology/link/update")
async def update_link(req: UpdateLinkRequest):
    found = False
    for lnk in simulator.routing_engine.links:
        if lnk.get("id") == req.id or f"{lnk['source']}-{lnk['target']}" == req.id:
            if req.cost is not None:
                lnk["cost"] = req.cost
                lnk["base_cost"] = req.cost
            if req.bandwidth is not None:
                lnk["bandwidth"] = req.bandwidth
            if req.latency is not None:
                lnk["latency"] = req.latency
            if req.packet_loss is not None:
                lnk["packet_loss"] = req.packet_loss
            found = True
            break

    if not found:
        raise HTTPException(status_code=404, detail="Link not found")

    simulator.routing_engine.recalculate_all_routes()
    await notify_websockets("TOPOLOGY_CHANGED", get_topology())
    return {"status": "UPDATED", "link_id": req.id}



@app.post("/api/routing/recalculate")
def recalculate_route_endpoint(req: RecalculateRouteRequest):
    route = simulator.recalculate_route(req.source, req.destination, ml_adjusted=req.ml_adjusted)
    return route


@app.get("/api/routing/compare")
def compare_routing(source: str = "Security", destination: str = "Medical"):
    return simulator.routing_engine.compare_routing_strategies(source, destination)


@app.get("/api/openflow/rules")
def get_openflow_rules():
    return simulator.controller.get_all_flow_tables()


@app.post("/api/scenario/run")
async def run_scenario_endpoint():
    log = await simulator.run_scenario_step_by_step()
    return {"status": "COMPLETE", "steps": log}


@app.post("/api/traffic/set-level")
async def set_traffic_level(req: TrafficLevelRequest):
    simulator.traffic_level = req.level
    simulator.update_telemetry_tick()
    await notify_websockets("TRAFFIC_LEVEL_CHANGED", {"level": req.level})
    return {"traffic_level": req.level}


@app.get("/api/events")
def get_events(limit: int = 50):
    return simulator.routing_engine.get_events(limit=limit)


@app.post("/api/topology/reset")
async def reset_topology():
    simulator.reset_to_default_topology()
    await notify_websockets("TOPOLOGY_CHANGED", get_topology())
    return {"status": "RESET", "topology": get_topology()}
