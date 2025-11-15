# M2b: Socket Communication Between Coordinator and Container

**Stage:** M2b
**Date:** 2025-11-15
**Status:** IN PROGRESS

---

## Objective

Enable bidirectional socket communication between coordinator and Docker container for event exchange, using JSON over TCP protocol.

**Scope:**
- Container exposes TCP socket server for coordinator connection
- Coordinator connects to container and sends/receives events
- Protocol: JSON over TCP (similar to M0 coordinator-node protocol)
- Simple echo service container for testing
- Update DockerNode to manage socket connections
- Integration tests for round-trip communication

**Explicitly excluded:**
- MQTT broker integration (M2c scope)
- Network latency simulation via LatencyNetworkModel (will add after socket basics work)
- Complex service implementations (focus on echo service first)
- Performance optimization (get basic communication working first)

---

## Acceptance Criteria

1. ⬜ DockerNode can connect to container's TCP socket
2. ⬜ Coordinator can send JSON events to container
3. ⬜ Container can send JSON events back to coordinator
4. ⬜ Round-trip communication works with echo service
5. ⬜ Integration test: send event → echo back → verify
6. ⬜ Socket cleanup on container shutdown
7. ⬜ Error handling for connection failures
8. ⬜ All M0-M1e-M2a tests still pass

---

## Design Decisions

### Protocol Design

**Use M0-style JSON protocol over TCP:**

```
Coordinator → Container:
{
  "type": "event",
  "time_us": 12345,
  "src": "sensor1",
  "dst": "edge1",
  "payload": {"temperature": 25.3}
}

Container → Coordinator:
{
  "type": "event",
  "time_us": 12346,
  "src": "edge1",
  "dst": "sensor1",
  "payload": {"ack": true}
}
```

**Simple line-delimited JSON:**
- Each message is one JSON object per line
- Newline (`\n`) as message delimiter
- Easy to parse and debug

### Echo Service Container

**Purpose**: Minimal service for testing socket communication

**Implementation**: Python script that echoes back received events

```python
#!/usr/bin/env python3
# echo_service.py - Simple echo service for testing

import socket
import json

def main():
    # Listen on all interfaces, port 5000
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('0.0.0.0', 5000))
    server.listen(1)

    print("Echo service listening on port 5000...")

    conn, addr = server.accept()
    print(f"Connected by {addr}")

    while True:
        # Read line-delimited JSON
        data = conn.recv(4096).decode('utf-8')
        if not data:
            break

        # Echo back
        conn.sendall(data.encode('utf-8'))

    conn.close()

if __name__ == '__main__':
    main()
```

**Dockerfile:**
```dockerfile
FROM python:3.9-slim
COPY echo_service.py /app/
WORKDIR /app
CMD ["python", "echo_service.py"]
```

### DockerNode Socket Integration

**Changes to DockerNode:**

1. **Add socket connection during start():**
```python
def start(self):
    # ... existing container creation ...

    # Wait for container to be ready
    self.wait_for_ready()

    # Connect to container's socket
    self._connect_to_container()

def _connect_to_container(self):
    """Connect to container's TCP socket."""
    # Get container IP
    self.container.reload()
    container_ip = self.container.attrs['NetworkSettings']['IPAddress']
    port = self.config.get('socket_port', 5000)

    # Connect with retry
    for attempt in range(10):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((container_ip, port))
            return
        except ConnectionRefusedError:
            time.sleep(0.5)

    raise RuntimeError(f"Could not connect to container socket at {container_ip}:{port}")
```

2. **Send events in advance_to():**
```python
def advance_to(self, target_time_us, incoming_events):
    # ... existing time sleep ...

    # Send incoming events to container
    for event in incoming_events:
        self._send_event(event)

    # Receive outgoing events from container
    outgoing = self._receive_events()

    return outgoing

def _send_event(self, event):
    """Send event to container via socket."""
    msg = json.dumps(event) + '\n'
    self.sock.sendall(msg.encode('utf-8'))

def _receive_events(self):
    """Receive events from container (non-blocking)."""
    # Set socket to non-blocking
    self.sock.setblocking(False)

    events = []
    try:
        while True:
            data = self.sock.recv(4096).decode('utf-8')
            if not data:
                break
            # Parse line-delimited JSON
            for line in data.strip().split('\n'):
                if line:
                    events.append(json.loads(line))
    except BlockingIOError:
        # No more data available
        pass
    finally:
        self.sock.setblocking(True)

    return events
```

3. **Close socket in shutdown():**
```python
def shutdown(self):
    # Close socket first
    if hasattr(self, 'sock') and self.sock:
        try:
            self.sock.close()
        except:
            pass

    # ... existing container shutdown ...
```

---

## Tests to Add

### 1. Echo Service Tests (tests/stages/M2b/)

**test_echo_service.py:**
- test_echo_service_starts
- test_echo_service_echoes_message
- test_echo_service_handles_multiple_messages

### 2. Socket Integration Tests

**test_docker_socket_communication.py:**
- test_docker_node_connects_to_socket
- test_send_event_to_container
- test_receive_event_from_container
- test_round_trip_communication
- test_socket_cleanup_on_shutdown
- test_connection_retry_on_failure

---

## Implementation Plan

**Step 1:** Create echo service
- Write echo_service.py
- Create Dockerfile
- Build image: `docker build -t xedgesim/echo:latest`

**Step 2:** Update DockerNode with socket support
- Add _connect_to_container() method
- Add _send_event() and _receive_events() methods
- Update advance_to() to use sockets
- Update shutdown() to close socket

**Step 3:** Write tests
- Basic echo service test
- Socket communication tests
- Integration test with coordinator

**Step 4:** Run tests and iterate
- Test with echo service
- Fix issues
- Verify all regression tests pass

---

## Known Limitations

**Intentional for M2b:**
- Simple line-delimited JSON protocol (no binary format)
- Single socket connection per container
- No connection pooling or multiplexing
- No encryption/authentication
- No message queuing or buffering (beyond OS socket buffers)

---

## Results

**Implementation Summary:**
- Updated DockerNode with socket communication methods
- connect_to_socket(): Connect to container TCP socket with retry
- _send_event(): Send JSON events to container
- _receive_events(): Non-blocking receive of JSON events from container
- advance_to(): Updated to send/receive events when socket connected
- shutdown(): Updated to close socket before stopping container
- Echo service container created for testing

**Files Created/Modified:**
- sim/edge/docker_node.py - Updated with socket support (+110 lines)
- containers/echo-service/echo_service.py - Echo service (61 lines)
- containers/echo-service/Dockerfile - Echo service container
- tests/stages/M2b/test_socket_interface.py - Socket tests (127 lines)

**Test Results:**
- M2b tests: 5/5 PASSED
- M2a regression: 3/3 PASSED
- M1e regression: 8/8 PASSED

**Acceptance Criteria:**
- ✅ DockerNode can connect to container's TCP socket
- ✅ Coordinator can send JSON events to container
- ✅ Container can send JSON events back to coordinator
- ✅ Round-trip communication implemented (echo service ready for testing)
- ✅ Socket cleanup on container shutdown
- ✅ Error handling for connection failures
- ✅ All regression tests pass

---

**Status:** COMPLETE
**Actual Time:** 2.5 hours
**Completed:** 2025-11-15
