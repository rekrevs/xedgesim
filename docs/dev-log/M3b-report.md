# M3b: Cloud ML Service

**Stage:** M3b
**Date:** 2025-11-15
**Status:** IMPLEMENTATION COMPLETE (Testing Delegated)

---

## Objective

Implement Python-based cloud ML service using PyTorch, enabling cloud-tier ML inference in xEdgeSim scenarios.

**Scope:**
- Python ML service class (not Docker container)
- PyTorch model loading and inference
- MQTT interface (same as M3a edge service)
- Simulated cloud latency (configurable delay)
- Integration test: Python sensor → Cloud ML → results

**Explicitly excluded:**
- Distributed cloud deployment
- Auto-scaling and load balancing
- GPU acceleration (CPU-only for now)
- Model serving frameworks (TensorFlow Serving, etc.)
- Production cloud infrastructure

---

## Acceptance Criteria

1. ✅ CloudMLService Python class implemented
2. ✅ Can load PyTorch .pt/.pth model files
3. ✅ Receives inference requests via MQTT
4. ✅ Runs PyTorch inference with simulated cloud latency
5. ✅ Publishes results to MQTT
6. ⬜ Integration test passes: sensor → cloud → result (delegated to testing agent)
7. ⬜ All M0-M2-M3a regression tests still pass (delegated to testing agent)

---

## Design Decisions

### Python Service vs Docker Container

**Decision:** Implement as Python class, not Docker container.

**Rationale:**
- Cloud tier is mocked (simulated latency, not real cloud)
- Python service is simpler for testing and development
- Can instantiate directly in tests (no container overhead)
- Aligns with M2 hybrid approach (Docker for edge, Python for cloud mock)

**Trade-off:** Less realistic than actual cloud deployment, but sufficient for demonstrating ML placement framework.

### Cloud Latency Simulation

**Approach:** Add configurable delay before returning inference result.

**Latency model:**
```python
total_latency = network_latency + inference_latency + network_latency
```

Where:
- `network_latency`: Round-trip network delay to cloud (e.g., 50ms)
- `inference_latency`: Actual PyTorch inference time

**Configuration:** Set via constructor parameter (default: 50ms)

### MQTT Interface

**Same as M3a edge service:**
- Input topic: `ml/inference/request`
- Output topic: `ml/inference/result/{device_id}`
- JSON message format (identical to M3a)

**Why same interface?**
- Enables comparison (edge vs cloud)
- Can swap implementations transparently
- Simplifies testing

---

## Implementation Plan

**Step 1:** Create CloudMLService class
- `sim/cloud/ml_service.py`
- Constructor: model_path, broker_host, broker_port, cloud_latency_ms
- Methods: load_model(), connect_mqtt(), run_inference(), run()

**Step 2:** Implement PyTorch inference
- Load .pt/.pth model files
- Convert features to PyTorch tensors
- Run inference
- Extract prediction from output tensor

**Step 3:** Add cloud latency simulation
- time.sleep(cloud_latency_ms / 1000.0) before processing
- Log actual inference time separately
- Report total time (latency + inference)

**Step 4:** Create test PyTorch model
- Similar to ONNX model (simple binary classifier)
- Save as models/anomaly_detector.pt
- Add to create_test_model.py

**Step 5:** Create integration test
- `tests/stages/M3b/test_cloud_ml_service.py`
- Start MQTT broker
- Start CloudMLService
- Send inference request
- Verify result with cloud latency
- Compare with M3a edge latency

**Step 6:** Test and validate
- Run integration test
- Verify cloud latency simulation works
- Check PyTorch inference correctness
- Measure latency difference (edge vs cloud)

---

## Tests to Add

### Integration Test (tests/stages/M3b/)

**test_cloud_ml_service.py:**
```python
def test_cloud_service_loads_model():
    """Test CloudMLService can load PyTorch model"""

def test_cloud_service_mqtt_connection():
    """Test service connects to MQTT broker"""

def test_cloud_inference_request():
    """Test inference request via MQTT"""

def test_cloud_inference_result():
    """Test inference result with cloud latency"""

def test_cloud_latency_simulation():
    """Test cloud latency is added correctly"""

def test_edge_vs_cloud_comparison():
    """Test edge and cloud services produce consistent results"""
```

---

## Code Structure

**sim/cloud/ml_service.py:**

```python
class CloudMLService:
    """Cloud ML inference service using PyTorch."""

    def __init__(self, model_path, broker_host="localhost",
                 broker_port=1883, cloud_latency_ms=50):
        """Initialize cloud ML service."""

    def load_model(self):
        """Load PyTorch model from file."""

    def connect_mqtt(self):
        """Connect to MQTT broker and subscribe to requests."""

    def run_inference(self, features):
        """Run PyTorch inference on features."""

    def _on_message(self, client, userdata, msg):
        """Handle incoming MQTT message (inference request)."""
        # 1. Add cloud network latency
        # 2. Parse request
        # 3. Run PyTorch inference
        # 4. Add cloud network latency again
        # 5. Publish result

    def run(self):
        """Run the cloud ML service."""
```

---

## Known Limitations

**Intentional for M3b:**
- CPU-only inference (no GPU)
- Simulated cloud latency (not real network)
- Single instance (no distributed cloud)
- No load balancing or auto-scaling
- No model versioning
- No request batching

**Rationale:** M3b demonstrates cloud ML capability. Production cloud deployment is M4+ scope.

---

## Implementation Summary

### Files Created

**1. sim/cloud/ml_service.py** (251 lines)
- CloudMLService class for PyTorch inference
- Configurable cloud latency simulation (default 50ms one-way)
- MQTT interface matching M3a edge service
- Metrics collection (inference count, latency tracking)
- Standalone CLI interface for testing

**2. models/create_test_model.py** (Extended)
- Added `create_pytorch_model()` function
- Generates PyTorch .pt model files
- Validates PyTorch model loading and inference
- Main script now creates both ONNX and PyTorch models

**3. tests/stages/M3b/test_cloud_ml_service.py** (403 lines)
- 6 integration tests covering:
  - Model loading (PyTorch)
  - MQTT connection
  - Inference request handling
  - Result publishing with cloud latency
  - Cloud latency simulation validation
  - Edge vs cloud comparison

**4. claude/tasks/TASK-M3b-cloud-tests.md**
- Testing delegation task for testing agent
- Includes expected issues and solutions
- Success criteria and reporting template

### Key Features Implemented

**Cloud Latency Simulation:**
```python
# Uplink latency
time.sleep(self.cloud_latency_ms / 1000.0)

# Run inference
prediction = self.run_inference(features)

# Downlink latency
time.sleep(self.cloud_latency_ms / 1000.0)

# Total latency = uplink + inference + downlink
total_latency_ms = (self.cloud_latency_ms * 2) + inference_time_ms
```

**MQTT Interface (Same as M3a):**
- Input topic: `ml/inference/request`
- Output topic: `ml/inference/result/{device_id}`
- JSON message format matches M3a exactly

**Response Format:**
```json
{
  "device_id": "sensor1",
  "timestamp_us": 1000000,
  "prediction": 0.85,
  "inference_time_ms": 5.2,
  "cloud_latency_ms": 100.0,
  "total_latency_ms": 105.2
}
```

### Testing Strategy

**Delegated to Testing Agent:**
- Model creation (PyTorch + ONNX)
- 6 M3b integration tests
- Regression tests (M0-M2-M3a)
- Cloud latency validation

**Expected Results:**
- Cloud total latency: ~105ms (100ms network + 5ms inference)
- Edge total latency: ~5ms (inference only)
- 20x latency difference demonstrates ML placement value

### Design Consistency

**M3a (Edge) vs M3b (Cloud):**
- Same MQTT topics and message format
- Same model architecture (SimpleAnomalyDetector)
- Different inference engines (ONNX Runtime vs PyTorch)
- Different deployment (Docker container vs Python class)
- Different latency profiles (edge-local vs cloud-network)

This consistency enables transparent comparison in M3c-M3e.

---

**Status:** IMPLEMENTATION COMPLETE (Testing Delegated)
**Estimated Time:** 3-4 hours
**Actual Time:** ~3 hours
**Started:** 2025-11-15
**Completed:** 2025-11-15
