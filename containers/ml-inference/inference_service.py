#!/usr/bin/env python3
"""
inference_service.py - ML Inference Service for Edge Tier

Runs ONNX Runtime for ML inference on edge tier.
Receives inference requests via MQTT, runs inference, publishes results.

MQTT Topics:
  Input:  ml/inference/request
  Output: ml/inference/result/{device_id}

Message Format (JSON):
  Request:  {"device_id": "sensor1", "timestamp_us": 1000000, "features": [0.1, 0.2, ...]}
  Response: {"device_id": "sensor1", "timestamp_us": 1000000, "prediction": 0.85, "inference_time_ms": 2.5}
"""

import os
import sys
import json
import time
import numpy as np

# Check dependencies
try:
    import onnxruntime as ort
except ImportError:
    print("Error: onnxruntime not installed", file=sys.stderr)
    sys.exit(1)

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("Error: paho-mqtt not installed", file=sys.stderr)
    sys.exit(1)


class MLInferenceService:
    """ML inference service using ONNX Runtime."""

    def __init__(self, model_path, broker_host="localhost", broker_port=1883):
        """
        Initialize ML inference service.

        Args:
            model_path: Path to ONNX model file
            broker_host: MQTT broker hostname
            broker_port: MQTT broker port
        """
        self.model_path = model_path
        self.broker_host = broker_host
        self.broker_port = broker_port

        self.session = None
        self.input_name = None
        self.output_name = None
        self.mqtt_client = None

        # Metrics
        self.inference_count = 0
        self.total_inference_time_ms = 0

    def load_model(self):
        """Load ONNX model."""
        print(f"Loading ONNX model: {self.model_path}", flush=True)

        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model not found: {self.model_path}")

        # Create ONNX Runtime session
        self.session = ort.InferenceSession(self.model_path)

        # Get input/output names
        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name

        input_shape = self.session.get_inputs()[0].shape
        output_shape = self.session.get_outputs()[0].shape

        print(f"Model loaded successfully", flush=True)
        print(f"  Input: {self.input_name}, shape: {input_shape}", flush=True)
        print(f"  Output: {self.output_name}, shape: {output_shape}", flush=True)

    def connect_mqtt(self):
        """Connect to MQTT broker."""
        print(f"Connecting to MQTT broker: {self.broker_host}:{self.broker_port}", flush=True)

        self.mqtt_client = mqtt.Client(client_id="ml_inference_service")
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
            # Parse request
            request = json.loads(msg.payload.decode('utf-8'))
            device_id = request.get('device_id')
            timestamp_us = request.get('timestamp_us')
            features = request.get('features')

            if not device_id or features is None:
                print(f"Invalid request: missing device_id or features", flush=True)
                return

            print(f"Inference request from {device_id}", flush=True)

            # Run inference
            start_time = time.time()
            prediction = self.run_inference(features)
            inference_time_ms = (time.time() - start_time) * 1000

            # Update metrics
            self.inference_count += 1
            self.total_inference_time_ms += inference_time_ms

            # Create response
            response = {
                'device_id': device_id,
                'timestamp_us': timestamp_us,
                'prediction': float(prediction),
                'inference_time_ms': inference_time_ms
            }

            # Publish result
            result_topic = f"ml/inference/result/{device_id}"
            client.publish(result_topic, json.dumps(response))

            print(f"  Prediction: {prediction:.4f}, Time: {inference_time_ms:.2f}ms", flush=True)

        except json.JSONDecodeError as e:
            print(f"Invalid JSON in request: {e}", flush=True)
        except Exception as e:
            print(f"Error processing request: {e}", flush=True)

    def run_inference(self, features):
        """
        Run inference on features.

        Args:
            features: List of feature values

        Returns:
            Prediction score (0-1)
        """
        # Convert to numpy array
        features_array = np.array(features, dtype=np.float32).reshape(1, -1)

        # Run inference
        inputs = {self.input_name: features_array}
        outputs = self.session.run([self.output_name], inputs)

        # Extract prediction (probability score)
        prediction = outputs[0][0][0]

        return prediction

    def run(self):
        """Run the inference service."""
        print("=" * 60, flush=True)
        print("ML Inference Service", flush=True)
        print("=" * 60, flush=True)

        # Load model
        self.load_model()

        # Connect to MQTT
        self.connect_mqtt()

        # Start MQTT loop
        print("\nService ready. Waiting for inference requests...", flush=True)
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
            avg_time = self.total_inference_time_ms / self.inference_count
            print(f"  Average inference time: {avg_time:.2f}ms", flush=True)


def main():
    """Main entry point."""
    # Get configuration from environment
    model_path = os.environ.get('MODEL_PATH', '/app/models/anomaly_detector.onnx')
    broker_host = os.environ.get('MQTT_BROKER_HOST', 'localhost')
    broker_port = int(os.environ.get('MQTT_BROKER_PORT', '1883'))

    # Create and run service
    service = MLInferenceService(model_path, broker_host, broker_port)
    service.run()


if __name__ == "__main__":
    main()
