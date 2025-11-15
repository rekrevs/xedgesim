"""
M3a: ML Inference Container Integration Tests

These tests require Docker daemon and MQTT broker to be running.
Tests will be skipped if Docker or required dependencies are not available.

Tests:
1. ML inference container starts successfully
2. Container can load ONNX model
3. Service receives inference request via MQTT
4. Service publishes inference result via MQTT
5. Inference latency is reasonable (<100ms for simple model)
6. End-to-end: sensor -> inference -> result
"""

import pytest
import time
import json
import os
import numpy as np
from pathlib import Path

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


@pytest.fixture(scope="module")
def test_model():
    """
    Fixture to ensure test model exists.

    Creates a simple ONNX model if it doesn't exist.
    """
    model_path = Path("models/anomaly_detector.onnx")

    if not model_path.exists():
        # Create model using the generator script
        print("\nCreating test model...")
        import subprocess
        result = subprocess.run(
            ["python", "models/create_test_model.py"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            pytest.skip(f"Could not create test model: {result.stderr}")

    return str(model_path.absolute())


@pytest.fixture(scope="function")
def mqtt_broker():
    """
    Fixture to start Mosquitto broker container.

    Yields broker info, then cleans up.
    """
    # Create DockerNode for broker
    config = {
        "image": "xedgesim/mosquitto:latest",
        "build_context": "containers/mqtt-broker",
        "ports": {1883: 1883}
    }

    broker = DockerNode("mqtt-broker", config, seed=42)

    # Start broker
    broker.start()
    broker.wait_for_ready()

    # Wait for broker to be ready
    time.sleep(2)

    yield {
        'node': broker,
        'host': 'localhost',
        'port': 1883
    }

    # Cleanup
    broker.shutdown()


@pytest.fixture(scope="function")
def ml_container(mqtt_broker, test_model):
    """
    Fixture to start ML inference container.

    Yields container info, then cleans up.
    """
    # Get absolute path to model directory
    models_dir = Path("models").absolute()

    # Create DockerNode for ML inference
    config = {
        "image": "xedgesim/ml-inference:latest",
        "build_context": "containers/ml-inference",
        "ports": {},
        "environment": {
            "MODEL_PATH": "/app/models/anomaly_detector.onnx",
            "MQTT_BROKER_HOST": "host.docker.internal",  # Access host's localhost
            "MQTT_BROKER_PORT": "1883"
        },
        "volumes": {
            str(models_dir): {
                'bind': '/app/models',
                'mode': 'ro'
            }
        }
    }

    ml_node = DockerNode("ml-inference", config, seed=42)

    # Start container
    ml_node.start()
    ml_node.wait_for_ready()

    # Wait for service to start
    time.sleep(3)

    yield {
        'node': ml_node
    }

    # Cleanup
    ml_node.shutdown()


def test_ml_container_starts(mqtt_broker, ml_container):
    """Test ML inference container starts successfully."""
    ml_node = ml_container['node']

    # Check container is running
    assert ml_node.container is not None
    ml_node.container.reload()
    assert ml_node.container.status == 'running'

    # Check logs for successful startup
    logs = ml_node.container.logs().decode('utf-8')
    assert 'ML Inference Service' in logs
    assert 'Model loaded successfully' in logs


def test_model_loads(ml_container):
    """Test container can load ONNX model."""
    ml_node = ml_container['node']

    # Check logs for model loading
    logs = ml_node.container.logs().decode('utf-8')
    assert 'Loading ONNX model' in logs
    assert 'Model loaded successfully' in logs
    assert 'Input:' in logs
    assert 'Output:' in logs


def test_mqtt_subscription(ml_container):
    """Test container subscribes to MQTT topic."""
    ml_node = ml_container['node']

    # Check logs for MQTT subscription
    logs = ml_node.container.logs().decode('utf-8')
    assert 'Connected to MQTT broker' in logs or 'MQTT connected' in logs
    assert 'Subscribed to: ml/inference/request' in logs


def test_inference_request(mqtt_broker, ml_container):
    """Test inference request via MQTT."""
    broker_host = mqtt_broker['host']
    broker_port = mqtt_broker['port']

    # Create MQTT client to send request
    client = mqtt.Client(client_id="test_client")
    client.connect(broker_host, broker_port, keepalive=60)
    client.loop_start()

    # Give connection time to establish
    time.sleep(1)

    # Send inference request
    request = {
        'device_id': 'test_sensor',
        'timestamp_us': 1000000,
        'features': np.random.randn(32).tolist()  # 32-dim random features
    }

    client.publish("ml/inference/request", json.dumps(request))

    # Wait for processing
    time.sleep(2)

    # Check container logs for inference
    ml_node = ml_container['node']
    logs = ml_node.container.logs().decode('utf-8')
    assert 'Inference request from test_sensor' in logs

    # Cleanup
    client.loop_stop()
    client.disconnect()


def test_inference_result(mqtt_broker, ml_container):
    """Test inference result received via MQTT."""
    broker_host = mqtt_broker['host']
    broker_port = mqtt_broker['port']

    # Shared state for callback
    results = []

    def on_message(client, userdata, msg):
        """Callback to capture inference results."""
        if msg.topic.startswith("ml/inference/result/"):
            result = json.loads(msg.payload.decode('utf-8'))
            results.append(result)

    # Create MQTT client
    client = mqtt.Client(client_id="test_client")
    client.on_message = on_message
    client.connect(broker_host, broker_port, keepalive=60)

    # Subscribe to results
    client.subscribe("ml/inference/result/#")
    client.loop_start()

    # Give connection time
    time.sleep(1)

    # Send inference request
    request = {
        'device_id': 'test_sensor',
        'timestamp_us': 1000000,
        'features': np.random.randn(32).tolist()
    }

    client.publish("ml/inference/request", json.dumps(request))

    # Wait for result
    time.sleep(3)

    # Verify result received
    assert len(results) > 0, "No inference result received"

    result = results[0]
    assert result['device_id'] == 'test_sensor'
    assert 'prediction' in result
    assert 0 <= result['prediction'] <= 1  # Probability score
    assert 'inference_time_ms' in result

    # Cleanup
    client.loop_stop()
    client.disconnect()


def test_inference_latency(mqtt_broker, ml_container):
    """Test inference latency is reasonable (<100ms for simple model)."""
    broker_host = mqtt_broker['host']
    broker_port = mqtt_broker['port']

    results = []

    def on_message(client, userdata, msg):
        if msg.topic.startswith("ml/inference/result/"):
            result = json.loads(msg.payload.decode('utf-8'))
            results.append(result)

    client = mqtt.Client(client_id="test_client")
    client.on_message = on_message
    client.connect(broker_host, broker_port, keepalive=60)
    client.subscribe("ml/inference/result/#")
    client.loop_start()

    time.sleep(1)

    # Send request
    request = {
        'device_id': 'test_sensor',
        'timestamp_us': 1000000,
        'features': np.random.randn(32).tolist()
    }

    client.publish("ml/inference/request", json.dumps(request))

    # Wait for result
    time.sleep(3)

    # Check latency
    assert len(results) > 0
    result = results[0]

    inference_time_ms = result['inference_time_ms']
    print(f"\nInference time: {inference_time_ms:.2f}ms")

    # Simple model should be fast (<100ms)
    assert inference_time_ms < 100, f"Inference too slow: {inference_time_ms}ms"

    client.loop_stop()
    client.disconnect()


def test_end_to_end(mqtt_broker, ml_container):
    """Test complete flow: sensor -> inference -> result."""
    broker_host = mqtt_broker['host']
    broker_port = mqtt_broker['port']

    results = []

    def on_message(client, userdata, msg):
        if msg.topic.startswith("ml/inference/result/"):
            result = json.loads(msg.payload.decode('utf-8'))
            results.append(result)

    # Create client
    client = mqtt.Client(client_id="test_sensor")
    client.on_message = on_message
    client.connect(broker_host, broker_port, keepalive=60)
    client.subscribe("ml/inference/result/#")
    client.loop_start()

    time.sleep(1)

    # Simulate sensor sending data
    for i in range(3):
        request = {
            'device_id': f'sensor_{i}',
            'timestamp_us': i * 1000000,
            'features': np.random.randn(32).tolist()
        }

        client.publish("ml/inference/request", json.dumps(request))
        time.sleep(0.5)

    # Wait for all results
    time.sleep(3)

    # Verify all results received
    assert len(results) >= 3, f"Expected 3 results, got {len(results)}"

    # Verify each result
    for i, result in enumerate(results[:3]):
        assert result['device_id'] == f'sensor_{i}'
        assert 0 <= result['prediction'] <= 1
        assert result['inference_time_ms'] < 100

    print(f"\nEnd-to-end test: {len(results)} inferences completed successfully")

    client.loop_stop()
    client.disconnect()
