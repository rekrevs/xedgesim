#!/usr/bin/env python3
"""
echo_service.py - Simple Echo Service for Docker Socket Testing

Receives JSON events via TCP socket and echoes them back.
Used to test coordinator ↔ container socket communication.
"""

import socket
import json
import sys


def main():
    """Run echo service listening on TCP port 5000."""
    # Create TCP socket
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('0.0.0.0', 5000))
    server.listen(1)

    print("Echo service listening on 0.0.0.0:5000", flush=True)

    # Accept connection from coordinator
    conn, addr = server.accept()
    print(f"Connected by {addr}", flush=True)

    buffer = ""

    try:
        while True:
            # Read data
            data = conn.recv(4096).decode('utf-8')
            if not data:
                print("Connection closed by client", flush=True)
                break

            # Add to buffer
            buffer += data

            # Process complete messages (line-delimited JSON)
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                if line.strip():
                    try:
                        # Parse JSON
                        event = json.loads(line)
                        print(f"Received: {event}", flush=True)

                        # Echo back
                        response = json.dumps(event) + '\n'
                        conn.sendall(response.encode('utf-8'))
                        print(f"Echoed back: {event}", flush=True)

                    except json.JSONDecodeError as e:
                        print(f"Invalid JSON: {line}: {e}", flush=True)

    except Exception as e:
        print(f"Error: {e}", flush=True)
    finally:
        conn.close()
        server.close()


if __name__ == '__main__':
    main()
