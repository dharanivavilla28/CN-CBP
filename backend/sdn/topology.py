"""
SDN Network Topology Definitions
Part of: ML-Enhanced SDN Emergency Communication Network

Defines the default campus emergency communication topology:
Emergency hosts:
  - Security (10.0.0.1)
  - Medical Room (10.0.0.2)
  - Admin (10.0.0.3)
  - Main Gate (10.0.0.4)
  - Back Gate (10.0.0.5)
  - Emergency Control (10.0.0.6)

Switches:
  - S1, S2, S3, S4
"""
from typing import Dict, Any, List

DEFAULT_HOSTS = [
    {
        "id": "Security",
        "label": "Security Post",
        "type": "host",
        "category": "security",
        "ip": "10.0.0.1",
        "mac": "00:00:00:00:00:01",
        "status": "active",
        "icon": "Shield",
        "connected_switch": "S1",
        "port": 1,
    },
    {
        "id": "Medical",
        "label": "Medical Room",
        "type": "host",
        "category": "medical",
        "ip": "10.0.0.2",
        "mac": "00:00:00:00:00:02",
        "status": "active",
        "icon": "Cross",
        "connected_switch": "S2",
        "port": 1,
    },
    {
        "id": "Admin",
        "label": "Admin Building",
        "type": "host",
        "category": "admin",
        "ip": "10.0.0.3",
        "mac": "00:00:00:00:00:03",
        "status": "active",
        "icon": "Building",
        "connected_switch": "S4",
        "port": 1,
    },
    {
        "id": "MainGate",
        "label": "Main Gate",
        "type": "host",
        "category": "gate",
        "ip": "10.0.0.4",
        "mac": "00:00:00:00:00:04",
        "status": "active",
        "icon": "DoorOpen",
        "connected_switch": "S3",
        "port": 1,
    },
    {
        "id": "BackGate",
        "label": "Back Gate",
        "type": "host",
        "category": "gate",
        "ip": "10.0.0.5",
        "mac": "00:00:00:00:00:05",
        "status": "active",
        "icon": "DoorClosed",
        "connected_switch": "S4",
        "port": 2,
    },
    {
        "id": "ControlRoom",
        "label": "Emergency Control",
        "type": "host",
        "category": "control",
        "ip": "10.0.0.6",
        "mac": "00:00:00:00:00:06",
        "status": "active",
        "icon": "Radio",
        "connected_switch": "S1",
        "port": 2,
    },
]

DEFAULT_SWITCHES = [
    {
        "id": "S1",
        "label": "SDN Switch 1 (Core West)",
        "type": "switch",
        "dpid": "0000000000000001",
        "status": "active",
        "ports": 4,
    },
    {
        "id": "S2",
        "label": "SDN Switch 2 (Core North)",
        "type": "switch",
        "dpid": "0000000000000002",
        "status": "active",
        "ports": 4,
    },
    {
        "id": "S3",
        "label": "SDN Switch 3 (Core South)",
        "type": "switch",
        "dpid": "0000000000000003",
        "status": "active",
        "ports": 4,
    },
    {
        "id": "S4",
        "label": "SDN Switch 4 (Core East)",
        "type": "switch",
        "dpid": "0000000000000004",
        "status": "active",
        "ports": 4,
    },
]

DEFAULT_LINKS = [
    # Host-to-Switch access links (base cost 1.0)
    {
        "id": "Security-S1",
        "source": "Security",
        "target": "S1",
        "type": "access",
        "cost": 1.0,
        "base_cost": 1.0,
        "bandwidth": 100,  # Mbps
        "latency": 2.0,     # ms
        "packet_loss": 0.0,
        "ml_risk": 0.05,
        "status": "active",
    },
    {
        "id": "ControlRoom-S1",
        "source": "ControlRoom",
        "target": "S1",
        "type": "access",
        "cost": 1.0,
        "base_cost": 1.0,
        "bandwidth": 1000,
        "latency": 1.0,
        "packet_loss": 0.0,
        "ml_risk": 0.02,
        "status": "active",
    },
    {
        "id": "Medical-S2",
        "source": "Medical",
        "target": "S2",
        "type": "access",
        "cost": 1.0,
        "base_cost": 1.0,
        "bandwidth": 100,
        "latency": 2.5,
        "packet_loss": 0.0,
        "ml_risk": 0.04,
        "status": "active",
    },
    {
        "id": "MainGate-S3",
        "source": "MainGate",
        "target": "S3",
        "type": "access",
        "cost": 1.0,
        "base_cost": 1.0,
        "bandwidth": 100,
        "latency": 4.0,
        "packet_loss": 0.0,
        "ml_risk": 0.08,
        "status": "active",
    },
    {
        "id": "Admin-S4",
        "source": "Admin",
        "target": "S4",
        "type": "access",
        "cost": 1.0,
        "base_cost": 1.0,
        "bandwidth": 100,
        "latency": 3.0,
        "packet_loss": 0.0,
        "ml_risk": 0.06,
        "status": "active",
    },
    {
        "id": "BackGate-S4",
        "source": "BackGate",
        "target": "S4",
        "type": "access",
        "cost": 1.0,
        "base_cost": 1.0,
        "bandwidth": 100,
        "latency": 4.5,
        "packet_loss": 0.0,
        "ml_risk": 0.07,
        "status": "active",
    },
    # Inter-switch trunk links (mesh backbone)
    {
        "id": "S1-S2",
        "source": "S1",
        "target": "S2",
        "type": "trunk",
        "cost": 2.0,
        "base_cost": 2.0,
        "bandwidth": 1000,
        "latency": 8.0,
        "packet_loss": 0.01,
        "ml_risk": 0.15,
        "status": "active",
    },
    {
        "id": "S1-S3",
        "source": "S1",
        "target": "S3",
        "type": "trunk",
        "cost": 2.5,
        "base_cost": 2.5,
        "bandwidth": 1000,
        "latency": 9.5,
        "packet_loss": 0.01,
        "ml_risk": 0.10,
        "status": "active",
    },
    {
        "id": "S2-S4",
        "source": "S2",
        "target": "S4",
        "type": "trunk",
        "cost": 3.0,
        "base_cost": 3.0,
        "bandwidth": 1000,
        "latency": 11.0,
        "packet_loss": 0.02,
        "ml_risk": 0.12,
        "status": "active",
    },
    {
        "id": "S3-S4",
        "source": "S3",
        "target": "S4",
        "type": "trunk",
        "cost": 2.0,
        "base_cost": 2.0,
        "bandwidth": 1000,
        "latency": 8.5,
        "packet_loss": 0.01,
        "ml_risk": 0.14,
        "status": "active",
    },
    {
        "id": "S2-S3",
        "source": "S2",
        "target": "S3",
        "type": "trunk",
        "cost": 4.0,
        "base_cost": 4.0,
        "bandwidth": 500,
        "latency": 14.0,
        "packet_loss": 0.03,
        "ml_risk": 0.20,
        "status": "active",
    },
]


def get_default_topology() -> Dict[str, Any]:
    return {
        "nodes": DEFAULT_HOSTS + DEFAULT_SWITCHES,
        "links": [dict(l) for l in DEFAULT_LINKS],
    }
