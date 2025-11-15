"""
M2c: MQTT Broker Integration Tests

These tests require Docker daemon to be running.
Tests will be skipped if Docker is not available.

Tests:
1. Mosquitto broker container starts successfully
2. Sensor node can connect to broker and publish messages
3. Gateway node can connect to broker and subscribe to topics
4. End-to-end: sensor publishes -> broker routes -> gateway receives
"""

import pytest
import time
import json
import os

# Try to import required modules
try:
    import docker
    DOCKER_AVAILABLE = True
except ImportError:
    docker = None
    DOCKER_AVAILABLE = False

try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    mqtt = None
    MQTT_AVAILABLE = False

from sim.device.sensor_node import SensorNode
from sim.edge.gateway_node import GatewayNode
from sim.edge.docker_node import DockerNode, get_docker_client


def is_docker_available():
    """Check if Docker daemon is accessible."""
    if not DOCKER_AVAILABLE:
        return False

    try:
        client = get_docker_client()
        client.ping()
        client.close()
        return True
    except Exception:
        return False


# Skip all tests if Docker or MQTT not available
pytestmark = [
    pytest.mark.skipif(not is_docker_available(), reason="Docker daemon not available"),
    pytest.mark.skipif(not MQTT_AVAILABLE, reason="paho-mqtt not installed")
]


@pytest.fixture(scope="function")
def mqtt_broker():
    """
    Fixture to start Mosquitto broker container.

    Yields broker container info, then cleans up.
    """
    # Create DockerNode for broker
    config = {
        "image": "xedgesim/mosquitto:latest",
        "build_context": "containers/mqtt-broker",
        "ports": {1883: 1883}  # Map port 1883 for localhost access
    }

    broker = DockerNode("mqtt-broker", config, seed=42)

    # Start broker container
    broker.start()

    # Wait for broker to be ready
    broker.wait_for_ready()
    time.sleep(2)

    # On macOS/Colima, use localhost instead of container IP
    # Container IP (172.17.x.x) is not accessible from host
    yield {
        'node': broker,
        'ip': 'localhost',  # Use localhost for macOS/Colima compatibility
        'port': 1883
    }

    # Cleanup
    broker.shutdown()


def test_mosquitto_broker_starts(mqtt_broker):
    """Test Mosquitto broker container starts successfully."""
    broker = mqtt_broker['node']

    # Check container is running
    assert broker.container is not None
    broker.container.reload()
    assert broker.container.status == 'running'

    # Check logs for successful startup
    logs = broker.container.logs().decode('utf-8')
    assert 'mosquitto version' in logs.lower()


def test_mqtt_client_can_connect(mqtt_broker):
    """Test that MQTT client can connect to broker."""
    broker_ip = mqtt_broker['ip']
    broker_port = mqtt_broker['port']

    # Create MQTT client
    client = mqtt.Client(client_id="test_client")

    connected = False

    def on_connect(client, userdata, flags, rc):
        nonlocal connected
        connected = (rc == 0)

    client.on_connect = on_connect

    # Connect to broker
    client.connect(broker_ip, broker_port, keepalive=60)
    client.loop_start()

    # Wait for connection
    time.sleep(1)

    assert connected, "Failed to connect to MQTT broker"

    # Cleanup
    client.loop_stop()
    client.disconnect()


def test_sensor_node_mqtt_publish(mqtt_broker):
    """Test sensor node can publish to MQTT broker."""
    broker_ip = mqtt_broker['ip']
    broker_port = mqtt_broker['port']

    # Create sensor node
    sensor = SensorNode("sensor1", {"interval_us": 1000000}, seed=42)

    # Connect to MQTT broker
    sensor.connect_mqtt(broker_ip, broker_port)

    # Give connection time to establish
    time.sleep(1)

    # Verify sensor has MQTT client
    assert hasattr(sensor, 'mqtt_client')
    assert sensor.mqtt_client is not None
    assert sensor.mqtt_client.is_connected()

    # Publish a test reading
    test_data = {
        'sensor_id': 'sensor1',
        'temperature': 25.5,
        'timestamp': 1000000
    }

    # This should not raise an exception
    sensor.publish_reading('sensor/sensor1/temperature', test_data)

    # Give time for publish
    time.sleep(0.5)

    # Cleanup
    sensor.disconnect_mqtt()


def test_gateway_node_mqtt_subscribe(mqtt_broker):
    """Test gateway node can subscribe to MQTT topics."""
    broker_ip = mqtt_broker['ip']
    broker_port = mqtt_broker['port']

    # Create gateway node
    gateway = GatewayNode("gateway1", {}, seed=42)

    # Connect to MQTT broker
    gateway.connect_mqtt(broker_ip, broker_port, topics=['sensor/#'])

    # Give connection time to establish
    time.sleep(1)

    # Verify gateway has MQTT client
    assert hasattr(gateway, 'mqtt_client')
    assert gateway.mqtt_client is not None
    assert gateway.mqtt_client.is_connected()

    # Verify gateway can store received messages
    assert hasattr(gateway, 'mqtt_messages')

    # Cleanup
    gateway.disconnect_mqtt()


def test_end_to_end_mqtt_flow(mqtt_broker):
    """
    Test complete sensor -> broker -> gateway flow.

    1. Start Mosquitto broker
    2. Gateway subscribes to sensor/# topic
    3. Sensor publishes temperature reading
    4. Gateway receives the message
    """
    broker_ip = mqtt_broker['ip']
    broker_port = mqtt_broker['port']

    # Create sensor and gateway
    sensor = SensorNode("sensor1", {"interval_us": 1000000}, seed=42)
    gateway = GatewayNode("gateway1", {}, seed=42)

    # Gateway subscribes first
    gateway.connect_mqtt(broker_ip, broker_port, topics=['sensor/#'])
    time.sleep(1)

    # Sensor connects and publishes
    sensor.connect_mqtt(broker_ip, broker_port)
    time.sleep(1)

    # Publish test message
    test_data = {
        'sensor_id': 'sensor1',
        'temperature': 25.5,
        'timestamp': 1000000
    }

    sensor.publish_reading('sensor/sensor1/temperature', test_data)

    # Wait for message to be routed
    time.sleep(2)

    # Verify gateway received the message
    assert len(gateway.mqtt_messages) > 0, "Gateway did not receive any messages"

    # Check the received message
    received = gateway.mqtt_messages[0]
    assert received['topic'] == 'sensor/sensor1/temperature'
    assert received['payload']['sensor_id'] == 'sensor1'
    assert received['payload']['temperature'] == 25.5

    # Cleanup
    sensor.disconnect_mqtt()
    gateway.disconnect_mqtt()


def test_multiple_sensors_to_gateway(mqtt_broker):
    """Test multiple sensors publishing to one gateway."""
    broker_ip = mqtt_broker['ip']
    broker_port = mqtt_broker['port']

    # Create gateway and multiple sensors
    gateway = GatewayNode("gateway1", {}, seed=42)
    sensor1 = SensorNode("sensor1", {"interval_us": 1000000}, seed=42)
    sensor2 = SensorNode("sensor2", {"interval_us": 1000000}, seed=43)

    # Gateway subscribes
    gateway.connect_mqtt(broker_ip, broker_port, topics=['sensor/#'])
    time.sleep(1)

    # Sensors connect
    sensor1.connect_mqtt(broker_ip, broker_port)
    sensor2.connect_mqtt(broker_ip, broker_port)
    time.sleep(1)

    # Sensors publish
    sensor1.publish_reading('sensor/sensor1/temperature', {
        'sensor_id': 'sensor1',
        'temperature': 25.5,
        'timestamp': 1000000
    })

    sensor2.publish_reading('sensor/sensor2/temperature', {
        'sensor_id': 'sensor2',
        'temperature': 30.2,
        'timestamp': 1000000
    })

    # Wait for messages
    time.sleep(2)

    # Verify gateway received both messages
    assert len(gateway.mqtt_messages) >= 2, f"Gateway received {len(gateway.mqtt_messages)} messages, expected 2"

    # Verify both sensors' messages are present
    sensor_ids = [msg['payload']['sensor_id'] for msg in gateway.mqtt_messages]
    assert 'sensor1' in sensor_ids
    assert 'sensor2' in sensor_ids

    # Cleanup
    sensor1.disconnect_mqtt()
    sensor2.disconnect_mqtt()
    gateway.disconnect_mqtt()
