"""
OpenFlow Protocol Definitions & Flow Rule Models
Part of: ML-Enhanced SDN Emergency Communication Network

Represents OpenFlow v1.3 messages, flow table entries,
match criteria, actions, and pipeline processing concepts.
"""
from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Dict, Any, List, Optional


class OFPActionType(str, Enum):
    OUTPUT = "OUTPUT"
    SET_FIELD = "SET_FIELD"
    DROP = "DROP"
    FLOOD = "FLOOD"
    CONTROLLER = "CONTROLLER"


class OFPType(str, Enum):
    HELLO = "OFPT_HELLO"
    PACKET_IN = "OFPT_PACKET_IN"
    FLOW_MOD = "OFPT_FLOW_MOD"
    PACKET_OUT = "OFPT_PACKET_OUT"
    STATS_REQUEST = "OFPT_STATS_REQUEST"
    STATS_REPLY = "OFPT_STATS_REPLY"


@dataclass
class OFPMatch:
    in_port: Optional[int] = None
    eth_src: Optional[str] = None
    eth_dst: Optional[str] = None
    eth_type: int = 0x0800  # IPv4
    ipv4_src: Optional[str] = None
    ipv4_dst: Optional[str] = None
    ip_proto: Optional[int] = 6  # TCP

    def to_dict(self) -> Dict[str, Any]:
        d = {"eth_type": hex(self.eth_type)}
        if self.in_port is not None:
            d["in_port"] = self.in_port
        if self.eth_src:
            d["eth_src"] = self.eth_src
        if self.eth_dst:
            d["eth_dst"] = self.eth_dst
        if self.ipv4_src:
            d["ipv4_src"] = self.ipv4_src
        if self.ipv4_dst:
            d["ipv4_dst"] = self.ipv4_dst
        if self.ip_proto:
            d["ip_proto"] = "TCP" if self.ip_proto == 6 else str(self.ip_proto)
        return d


@dataclass
class OFPAction:
    action_type: OFPActionType
    port: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        res = {"type": self.action_type.value}
        if self.port is not None:
            res["port"] = self.port
        return res


@dataclass
class OFPFlowEntry:
    table_id: int = 0
    priority: int = 100
    cookie: int = 0
    match: OFPMatch = field(default_factory=OFPMatch)
    actions: List[OFPAction] = field(default_factory=list)
    idle_timeout: int = 0
    hard_timeout: int = 0
    packet_count: int = 0
    byte_count: int = 0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "table_id": self.table_id,
            "priority": self.priority,
            "cookie": hex(self.cookie),
            "match": self.match.to_dict(),
            "actions": [a.to_dict() for a in self.actions],
            "packet_count": self.packet_count,
            "byte_count": self.byte_count,
            "duration_sec": round(time.time() - self.created_at, 1),
        }
