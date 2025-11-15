# M2c: MQTT Broker Container Integration

**Stage:** M2c
**Date:** 2025-11-15
**Status:** IN PROGRESS

---

## Objective

Run a real MQTT broker (Eclipse Mosquitto) in Docker container and integrate it with Python simulation nodes for realistic pub/sub messaging.

**Scope:**
- Create Mosquitto broker Dockerfile
- Run broker in Docker container using DockerNode
- Python sensor nodes publish MQTT messages to broker
- Python gateway node subscribes to MQTT topics
- End-to-end integration test: sensor → MQTT broker → gateway
- Add `paho-mqtt` dependency for Python MQTT clients

**Explicitly excluded:**
- ML inference integration (M3 scope)
- Complex MQTT topologies (QoS levels, retained messages, will messages)
- MQTT authentication/authorization
- TLS/SSL encryption
- Bridging multiple brokers

---

## Acceptance Criteria

1. ⬜ Mosquitto broker Dockerfile created
2. ⬜ Broker runs in Docker container
3. ⬜ Python nodes can connect to broker
4. ⬜ Sensor publishes messages to topic
5. ⬜ Gateway subscribes and receives messages
6. ⬜ End-to-end test passes: sensor → broker → gateway
7. ⬜ Broker container cleanup working
8. ⬜ All M0-M1e-M2a-M2b tests still pass

---

## Design Decisions

### MQTT Broker Choice

**Selected:** Eclipse Mosquitto
- Industry-standard open-source MQTT broker
- Lightweight (official Docker image ~10MB)
- Easy configuration
- Well-documented

**Alternatives considered:**
- EMQX: More features, but heavier
- HiveMQ: Commercial, overkill for simulation
- VerneMQ: Complex configuration

### MQTT Integration Architecture

```
┌─────────────────────────────────────────────────────┐
│                 Simulation Architecture              │
└─────────────────────────────────────────────────────┘

Python Sensor Node                 Docker Container
┌──────────────┐                  ┌────────────────┐
│              │                  │   Mosquitto    │
│ SensorNode   │  MQTT Publish    │     Broker     │
│              ├─────────────────>│   Port 1883    │
│ (temp data)  │  topic: sensor/1 │                │
└──────────────┘                  └────────┬───────┘
                                           │
                                           │ MQTT Subscribe
Python Gateway Node                        │ topic: sensor/#
┌──────────────┐                           │
│              │<──────────────────────────┘
│ GatewayNode  │  Receives messages
│              │
│ (aggregator) │
└──────────────┘
```

### Mosquitto Container Configuration

**Dockerfile:**
```dockerfile
FROM eclipse-mosquitto:2.0

# Custom mosquitto.conf for development
COPY mosquitto.conf /mosquitto/config/mosquitto.conf

# Expose MQTT port
EXPOSE 1883

# Run broker
CMD ["/usr/sbin/mosquitto", "-c", "/mosquitto/config/mosquitto.conf"]
```

**mosquitto.conf:**
```conf
# Listen on all interfaces
listener 1883 0.0.0.0

# Allow anonymous connections (development only)
allow_anonymous true

# Logging
log_dest stdout
log_type all
```

### Python MQTT Client Integration

**Add dependency:** `paho-mqtt>=1.6.1` to `requirements-dev.txt`

**Sensor Node publishes:**
```python
import paho.mqtt.client as mqtt

class SensorNode:
    def connect_mqtt(self, broker_host, broker_port=1883):
        """Connect to MQTT broker."""
        self.mqtt_client = mqtt.Client(client_id=f"sensor_{self.node_id}")
        self.mqtt_client.connect(broker_host, broker_port)
        self.mqtt_client.loop_start()  # Background thread for network

    def publish_reading(self, topic, data):
        """Publish sensor reading to MQTT."""
        payload = json.dumps(data)
        self.mqtt_client.publish(topic, payload)
```

**Gateway Node subscribes:**
```python
import paho.mqtt.client as mqtt

class GatewayNode:
    def connect_mqtt(self, broker_host, broker_port=1883):
        """Connect to MQTT broker and subscribe."""
        self.mqtt_client = mqtt.Client(client_id=f"gateway_{self.node_id}")
        self.mqtt_client.on_message = self._on_mqtt_message
        self.mqtt_client.connect(broker_host, broker_port)
        self.mqtt_client.subscribe("sensor/#")  # Subscribe to all sensors
        self.mqtt_client.loop_start()

    def _on_mqtt_message(self, client, userdata, msg):
        """Handle incoming MQTT message."""
        payload = json.loads(msg.payload.decode())
        # Process sensor data
        self.received_messages.append({
            'topic': msg.topic,
            'payload': payload
        })
```

---

## Implementation Plan

**Step 1:** Add paho-mqtt dependency
- Update `requirements-dev.txt`

**Step 2:** Create Mosquitto broker container
- Create `containers/mqtt-broker/Dockerfile`
- Create `containers/mqtt-broker/mosquitto.conf`

**Step 3:** Write integration test (TDD)
- Create `tests/stages/M2c/test_mqtt_integration.py`
- Test: Start broker, sensor publishes, gateway receives

**Step 4:** Extend SensorNode with MQTT support
- Add `connect_mqtt()` method
- Add `publish_reading()` method

**Step 5:** Extend GatewayNode with MQTT support
- Add `connect_mqtt()` method
- Add message handler

**Step 6:** Create end-to-end test
- Start Mosquitto container
- Connect sensor and gateway
- Publish message
- Verify gateway receives it

**Step 7:** Delegate testing to testing agent
- Cannot test Docker locally
- Create task in `claude/tasks/TASK-M2c-mqtt-tests.md`

---

## Tests to Add

### Integration Test (tests/stages/M2c/)

**test_mqtt_integration.py:**
```python
def test_mosquitto_broker_starts():
    """Test Mosquitto broker container starts successfully."""
    # Start broker container
    # Verify it's running
    # Verify port 1883 is listening

def test_sensor_publishes_to_broker():
    """Test sensor can publish to MQTT broker."""
    # Start broker
    # Create sensor node
    # Connect to broker
    # Publish message
    # Verify no errors

def test_gateway_subscribes_and_receives():
    """Test gateway receives messages from broker."""
    # Start broker
    # Create sensor and gateway
    # Gateway subscribes
    # Sensor publishes
    # Verify gateway receives message

def test_end_to_end_mqtt_flow():
    """Test complete sensor → broker → gateway flow."""
    # Full integration test
```

---

## Known Limitations

**Intentional for M2c:**
- Anonymous connections only (no authentication)
- No TLS/SSL encryption
- Simple QoS 0 (at most once delivery)
- Single broker (no clustering)
- No message persistence
- No retained messages or will messages

---

**Status:** IN PROGRESS
**Estimated Time:** 3-4 hours (implementation) + testing delegation
**Started:** 2025-11-15
