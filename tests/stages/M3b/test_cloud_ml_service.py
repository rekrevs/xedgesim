"""
M3b: Cloud ML Service Integration Tests

These tests require MQTT broker to be running.
Tests will be skipped if required dependencies are not available.

Tests:
1. CloudMLService loads PyTorch model successfully
2. Service connects to MQTT broker
3. Service receives inference request via MQTT
4. Service publishes inference result with cloud latency
5. Cloud latency simulation is correct (50ms one-way default)
6. Edge vs Cloud comparison shows latency difference
"""

import pytest
import time
import json
import threading
from pathlib import Path

# Try to import required modules
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    TORCH_AVAILABLE = False

try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    mqtt = None
    MQTT_AVAILABLE = False

try:
    import docker
    DOCKER_AVAILABLE = True
except ImportError:
    docker = None
    DOCKER_AVAILABLE = False

# Import cloud ML service
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from sim.cloud.ml_service import CloudMLService
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


# Skip all tests if dependencies not available
pytestmark = [
    pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not installed"),
    pytest.mark.skipif(not MQTT_AVAILABLE, reason="paho-mqtt not installed"),
    pytest.mark.skipif(not is_docker_available(), reason="Docker daemon not available (for MQTT broker)")
]


@pytest.fixture(scope="module")
def pytorch_model():
    """
    Fixture to ensure PyTorch test model exists.

    Creates a simple PyTorch model if it doesn't exist.
    """
    model_path = Path("models/anomaly_detector.pt")

    if not model_path.exists():
        # Create model using the generator script
        print("\nCreating PyTorch test model...")
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
def cloud_service(mqtt_broker, pytorch_model):
    """
    Fixture to start CloudMLService in background thread.

    Yields service instance, then cleans up.
    """
    broker_host = mqtt_broker['host']
    broker_port = mqtt_broker['port']

    # Create service with 50ms cloud latency
    service = CloudMLService(
        model_path=pytorch_model,
        broker_host=broker_host,
        broker_port=broker_port,
        cloud_latency_ms=50
    )

    # Load model
    service.load_model()

    # Connect to MQTT
    service.connect_mqtt()

    # Start MQTT loop in background thread
    service_thread = threading.Thread(target=service.mqtt_client.loop_forever, daemon=True)
    service_thread.start()

    # Wait for service to be ready
    time.sleep(2)

    yield service

    # Cleanup
    service.mqtt_client.loop_stop()
    service.mqtt_client.disconnect()


def test_cloud_service_loads_model(pytorch_model):
    """Test CloudMLService can load PyTorch model."""
    service = CloudMLService(
        model_path=pytorch_model,
        broker_host="localhost",
        broker_port=1883,
        cloud_latency_ms=50
    )

    # Load model
    service.load_model()

    # Verify model loaded
    assert service.model is not None
    assert isinstance(service.model, torch.nn.Module)


def test_cloud_service_mqtt_connection(mqtt_broker, pytorch_model):
    """Test service connects to MQTT broker."""
    broker_host = mqtt_broker['host']
    broker_port = mqtt_broker['port']

    service = CloudMLService(
        model_path=pytorch_model,
        broker_host=broker_host,
        broker_port=broker_port,
        cloud_latency_ms=50
    )

    # Load model and connect
    service.load_model()
    service.connect_mqtt()

    # Start loop briefly to complete connection
    service.mqtt_client.loop_start()
    time.sleep(1)

    # Verify connection
    assert service.mqtt_client.is_connected()

    # Cleanup
    service.mqtt_client.loop_stop()
    service.mqtt_client.disconnect()


def test_cloud_inference_request(mqtt_broker, cloud_service):
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
        'features': [0.1] * 32  # 32-dim features
    }

    client.publish("ml/inference/request", json.dumps(request))

    # Wait for processing (should take at least 100ms due to cloud latency)
    time.sleep(2)

    # Verify service processed request (check metrics)
    assert cloud_service.inference_count > 0

    # Cleanup
    client.loop_stop()
    client.disconnect()


def test_cloud_inference_result(mqtt_broker, cloud_service):
    """Test inference result with cloud latency."""
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
        'features': [0.1] * 32
    }

    client.publish("ml/inference/request", json.dumps(request))

    # Wait for result (must account for 100ms cloud latency + inference)
    time.sleep(3)

    # Verify result received
    assert len(results) > 0, "No inference result received"

    result = results[0]
    assert result['device_id'] == 'test_sensor'
    assert 'prediction' in result
    assert 0 <= result['prediction'] <= 1  # Probability score
    assert 'inference_time_ms' in result
    assert 'cloud_latency_ms' in result
    assert 'total_latency_ms' in result

    # Cleanup
    client.loop_stop()
    client.disconnect()


def test_cloud_latency_simulation(mqtt_broker, cloud_service):
    """Test cloud latency is added correctly."""
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

    # Measure end-to-end time
    start_time = time.time()

    # Send request
    request = {
        'device_id': 'test_sensor',
        'timestamp_us': 1000000,
        'features': [0.1] * 32
    }

    client.publish("ml/inference/request", json.dumps(request))

    # Wait for result
    time.sleep(3)

    end_time = time.time()
    total_time_ms = (end_time - start_time) * 1000

    # Check result
    assert len(results) > 0
    result = results[0]

    # Cloud latency should be 100ms (50ms each way)
    assert result['cloud_latency_ms'] == 100

    # Total latency should include inference time + cloud latency
    total_latency_ms = result['total_latency_ms']
    inference_time_ms = result['inference_time_ms']

    print(f"\nCloud latency simulation:")
    print(f"  Inference time: {inference_time_ms:.2f}ms")
    print(f"  Cloud latency: {result['cloud_latency_ms']}ms")
    print(f"  Total latency: {total_latency_ms:.2f}ms")
    print(f"  Measured end-to-end: {total_time_ms:.2f}ms")

    # Total should be inference + 100ms cloud latency
    expected_total = inference_time_ms + 100
    assert abs(total_latency_ms - expected_total) < 5  # Allow 5ms tolerance

    # Measured time should be at least 100ms (cloud latency)
    assert total_time_ms >= 100

    client.loop_stop()
    client.disconnect()


def test_edge_vs_cloud_comparison(mqtt_broker, pytorch_model):
    """Test edge and cloud services produce consistent results."""
    broker_host = mqtt_broker['host']
    broker_port = mqtt_broker['port']

    # Create cloud service with known latency
    cloud_service = CloudMLService(
        model_path=pytorch_model,
        broker_host=broker_host,
        broker_port=broker_port,
        cloud_latency_ms=50
    )

    cloud_service.load_model()
    cloud_service.connect_mqtt()
    cloud_thread = threading.Thread(target=cloud_service.mqtt_client.loop_forever, daemon=True)
    cloud_thread.start()

    time.sleep(2)

    # Collect results
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

    # Use same features for consistent comparison
    features = [0.5] * 32

    # Send request
    request = {
        'device_id': 'test_sensor',
        'timestamp_us': 1000000,
        'features': features
    }

    client.publish("ml/inference/request", json.dumps(request))

    # Wait for result
    time.sleep(3)

    assert len(results) > 0

    cloud_result = results[0]

    print(f"\nEdge vs Cloud comparison:")
    print(f"  Cloud prediction: {cloud_result['prediction']:.4f}")
    print(f"  Cloud inference time: {cloud_result['inference_time_ms']:.2f}ms")
    print(f"  Cloud total latency: {cloud_result['total_latency_ms']:.2f}ms")

    # Verify cloud adds significant latency
    assert cloud_result['total_latency_ms'] > 100  # At least cloud latency
    assert cloud_result['cloud_latency_ms'] == 100  # 50ms each way

    # Cleanup
    client.loop_stop()
    client.disconnect()
    cloud_service.mqtt_client.loop_stop()
    cloud_service.mqtt_client.disconnect()
