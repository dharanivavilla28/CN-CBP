"""
Medical Host Server (Standalone TCP Socket Listener)
Part of: ML-Enhanced SDN Emergency Communication Network

Listens on TCP port 9102 (representing Medical Room 10.0.0.2).
Run standalone to demonstrate real socket reception:
    python backend/network/medical_server.py
"""
import json
import socket
import sys

HOST = "127.0.0.1"
PORT = 9102

print(f"=====================================================")
print(f"  Medical Room Host (10.0.0.2) TCP Socket Listener  ")
print(f"  Listening on {HOST}:{PORT}...                      ")
print(f"=====================================================")

try:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen()
        while True:
            conn, addr = s.accept()
            with conn:
                data = conn.recv(4096)
                if data:
                    try:
                        msg = json.loads(data.decode("utf-8"))
                        print(f"\n[ALERT RECEIVED] From: {msg.get('source')} ({msg.get('source_ip')})")
                        print(f"  Priority: {msg.get('priority')}")
                        print(f"  Message:  {msg.get('message')}")
                        print(f"  Route:    {' -> '.join(msg.get('route_path', []))}")
                        ack = json.dumps({"status": "DELIVERED", "host": "Medical"}).encode("utf-8")
                        conn.sendall(ack)
                    except Exception as e:
                        print("Raw data:", data.decode("utf-8", errors="ignore"))
except KeyboardInterrupt:
    print("\nMedical host server shut down.")
    sys.exit(0)
