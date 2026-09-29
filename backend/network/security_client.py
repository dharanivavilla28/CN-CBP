"""
Security Host Client (Standalone TCP Socket Sender)
Part of: ML-Enhanced SDN Emergency Communication Network

Sends an emergency message from Security (10.0.0.1) to Medical (10.0.0.2).
Run standalone to test real TCP socket message delivery:
    python backend/network/security_client.py "FIRE ALERT AT MAIN GATE"
"""
import json
import socket
import sys
import time

DEST_HOST = "127.0.0.1"
DEST_PORT = 9102

msg_text = sys.argv[1] if len(sys.argv) > 1 else "FIRE ALERT AT MAIN GATE"

payload = {
    "source": "Security",
    "source_ip": "10.0.0.1",
    "destination": "Medical",
    "destination_ip": "10.0.0.2",
    "message": msg_text,
    "priority": "CRITICAL",
    "protocol": "TCP",
    "sent_at": time.time(),
    "route_path": ["Security", "S1", "S2", "Medical"],
    "route_cost": 4.0,
}

print("=====================================================")
print(f"  Security Host (10.0.0.1) -> Medical (10.0.0.2)")
print(f"  Attempting TCP connect to {DEST_HOST}:{DEST_PORT}...")
print("=====================================================")

try:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(3.0)
        s.connect((DEST_HOST, DEST_PORT))
        s.sendall(json.dumps(payload).encode("utf-8"))
        ack = s.recv(1024)
        print("\n[SUCCESS] Server acknowledged:", ack.decode("utf-8"))
except Exception as e:
    print(f"\n[ERROR] Connection failed: {e}")
    print("Ensure backend or medical_server.py is running on port 9102.")
