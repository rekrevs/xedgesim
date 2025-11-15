#!/usr/bin/env python3
"""
ml_service.py - Cloud ML Service for ML Placement Framework

Python-based cloud ML service using PyTorch.
Simulates cloud-tier ML inference with configurable latency.

MQTT Topics:
  Input:  ml/inference/request
  Output: ml/inference/result/{device_id}

Message Format (JSON):
  Request:  {"device_id": "sensor1", "timestamp_us": 1000000, "features": [0.1, 0.2, ...]}
  Response: {"device_id": "sensor1", "timestamp_us": 1000000, "prediction": 0.85,
             "inference_time_ms": 2.5, "cloud_latency_ms": 50.0}
"""

import os
import sys
import json
import time

# Add parent directory to path for model imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Check dependencies
try:
    import torch
except ImportError:
    print("Error: torch not installed. Install with: pip install torch", file=sys.stderr)
    sys.exit(1)

try:
    from models.simple_anomaly_detector import SimpleAnomalyDetector
except ImportError:
    print("Error: Could not import SimpleAnomalyDetector model", file=sys.stderr)
    sys.exit(1)

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("Error: paho-mqtt not installed", file=sys.stderr)
    sys.exit(1)


class CloudMLService:
    """
    Cloud ML inference service using PyTorch.

    Simulates cloud-tier ML inference with configurable network latency.
    """

    def __init__(self, model_path, broker_host="localhost", broker_port=1883,
                 cloud_latency_ms=50):
        """
        Initialize cloud ML service.

        Args:
            model_path: Path to PyTorch model file (.pt or .pth)
            broker_host: MQTT broker hostname
            broker_port: MQTT broker port
            cloud_latency_ms: Simulated cloud network latency (one-way, in ms)
        """
        self.model_path = model_path
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.cloud_latency_ms = cloud_latency_ms

        self.model = None
        self.mqtt_client = None

        # Metrics
        self.inference_count = 0
        self.total_inference_time_ms = 0
        self.total_latency_ms = 0

    def load_model(self):
        """Load PyTorch model from file."""
        print(f"Loading PyTorch model: {self.model_path}", flush=True)

        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model not found: {self.model_path}")

        # Load PyTorch model
        # Note: weights_only=False is needed for models saved with torch.save(model, ...)
        # This is safe for our test models created locally
        self.model = torch.load(self.model_path, weights_only=False)
        self.model.eval()  # Set to evaluation mode

        print(f"Model loaded successfully", flush=True)
        print(f"  Model type: {type(self.model).__name__}", flush=True)
        print(f"  Cloud latency: {self.cloud_latency_ms}ms (one-way)", flush=True)

    def connect_mqtt(self):
        """Connect to MQTT broker."""
        print(f"Connecting to MQTT broker: {self.broker_host}:{self.broker_port}", flush=True)

        self.mqtt_client = mqtt.Client(client_id="cloud_ml_service")
        self.mqtt_client.on_connect = self._on_connect
        self.mqtt_client.on_message = self._on_message

        self.mqtt_client.connect(self.broker_host, self.broker_port, keepalive=60)

        print("Connected to MQTT broker", flush=True)

    def _on_connect(self, client, userdata, flags, rc):
        """Handle MQTT connection."""
        if rc == 0:
            print("MQTT connected successfully", flush=True)
            # Subscribe to inference requests
            client.subscribe("ml/inference/request")
            print("Subscribed to: ml/inference/request", flush=True)
        else:
            print(f"MQTT connection failed with code {rc}", flush=True)

    def _on_message(self, client, userdata, msg):
        """Handle incoming MQTT message (inference request)."""
        try:
            # Simulate network latency to cloud (uplink)
            time.sleep(self.cloud_latency_ms / 1000.0)

            # Parse request
            request = json.loads(msg.payload.decode('utf-8'))
            device_id = request.get('device_id')
            timestamp_us = request.get('timestamp_us')
            features = request.get('features')

            if not device_id or features is None:
                print(f"Invalid request: missing device_id or features", flush=True)
                return

            print(f"Cloud inference request from {device_id}", flush=True)

            # Run inference
            start_time = time.time()
            prediction = self.run_inference(features)
            inference_time_ms = (time.time() - start_time) * 1000

            # Simulate network latency from cloud (downlink)
            time.sleep(self.cloud_latency_ms / 1000.0)

            # Total latency includes both network delays
            total_latency_ms = (self.cloud_latency_ms * 2) + inference_time_ms

            # Update metrics
            self.inference_count += 1
            self.total_inference_time_ms += inference_time_ms
            self.total_latency_ms += total_latency_ms

            # Create response
            response = {
                'device_id': device_id,
                'timestamp_us': timestamp_us,
                'prediction': float(prediction),
                'inference_time_ms': inference_time_ms,
                'cloud_latency_ms': self.cloud_latency_ms * 2,  # Round-trip
                'total_latency_ms': total_latency_ms
            }

            # Publish result
            result_topic = f"ml/inference/result/{device_id}"
            client.publish(result_topic, json.dumps(response))

            print(f"  Prediction: {prediction:.4f}, " +
                  f"Inference: {inference_time_ms:.2f}ms, " +
                  f"Total (with latency): {total_latency_ms:.2f}ms", flush=True)

        except json.JSONDecodeError as e:
            print(f"Invalid JSON in request: {e}", flush=True)
        except Exception as e:
            print(f"Error processing request: {e}", flush=True)

    def run_inference(self, features):
        """
        Run PyTorch inference on features.

        Args:
            features: List of feature values

        Returns:
            Prediction score (0-1)
        """
        with torch.no_grad():  # Disable gradient computation
            # Convert to PyTorch tensor
            features_tensor = torch.tensor(features, dtype=torch.float32).reshape(1, -1)

            # Run inference
            output = self.model(features_tensor)

            # Extract prediction (probability score)
            # Handle both single output and multi-output models
            if isinstance(output, torch.Tensor):
                prediction = torch.sigmoid(output).item()  # Apply sigmoid for probability
            else:
                prediction = output[0].item()

        return prediction

    def run(self):
        """Run the cloud ML service."""
        print("=" * 60, flush=True)
        print("Cloud ML Service (PyTorch)", flush=True)
        print("=" * 60, flush=True)

        # Load model
        self.load_model()

        # Connect to MQTT
        self.connect_mqtt()

        # Start MQTT loop
        print("\nService ready. Waiting for inference requests...", flush=True)
        print(f"Cloud latency: {self.cloud_latency_ms}ms one-way " +
              f"({self.cloud_latency_ms * 2}ms round-trip)", flush=True)
        print("Press Ctrl+C to stop", flush=True)

        try:
            self.mqtt_client.loop_forever()
        except KeyboardInterrupt:
            print("\nShutting down...", flush=True)
            self.print_stats()
        finally:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()

    def print_stats(self):
        """Print service statistics."""
        print("\nService Statistics:", flush=True)
        print(f"  Total inferences: {self.inference_count}", flush=True)
        if self.inference_count > 0:
            avg_inference_time = self.total_inference_time_ms / self.inference_count
            avg_total_latency = self.total_latency_ms / self.inference_count
            print(f"  Average inference time: {avg_inference_time:.2f}ms", flush=True)
            print(f"  Average total latency (with cloud): {avg_total_latency:.2f}ms", flush=True)


def main():
    """Main entry point for standalone cloud ML service."""
    import argparse

    parser = argparse.ArgumentParser(description="Cloud ML Service (PyTorch)")
    parser.add_argument("model_path", help="Path to PyTorch model file (.pt or .pth)")
    parser.add_argument("--broker-host", default="localhost", help="MQTT broker host")
    parser.add_argument("--broker-port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--cloud-latency", type=float, default=50.0,
                        help="Simulated cloud network latency (one-way, ms)")

    args = parser.parse_args()

    # Create and run service
    service = CloudMLService(
        model_path=args.model_path,
        broker_host=args.broker_host,
        broker_port=args.broker_port,
        cloud_latency_ms=args.cloud_latency
    )
    service.run()


if __name__ == "__main__":
    main()
