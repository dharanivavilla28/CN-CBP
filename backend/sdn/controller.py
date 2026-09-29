"""
SDN Controller Simulation
Part of: ML-Enhanced SDN Emergency Communication Network

Simulates the role of an SDN controller (Ryu/OpenFlow concepts).
Maintains switch/flow tables, topology discovery, and flow installation.
When Ryu is available, this module bridges to real OpenFlow.
"""
import logging
import time
import uuid
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class OpenFlowRule:
    """
    Represents an OpenFlow flow table entry.
    Match: destination IP → Action: output port
    """

    def __init__(
        self,
        switch_id: str,
        match_dst_ip: str,
        out_port: str,
        priority: int = 100,
        cookie: Optional[str] = None,
    ):
        self.id = cookie or str(uuid.uuid4())[:8]
        self.switch_id = switch_id
        self.match_dst_ip = match_dst_ip
        self.out_port = out_port
        self.priority = priority
        self.installed_at = time.time()
        self.packet_count = 0
        self.byte_count = 0

    def to_dict(self):
        return {
            "id": self.id,
            "switch": self.switch_id,
            "match": {"dst_ip": self.match_dst_ip},
            "action": {"output_port": self.out_port},
            "priority": self.priority,
            "installed_at": self.installed_at,
            "packet_count": self.packet_count,
            "byte_count": self.byte_count,
        }


class SDNController:
    """
    Software Defined Networking controller simulation.

    Concepts implemented:
      - Topology discovery (switches, hosts, links)
      - Flow table management
      - OpenFlow flow installation / deletion
      - Link-state database
      - Packet statistics collection
      - Control plane / data plane separation

    In REAL mode:
      - Bridges to a running Ryu controller via REST API
    In SIMULATION mode:
      - Maintains all state in-memory
    """

    MODE_SIMULATION = "SIMULATION"
    MODE_REAL = "REAL"

    def __init__(self, mode: str = MODE_SIMULATION, ryu_url: str = "http://localhost:8080"):
        self.mode = mode
        self.ryu_url = ryu_url

        # Topology state (populated by routing engine/simulation)
        self.switches: Dict[str, dict] = {}
        self.hosts: Dict[str, dict] = {}
        self.ports: Dict[str, List[dict]] = {}  # switch_id → port list

        # Flow tables: switch_id → list of rules
        self.flow_tables: Dict[str, List[OpenFlowRule]] = {}

        # Link-state database
        self.link_state: Dict[str, dict] = {}  # link_id → metrics

        # Packet statistics
        self.stats: Dict[str, dict] = {}  # switch_id → stats

        # Controller events
        self.events: List[dict] = []

        self._total_flows_installed = 0

        logger.info("SDN Controller initialised — mode: %s", mode)

    # ─────────────────────────── Topology Discovery ─────────────────────── #

    def register_switch(self, switch_id: str, dp_id: int = 0, ports: int = 4):
        self.switches[switch_id] = {
            "id": switch_id,
            "datapath_id": dp_id or hash(switch_id) % 0xFFFFFFFFFFFF,
            "connected": True,
            "port_count": ports,
            "connected_at": time.time(),
        }
        self.flow_tables[switch_id] = []
        self.ports[switch_id] = [
            {"port_no": i + 1, "name": f"eth{i}", "state": "LIVE"}
            for i in range(ports)
        ]
        self._emit_event("INFO", f"Switch registered: {switch_id}", f"dp_id={dp_id}")

    def register_host(self, host_id: str, ip: str, mac: str, switch: str, port: int):
        self.hosts[host_id] = {
            "id": host_id,
            "ip": ip,
            "mac": mac,
            "connected_switch": switch,
            "port": port,
            "last_seen": time.time(),
        }

    def update_link_state(self, link_id: str, metrics: dict):
        self.link_state[link_id] = {**metrics, "updated_at": time.time()}

    # ─────────────────────────── Flow Management ────────────────────────── #

    def install_flow(
        self,
        switch_id: str,
        dst_ip: str,
        out_port: str,
        priority: int = 100,
    ) -> OpenFlowRule:
        """
        Install an OpenFlow forwarding rule on a switch.
        Match: dst_ip → Action: output to out_port
        """
        # Remove any existing rule for the same dst_ip on this switch
        self.delete_flow(switch_id, dst_ip)

        rule = OpenFlowRule(switch_id, dst_ip, out_port, priority)
        if switch_id not in self.flow_tables:
            self.flow_tables[switch_id] = []
        self.flow_tables[switch_id].append(rule)
        self._total_flows_installed += 1

        self._emit_event(
            "INFO",
            f"Flow installed: {switch_id}",
            f"dst={dst_ip} → port={out_port}",
        )

        if self.mode == self.MODE_REAL:
            self._push_flow_to_ryu(switch_id, dst_ip, out_port, priority)

        return rule

    def delete_flow(self, switch_id: str, dst_ip: str):
        if switch_id in self.flow_tables:
            before = len(self.flow_tables[switch_id])
            self.flow_tables[switch_id] = [
                r for r in self.flow_tables[switch_id]
                if r.match_dst_ip != dst_ip
            ]
            removed = before - len(self.flow_tables[switch_id])
            if removed:
                self._emit_event(
                    "WARNING",
                    f"Flow removed: {switch_id}",
                    f"dst={dst_ip} ({removed} rules)",
                )

    def install_path_flows(self, path: List[str], dst_ip: str, nodes: List[dict]):
        """
        Install forwarding rules for every switch in the path.
        Uses sequential port numbering based on path order.
        """
        switch_nodes = {n["id"]: n for n in nodes if n.get("type") == "switch"}

        for i, node_id in enumerate(path):
            if node_id not in switch_nodes:
                continue
            # Next hop in path (find the output port)
            if i + 1 < len(path):
                next_hop = path[i + 1]
                out_port = f"port-to-{next_hop}"
            else:
                out_port = "LOCAL"

            self.install_flow(node_id, dst_ip, out_port)

        self._emit_event(
            "SUCCESS",
            f"Path flows installed for dst={dst_ip}",
            f"Path: {' → '.join(path)}",
        )

    def get_flow_table(self, switch_id: str) -> List[dict]:
        return [r.to_dict() for r in self.flow_tables.get(switch_id, [])]

    def get_all_flow_tables(self) -> dict:
        return {sw: self.get_flow_table(sw) for sw in self.flow_tables}

    # ─────────────────────────── Statistics ─────────────────────────────── #

    def collect_stats(self, switch_id: str) -> dict:
        """Simulate / collect packet/byte statistics for a switch."""
        import random
        existing = self.stats.get(switch_id, {
            "tx_packets": 0, "rx_packets": 0,
            "tx_bytes": 0, "rx_bytes": 0,
            "drops": 0,
        })
        # Increment with realistic deltas
        delta_pkts = random.randint(50, 500)
        delta_bytes = delta_pkts * random.randint(64, 1500)
        existing["tx_packets"] += delta_pkts
        existing["rx_packets"] += delta_pkts
        existing["tx_bytes"] += delta_bytes
        existing["rx_bytes"] += delta_bytes
        existing["drops"] += random.randint(0, 2)
        existing["updated_at"] = time.time()
        self.stats[switch_id] = existing
        return existing

    def get_network_stats_summary(self) -> dict:
        total_pkts = sum(s.get("rx_packets", 0) for s in self.stats.values())
        total_bytes = sum(s.get("rx_bytes", 0) for s in self.stats.values())
        total_flows = sum(len(v) for v in self.flow_tables.values())
        return {
            "mode": self.mode,
            "switches": len(self.switches),
            "hosts": len(self.hosts),
            "active_flows": total_flows,
            "total_flows_installed": self._total_flows_installed,
            "total_packets": total_pkts,
            "total_bytes": total_bytes,
            "link_states": len(self.link_state),
        }

    # ─────────────────────────── Ryu Bridge ─────────────────────────────── #

    def _push_flow_to_ryu(self, switch_id: str, dst_ip: str, out_port: str, priority: int):
        """Push flow mod to real Ryu controller (only in REAL mode)."""
        try:
            import requests
            dp_id = self.switches.get(switch_id, {}).get("datapath_id", 1)
            url = f"{self.ryu_url}/stats/flowentry/add"
            payload = {
                "dpid": dp_id,
                "priority": priority,
                "match": {"nw_dst": dst_ip, "dl_type": 0x0800},
                "actions": [{"type": "OUTPUT", "port": out_port}],
            }
            resp = requests.post(url, json=payload, timeout=2)
            if resp.status_code != 200:
                logger.warning("Ryu flow install failed: %s", resp.text)
        except Exception as exc:
            logger.error("Cannot reach Ryu controller: %s", exc)

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
        if len(self.events) > 200:
            self.events = self.events[-200:]

    def get_events(self, limit: int = 30) -> List[dict]:
        return list(reversed(self.events[-limit:]))
