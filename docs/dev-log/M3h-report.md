# M3h Stage Report: Unify Container Protocol with Coordinator Timebase

**Stage:** M3h
**Created:** 2025-11-15
**Status:** PENDING (blocked on M3g)
**Objective:** Implement coordinator protocol in Docker containers for deterministic co-simulation

---

## 1. Objective

Unify container execution with coordinator virtual time by:

1. Implementing INIT/ADVANCE/DONE protocol in container services
2. Creating reusable protocol adapter for containers
3. Updating DockerNode to marshal events bidirectionally
4. Replacing wall-clock `time.sleep` with message-driven advancement
5. Ensuring MQTT/ML pipelines honor virtual time
6. Validating determinism across Docker nodes

**Issue being addressed:** Docker containers currently run on wall-clock time and lack the coordinator protocol, preventing deterministic co-simulation across tiers. Edge services use `time.sleep()` which breaks the virtual time model.

---

## 2. Acceptance Criteria

**Must have:**
- [ ] Protocol adapter library for containers (`containers/protocol_adapter.py`)
- [ ] ML inference container implements INIT/ADVANCE/DONE protocol
- [ ] MQTT gateway container implements INIT/ADVANCE/DONE protocol
- [ ] DockerNode marshals events between coordinator and container
- [ ] DockerNode replaces `time.sleep` with event-driven advancement
- [ ] Integration test: coordinator drives Docker node deterministically
- [ ] Determinism test: same YAML + seed → identical Docker outputs
- [ ] All existing M0-M3 tests still pass

**Should have:**
- [ ] Multiple Docker nodes in single simulation
- [ ] Event buffering in containers
- [ ] Graceful handling of container crashes
- [ ] Performance metrics (overhead vs wall-clock)

**Nice to have:**
- [ ] Time-window filtering for events
- [ ] Container state checkpointing
- [ ] Hot-reload of container config

---

## 3. Design Decisions

### 3.1 Protocol Design

**Message format (JSON over stdin/stdout):**

```json
// Coordinator → Container
{
  "type": "INIT",
  "time_us": 0,
  "config": {...}
}

{
  "type": "ADVANCE",
  "time_us": 1000000,
  "events": [
    {"type": "mqtt_message", "topic": "sensors/temp", "payload": "25.3"}
  ]
}

{
  "type": "SHUTDOWN"
}

// Container → Coordinator
{
  "type": "READY",
  "time_us": 0
}

{
  "type": "DONE",
  "time_us": 1000000,
  "events": [
    {"type": "inference_result", "label": "anomaly", "confidence": 0.95}
  ]
}
```

**Rationale:**
- JSON: easy to parse in Python containers
- stdin/stdout: standard Docker communication
- Event-driven: no wall-clock dependencies
- Simple: minimal protocol overhead

### 3.2 Protocol Adapter Architecture

```python
# containers/protocol_adapter.py

class CoordinatorProtocolAdapter:
    """Adapter for container services to communicate with coordinator."""

    def __init__(self, service_callback):
        self.service_callback = service_callback
        self.current_time_us = 0
        self.running = False

    def run(self):
        """Main event loop - reads from stdin, processes, writes to stdout."""
        while self.running:
            message = self._read_message()  # Read JSON from stdin
            response = self._process_message(message)
            self._write_message(response)  # Write JSON to stdout

    def _process_message(self, message):
        if message['type'] == 'INIT':
            return self._handle_init(message)
        elif message['type'] == 'ADVANCE':
            return self._handle_advance(message)
        elif message['type'] == 'SHUTDOWN':
            return self._handle_shutdown(message)

    def _handle_advance(self, message):
        """Advance virtual time and process events."""
        target_time = message['time_us']
        input_events = message.get('events', [])

        # Process events at virtual time (no wall-clock delays!)
        output_events = self.service_callback(
            current_time=self.current_time_us,
            target_time=target_time,
            events=input_events
        )

        self.current_time_us = target_time

        return {
            'type': 'DONE',
            'time_us': target_time,
            'events': output_events
        }
```

**Usage in containers:**

```python
# containers/ml-inference/inference_service.py (updated)

def ml_service_callback(current_time, target_time, events):
    """Process ML inference events in virtual time."""
    output_events = []

    for event in events:
        if event['type'] == 'inference_request':
            # Run inference (wall-clock time doesn't matter!)
            result = model.predict(event['data'])

            # Return result with virtual timestamp
            output_events.append({
                'type': 'inference_result',
                'timestamp_us': current_time,  # Virtual time!
                'result': result
            })

    return output_events

if __name__ == '__main__':
    adapter = CoordinatorProtocolAdapter(ml_service_callback)
    adapter.run()
```

### 3.3 DockerNode Updates

**Current implementation (wall-clock):**

```python
# sim/nodes/docker_node.py (CURRENT - BROKEN)

class DockerNode:
    def advance(self, target_time_us):
        delta_us = target_time_us - self.current_time_us
        time.sleep(delta_us / 1e6)  # ❌ Wall-clock sleep!
        self.current_time_us = target_time_us
        return []
```

**New implementation (event-driven):**

```python
# sim/nodes/docker_node.py (NEW - DETERMINISTIC)

class DockerNode:
    def __init__(self, node_id, config):
        self.node_id = node_id
        self.container = None
        self.stdin_pipe = None
        self.stdout_pipe = None
        self.current_time_us = 0
        self.pending_events = []

    def advance(self, target_time_us, input_events=None):
        """Advance container to target time via protocol."""
        # Send ADVANCE message to container
        message = {
            'type': 'ADVANCE',
            'time_us': target_time_us,
            'events': input_events or []
        }
        self._send_message(message)

        # Wait for DONE response
        response = self._receive_message()
        assert response['type'] == 'DONE'
        assert response['time_us'] == target_time_us

        self.current_time_us = target_time_us
        return response.get('events', [])

    def _send_message(self, message):
        """Send JSON message to container stdin."""
        json_str = json.dumps(message) + '\n'
        self.stdin_pipe.write(json_str.encode())
        self.stdin_pipe.flush()

    def _receive_message(self):
        """Receive JSON message from container stdout."""
        line = self.stdout_pipe.readline().decode()
        return json.loads(line)
```

### 3.4 MQTT Service Integration

**Challenge:** MQTT broker (Mosquitto) doesn't understand virtual time

**Solution:** Wrap MQTT operations in protocol adapter

```python
# containers/mqtt-gateway/gateway_service.py

class MQTTGatewayService:
    def __init__(self):
        self.mqtt_client = mqtt.Client()
        self.message_buffer = []

    def process_time_window(self, current_time, target_time, events):
        """Process MQTT messages within time window."""
        output_events = []

        for event in events:
            if event['type'] == 'mqtt_publish':
                # Publish to MQTT (happens immediately in wall-clock)
                self.mqtt_client.publish(event['topic'], event['payload'])

                # Record event at virtual timestamp
                output_events.append({
                    'type': 'mqtt_published',
                    'timestamp_us': current_time,
                    'topic': event['topic']
                })

        # Check for received messages (buffer them)
        while self.message_buffer:
            msg = self.message_buffer.pop(0)
            output_events.append({
                'type': 'mqtt_received',
                'timestamp_us': current_time,
                'topic': msg.topic,
                'payload': msg.payload
            })

        return output_events

if __name__ == '__main__':
    service = MQTTGatewayService()
    adapter = CoordinatorProtocolAdapter(service.process_time_window)
    adapter.run()
```

### 3.5 Determinism Strategy

**Challenge:** Docker containers have inherent non-determinism (scheduling, I/O)

**Approach:** Make protocol layer deterministic, accept service layer variance

**Deterministic:**
- ✅ Message ordering (coordinator controls advancement)
- ✅ Event timestamps (virtual time only)
- ✅ Coordinator-container communication (request-response)

**Non-deterministic (acceptable):**
- ⚠️ Inference latency (real ML model execution time varies)
- ⚠️ MQTT delivery order within time window (millisecond-level variance)
- ⚠️ Container startup time

**Testing strategy:**
- Determinism test: verify event *sequences* match
- Performance test: verify event *timing* is within tolerance
- Integration test: verify *behavior* is correct

---

## 4. Tests Designed (Test-First Approach)

### 4.1 Unit Tests (Local)

```python
# tests/stages/M3h/test_protocol_adapter.py

class TestProtocolAdapter:
    """Test protocol adapter logic (no Docker required)."""

    def test_adapter_init_message(self):
        """Test adapter handles INIT message."""
        def callback(current, target, events):
            return []

        adapter = CoordinatorProtocolAdapter(callback)
        message = {'type': 'INIT', 'time_us': 0, 'config': {}}

        response = adapter._process_message(message)

        assert response['type'] == 'READY'

    def test_adapter_advance_message(self):
        """Test adapter handles ADVANCE message."""
        def callback(current, target, events):
            # Process events, return outputs
            return [{'type': 'output', 'value': 42}]

        adapter = CoordinatorProtocolAdapter(callback)
        message = {
            'type': 'ADVANCE',
            'time_us': 1000,
            'events': [{'type': 'input'}]
        }

        response = adapter._process_message(message)

        assert response['type'] == 'DONE'
        assert response['time_us'] == 1000
        assert len(response['events']) == 1
```

### 4.2 Integration Tests (Docker Required - DELEGATE)

```python
# tests/stages/M3h/test_docker_protocol.py

@pytest.mark.docker
class TestDockerProtocol:
    """Test Docker containers with protocol (REQUIRES DOCKER)."""

    def test_docker_node_advance(self):
        """Test DockerNode can advance container via protocol."""
        # Start container with protocol adapter
        # Send ADVANCE via DockerNode
        # Verify DONE response
        # Verify events marshaled correctly

    def test_docker_determinism(self):
        """Test Docker execution is deterministic."""
        # Run scenario twice with same seed
        # Verify event sequences match

    def test_multiple_docker_nodes(self):
        """Test multiple Docker nodes in single simulation."""
        # Create 2+ Docker nodes
        # Advance in lockstep
        # Verify coordination works
```

---

## 5. Implementation Plan

### 5.1 Phase 1: Protocol Adapter (Local)

**Deliverables:**
- `containers/protocol_adapter.py` (core library)
- Unit tests for adapter logic
- Documentation

**Timeline:** 1 day

### 5.2 Phase 2: DockerNode Updates (Local)

**Deliverables:**
- Updated `sim/nodes/docker_node.py`
- stdin/stdout piping logic
- Unit tests (mocked Docker)

**Timeline:** 1 day

### 5.3 Phase 3: Container Integration (DELEGATE)

**Deliverables (testing agent):**
- Update `containers/ml-inference/inference_service.py` with protocol
- Update `containers/mqtt-gateway/gateway_service.py` with protocol
- Integration tests with real Docker
- Determinism validation

**Timeline:** 1-2 days (testing agent)

### 5.4 Phase 4: End-to-End Validation (DELEGATE)

**Deliverables (testing agent):**
- Full scenario with Docker nodes in virtual time
- Performance benchmarking
- Regression testing

**Timeline:** 0.5 day (testing agent)

---

## 6. Test Results

### 6.1 Local Unit Tests

(To be filled during Phase 1-2)

### 6.2 Delegated Integration Tests

(To be filled after testing agent completes tasks)

**Task files:**
- `claude/tasks/TASK-M3h-docker-protocol.md`
- `claude/tasks/TASK-M3h-determinism.md`

**Results files:**
- `claude/results/TASK-M3h-docker-protocol.md`
- `claude/results/TASK-M3h-determinism.md`

---

## 7. Code Review Checklist

(To be completed before commit)

- [ ] Protocol messages well-defined and documented
- [ ] stdin/stdout communication robust
- [ ] Error handling for container crashes
- [ ] No wall-clock dependencies in protocol layer
- [ ] Event marshaling preserves timestamps
- [ ] Cleanup logic terminates containers properly
- [ ] Documentation explains virtual time model
- [ ] Tests cover happy path and error cases

---

## 8. Lessons Learned

(To be filled after completion)

---

## 9. Contribution to M3g-M3i Goal

This stage enables deterministic co-simulation with Docker:
- ⏭️ Containers now use virtual time
- ⏭️ Edge services participate in federated time model
- ⏭️ MQTT/ML pipelines become deterministic
- ⏭️ Foundation for cross-tier experiments (M3i)
- ⏭️ Reproducible paper results

**Next stage:** M3i - Network and device event routing

---

## 10. Known Limitations and Technical Debt

**Deferred to later stages:**
- Full ns-3 integration (using LatencyNetworkModel for now)
- Time dilation for containers (not needed if protocol works)
- Container checkpointing/replay
- Distributed container orchestration

**Known issues:**
- (To be documented during implementation)

---

**Status:** PENDING (blocked on M3g)
**Last updated:** 2025-11-15
