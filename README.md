# ML-Enhanced Software Defined Emergency Communication Network with Dynamic Fault-Aware Routing

A complete, production-grade Computer Networks Capstone Project (CBP) implementing an SDN-based virtual emergency communication network with manual Dijkstra shortest-path routing, real Python TCP socket communication, OpenFlow 1.3 flow-table installation, dynamic link-state cost adaptation via a machine learning classifier trained on network traffic data (CICIDS2017), and two separate specialized web user interfaces.

---

## 1. Project Overview

During campus emergencies (fires, natural disasters, active security alerts), traditional communication networks suffer from congestion, packet loss, or physical link severed conditions. This project designs and implements an intelligent **Software-Defined Emergency Communication Network** that guarantees fault-tolerant communication between critical zones:
- **Security Post** (`10.0.0.1`)
- **Medical Room** (`10.0.0.2`)
- **Admin Building** (`10.0.0.3`)
- **Main Gate** (`10.0.0.4`)
- **Back Gate** (`10.0.0.5`)
- **Emergency Control Room** (`10.0.0.6`)

The network uses an SDN control plane to monitor link telemetry (throughput, latency, packet loss, buffer drops). A Machine Learning engine predicts link congestion risk and converts it into dynamic routing penalties. When trunk links fail or degrade, manual Dijkstra routing recalculates optimal paths and installs updated OpenFlow flow rules in switches, re-routing critical alerts over alternate paths without packet drop.

---

## 2. Architecture

```
                ┌──────────────────────────────────────────────┐
                │                     UI 1                     │
                │        Network Monitoring Dashboard          │
                │                 /dashboard                   │
                └──────────────────────┬───────────────────────┘
                                       │ WebSocket & REST
                ┌──────────────────────▼───────────────────────┐
                │                 Backend API                  │
                │             FastAPI + WebSockets             │
                └──────────────────────┬───────────────────────┘
                                       │
          ┌────────────────────────────┼───────────────────────────┐
          │                            │                           │
          ▼                            ▼                           ▼
   SDN Controller                ML Prediction               Routing Engine
  Ryu/OpenFlow v1.3             Random Forest            Manual Dijkstra O(E log V)
  Flow Mod Installation       CICIDS2017 Pipeline        Cost: base * (1 + risk)
          │                            │                           │
          └────────────────────────────┼───────────────────────────┘
                                       │
                                       ▼
                     Mininet Virtual Network / Emulated Mesh
                                       │
                ┌──────────────────────┼───────────────────────┐
                │                      │                       │
               S1                     S2                      S3
        (Core West Switch)     (Core North Switch)    (Core South Switch)
                │                      │                       │
          Security/Control          Medical                Main Gate
                                       │
                                       ▼
                ┌──────────────────────────────────────────────┐
                │                     UI 2                     │
                │         Topology & Routing Dashboard         │
                │                  /topology                   │
                └──────────────────────────────────────────────┘
```

---

## 3. Technologies Used

- **Frontend**:
  - React 19 + Vite 8
  - Tailwind CSS v4
  - React Flow (Interactive custom topology graph)
  - Recharts (Real-time telemetry and KPI area charts)
  - Lucide React (Visual identity icons for security, medical, switches, etc.)
  - React Router DOM (Route segregation)
- **Backend**:
  - Python 3.12+
  - FastAPI (REST endpoints and OpenAPI specification)
  - WebSockets (Real-time push notifications at 1.5s intervals)
  - Uvicorn (ASGI web server)
- **SDN**:
  - OpenFlow 1.3 message and flow-table definitions
  - Mininet custom topology (`EmergencyCampusTopo`)
  - Ryu SDN controller REST bridge
- **Routing**:
  - Dijkstra shortest path algorithm implemented manually from scratch with a min-heap priority queue
  - Dynamic link weights using ML risk multipliers
- **Machine Learning**:
  - scikit-learn (RandomForestClassifier, StandardScaler, LabelEncoder)
  - pandas & numpy (Data processing pipeline)
  - joblib (Model serialization)
  - Dataset: CICIDS2017 with realistic synthetic fallback generator

---

## 4. Installation

### Prerequisites
- Node.js (v18+)
- Python (v3.10+)

### Setup Commands
```bash
# Clone the repository and navigate into the workspace
cd "ML-Enhanced-SDN-Emergency-Network"

# Run setup script
# On Linux / Mac:
chmod +x scripts/*.sh
./scripts/setup.sh

# On Windows:
# 1. Install backend requirements:
pip install fastapi uvicorn scikit-learn pandas numpy joblib websockets requests

# 2. Train the ML model:
cd backend
python -m ml.train
cd ..

# 3. Install frontend dependencies:
cd frontend
npm install
cd ..
```

---

## 5. Dataset Setup

The ML pipeline is designed for the **CICIDS2017** benchmark intrusion and traffic dataset.
To use raw CSV files from CICIDS2017:
1. Place CSV files (e.g. `Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv`) inside `backend/data/raw/`.
2. Run `python -m ml.train` from `backend/`.
3. If no CSVs are provided, the system automatically uses `generate_synthetic_dataset()` which generates 15,000 realistic records matching CICIDS2017 feature distributions, clearly labeled in metadata.

---

## 6. Machine Learning Pipeline & Training

Run model training:
```bash
cd backend
python -m ml.train
```

### Preprocessing Steps:
1. Extracts 17 core traffic features (`Flow Duration`, `Total Fwd Packets`, `Flow Bytes/s`, `Flow Packets/s`, `Flow IAT Mean`, `Packet Length Mean`, etc.).
2. Handles infinite values (`np.inf`) and imputes median values for missing data.
3. Quantile capping (99th percentile) to handle extreme outliers.
4. Categorical label encoding into 3 classes: `NORMAL`, `CONGESTED`, `HIGH_RISK`.
5. Feature scaling using `StandardScaler`.
6. Stratified 80/20 train/test split.
7. Trains a `RandomForestClassifier` with balanced class weights.
8. Evaluates Accuracy, Precision, Recall, F1-score, and Confusion Matrix, and saves artefacts to `backend/data/models/`.

---

## 7. Mininet Setup

For running on an Ubuntu / SDN Virtual Machine:
```bash
sudo mn -c  # Clean existing topologies
sudo python3 mininet/topology.py
```
This builds:
- 4 OpenvSwitch switches (`s1`, `s2`, `s3`, `s4`) configured for OpenFlow 1.3
- 6 emergency hosts with assigned IPs (`10.0.0.1` - `10.0.0.6`)
- Configurable bandwidth, latency, and packet loss on links via Linux Traffic Control (`tc`)

---

## 8. Ryu SDN Controller Setup

If running Ryu in REAL SDN mode:
```bash
ryu-manager ryu.app.rest_topology ryu.app.ofctl_rest ryu.app.simple_switch_13
```
The FastAPI backend seamlessly connects to Ryu's REST API at `http://localhost:8080/stats/flowentry/add` to install physical OpenFlow rules.

---

## 9. Running the Backend

```bash
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
Interactive API documentation available at:
`http://localhost:8000/docs`

---

## 10. Running the Frontend

```bash
cd frontend
npm run dev
```
Access the application at:
`http://localhost:5173`

---

## 11. Running in Simulation Mode

If Mininet or Ryu are unavailable (e.g. running on Windows or standard laptops without Linux kernel OpenvSwitch):
- The system automatically runs in **SIMULATION MODE**.
- The UI displays `SIMULATION DATA` and `SIMULATION MODE`.
- The simulation emulates:
  - Exact OpenFlow flow-table matching (`dst_ip` → `output_port`)
  - Live link telemetry (latency, packet loss, bandwidth utilization)
  - Link failure and dynamic Dijkstra re-routing
  - Real Python TCP socket transmissions across loopback ports (`9101`-`9106`)

---

## 12. Running in Real SDN Mode

When connected to a live Ryu controller and Mininet network:
- Change mode via config or environment variable `SDN_MODE=REAL`.
- Flow modifications are pushed directly to OpenFlow switches over Ryu's REST API.

---

## 13. Creating Custom Topologies

In UI 2 (`/topology`):
- Click **"Add Node"**: Create new OpenFlow switches or Emergency hosts with custom IP and MAC addresses.
- Click **"Connect Nodes"**: Establish links between any two nodes with custom base costs, bandwidth (Mbps), and delay.
- Click on any node or link in the canvas and press **"Delete"** in the Inspector to remove it.
- Click **"Reset Topology"** to restore default campus topology.

---

## 14. Sending Emergency Messages

In UI 2 (`/topology`):
1. Select **Source** (e.g. `Security`).
2. Select **Destination** (e.g. `Medical Room`).
3. Enter message payload (e.g. `FIRE ALERT AT MAIN GATE`).
4. Select Priority: `Normal`, `Emergency`, or `Critical`.
5. Click **"SEND"**.
6. The system executes Dijkstra, verifies path viability, transmits the packet via real Python TCP sockets, and displays an animated traveling packet across the graph.

---

## 15. Testing Link Failure

1. In UI 2 (`/topology`), locate the **"Fault Injection & Recovery"** panel.
2. Select target trunk link (e.g. `S1-S2`).
3. Click **"FAIL LINK"**.
4. The link turns **RED dashed** (`S1 ─── X ─── S2`).
5. A `LINK_FAILED` event is broadcast.
6. The routing engine recalculates routes and immediately diverts traffic through alternate trunk switches (e.g. `S1 → S3 → S4 → S2`).
7. A "ROUTE CHANGED" alert banner explains the re-routing reason.

---

## 16. Testing Route Recovery

1. With the link failed, click **"RESTORE"**.
2. The link status reverts to `ACTIVE` (Cyan).
3. The routing engine recalculates Dijkstra costs and reinstates the original minimum cost path.

---

## 17. ML Pipeline & Cost Formula

The ML model predicts link failure and congestion probabilities:
```
adjusted_cost = base_cost × (1 + ml_risk)
```
- When `ml_risk = 0%`: `adjusted_cost = base_cost × 1.0 = 2.0`
- When traffic surges on trunk `S1-S2` and `ml_risk = 85%`: `adjusted_cost = 2.0 × (1 + 0.85) = 3.70`
- If an alternate path (e.g. `S1 → S3 → S4 → Medical`, cost = 3.50) has a lower combined cost, Dijkstra automatically switches to the alternate path **before packet loss occurs**.

---

## 18. Manual Dijkstra Implementation

Located in `backend/routing/dijkstra.py`:
- Implemented manually using Python's `heapq` min-heap.
- Time complexity: $O(E \log V)$ where $V$ is vertices and $E$ is edges.
- Supports exclusion of failed links dynamically.
- Returns reconstructed node path, total path cost, and per-hop metrics.

---

## 19. OpenFlow Flow Rules

The SDN controller creates flow table entries:
```json
{
  "switch": "S1",
  "match": { "dst_ip": "10.0.0.2" },
  "action": { "output_port": "port-to-S2" },
  "priority": 100
}
```
When route changes, the controller clears stale entries and installs new forwarding rules for every switch along the computed Dijkstra path.

---

## 20. Real TCP Socket Communication

Demonstrated via:
- In-process TCP socket servers bound to ports `9101`-`9106` in `backend/network/sockets.py`.
- Standalone host scripts:
  - `python backend/network/medical_server.py`
  - `python backend/network/security_client.py "FIRE ALERT AT MAIN GATE"`

---

## 21. API Documentation

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/status` | Controller, network, and ML engine online status |
| `GET` | `/api/topology` | Nodes, links, and failed links |
| `GET` | `/api/network-stats` | 8 KPI metrics and historical telemetry |
| `GET` | `/api/ml/prediction` | Predictions for all active links |
| `GET` | `/api/ml/info` | Trained model metadata and metrics |
| `POST` | `/api/messages/send` | Transmit emergency message via TCP socket |
| `POST` | `/api/links/fail` | Mark link as failed |
| `POST` | `/api/links/restore` | Restore previously failed link |
| `POST` | `/api/topology/node` | Add custom host or switch |
| `DELETE` | `/api/topology/node/{id}` | Delete node from topology |
| `POST` | `/api/topology/link` | Add custom link |
| `DELETE` | `/api/topology/link/{id}` | Delete link from topology |
| `GET` | `/api/routing/compare` | Compare Static vs Dijkstra vs ML-Dijkstra |
| `POST` | `/api/scenario/run` | Run the 14-step automated CBP evaluation scenario |
| `WS` | `/ws/network` | Live WebSocket streaming telemetry |

---

## 22. Project Limitations

1. **Host-scale**: Default campus topology is designed for 10 nodes; large networks with >1000 nodes would require distributed hierarchical SDN controllers.
2. **Mininet OS compatibility**: Real OpenvSwitch kernel modules require Linux; on Windows, high-fidelity socket emulation and simulation mode are utilized.
3. **Bandwidth QoS**: Dynamic cost penalization avoids congested links, but packet queuing disciplines (DiffServ / WFQ) require hardware OVS queues.

---

## 23. Future Improvements

1. Multi-controller SDN synchronization via Raft consensus (ONOS/OpenDaylight).
2. Deep Reinforcement Learning (PPO/DQN) for real-time proactive traffic engineering.
3. P4 programmable data-plane hardware integration.
4. Cryptographic HMAC authentication for emergency alert packets.
