# M3i Stage Report: Integrate Realistic Network and Device Event Routing

**Stage:** M3i
**Created:** 2025-11-15
**Status:** PENDING (blocked on M3g, M3h)
**Objective:** Enable cross-tier event routing from devices through network to edge/cloud services

---

## 1. Objective

Implement complete cross-tier event routing to enable end-to-end experiments:

1. Forward parsed UART events from RenodeNode to network model
2. Route network events from network model to edge/cloud services
3. Enable bidirectional communication: device ↔ network ↔ edge ↔ cloud
4. Validate with end-to-end integration test: Renode firmware → edge ML → metrics
5. Measure cross-tier latency accurately
6. (Optional) Foundation for ns-3 integration in M4

**Issue being addressed:** Device outputs from RenodeNode and network model events do not reach edge/cloud services. Event routing is incomplete, preventing real experiments that combine all tiers.

---

## 2. Acceptance Criteria

**Must have:**
- [ ] RenodeNode forwards UART events to network model
- [ ] Network model routes events to destination nodes (edge/cloud)
- [ ] Coordinator implements cross-tier routing logic
- [ ] Edge ML containers receive device data
- [ ] Bidirectional flow: device → edge → cloud → edge → device
- [ ] Integration test: Renode → LatencyNetworkModel → Docker → metrics
- [ ] Cross-tier latency measured correctly
- [ ] All existing M0-M3 tests still pass

**Should have:**
- [ ] Network model supports multiple protocols (MQTT, CoAP, HTTP)
- [ ] Message filtering/transformation at network layer
- [ ] Packet loss simulation works with routing
- [ ] Event tracing across tiers for debugging

**Nice to have:**
- [ ] ns-3 adapter foundation (for M4 full integration)
- [ ] Network topology visualization
- [ ] Traffic pattern analysis

---

## 3. Design Decisions

### 3.1 Event Routing Architecture

**Current (broken):**
```
RenodeNode → events → ❌ nowhere
LatencyNetworkModel → ❌ no routing
Edge containers → ❌ isolated
```

**Target (working):**
```
RenodeNode → parse UART → events
    ↓
Coordinator.route_events()
    ↓
NetworkModel.deliver(src, dst, payload)
    ↓
Coordinator.route_events()
    ↓
EdgeNode.receive(event)
```

### 3.2 Message Routing Protocol

**Event structure:**

```python
@dataclass
class Event:
    timestamp_us: int
    source: str        # Node ID
    destination: str   # Node ID or "broadcast"
    event_type: str    # "mqtt_publish", "coap_request", etc.
    payload: dict      # Event-specific data
    network_metadata: dict = field(default_factory=dict)  # Latency, loss, etc.
```

**Routing logic:**

```python
# sim/coordinator.py (extend)

class Coordinator:
    def route_events(self, events: List[Event]) -> Dict[str, List[Event]]:
        """Route events through network model to destinations."""
        routed_events = defaultdict(list)

        for event in events:
            # Check if event needs network routing
            if self._is_network_event(event):
                # Send through network model
                network_events = self.network_model.deliver(
                    source=event.source,
                    destination=event.destination,
                    payload=event.payload,
                    timestamp_us=event.timestamp_us
                )

                # Network model returns events with added latency/loss
                for net_event in network_events:
                    dest_node = net_event.destination
                    routed_events[dest_node].append(net_event)
            else:
                # Direct delivery (no network)
                routed_events[event.destination].append(event)

        return routed_events
```

### 3.3 RenodeNode Event Forwarding

**Current (broken):**

```python
# sim/device/renode_node.py (CURRENT)

class RenodeNode:
    def advance(self, target_time_us):
        # ... execute firmware ...
        uart_lines = self._read_uart()
        events = self._parse_uart(uart_lines)
        return events  # ❌ Events returned but never routed!
```

**Target (working):**

```python
# sim/device/renode_node.py (NEW)

class RenodeNode:
    def __init__(self, node_id, config):
        self.node_id = node_id
        self.destination_node = config.get('mqtt_gateway', 'gateway_1')
        # ...

    def advance(self, target_time_us):
        # ... execute firmware ...
        uart_lines = self._read_uart()
        raw_events = self._parse_uart(uart_lines)

        # Transform UART events into network events
        network_events = []
        for uart_event in raw_events:
            if uart_event['type'] == 'MQTT_PUBLISH':
                network_events.append(Event(
                    timestamp_us=target_time_us,
                    source=self.node_id,
                    destination=self.destination_node,
                    event_type='mqtt_publish',
                    payload={
                        'topic': uart_event['topic'],
                        'data': uart_event['payload']
                    }
                ))

        return network_events  # ✅ Properly formatted for routing
```

### 3.4 Network Model Enhancements

**Current LatencyNetworkModel:**

```python
# sim/network/latency_model.py (CURRENT)

class LatencyNetworkModel:
    def __init__(self, config):
        self.default_latency_ms = config.get('default_latency_ms', 10)
        self.loss_rate = config.get('loss_rate', 0.0)

    # ❌ No deliver() method!
```

**Enhanced LatencyNetworkModel:**

```python
# sim/network/latency_model.py (NEW)

class LatencyNetworkModel:
    def __init__(self, config, seed=None):
        self.default_latency_ms = config.get('default_latency_ms', 10)
        self.loss_rate = config.get('loss_rate', 0.0)
        self.rng = random.Random(seed)
        self.pending_events = []  # Events in-flight

    def deliver(self, source: str, destination: str, payload: dict,
                timestamp_us: int) -> List[Event]:
        """Simulate network delivery with latency and loss."""

        # Simulate packet loss
        if self.rng.random() < self.loss_rate:
            # Packet lost - return empty list
            return []

        # Calculate delivery time
        latency_us = self.default_latency_ms * 1000
        delivery_time_us = timestamp_us + latency_us

        # Create network event
        event = Event(
            timestamp_us=delivery_time_us,
            source=source,
            destination=destination,
            event_type=payload.get('type', 'data'),
            payload=payload,
            network_metadata={
                'latency_us': latency_us,
                'sent_time_us': timestamp_us,
                'delivered_time_us': delivery_time_us
            }
        )

        # Add to pending events (will be delivered at correct time)
        self.pending_events.append(event)
        return [event]

    def advance(self, target_time_us) -> List[Event]:
        """Return events that should be delivered by target time."""
        ready_events = [
            e for e in self.pending_events
            if e.timestamp_us <= target_time_us
        ]

        self.pending_events = [
            e for e in self.pending_events
            if e.timestamp_us > target_time_us
        ]

        return ready_events
```

### 3.5 Edge Service Event Reception

**Updated DockerNode (from M3h):**

```python
# sim/nodes/docker_node.py (assumes M3h complete)

class DockerNode:
    def advance(self, target_time_us, input_events=None):
        """Advance container with input events."""
        # Send ADVANCE with events to container
        message = {
            'type': 'ADVANCE',
            'time_us': target_time_us,
            'events': input_events or []  # ✅ Events delivered to container!
        }
        self._send_message(message)

        # Container processes events and returns outputs
        response = self._receive_message()
        return response.get('events', [])
```

### 3.6 End-to-End Flow Example

**Complete flow:** Device sensor → MQTT gateway → ML inference → Cloud

```
1. RenodeNode (device):
   - Firmware reads sensor, publishes MQTT
   - UART: {"type": "MQTT_PUBLISH", "topic": "sensors/temp", "payload": "25.3"}
   - Returns Event(source="device1", dest="gateway1", type="mqtt_publish")

2. Coordinator.route_events():
   - Receives event from device1
   - Passes to NetworkModel.deliver(device1, gateway1, payload)

3. LatencyNetworkModel:
   - Simulates 10ms latency
   - Returns Event(delivery_time=current_time+10ms)

4. Coordinator (at T+10ms):
   - NetworkModel.advance() returns ready events
   - Routes to gateway1 (DockerNode)

5. DockerNode (gateway1):
   - advance(T+10ms, events=[mqtt_event])
   - Container receives ADVANCE message with MQTT event
   - Container processes, publishes to edge ML service
   - Returns Event(type="mqtt_forwarded")

6. Edge ML Container:
   - Receives inference request via MQTT
   - Runs ONNX model
   - Returns Event(type="inference_result", label="normal")

7. Cloud Service (if configured):
   - Receives aggregated results
   - Logs metrics
```

---

## 4. Tests Designed (Test-First Approach)

### 4.1 Unit Tests (Local)

```python
# tests/stages/M3i/test_event_routing.py

class TestEventRouting:
    """Test coordinator event routing logic."""

    def test_route_network_event(self):
        """Test coordinator routes event through network model."""
        coordinator = Coordinator(simple_scenario)

        event = Event(
            timestamp_us=0,
            source="device1",
            destination="gateway1",
            event_type="mqtt_publish",
            payload={"topic": "test", "data": "42"}
        )

        routed = coordinator.route_events([event])

        # Event should go through network with latency
        assert "gateway1" in routed
        assert len(routed["gateway1"]) == 1
        assert routed["gateway1"][0].network_metadata['latency_us'] > 0

    def test_network_model_deliver(self):
        """Test network model deliver() method."""
        network = LatencyNetworkModel({'default_latency_ms': 5})

        events = network.deliver(
            source="device1",
            destination="gateway1",
            payload={"data": "test"},
            timestamp_us=0
        )

        assert len(events) == 1
        assert events[0].timestamp_us == 5000  # 5ms latency
        assert events[0].destination == "gateway1"

    def test_network_model_packet_loss(self):
        """Test network model simulates packet loss."""
        network = LatencyNetworkModel({
            'default_latency_ms': 5,
            'loss_rate': 1.0  # 100% loss
        }, seed=42)

        events = network.deliver(
            source="device1",
            destination="gateway1",
            payload={"data": "test"},
            timestamp_us=0
        )

        assert len(events) == 0  # Packet lost
```

### 4.2 Integration Tests (Local - Python Only)

```python
# tests/stages/M3i/test_device_to_gateway.py

class TestDeviceToGateway:
    """Test device events reach gateway nodes."""

    def test_sensor_to_gateway_routing(self):
        """Test SensorNode events reach GatewayNode through network."""
        scenario = {
            'nodes': {
                'sensor1': {'type': 'sensor', 'sensors': ['temperature']},
                'gateway1': {'type': 'gateway'}
            },
            'network': {
                'type': 'latency',
                'default_latency_ms': 10
            },
            'duration_sec': 1.0
        }

        coordinator = Coordinator(scenario)
        results = coordinator.run()

        # Verify gateway received sensor data
        gateway_events = [e for e in results.events
                          if e.destination == 'gateway1']
        assert len(gateway_events) > 0
        assert any(e.event_type == 'sensor_data' for e in gateway_events)
```

### 4.3 End-to-End Tests (DELEGATE - Requires Docker + Renode)

```python
# tests/integration/test_e2e_cross_tier.py

@pytest.mark.integration
@pytest.mark.docker
@pytest.mark.renode
class TestEndToEndCrossTier:
    """Test complete cross-tier event flow (REQUIRES DOCKER + RENODE)."""

    def test_renode_to_edge_ml(self, firmware_path, platform_path):
        """
        Complete flow test:
        Renode firmware → Network → Edge ML → Metrics

        Requires:
        - Renode installed
        - Docker running
        - Firmware built
        """
        scenario = {
            'nodes': {
                'device1': {
                    'type': 'renode',
                    'platform': platform_path,
                    'firmware': firmware_path
                },
                'ml_edge': {
                    'type': 'docker',
                    'image': 'xedgesim/ml-inference',
                    'config': {'model_path': '/models/anomaly_detector.onnx'}
                }
            },
            'network': {
                'type': 'latency',
                'default_latency_ms': 10
            },
            'connections': [
                {'from': 'device1', 'to': 'ml_edge'}
            ],
            'duration_sec': 5.0
        }

        launcher = SimulationLauncher(scenario)
        coordinator = launcher.launch()
        results = coordinator.run()
        launcher.shutdown()

        # Verify end-to-end flow
        ml_events = [e for e in results.events
                     if e.event_type == 'inference_result']
        assert len(ml_events) > 0

        # Verify latency measurements
        for event in ml_events:
            assert 'network_metadata' in event
            assert event.network_metadata['latency_us'] >= 10000  # ≥10ms
```

---

## 5. Implementation Plan

### 5.1 Phase 1: Coordinator Routing (Local)

**Deliverables:**
- Extend `sim/coordinator.py` with `route_events()` method
- Event dataclass definition
- Unit tests for routing logic

**Timeline:** 0.5 day

### 5.2 Phase 2: Network Model Enhancement (Local)

**Deliverables:**
- Extend `sim/network/latency_model.py` with `deliver()` method
- Event buffering logic
- Unit tests for network model

**Timeline:** 0.5 day

### 5.3 Phase 3: RenodeNode Event Forwarding (Local)

**Deliverables:**
- Extend `sim/device/renode_node.py` with event transformation
- UART parsing to Event conversion
- Unit tests (mocked Renode)

**Timeline:** 0.5 day

### 5.4 Phase 4: Integration Testing (DELEGATE)

**Deliverables (testing agent):**
- End-to-end test with Renode + Docker
- Cross-tier latency validation
- Determinism verification
- Performance benchmarking

**Timeline:** 1 day (testing agent)

### 5.5 Phase 5: Optional ns-3 Foundation (Local)

**Deliverables:**
- `sim/network/ns3_adapter.py` stub
- Interface definition
- Documentation for M4

**Timeline:** 0.5 day

---

## 6. Test Results

### 6.1 Local Unit Tests

(To be filled during Phase 1-3)

### 6.2 Local Integration Tests

(To be filled during Phase 1-3)

### 6.3 Delegated End-to-End Tests

(To be filled after testing agent completes tasks)

**Task file:** `claude/tasks/TASK-M3i-e2e-routing.md`
**Results file:** `claude/results/TASK-M3i-e2e-routing.md`

---

## 7. Code Review Checklist

(To be completed before commit)

- [ ] Event routing is deterministic (seeded network model)
- [ ] No events lost or duplicated
- [ ] Latency calculations correct
- [ ] Packet loss simulation works
- [ ] Cross-tier timestamps preserved
- [ ] No circular routing
- [ ] Error handling for invalid destinations
- [ ] Performance is acceptable (no bottlenecks)

---

## 8. Lessons Learned

(To be filled after completion)

---

## 9. Contribution to M3g-M3i Goal

This stage completes the federated co-simulation architecture:
- ⏭️ Enables real end-to-end experiments
- ⏭️ Device → Network → Edge → Cloud flows work
- ⏭️ Cross-tier latency measured accurately
- ⏭️ Foundation for paper experiments complete
- ⏭️ Ready for ns-3 full integration (M4)

**Next:** M3g-M3i summary and M4 planning

---

## 10. Known Limitations and Technical Debt

**Deferred to M4:**
- Full ns-3 integration (packet-level simulation)
- Advanced routing (multi-hop, mesh networks)
- Protocol-specific handling (CoAP, LwM2M, etc.)
- Network topology changes during simulation
- QoS/priority routing

**Known issues:**
- (To be documented during implementation)

---

**Status:** PENDING (blocked on M3g, M3h)
**Last updated:** 2025-11-15
