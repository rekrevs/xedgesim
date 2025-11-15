# TASK: M3b Cloud ML Service Testing

**Delegated to:** Testing Agent
**Created:** 2025-11-15
**Priority:** High
**Status:** PENDING

---

## Context

M3b (Cloud ML Service) implementation is complete. Need testing validation before finalizing.

**What was implemented:**
- `sim/cloud/ml_service.py` - CloudMLService class (PyTorch-based)
- `models/create_test_model.py` - Extended to create PyTorch models
- `tests/stages/M3b/test_cloud_ml_service.py` - 6 integration tests

**Dependencies:**
- PyTorch (torch) - for CloudMLService
- paho-mqtt - for MQTT communication
- Docker - for MQTT broker in tests

---

## Your Task

### 1. Generate Test Models

Run model creation script to generate both ONNX and PyTorch models:

```bash
cd /home/user/xedgesim
python models/create_test_model.py
```

This should create:
- `models/anomaly_detector.onnx` (for M3a edge tier)
- `models/anomaly_detector.pt` (for M3b cloud tier)

### 2. Run M3b Tests

Execute M3b cloud ML service tests:

```bash
pytest tests/stages/M3b/ -v
```

**Expected tests (6 total):**
1. `test_cloud_service_loads_model` - PyTorch model loading
2. `test_cloud_service_mqtt_connection` - MQTT broker connection
3. `test_cloud_inference_request` - Inference request handling
4. `test_cloud_inference_result` - Result publishing
5. `test_cloud_latency_simulation` - Cloud latency simulation (50ms one-way)
6. `test_edge_vs_cloud_comparison` - Edge vs cloud latency comparison

### 3. Verify Cloud Latency Simulation

Key validation point: Cloud service should add **100ms latency** (50ms uplink + 50ms downlink).

Check test output for:
- Total latency > 100ms
- Cloud latency reported as 100ms
- Inference time < 100ms (simple model should be fast)

### 4. Run Regression Tests

Ensure M0-M2-M3a still pass:

```bash
# M0 tests
pytest tests/stages/M0/ -v

# M1 tests
pytest tests/stages/M1a/ tests/stages/M1b/ tests/stages/M1c/ tests/stages/M1d/ tests/stages/M1e/ -v

# M2 tests
pytest tests/stages/M2a/ tests/stages/M2b/ tests/stages/M2c/ tests/stages/M2d/ -v

# M3a tests
pytest tests/stages/M3a/ -v
```

---

## Expected Issues and Solutions

### Issue 1: PyTorch Not Installed
**Error:** `ImportError: No module named 'torch'`

**Solution:**
```bash
pip install torch
```

### Issue 2: Model Files Missing
**Error:** `FileNotFoundError: models/anomaly_detector.pt`

**Solution:**
```bash
python models/create_test_model.py
```

### Issue 3: macOS/Colima Networking (MQTT Broker)
**Context:** This is the 4th occurrence of this issue pattern.

**Symptoms:**
- MQTT broker container starts
- Tests hang or timeout on connection
- `localhost:1883` not reachable

**Solution:**
Port mapping is already configured in tests. If still fails, verify:
```bash
docker ps  # Check broker container is running
docker port <container_id>  # Verify 1883 mapped correctly
```

### Issue 4: Import Path Issues
**Error:** `ModuleNotFoundError: No module named 'sim'`

**Solution:** Tests run from repo root, should work. If not:
```bash
cd /home/user/xedgesim
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest tests/stages/M3b/ -v
```

---

## Reporting

### Document Results In:
`claude/results/TASK-M3b-cloud-tests-RESULTS.md`

### Include:

1. **Model Creation Output**
   - ONNX model creation successful?
   - PyTorch model creation successful?
   - Validation inference results

2. **M3b Test Results**
   - Total tests: X/6 passed
   - Each test result (pass/fail)
   - Any failures: full error messages
   - Latency measurements from cloud_latency_simulation test

3. **Regression Test Results**
   - M0: X/Y passed
   - M1: X/Y passed
   - M2: X/Y passed
   - M3a: X/Y passed

4. **Issues Found**
   - List any bugs discovered
   - Code fixes applied (if any)
   - Recommended changes

5. **Performance Metrics**
   - Cloud inference time (ms)
   - Total latency with cloud (ms)
   - Comparison: Edge latency vs Cloud latency

---

## Success Criteria

- [ ] PyTorch and ONNX models created successfully
- [ ] All 6 M3b tests pass
- [ ] Cloud latency simulation works (100ms added)
- [ ] All regression tests pass (M0-M2-M3a)
- [ ] No critical bugs found
- [ ] Results documented

---

## Notes

**Why Python Service, Not Docker?**
- Cloud tier is mocked (simulated latency)
- Python class is simpler for testing
- Can instantiate directly without container overhead
- Aligns with M2 hybrid approach

**Cloud Latency Model:**
```
total_latency = network_uplink + inference_time + network_downlink
              = 50ms + ~5ms + 50ms
              = ~105ms
```

**Comparison with Edge:**
- Edge (M3a): Inference time only (~5ms)
- Cloud (M3b): Inference time + cloud latency (~105ms)
- Demonstrates ML placement framework value

---

**Priority:** HIGH - Blocking M3c implementation
**Estimated Time:** 30-45 minutes
**Dependencies:** Docker daemon, PyTorch, paho-mqtt
