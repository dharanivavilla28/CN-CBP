"""
Routing Engine — ML-Aware Dynamic Routing
Part of: ML-Enhanced SDN Emergency Communication Network

This module acts as the bridge between:
  - The topology/network state (nodes, links, failures)
  - The ML prediction model (risk scores per link)
  - The Dijkstra algorithm (path calculation)
  - The SDN controller (flow rule installation)
"""
import time
import logging
from typing import Dict, List, Optional, Set, Tuple

from routing.dijkstra import (
    build_graph_from_topology,
    dijkstra,
    explain_path,
    all_pairs_shortest_paths,
)

logger = logging.getLogger(__name__)


class RoutingEngine:
    """
    Central routing engine that maintains network state and computes paths.

    Lifecycle:
      1. Topology is loaded/updated.
      2. ML risk scores are applied to links.
      3. Dijkstra is run to find the best path.
      4. Failed links are excluded from the graph.
      5. Route-change events are emitted for real-time UI updates.
    """

    ML_RISK_FORMULA = "adjusted_cost = base_cost × (1 + ml_risk)"

    def __init__(self):
        self.nodes: List[dict] = []
        self.links: List[dict] = []
        self.failed_links: Set[Tuple[str, str]] = set()
        self.ml_risk_scores: Dict[str, float] = {}  # link_id -> risk 0-1
        self.current_routes: Dict[str, dict] = {}   # src->dst key -> route info
        self.route_history: List[dict] = []
        self.events: List[dict] = []
        self._last_updated = time.time()

    # ─────────────────────────── Topology Management ────────────────────── #

    def update_topology(self, nodes: List[dict], links: List[dict]):
        """Replace topology with a new set of nodes and links."""
        self.nodes = nodes
        self.links = links
        self._last_updated = time.time()
        self._emit_event("INFO", "Topology updated",
                         f"{len(nodes)} nodes, {len(links)} links")

    def add_node(self, node: dict):
        if any(n["id"] == node["id"] for n in self.nodes):
            raise ValueError(f"Node {node['id']} already exists")
        self.nodes.append(node)
        self._emit_event("INFO", f"Node added: {node['id']}", node.get("label", ""))

    def remove_node(self, node_id: str):
        self.nodes = [n for n in self.nodes if n["id"] != node_id]
        # Also remove links touching this node
        self.links = [
            lnk for lnk in self.links
            if lnk["source"] != node_id and lnk["target"] != node_id
        ]
        self._emit_event("WARNING", f"Node removed: {node_id}", "")

    def add_link(self, link: dict):
        # Prevent duplicate links
        for existing in self.links:
            if (
                existing["source"] == link["source"]
                and existing["target"] == link["target"]
            ) or (
                existing["source"] == link["target"]
                and existing["target"] == link["source"]
            ):
                raise ValueError(
                    f"Link {link['source']}↔{link['target']} already exists"
                )
        link.setdefault("status", "active")
        link.setdefault("cost", 1.0)
        link.setdefault("bandwidth", 100)
        link.setdefault("latency", 5)
        link.setdefault("packet_loss", 0.0)
        link.setdefault("ml_risk", 0.0)
        self.links.append(link)
        self._emit_event(
            "INFO",
            f"Link added: {link['source']}↔{link['target']}",
            f"cost={link['cost']}",
        )

    def remove_link(self, link_id: str):
        self.links = [lnk for lnk in self.links if lnk.get("id") != link_id]
        self._emit_event("WARNING", f"Link removed: {link_id}", "")

    # ─────────────────────────── Link Failure ───────────────────────────── #

    def fail_link(self, source: str, target: str):
        """Mark a link as failed and trigger re-routing."""
        key = (source, target)
        rkey = (target, source)
        self.failed_links.add(key)
        self.failed_links.add(rkey)

        for lnk in self.links:
            if (lnk["source"] == source and lnk["target"] == target) or (
                lnk["source"] == target and lnk["target"] == source
            ):
                lnk["status"] = "failed"

        self._emit_event(
            "ERROR",
            f"Link FAILED: {source}–{target}",
            "Triggering route recalculation",
        )
        # Invalidate affected cached routes
        self._invalidate_routes_using_link(source, target)
        logger.warning("Link failed: %s – %s", source, target)

    def restore_link(self, source: str, target: str):
        """Restore a previously failed link."""
        self.failed_links.discard((source, target))
        self.failed_links.discard((target, source))

        for lnk in self.links:
            if (lnk["source"] == source and lnk["target"] == target) or (
                lnk["source"] == target and lnk["target"] == source
            ):
                lnk["status"] = "active"

        self._emit_event(
            "SUCCESS",
            f"Link RESTORED: {source}–{target}",
            "Route optimisation in progress",
        )
        logger.info("Link restored: %s – %s", source, target)

    # ─────────────────────────── ML Integration ─────────────────────────── #

    def update_ml_risk(self, link_id: str, risk: float):
        """
        Update the ML-predicted risk score for a link and adjust its cost.
        Formula: adjusted_cost = base_cost * (1 + ml_risk)
        """
        risk = max(0.0, min(1.0, risk))
        self.ml_risk_scores[link_id] = risk

        for lnk in self.links:
            if lnk.get("id") == link_id:
                lnk["ml_risk"] = risk
                base = lnk.get("base_cost", lnk.get("cost", 1.0))
                lnk["base_cost"] = base
                lnk["cost"] = round(base * (1.0 + risk), 4)

                self._emit_event(
                    "WARNING" if risk > 0.6 else "INFO",
                    f"ML risk updated: {link_id}",
                    f"risk={risk:.0%}  adjusted_cost={lnk['cost']}",
                )
                break

    def bulk_update_ml_risks(self, risk_map: Dict[str, float]):
        for link_id, risk in risk_map.items():
            self.update_ml_risk(link_id, risk)

    # ─────────────────────────── Routing ────────────────────────────────── #

    def calculate_route(
        self,
        source: str,
        destination: str,
        ml_adjusted: bool = True,
    ) -> dict:
        """
        Run Dijkstra to find the best path from source to destination.

        Returns a dict with:
          - path (list of node IDs)
          - cost (total effective cost)
          - hops (per-hop breakdown)
          - ml_adjusted (bool)
          - timestamp
          - status
        """
        graph = build_graph_from_topology(
            self.nodes,
            self.links,
            failed_links=self.failed_links,
            ml_adjusted=ml_adjusted,
        )

        path, cost = dijkstra(graph, source, destination, self.failed_links)

        # Define route_key before any branch so it is always in scope
        route_key = f"{source}→{destination}"

        if path is None:
            self._emit_event(
                "ERROR",
                f"No path: {source} → {destination}",
                "All routes unavailable - NO PATH EXISTS",
            )
            route = {
                "path": [],
                "path_str": "NO PATH EXISTS",
                "cost": float("inf"),
                "hops": [],
                "hop_count": 0,
                "ml_adjusted": ml_adjusted,
                "status": "NO_PATH",
                "source": source,
                "destination": destination,
                "timestamp": time.time(),
                "formula": self.ML_RISK_FORMULA,
            }
            self.current_routes[route_key] = route
            return route

        hops = explain_path(path, graph, self.links)

        old_route = self.current_routes.get(route_key)

        route = {
            "path": path,
            "path_str": " → ".join(path),
            "cost": round(cost, 4),
            "hops": hops,
            "hop_count": len(path) - 1,
            "ml_adjusted": ml_adjusted,
            "status": "ACTIVE",
            "source": source,
            "destination": destination,
            "timestamp": time.time(),
            "formula": self.ML_RISK_FORMULA,
        }

        # Detect route change
        if old_route and old_route.get("path") != path:
            self._emit_event(
                "SUCCESS",
                f"Route CHANGED: {source} → {destination}",
                f"New: {route['path_str']}",
            )
            self.route_history.append(
                {
                    "timestamp": time.time(),
                    "source": source,
                    "destination": destination,
                    "old_path": old_route.get("path_str", ""),
                    "new_path": route["path_str"],
                    "reason": "topology/ml_change",
                }
            )

        self.current_routes[route_key] = route
        return route

    def recalculate_all_routes(self) -> List[dict]:
        """Recalculate every currently tracked route."""
        results = []
        for key, info in list(self.current_routes.items()):
            route = self.calculate_route(info["source"], info["destination"])
            results.append(route)
        return results

    def get_routing_table(self) -> dict:
        """Return the full shortest-path routing table for all node pairs."""
        graph = build_graph_from_topology(
            self.nodes, self.links, failed_links=self.failed_links
        )
        return all_pairs_shortest_paths(graph, self.failed_links)

    # ─────────────────────────── Comparison ─────────────────────────────── #

    def compare_routing_strategies(
        self, source: str, destination: str
    ) -> dict:
        """
        Compare three routing strategies for the same source/destination.
        Returns metrics for static, plain-Dijkstra, and ML-Dijkstra routing.
        """
        # Static: use only hop count (weight=1 for every link)
        static_graph: Dict[str, Dict[str, float]] = {}
        for node in self.nodes:
            static_graph[node["id"]] = {}
        for lnk in self.links:
            if lnk.get("status") != "failed":
                static_graph[lnk["source"]][lnk["target"]] = 1.0
                static_graph[lnk["target"]][lnk["source"]] = 1.0

        static_path, static_cost = dijkstra(
            static_graph, source, destination, self.failed_links
        )

        # Plain Dijkstra (base cost, no ML) — calculate once
        plain_route = self.calculate_route(source, destination, ml_adjusted=False)
        plain_path = plain_route["path"]
        plain_cost = plain_route["cost"]

        # ML-aware Dijkstra
        ml_route = self.calculate_route(source, destination, ml_adjusted=True)

        return {
            "static": {
                "path": static_path,
                "path_str": " → ".join(static_path) if static_path else "N/A",
                "cost": static_cost,
                "method": "Static (hop count)",
            },
            "dijkstra": {
                "path": plain_path,
                "path_str": " → ".join(plain_path) if plain_path else "N/A",
                "cost": plain_cost,
                "method": "Dijkstra (base cost)",
            },
            "ml_dijkstra": {
                "path": ml_route["path"],
                "path_str": ml_route["path_str"],
                "cost": ml_route["cost"],
                "method": "ML-Aware Dijkstra",
            },
        }

    # ─────────────────────────── Events ─────────────────────────────────── #

    def _emit_event(self, level: str, title: str, detail: str):
        event = {
            "id": len(self.events),
            "level": level,
            "title": title,
            "detail": detail,
            "timestamp": time.time(),
            "time_str": time.strftime("%H:%M:%S"),
        }
        self.events.append(event)
        # Keep only the last 200 events
        if len(self.events) > 200:
            self.events = self.events[-200:]
        logger.info("[%s] %s — %s", level, title, detail)

    def get_events(self, limit: int = 50) -> List[dict]:
        return list(reversed(self.events[-limit:]))

    # ─────────────────────────── Helpers ────────────────────────────────── #

    def _invalidate_routes_using_link(self, u: str, v: str):
        """Remove cached routes that pass through the failed link."""
        to_remove = []
        for key, route in self.current_routes.items():
            path = route.get("path", [])
            for i in range(len(path) - 1):
                if (path[i] == u and path[i + 1] == v) or (
                    path[i] == v and path[i + 1] == u
                ):
                    to_remove.append(key)
                    break
        for key in to_remove:
            del self.current_routes[key]

    def get_network_stats(self) -> dict:
        active_links = [
            lnk for lnk in self.links if lnk.get("status") != "failed"
        ]
        failed = [lnk for lnk in self.links if lnk.get("status") == "failed"]
        avg_risk = (
            sum(lnk.get("ml_risk", 0) for lnk in active_links) / len(active_links)
            if active_links
            else 0.0
        )
        return {
            "total_nodes": len(self.nodes),
            "active_nodes": sum(
                1 for n in self.nodes if n.get("status", "active") == "active"
            ),
            "total_links": len(self.links),
            "active_links": len(active_links),
            "failed_links": len(failed),
            "active_routes": len(self.current_routes),
            "route_changes": len(self.route_history),
            "average_ml_risk": round(avg_risk, 4),
            "last_updated": self._last_updated,
        }
