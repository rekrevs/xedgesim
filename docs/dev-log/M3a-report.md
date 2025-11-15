# M3a: Edge ML Inference Container

**Stage:** M3a
**Date:** 2025-11-15
**Status:** IN PROGRESS

---

## Objective

Create a Docker container that runs ONNX Runtime for ML inference on the edge tier, demonstrating xEdgeSim's ML placement capability.

**Scope:**
- Docker container with ONNX Runtime
- MQTT-based inference service (receive data, run inference, publish results)
- Simple example model (binary anomaly detection)
- Integration test: Python sensor → MQTT → ML container → results

**Explicitly excluded:**
- Complex multi-model inference
- GPU acceleration (CPU-only for now)
- Model training (use pre-trained models)
- Real-time optimization
- Resource monitoring and limits

---

## Acceptance Criteria

1. ⬜ Docker container with ONNX Runtime builds successfully
2. ⬜ Container can load .onnx model file from volume mount
3. ⬜ Service receives sensor data via MQTT
4. ⬜ Runs inference and publishes results to MQTT
5. ⬜ Inference latency measured and logged
6. ⬜ Integration test passes: sensor → broker → ML → results
7. ⬜ All M0-M2 regression tests still pass

---

## Design Decisions

### Container Architecture

**Base image:** `python:3.9-slim`
- Rationale: ONNX Runtime available via pip, smaller than full Python image
- Alternative considered: `mcr.microsoft.com/onnxruntime/onnxruntime:latest` (official but heavier)

**Dependencies:**
- `onnxruntime` (CPU-only, ~50MB)
- `paho-mqtt` (for MQTT communication)
- `numpy` (for tensor operations)

**Model loading:**
- Models mounted as volume: `/app/models/model.onnx`
- Configuration via environment variables
- Fail fast if model not found

### Inference Service Design

**MQTT Topics:**
```
Input:  ml/inference/request
Output: ml/inference/result/{device_id}
```

**Message Format:**
```json
// Request
{
  "device_id": "sensor1",
  "timestamp_us": 1000000,
  "features": [0.1, 0.2, 0.3, ...]
}

// Response
{
  "device_id": "sensor1",
  "timestamp_us": 1000000,
  "prediction": 0.85,
  "inference_time_ms": 2.5
}
```

**Processing flow:**
1. Subscribe to `ml/inference/request`
2. Parse incoming JSON message
3. Convert features to numpy array
4. Run ONNX inference
5. Publish result to `ml/inference/result/{device_id}`
6. Log metrics (latency, throughput)

---

## Implementation Plan

**Step 1:** Create simple ONNX model for testing
- Generate synthetic binary classifier (2-class anomaly detection)
- Input: 32-dimensional feature vector
- Output: Single probability score (0-1)
- Save as `models/anomaly_detector.onnx`

**Step 2:** Create ML inference service
- `containers/ml-inference/inference_service.py`
- Load ONNX model at startup
- MQTT subscriber for inference requests
- MQTT publisher for results
- Logging for metrics

**Step 3:** Create Dockerfile
- `containers/ml-inference/Dockerfile`
- Base: python:3.9-slim
- Install: onnxruntime, paho-mqtt, numpy
- Copy inference service
- Expose port (for debugging, not required)
- CMD: Run inference service

**Step 4:** Create integration test
- `tests/stages/M3a/test_ml_inference.py`
- Start Mosquitto broker
- Start ML inference container
- Send test inference request via MQTT
- Verify result received
- Check inference latency is reasonable

**Step 5:** Test and validate
- Run integration test
- Verify container startup
- Check MQTT communication
- Validate inference results
- Measure latency

---

## Tests to Add

### Integration Test (tests/stages/M3a/)

**test_ml_inference.py:**
```python
def test_ml_container_starts():
    """Test ML inference container starts successfully"""

def test_model_loads():
    """Test container can load ONNX model"""

def test_inference_request():
    """Test inference request via MQTT"""

def test_inference_result():
    """Test inference result received via MQTT"""

def test_inference_latency():
    """Test inference latency is reasonable (<100ms)"""

def test_end_to_end():
    """Test complete flow: sensor -> inference -> result"""
```

---

## Example Model Creation

For testing, create a simple ONNX model using this Python script:

```python
import torch
import torch.nn as nn
import torch.onnx

class SimpleAnomalyDetector(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc1 = nn.Linear(32, 16)
        self.fc2 = nn.Linear(16, 1)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        x = torch.relu(self.fc1(x))
        x = self.fc2(x)
        x = self.sigmoid(x)
        return x

# Create model
model = SimpleAnomalyDetector()
model.eval()

# Export to ONNX
dummy_input = torch.randn(1, 32)
torch.onnx.export(
    model,
    dummy_input,
    "models/anomaly_detector.onnx",
    input_names=['features'],
    output_names=['probability'],
    dynamic_axes={
        'features': {0: 'batch_size'},
        'probability': {0: 'batch_size'}
    }
)
```

---

## Known Limitations

**Intentional for M3a:**
- CPU-only inference (no GPU)
- Single model only (no multi-model)
- Simple binary classification (not complex models)
- No model versioning or A/B testing
- No request batching or optimization

---

**Status:** IN PROGRESS
**Estimated Time:** 4-6 hours
**Started:** 2025-11-15
