# TASK: M3 Comprehensive Testing (All M3 Stages)

**Delegated to:** Testing Agent
**Created:** 2025-11-15
**Priority:** CRITICAL
**Status:** PENDING

---

## Overview

This task consolidates ALL M3 testing requirements across M3a (Edge ML), M3b (Cloud ML), and M3c (Schema). Complete all tests in sequence and report results.

**What's been implemented:**
- M3a: Edge ML Inference Container (ONNX Runtime in Docker)
- M3b: Cloud ML Service (PyTorch Python service)
- M3c: ML Placement YAML Schema extension

**Dependencies required:**
- Docker daemon running
- PyTorch (pip install torch)
- ONNX Runtime (pip install onnxruntime)
- paho-mqtt (pip install paho-mqtt)
- pytest

---

## Step 1: Generate Test Models

**Why:** Both M3a and M3b need model files (.onnx and .pt).

```bash
cd /home/user/xedgesim
python models/create_test_model.py
```

**Expected output:**
- `models/anomaly_detector.onnx` (for edge tier)
- `models/anomaly_detector.pt` (for cloud tier)

**Validation:**
- Both files created successfully
- ONNX validation passes
- PyTorch validation passes
- Test inference outputs probability score (0-1)

**Report in results:**
- Model creation output (full log)
- File sizes
- Test inference results

---

## Step 2: M3a Edge ML Inference Tests

**Location:** `tests/stages/M3a/test_ml_inference.py`

**Run:**
```bash
pytest tests/stages/M3a/ -v
```

**Expected: 7 tests**
1. `test_ml_container_starts` - Container starts successfully
2. `test_model_loads` - ONNX model loads
3. `test_mqtt_subscription` - Subscribes to MQTT topics
4. `test_inference_request` - Processes inference request
5. `test_inference_result` - Publishes result via MQTT
6. `test_inference_latency` - Latency < 100ms for simple model
7. `test_end_to_end` - Complete sensor → inference → result flow

**Key validation:**
- All 7/7 tests pass
- Edge inference latency (should be ~5-10ms for CPU)
- MQTT communication works
- Docker container networking (macOS/Colima ports)

**Known issue:** macOS/Colima networking (4th occurrence)
- Tests use `localhost:1883` with port mapping
- Should work, but verify if connection hangs

**Report in results:**
- Test output (pass/fail for each test)
- Inference latency measurements
- Any failures with full error messages

---

## Step 3: M3b Cloud ML Service Tests

**Location:** `tests/stages/M3b/test_cloud_ml_service.py`

**Run:**
```bash
pytest tests/stages/M3b/ -v
```

**Expected: 6 tests**
1. `test_cloud_service_loads_model` - PyTorch model loading
2. `test_cloud_service_mqtt_connection` - MQTT connection
3. `test_cloud_inference_request` - Inference request handling
4. `test_cloud_inference_result` - Result publishing
5. `test_cloud_latency_simulation` - Cloud latency validation (100ms)
6. `test_edge_vs_cloud_comparison` - Latency comparison

**Key validation:**
- All 6/6 tests pass
- Cloud total latency = inference time + 100ms (50ms uplink + 50ms downlink)
- CloudMLService runs in Python (not Docker)
- MQTT broker in Docker, service in Python

**Expected measurements:**
- Cloud inference time: ~5-10ms (PyTorch CPU)
- Cloud network latency: 100ms (simulated)
- Total cloud latency: ~105-110ms
- Edge latency: ~5-10ms (for comparison)
- **Ratio: Cloud should be ~20x slower than edge**

**Report in results:**
- Test output (pass/fail for each test)
- Latency measurements from `test_cloud_latency_simulation`
- Edge vs cloud comparison metrics

---

## Step 4: M3c Schema Validation Tests

**NOTE:** Schema tests need to be created first. Here's what to create:

### Create test file: `tests/stages/M3c/test_ml_schema.py`

```python
"""
M3c: ML Inference YAML Schema Validation Tests

Tests for ml_inference section in YAML scenarios.
"""

import pytest
import tempfile
import yaml
from pathlib import Path
import sys

# Add sim to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from sim.config.scenario import load_scenario


def test_edge_placement_config(tmp_path):
    """Test YAML with edge ML placement config."""
    # Create dummy model file
    model_file = tmp_path / "test.onnx"
    model_file.write_text("dummy")

    # Create test scenario YAML
    scenario_yaml = tmp_path / "test.yaml"
    scenario_yaml.write_text(f"""
simulation:
  duration_s: 10
  seed: 42

ml_inference:
  placement: edge
  edge_config:
    model_path: {str(model_file)}
    broker_host: localhost
    broker_port: 1883

nodes:
  - id: sensor1
    type: sensor
    port: 5001
""")

    # Load and validate
    scenario = load_scenario(str(scenario_yaml))
    assert scenario.ml_inference is not None
    assert scenario.ml_inference.placement == "edge"
    assert scenario.ml_inference.edge_config['model_path'] == str(model_file)


def test_cloud_placement_config(tmp_path):
    """Test YAML with cloud ML placement config."""
    model_file = tmp_path / "test.pt"
    model_file.write_text("dummy")

    scenario_yaml = tmp_path / "test.yaml"
    scenario_yaml.write_text(f"""
simulation:
  duration_s: 10
  seed: 42

ml_inference:
  placement: cloud
  cloud_config:
    model_path: {str(model_file)}
    broker_host: localhost
    broker_port: 1883
    latency_ms: 50

nodes:
  - id: sensor1
    type: sensor
    port: 5001
""")

    scenario = load_scenario(str(scenario_yaml))
    assert scenario.ml_inference is not None
    assert scenario.ml_inference.placement == "cloud"
    assert scenario.ml_inference.cloud_config['latency_ms'] == 50


def test_missing_ml_config(tmp_path):
    """Test scenario without ML config (should be optional)."""
    scenario_yaml = tmp_path / "test.yaml"
    scenario_yaml.write_text("""
simulation:
  duration_s: 10
  seed: 42

nodes:
  - id: sensor1
    type: sensor
    port: 5001
""")

    scenario = load_scenario(str(scenario_yaml))
    assert scenario.ml_inference is None  # Optional field


def test_invalid_placement_value(tmp_path):
    """Test invalid placement value raises error."""
    scenario_yaml = tmp_path / "test.yaml"
    scenario_yaml.write_text("""
simulation:
  duration_s: 10
  seed: 42

ml_inference:
  placement: hybrid  # Invalid!
  edge_config:
    model_path: test.onnx

nodes:
  - id: sensor1
    type: sensor
    port: 5001
""")

    with pytest.raises(ValueError, match="placement must be 'edge' or 'cloud'"):
        load_scenario(str(scenario_yaml))


def test_missing_edge_config(tmp_path):
    """Test edge placement without edge_config raises error."""
    scenario_yaml = tmp_path / "test.yaml"
    scenario_yaml.write_text("""
simulation:
  duration_s: 10
  seed: 42

ml_inference:
  placement: edge
  # Missing edge_config!

nodes:
  - id: sensor1
    type: sensor
    port: 5001
""")

    with pytest.raises(ValueError, match="requires 'edge_config'"):
        load_scenario(str(scenario_yaml))


def test_missing_cloud_config(tmp_path):
    """Test cloud placement without cloud_config raises error."""
    scenario_yaml = tmp_path / "test.yaml"
    scenario_yaml.write_text("""
simulation:
  duration_s: 10
  seed: 42

ml_inference:
  placement: cloud
  # Missing cloud_config!

nodes:
  - id: sensor1
    type: sensor
    port: 5001
""")

    with pytest.raises(ValueError, match="requires 'cloud_config'"):
        load_scenario(str(scenario_yaml))


def test_model_path_validation(tmp_path):
    """Test model path validation (file exists check)."""
    scenario_yaml = tmp_path / "test.yaml"
    scenario_yaml.write_text("""
simulation:
  duration_s: 10
  seed: 42

ml_inference:
  placement: edge
  edge_config:
    model_path: /nonexistent/model.onnx

nodes:
  - id: sensor1
    type: sensor
    port: 5001
""")

    with pytest.raises(FileNotFoundError, match="Edge ML model not found"):
        load_scenario(str(scenario_yaml))


def test_backward_compatibility(tmp_path):
    """Test existing scenarios without ml_inference still work."""
    # Load an existing M1 or M2 scenario to verify backward compatibility
    scenario_files = [
        "scenarios/m1b/simple_network.yaml",
        "scenarios/m1b/two_sensors_one_gateway.yaml"
    ]

    for scenario_file in scenario_files:
        if Path(scenario_file).exists():
            scenario = load_scenario(scenario_file)
            assert scenario.ml_inference is None  # Should be None, not error
            # Verify scenario still loads correctly
            assert scenario.duration_s > 0
            assert len(scenario.nodes) > 0
```

### Create the test directory and file:

```bash
mkdir -p tests/stages/M3c
# Create the test file above
```

### Run M3c tests:

```bash
pytest tests/stages/M3c/ -v
```

**Expected: 8 tests**
1. `test_edge_placement_config` - Edge placement config valid
2. `test_cloud_placement_config` - Cloud placement config valid
3. `test_missing_ml_config` - Optional field (backward compatible)
4. `test_invalid_placement_value` - Invalid placement rejected
5. `test_missing_edge_config` - Missing edge_config error
6. `test_missing_cloud_config` - Missing cloud_config error
7. `test_model_path_validation` - Model file validation
8. `test_backward_compatibility` - Existing scenarios still work

**Key validation:**
- Schema parsing works correctly
- Validation catches errors
- Backward compatibility maintained

**Report in results:**
- All 8/8 tests pass
- Any validation errors
- Backward compatibility status

---

## Step 5: Regression Tests

**Ensure M0-M2 still pass:**

```bash
# M0 tests
pytest tests/stages/M0/ -v

# M1 tests
pytest tests/stages/M1a/ tests/stages/M1b/ tests/stages/M1c/ tests/stages/M1d/ tests/stages/M1e/ -v

# M2 tests
pytest tests/stages/M2a/ tests/stages/M2b/ tests/stages/M2c/ tests/stages/M2d/ -v
```

**Expected:**
- All previous tests still pass
- No regressions from M3 changes

**Report summary:**
- M0: X/Y passed
- M1: X/Y passed
- M2: X/Y passed

---

## Expected Issues and Solutions

### Issue 1: PyTorch Not Installed
**Error:** `ImportError: No module named 'torch'`

**Solution:**
```bash
pip install torch
```

### Issue 2: ONNX Runtime Not Installed
**Error:** `ImportError: No module named 'onnxruntime'`

**Solution:**
```bash
pip install onnxruntime
```

### Issue 3: Model Files Missing
**Error:** `FileNotFoundError: models/anomaly_detector.pt`

**Solution:**
```bash
python models/create_test_model.py
```

### Issue 4: macOS/Colima MQTT Networking
**Context:** This is the 4th occurrence pattern.

**Symptoms:**
- MQTT broker container starts
- Tests hang on connection
- `localhost:1883` not reachable

**Solution:**
- Port mapping already configured (1883:1883)
- Verify with: `docker ps` and `docker port <container_id>`
- If still fails, may need `host.docker.internal` in MQTT config

### Issue 5: Import Path Issues
**Error:** `ModuleNotFoundError: No module named 'sim'`

**Solution:**
```bash
cd /home/user/xedgesim
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest tests/stages/M3c/ -v
```

---

## Reporting

### Create: `claude/results/TASK-M3-comprehensive-tests-RESULTS.md`

### Include:

**1. Model Creation**
- ONNX model created? (Y/N)
- PyTorch model created? (Y/N)
- Validation output
- File sizes

**2. M3a Edge ML Tests**
- Results: X/7 passed
- Each test result (pass/fail)
- Edge inference latency measurements
- Any failures with full error logs

**3. M3b Cloud ML Tests**
- Results: X/6 passed
- Each test result (pass/fail)
- Cloud latency measurements:
  - Inference time: X ms
  - Network latency: X ms (should be 100ms)
  - Total latency: X ms
- Edge vs cloud comparison

**4. M3c Schema Tests**
- Results: X/8 passed
- Each test result (pass/fail)
- Validation error messages (if any)
- Backward compatibility status

**5. Regression Tests**
- M0: X/Y passed
- M1: X/Y passed
- M2: X/Y passed
- Total regressions: X (should be 0)

**6. Issues Found**
- List all bugs discovered
- Code fixes applied (if any)
- Recommended changes

**7. Performance Summary**
- Edge inference: X ms average
- Cloud inference: X ms average
- Cloud total (with latency): X ms average
- Speedup factor: Edge is X times faster than cloud

---

## Success Criteria

**All of the following must be true:**

- [ ] ONNX and PyTorch models created successfully
- [ ] All M3a tests pass (7/7)
- [ ] All M3b tests pass (6/6)
- [ ] All M3c tests pass (8/8)
- [ ] All regression tests pass (M0-M2)
- [ ] Cloud latency simulation works (100ms added)
- [ ] Edge vs cloud shows ~20x latency difference
- [ ] No critical bugs found
- [ ] Results fully documented

---

## Timeline

**Estimated time:** 1-2 hours

**Sequence:**
1. Model creation: 5 minutes
2. M3a tests: 20 minutes
3. M3b tests: 20 minutes
4. M3c test creation: 15 minutes
5. M3c test execution: 10 minutes
6. Regression tests: 20 minutes
7. Documentation: 15 minutes

---

## Notes

**Why This Matters:**

M3 is the "killer app" for xEdgeSim - running actual ML models with real inference latency. These tests validate that:

1. **M3a**: Edge ML inference works (ONNX Runtime in Docker)
2. **M3b**: Cloud ML inference works (PyTorch with simulated latency)
3. **M3c**: Placement can be specified in YAML
4. **Combined**: Researchers can compare edge vs cloud placement decisions

**Key Metric:** Edge should be ~20x faster than cloud (5ms vs 105ms) for same model, demonstrating placement framework value.

---

**Priority:** CRITICAL - Blocking M3 completion
**Dependencies:** Docker, PyTorch, ONNX Runtime, paho-mqtt, pytest
**Complexity:** Medium-High (3 test suites + model generation)
