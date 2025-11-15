# ML Placement Framework - User Guide

**xEdgeSim ML Placement Framework (M3)**

This guide explains how to use xEdgeSim's ML placement framework to evaluate edge vs cloud ML inference strategies.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Quick Start](#quick-start)
4. [Running Scenarios](#running-scenarios)
5. [Collecting Metrics](#collecting-metrics)
6. [Analyzing Results](#analyzing-results)
7. [Example Workflows](#example-workflows)
8. [Understanding Results](#understanding-results)

---

## Overview

The ML Placement Framework enables researchers to:
- **Run actual ML models** (ONNX, PyTorch) in simulation
- **Compare placement strategies** (edge vs cloud inference)
- **Measure real latency** (not abstract models)
- **Analyze trade-offs** (latency vs complexity)

**Key differentiator:** Unlike other simulators (iFogSim, EdgeCloudSim), xEdgeSim runs **real ML models** and measures **actual inference latency**.

---

## Architecture

### Components (M3a-M3e)

**M3a: Edge ML Inference Container**
- ONNX Runtime in Docker containers
- Runs on edge gateway nodes
- Low latency (~5-10ms), limited model complexity
- Production-ready deployment

**M3b: Cloud ML Service**
- PyTorch-based inference service
- Simulated cloud latency (50ms one-way, 100ms round-trip)
- Higher latency (~105ms), supports complex models
- Python implementation

**M3c: ML Placement YAML Schema**
- Specify placement in scenario files
- `placement: edge` or `placement: cloud`
- Same topology, different inference location

**M3d: ML Metrics Collection**
- Tracks inference latency (edge vs cloud)
- CSV export for analysis
- Statistics computation (mean, p50, p95, p99)
- Comparison utility

**M3e: Placement Comparison Example**
- Demonstration scenarios
- Documentation and workflows
- Expected results and interpretation

### Data Flow

**Edge Placement:**
```
Sensor → MQTT → Edge Gateway (ONNX) → Result
                 (5-10ms)
```

**Cloud Placement:**
```
Sensor → MQTT → Cloud Service (PyTorch) → Result
                 (100ms network + 5ms inference = 105ms)
```

---

## Quick Start

### Prerequisites

- Docker installed and running
- Python 3.9+ with dependencies:
  ```bash
  pip install torch onnxruntime paho-mqtt pyyaml
  ```
- xEdgeSim repository cloned

### Generate Test Models

```bash
cd /path/to/xedgesim
python models/create_test_model.py
```

This creates:
- `models/anomaly_detector.onnx` (for edge tier)
- `models/anomaly_detector.pt` (for cloud tier)

### Verify Installation

```bash
# Check ONNX model
python -c "import onnxruntime as ort; print(f'ONNX Runtime: {ort.__version__}')"

# Check PyTorch model
python -c "import torch; print(f'PyTorch: {torch.__version__}')"

# Check Docker
docker ps
```

---

## Running Scenarios

### Edge Placement Scenario

**Scenario:** `scenarios/m3c/edge_ml_placement.yaml`

**1. Start MQTT Broker**
```bash
docker run -d --name mqtt-broker \
  -p 1883:1883 \
  eclipse-mosquitto:latest
```

**2. Start Edge ML Container**
```bash
docker run -d --name ml-edge \
  --network host \
  -v $(pwd)/models:/app/models:ro \
  -e MODEL_PATH=/app/models/anomaly_detector.onnx \
  -e MQTT_BROKER_HOST=localhost \
  -e MQTT_BROKER_PORT=1883 \
  xedgesim/ml-inference:latest
```

**3. Run Simulation**
```bash
# Note: This is conceptual - actual run_scenario.py implementation pending
python examples/run_edge_placement.py
```

**4. Check Metrics**
```bash
# Metrics saved to metrics/edge_results.csv
head metrics/edge_results.csv
```

### Cloud Placement Scenario

**Scenario:** `scenarios/m3c/cloud_ml_placement.yaml`

**1. Start MQTT Broker** (same as above)

**2. Start Cloud ML Service**
```bash
python -c "
from sim.cloud.ml_service import CloudMLService

service = CloudMLService(
    model_path='models/anomaly_detector.pt',
    broker_host='localhost',
    broker_port=1883,
    cloud_latency_ms=50  # 50ms one-way
)
service.load_model()
service.connect_mqtt()
service.run()
"
```

**3. Run Simulation**
```bash
python examples/run_cloud_placement.py
```

**4. Check Metrics**
```bash
head metrics/cloud_results.csv
```

---

## Collecting Metrics

### Using MLMetricsCollector

```python
from sim.metrics.ml_metrics import MLMetricsCollector

# Initialize collector
metrics = MLMetricsCollector(output_dir="metrics")

# Record edge inference
metrics.record_inference(
    timestamp_us=1000000,
    device_id="sensor1",
    placement="edge",
    inference_time_ms=5.2,
    cloud_latency_ms=0,
    total_latency_ms=5.2
)

# Record cloud inference
metrics.record_inference(
    timestamp_us=2000000,
    device_id="sensor2",
    placement="cloud",
    inference_time_ms=4.8,
    cloud_latency_ms=100,
    total_latency_ms=104.8
)

# Export to CSV
metrics.export_csv("ml_metrics.csv")

# Print summary
metrics.print_summary()
```

### CSV Format

```csv
timestamp_us,device_id,placement,inference_time_ms,cloud_latency_ms,total_latency_ms
1000000,sensor1,edge,5.2,0.0,5.2
2000000,sensor2,cloud,4.8,100.0,104.8
```

---

## Analyzing Results

### Comparison Utility

```bash
# Compare edge vs cloud from single file
python scripts/compare_ml_metrics.py metrics/combined.csv

# Compare from separate files
python scripts/compare_ml_metrics.py \
  --edge metrics/edge_results.csv \
  --cloud metrics/cloud_results.csv
```

### Example Output

```
======================================================================
ML Placement Comparison
======================================================================

Edge Placement:
  Samples: 100
  Mean inference time: 5.35ms
  Mean total latency: 5.35ms
  P50 total latency: 5.20ms
  P95 total latency: 8.10ms

Cloud Placement:
  Samples: 100
  Mean inference time: 4.95ms
  Mean cloud latency: 100.00ms
  Mean total latency: 104.95ms
  P50 total latency: 104.80ms
  P95 total latency: 107.30ms

Comparison:
  Edge is 19.6x faster than cloud (mean latency)
  Cloud latency breakdown:
    Network: 100.00ms (95.3%)
    Inference: 4.95ms (4.7%)
======================================================================
```

---

## Example Workflows

### Workflow 1: Basic Edge vs Cloud Comparison

**Goal:** Compare edge and cloud placement for same scenario

```bash
# 1. Run edge variant
./examples/run_edge_placement.sh > logs/edge.log 2>&1

# 2. Run cloud variant
./examples/run_cloud_placement.sh > logs/cloud.log 2>&1

# 3. Compare results
python scripts/compare_ml_metrics.py \
  --edge metrics/edge_results.csv \
  --cloud metrics/cloud_results.csv
```

**Expected result:** Edge ~20x faster than cloud

### Workflow 2: Latency Requirements Analysis

**Goal:** Determine if edge placement meets latency requirements

```bash
# Run edge placement
./examples/run_edge_placement.sh

# Analyze P95 latency
python -c "
import csv
latencies = []
with open('metrics/edge_results.csv') as f:
    reader = csv.DictReader(f)
    latencies = [float(r['total_latency_ms']) for r in reader]

latencies.sort()
p95 = latencies[int(len(latencies) * 0.95)]
print(f'P95 latency: {p95:.2f}ms')

if p95 < 10:
    print('✓ Meets real-time requirement (<10ms)')
else:
    print('✗ Does not meet real-time requirement')
"
```

### Workflow 3: Model Complexity vs Latency

**Goal:** Understand trade-offs between model complexity and latency

```
Edge tier:
  - ONNX Runtime (optimized)
  - Simple models only
  - Fast inference (~5ms)
  - Limited accuracy

Cloud tier:
  - PyTorch (full framework)
  - Complex models supported
  - Slower total latency (~105ms)
  - Higher accuracy potential
```

---

## Understanding Results

### Latency Breakdown

**Edge Placement:**
```
Total Latency = Inference Time
              ≈ 5-10ms
```

**Cloud Placement:**
```
Total Latency = Network Uplink + Inference + Network Downlink
              = 50ms + 5ms + 50ms
              ≈ 105ms
```

### When to Use Edge

✅ **Use edge when:**
- Low latency required (< 50ms)
- Real-time response needed
- Network unreliable
- Privacy/data sovereignty important
- Simple models sufficient

### When to Use Cloud

✅ **Use cloud when:**
- Higher latency acceptable (> 100ms)
- Complex models needed
- Limited edge compute available
- Frequent model updates required
- Centralized analytics needed

### Performance Expectations

| Metric | Edge (ONNX) | Cloud (PyTorch) |
|--------|-------------|-----------------|
| Mean Latency | 5-10ms | 100-110ms |
| P95 Latency | 8-15ms | 105-120ms |
| Speedup | 1x (baseline) | 0.05x (20x slower) |
| Model Complexity | Simple | Complex |
| Deployment | Container | Python Service |

---

## Advanced Topics

### Custom Models

**Edge (ONNX):**
```python
# Export PyTorch model to ONNX
import torch

model = YourModel()
dummy_input = torch.randn(1, input_dim)

torch.onnx.export(
    model,
    dummy_input,
    "models/your_model.onnx",
    input_names=['features'],
    output_names=['prediction']
)
```

**Cloud (PyTorch):**
```python
# Save PyTorch model
torch.save(model, "models/your_model.pt")
```

### Adjusting Cloud Latency

Modify simulated cloud latency in YAML:

```yaml
ml_inference:
  placement: cloud
  cloud_config:
    model_path: models/anomaly_detector.pt
    latency_ms: 25  # 25ms one-way (50ms round-trip)
```

Or when starting CloudMLService:

```python
service = CloudMLService(
    model_path="models/anomaly_detector.pt",
    cloud_latency_ms=25  # Adjust based on network conditions
)
```

### Hybrid Placement (Future)

**Concept:** Route requests based on conditions

```
if urgency == "high":
    use edge (fast, lower accuracy)
else:
    use cloud (slower, higher accuracy)
```

**Status:** Deferred to M4+ (requires routing logic)

---

## Troubleshooting

### Issue: Edge container can't find model

**Error:** `FileNotFoundError: /app/models/anomaly_detector.onnx`

**Solution:** Ensure volume mount is correct:
```bash
docker run ... -v $(pwd)/models:/app/models:ro ...
```

### Issue: MQTT connection timeout

**Error:** Connection to localhost:1883 times out

**Solution (macOS/Colima):** Use `host.docker.internal` instead:
```bash
docker run ... -e MQTT_BROKER_HOST=host.docker.internal ...
```

### Issue: PyTorch model loading fails

**Error:** `weights_only=True` pickle error

**Solution:** Ensure model created with new script:
```bash
python models/create_test_model.py  # Regenerate models
```

---

## References

- **M3a Report:** `docs/dev-log/M3a-report.md` (Edge ML Inference)
- **M3b Report:** `docs/dev-log/M3b-report.md` (Cloud ML Service)
- **M3c Report:** `docs/dev-log/M3c-report.md` (YAML Schema)
- **M3d Report:** `docs/dev-log/M3d-report.md` (Metrics Collection)
- **M3e Report:** `docs/dev-log/M3e-report.md` (This Example)

---

## Citation

If you use xEdgeSim's ML Placement Framework in your research, please cite:

```
@software{xedgesim_ml_placement_2025,
  title={xEdgeSim ML Placement Framework},
  author={xEdgeSim Contributors},
  year={2025},
  note={M3 Milestone: ML Placement Framework with Real Inference}
}
```

---

**Status:** Complete (M3e)
**Last Updated:** 2025-11-15
**Version:** 1.0
