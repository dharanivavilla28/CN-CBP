"""
Dijkstra's Shortest Path Algorithm - Manual Implementation
Part of: ML-Enhanced SDN Emergency Communication Network
"""
import heapq
from typing import Dict, List, Tuple, Optional, Set


def dijkstra(
    graph: Dict[str, Dict[str, float]],
    source: str,
    destination: str,
    failed_links: Optional[Set[Tuple[str, str]]] = None,
) -> Tuple[Optional[List[str]], float]:
    """
    Manual implementation of Dijkstra's shortest-path algorithm.

    Args:
        graph: Adjacency dict {node: {neighbor: weight, ...}, ...}
        source: Starting node ID
        destination: Target node ID
        failed_links: Set of (u, v) tuples representing failed/disabled links

    Returns:
        (path_list, total_cost) or (None, inf) if no path exists

    Algorithm:
        1. Initialize distances to infinity for all nodes except source (0).
        2. Use a min-heap priority queue for O(E log V) complexity.
        3. For each extracted node, relax edges to neighbours.
        4. Track predecessors to reconstruct the path.
        5. Stop early when destination is settled.
    """
    if failed_links is None:
        failed_links = set()

    # Step 1 – initialise
    INF = float("inf")
    dist: Dict[str, float] = {node: INF for node in graph}
    prev: Dict[str, Optional[str]] = {node: None for node in graph}

    if source not in graph:
        return None, INF
    if destination not in graph:
        return None, INF

    dist[source] = 0.0

    # Priority queue: (distance, node)
    pq: List[Tuple[float, str]] = [(0.0, source)]
    visited: Set[str] = set()

    while pq:
        # Step 2 – extract minimum
        current_dist, u = heapq.heappop(pq)

        if u in visited:
            continue
        visited.add(u)

        # Early termination
        if u == destination:
            break

        # Step 3 – relax edges
        for v, weight in graph.get(u, {}).items():
            # Skip failed links (bidirectional check)
            if (u, v) in failed_links or (v, u) in failed_links:
                continue

            alt = current_dist + weight
            if alt < dist.get(v, INF):
                dist[v] = alt
                prev[v] = u
                heapq.heappush(pq, (alt, v))

    # Step 4 – reconstruct path
    if dist[destination] == INF:
        return None, INF  # No path found

    path: List[str] = []
    current: Optional[str] = destination
    while current is not None:
        path.append(current)
        current = prev[current]
    path.reverse()

    return path, dist[destination]


def all_pairs_shortest_paths(
    graph: Dict[str, Dict[str, float]],
    failed_links: Optional[Set[Tuple[str, str]]] = None,
) -> Dict[str, Dict[str, Tuple[Optional[List[str]], float]]]:
    """
    Run Dijkstra from every node to build a full routing table.
    Returns: {source: {destination: (path, cost)}}
    """
    results = {}
    for source in graph:
        results[source] = {}
        for destination in graph:
            if source != destination:
                path, cost = dijkstra(graph, source, destination, failed_links)
                results[source][destination] = (path, cost)
    return results


def build_graph_from_topology(
    nodes: List[dict],
    links: List[dict],
    failed_links: Optional[Set[Tuple[str, str]]] = None,
    ml_adjusted: bool = True,
) -> Dict[str, Dict[str, float]]:
    """
    Convert the topology data structures into a weighted adjacency dict.

    Link weight = base_cost * (1 + ml_risk)   [ML-aware Dijkstra]
    """
    if failed_links is None:
        failed_links = set()

    graph: Dict[str, Dict[str, float]] = {}

    # Initialise every node
    for node in nodes:
        graph[node["id"]] = {}

    for link in links:
        src = link["source"]
        dst = link["target"]

        # Skip failed links
        if (src, dst) in failed_links or (dst, src) in failed_links:
            continue
        if link.get("status") == "failed":
            continue

        base_cost = link.get("cost", 1.0)
        ml_risk = link.get("ml_risk", 0.0)  # 0.0–1.0

        if ml_adjusted:
            # ML-aware cost: adjusted_cost = base_cost * (1 + ml_risk)
            effective_cost = base_cost * (1.0 + ml_risk)
        else:
            effective_cost = base_cost

        # Add bidirectional edges
        graph[src][dst] = effective_cost
        graph[dst][src] = effective_cost

    return graph


def explain_path(
    path: List[str],
    graph: Dict[str, Dict[str, float]],
    links: List[dict],
) -> List[dict]:
    """
    Return per-hop cost details for path explanation on the UI.
    """
    hops = []
    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        cost = graph.get(u, {}).get(v, 0.0)

        # Find matching link info
        link_info = {}
        for lnk in links:
            if (lnk["source"] == u and lnk["target"] == v) or (
                lnk["source"] == v and lnk["target"] == u
            ):
                link_info = lnk
                break

        hops.append(
            {
                "from": u,
                "to": v,
                "effective_cost": round(cost, 4),
                "base_cost": link_info.get("cost", 1.0),
                "ml_risk": link_info.get("ml_risk", 0.0),
                "latency": link_info.get("latency", 0),
                "bandwidth": link_info.get("bandwidth", 100),
                "status": link_info.get("status", "active"),
            }
        )
    return hops
