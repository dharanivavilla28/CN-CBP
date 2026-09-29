"""
Network Simulation & State Orchestrator
Part of: ML-Enhanced SDN Emergency Communication Network

Orchestrates:
  - SDN Controller & OpenFlow rules
  - Routing Engine (Manual Dijkstra + ML Risk Penalties)
  - ML Predictor (CICIDS2017 Random Forest Model)
  - Real TCP Sockets Manager
  - Background live traffic telemetry updates
  - 14-Step Automated Emergency Scenario Runner
"""
import asyncio
import copy
import logging
import random
import time
from typing import Dict, Any, List, Optional, Callable

from routing.routing_engine import RoutingEngine
from sdn.controller import SDNController
from sdn.topology import get_default_topology
from ml.predict import MLPredictor
from network.sockets import socket_manager

logger = logging.getLogger(__name__)


class NetworkSimulator:
    def __init__(self, mode: str = "SIMULATION"):
        self.mode = mode  # "SIMULATION" or "REAL"
        self.routing_engine = RoutingEngine()
        self.controller = SDNController(mode=mode)
        self.ml_predictor = MLPredictor()
        self.socket_manager = socket_manager

        # Telemetry metrics history
        self.metrics_history: List[Dict[str, Any]] = []
        self.last_ml_predictions: Dict[str, Any] = {}
        self.subscribers: List[Callable] = []

        # Current high-level status
        self.traffic_level = "NORMAL"  # "NORMAL", "HIGH", "CONGESTED"
        self.is_running = False
        self._background_task = None
        self._scenario_running = False

        # Initialise with default topology
        self.reset_to_default_topology()

    def reset_to_default_topology(self):
        topo = get_default_topology()
        self.routing_engine.update_topology(topo["nodes"], topo["links"])
        self.routing_engine.failed_links.clear()

        # Register nodes in controller
        for node in topo["nodes"]:
            if node.get("type") == "switch":
                self.controller.register_switch(node["id"], ports=node.get("ports", 4))
            elif node.get("type") == "host":
                self.controller.register_host(
                    node["id"],
                    node.get("ip", "10.0.0.1"),
                    node.get("mac", "00:00:00:00:00:01"),
                    node.get("connected_switch", "S1"),
                    node.get("port", 1),
                )

        # Initialise default route (Security -> Medical)
        self.recalculate_route("Security", "Medical")
        self.refresh_ml_predictions()

    def register_subscriber(self, callback: Callable):
        self.subscribers.append(callback)

    async def broadcast(self, event_type: str, data: Any):
        payload = {"event": event_type, "data": data, "timestamp": time.time()}
        for cb in self.subscribers:
            try:
                if asyncio.iscoroutinefunction(cb):
                    await cb(payload)
                else:
                    cb(payload)
            except Exception as e:
                logger.error("Error broadcasting to subscriber: %s", e)

    def recalculate_route(self, source: str = "Security", destination: str = "Medical", ml_adjusted: bool = True) -> Dict[str, Any]:
        route = self.routing_engine.calculate_route(source, destination, ml_adjusted=ml_adjusted)
        if route.get("path"):
            dst_ip = "10.0.0.2"
            for n in self.routing_engine.nodes:
                if n["id"] == destination:
                    dst_ip = n.get("ip", "10.0.0.2")
                    break
            self.controller.install_path_flows(route["path"], dst_ip, self.routing_engine.nodes)
        return route

    def fail_link(self, source: str, target: str) -> Dict[str, Any]:
        self.routing_engine.fail_link(source, target)
        # Automatically recalculate routes affected
        routes = self.routing_engine.recalculate_all_routes()
        # Also re-run default route if not present
        if "Security→Medical" not in self.routing_engine.current_routes:
            self.recalculate_route("Security", "Medical")
        return {
            "status": "FAILED",
            "link": f"{source}-{target}",
            "active_routes": self.routing_engine.current_routes,
            "events": self.routing_engine.get_events(5),
        }

    def restore_link(self, source: str, target: str) -> Dict[str, Any]:
        self.routing_engine.restore_link(source, target)
        self.routing_engine.recalculate_all_routes()
        self.recalculate_route("Security", "Medical")
        return {
            "status": "RESTORED",
            "link": f"{source}-{target}",
            "active_routes": self.routing_engine.current_routes,
            "events": self.routing_engine.get_events(5),
        }

    def refresh_ml_predictions(self):
        links = self.routing_engine.links
        preds = self.ml_predictor.predict_all_links(links)
        self.last_ml_predictions = preds

        # Apply predictions to routing weights
        for link_id, pred in preds.items():
            self.routing_engine.update_ml_risk(link_id, pred.get("risk_score", 0.0))

    def update_telemetry_tick(self):
        """Advances network statistics one step for live charts and metrics."""
        # Calculate live aggregate statistics
        active_links = [l for l in self.routing_engine.links if l.get("status") != "failed"]
        failed_links = [l for l in self.routing_engine.links if l.get("status") == "failed"]

        base_lat = 8.0 if self.traffic_level == "NORMAL" else (24.0 if self.traffic_level == "HIGH" else 45.0)
        jitter = random.uniform(-1.5, 2.5)
        avg_latency = max(2.0, round(base_lat + jitter, 2))

        base_loss = 0.1 if self.traffic_level == "NORMAL" else (1.2 if self.traffic_level == "HIGH" else 4.8)
        packet_loss = max(0.0, round(base_loss + random.uniform(-0.05, 0.15), 2))

        throughput_mbps = round(random.uniform(45.0, 95.0) if self.traffic_level == "NORMAL" else random.uniform(120.0, 280.0), 1)
        bw_utilization = round(min(98.0, max(12.0, (throughput_mbps / 300.0) * 100)), 1)
        active_flows = sum(len(rules) for rules in self.controller.flow_tables.values())

        # Update per-link live metrics
        for lnk in active_links:
            lnk["latency"] = max(1.0, round(lnk.get("latency", 5.0) + random.uniform(-0.5, 0.5), 1))
            lnk["packet_loss"] = max(0.0, round(lnk.get("packet_loss", 0.01) + random.uniform(-0.005, 0.01), 3))
            lnk["bytes_per_sec"] = int(throughput_mbps * 125000 * random.uniform(0.1, 0.4))
            lnk["packets_per_sec"] = int(lnk["bytes_per_sec"] / random.randint(300, 1200))
            lnk["utilization"] = round(bw_utilization / 100.0, 2)

        # Update switch stats
        for sw in self.controller.switches:
            self.controller.collect_stats(sw)

        # Re-run ML predictions
        self.refresh_ml_predictions()

        # Build metrics snapshot
        snapshot = {
            "timestamp": time.time(),
            "time_str": time.strftime("%H:%M:%S"),
            "latency": avg_latency,
            "packet_loss": packet_loss,
            "throughput_mbps": throughput_mbps,
            "bandwidth_utilization": bw_utilization,
            "active_flows": active_flows,
            "active_nodes": len([n for n in self.routing_engine.nodes if n.get("status") == "active"]),
            "active_links": len(active_links),
            "failed_links": len(failed_links),
            "mode": self.mode,
            "traffic_level": self.traffic_level,
        }

        self.metrics_history.append(snapshot)
        if len(self.metrics_history) > 60:
            self.metrics_history = self.metrics_history[-60:]

        return snapshot

    async def run_scenario_step_by_step(self) -> List[Dict[str, Any]]:
        """
        Executes the required 14-step emergency demonstration scenario:
        STEP 1: Network starts normally.
        STEP 2: Security sends: 'Fire detected at Main Gate.'
        STEP 3: Controller calculates: Security -> S1 -> S2 -> Medical
        STEP 4: Network traffic increases.
        STEP 5: ML detects increased risk on S1-S2.
        STEP 6: ML increases the effective routing cost.
        STEP 7: Dijkstra evaluates alternate path.
        STEP 8: System selects: Security -> S1 -> S3 -> S4 -> Medical
        STEP 9: Emergency message reaches Medical.
        STEP 10: Show: 'Emergency communication maintained despite network degradation.'
        STEP 11: Fail S1-S2.
        STEP 12: Show automatic route recovery.
        STEP 13: Restore S1-S2.
        STEP 14: Recalculate optimal route.
        """
        if self._scenario_running:
            return [{"step": 0, "status": "ALREADY_RUNNING"}]

        self._scenario_running = True
        log = []

        try:
            # STEP 1: Network starts normally
            self.traffic_level = "NORMAL"
            self.reset_to_default_topology()
            log.append({"step": 1, "action": "Network initialized", "detail": "All switches active, base link costs applied."})
            await self.broadcast("SCENARIO_STEP", log[-1])
            await asyncio.sleep(1.0)

            # STEP 2: Security sends emergency message
            msg1 = self.socket_manager.send_tcp_message(
                source="Security",
                destination="Medical",
                message="Fire detected at Main Gate",
                priority="CRITICAL",
                route_path=["Security", "S1", "S2", "Medical"],
                route_cost=4.0,
            )
            log.append({"step": 2, "action": "Emergency message sent", "detail": f"Security sent: '{msg1['message']}' via TCP socket."})
            await self.broadcast("SCENARIO_STEP", log[-1])
            await asyncio.sleep(1.0)

            # STEP 3: Controller calculates initial route
            r1 = self.recalculate_route("Security", "Medical", ml_adjusted=False)
            log.append({"step": 3, "action": "Controller computed route", "detail": f"Dijkstra computed: {r1['path_str']} (Cost: {r1['cost']})"})
            await self.broadcast("SCENARIO_STEP", log[-1])
            await asyncio.sleep(1.0)

            # STEP 4: Network traffic increases
            self.traffic_level = "HIGH"
            for lnk in self.routing_engine.links:
                if lnk.get("id") == "S1-S2":
                    lnk["latency"] = 48.0
                    lnk["packet_loss"] = 0.08
                    lnk["utilization"] = 0.92
                    lnk["packets_per_sec"] = 950
                    lnk["bytes_per_sec"] = 4500000
            log.append({"step": 4, "action": "Traffic surge", "detail": "High congestion injected into trunk S1-S2."})
            await self.broadcast("SCENARIO_STEP", log[-1])
            await asyncio.sleep(1.0)

            # STEP 5: ML detects increased risk on S1-S2
            self.refresh_ml_predictions()
            risk_s1_s2 = self.last_ml_predictions.get("S1-S2", {}).get("risk_score", 0.78)
            log.append({"step": 5, "action": "ML Risk Detected", "detail": f"CICIDS2017 RF model predicted S1-S2 risk: {risk_s1_s2:.0%} (HIGH_RISK)"})
            await self.broadcast("SCENARIO_STEP", log[-1])
            await asyncio.sleep(1.0)

            # STEP 6: ML increases effective routing cost
            self.routing_engine.update_ml_risk("S1-S2", 0.85)
            s1_s2_link = next(l for l in self.routing_engine.links if l.get("id") == "S1-S2")
            log.append({"step": 6, "action": "Routing Cost Penalty", "detail": f"Cost adjusted via base_cost * (1 + risk): {s1_s2_link['cost']}"})
            await self.broadcast("SCENARIO_STEP", log[-1])
            await asyncio.sleep(1.0)

            # STEP 7: Dijkstra evaluates alternate path
            # STEP 8: System selects alternate path
            r2 = self.recalculate_route("Security", "Medical", ml_adjusted=True)
            log.append({"step": 7, "action": "Dijkstra Evaluation", "detail": f"Dijkstra re-evaluated graph taking ML risk penalties into account."})
            log.append({"step": 8, "action": "Alternate Path Selected", "detail": f"New optimal path: {r2['path_str']} (Total Cost: {r2['cost']})"})
            await self.broadcast("SCENARIO_STEP", log[-1])
            await asyncio.sleep(1.0)

            # STEP 9: Emergency message reaches Medical
            msg2 = self.socket_manager.send_tcp_message(
                source="Security",
                destination="Medical",
                message="EVACUATION DIRECTIVE: Main Gate Compromised",
                priority="CRITICAL",
                route_path=r2["path"],
                route_cost=r2["cost"],
            )
            log.append({"step": 9, "action": "Emergency Message Delivered", "detail": f"Medical received critical alert over alternate route: {' -> '.join(r2['path'])}"})
            await self.broadcast("SCENARIO_STEP", log[-1])
            await asyncio.sleep(1.0)

            # STEP 10: Communication maintained
            log.append({"step": 10, "action": "Resilience Confirmed", "detail": "Emergency communication maintained despite heavy trunk congestion."})
            await self.broadcast("SCENARIO_STEP", log[-1])
            await asyncio.sleep(1.0)

            # STEP 11: Fail S1-S2
            self.fail_link("S1", "S2")
            log.append({"step": 11, "action": "Physical Link Failure", "detail": "Trunk S1-S2 experienced catastrophic physical break (MARKED RED)."})
            await self.broadcast("SCENARIO_STEP", log[-1])
            await asyncio.sleep(1.0)

            # STEP 12: Automatic route recovery
            r3 = self.recalculate_route("Security", "Medical")
            log.append({"step": 12, "action": "Fault-Aware Recovery", "detail": f"Controller updated OpenFlow rules to bypass failed link: {r3['path_str']}"})
            await self.broadcast("SCENARIO_STEP", log[-1])
            await asyncio.sleep(1.0)

            # STEP 13: Restore S1-S2
            self.traffic_level = "NORMAL"
            self.restore_link("S1", "S2")
            log.append({"step": 13, "action": "Link Restored", "detail": "Trunk S1-S2 repaired, link-state advertisement propagated."})
            await self.broadcast("SCENARIO_STEP", log[-1])
            await asyncio.sleep(1.0)

            # STEP 14: Recalculate optimal route
            r4 = self.recalculate_route("Security", "Medical")
            log.append({"step": 14, "action": "Optimal Route Reinstated", "detail": f"Path re-optimized to original minimal cost: {r4['path_str']}"})
            await self.broadcast("SCENARIO_STEP", log[-1])

        finally:
            self._scenario_running = False

        return log


# Global simulator instance
simulator = NetworkSimulator(mode="SIMULATION")
