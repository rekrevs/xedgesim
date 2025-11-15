# TASK: M3a ML Inference Container Testing

**Status:** PENDING
**Created:** 2025-11-15
**Priority:** HIGH (blocks M3b validation)
**Estimated Time:** 30-40 minutes

---

## Context

I (developer agent) have implemented M3a (Edge ML Inference Container) - the first stage of xEdgeSim's ML placement framework. This container runs ONNX Runtime for ML inference on the edge tier.

I cannot test it because:
1. Docker not available in my environment
2. ML dependencies (PyTorch, ONNX Runtime) not installed

I need you (testing agent) to:
1. Install ML dependencies
2. Create test ONNX model
3. Build ML inference container
4. Run integration tests
5. Fix any issues found
6. Document results

## What I've Implemented

**Edge ML Inference Container:**
- Docker container with ONNX Runtime
- MQTT-based inference service
- Request/response pattern for ML inference
- Model loading from volume mount
- Inference latency metrics

**Code locations:**
- `containers/ml-inference/Dockerfile` - Container definition
- `containers/ml-inference/inference_service.py` - MQTT inference service
- `models/create_test_model.py` - Generate test ONNX model
- `tests/stages/M3a/test_ml_inference.py` - 7 integration tests
- `requirements-dev.txt` - Added torch, onnxruntime, numpy

---

## Your Task

Run the M3a ML inference integration tests and fix any issues you find.

### Step 1: Install ML Dependencies

```bash
pip install -r requirements-dev.txt
```

This installs:
- `torch>=2.0.0` (PyTorch for model creation)
- `onnxruntime>=1.16.0` (ONNX Runtime for inference)
- `numpy>=1.24.0` (tensor operations)

**Note:** PyTorch is large (~1GB). Use CPU-only version if available:
```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

### Step 2: Create Test ONNX Model

```bash
python models/create_test_model.py
```

Expected output:
- Creates `models/anomaly_detector.onnx` (simple binary classifier)
- ~50KB model file
- Input: 32-dimensional features
- Output: Single probability (0-1)

Verify:
```bash
ls -lh models/anomaly_detector.onnx
```

### Step 3: Build ML Inference Container

```bash
cd containers/ml-inference
docker build -t xedgesim/ml-inference:latest .
cd ../..
```

Expected: Image builds successfully (~200MB)

Check image:
```bash
docker images | grep ml-inference
```

### Step 4: Build MQTT Broker (if not already built)

```bash
cd containers/mqtt-broker
docker build -t xedgesim/mosquitto:latest .
cd ../..
```

### Step 5: Run M3a Integration Tests

```bash
pytest tests/stages/M3a/test_ml_inference.py -v
```

This will run 7 tests:
1. `test_ml_container_starts` - Container starts successfully
2. `test_model_loads` - ONNX model loads correctly
3. `test_mqtt_subscription` - Service subscribes to MQTT
4. `test_inference_request` - Receives inference requests
5. `test_inference_result` - Publishes inference results
6. `test_inference_latency` - Inference time <100ms
7. `test_end_to_end` - Complete flow: sensor → inference → result

Expected: All 7 tests PASS

### Step 6: Run Regression Tests

Verify M0-M2 still work:

```bash
# M1d, M1e tests
pytest tests/stages/M1d/test_latency_network_model.py -v
pytest tests/stages/M1e/test_network_metrics.py -v

# M2a basic tests (no Docker)
python tests/stages/M2a/test_docker_node_basic.py

# M2b socket tests (no Docker)
python tests/stages/M2b/test_socket_interface.py

# M2d schema tests
python tests/stages/M2d/test_hybrid_schema.py
```

Expected: All regression tests still pass.

---

## Expected Results

**Success Criteria:**
- ✅ ML dependencies installed successfully
- ✅ Test ONNX model created (models/anomaly_detector.onnx)
- ✅ ML inference container builds successfully
- ✅ All 7 M3a integration tests **PASS**
- ✅ Inference latency <100ms for simple model
- ✅ All regression tests pass (M1d, M1e, M2a, M2b, M2d)
- ✅ No orphaned containers after tests

---

## If Tests Fail

**Debug locally before reporting back:**

### Issue 1: PyTorch Installation Too Large

If PyTorch download is too large/slow:

```bash
# Use CPU-only version (much smaller)
pip uninstall torch
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

### Issue 2: Model Creation Fails

```bash
# Check PyTorch installation
python -c "import torch; print(torch.__version__)"

# Try creating model manually
python models/create_test_model.py

# Check error messages
```

### Issue 3: Container Fails to Start

```bash
# Check container logs
docker logs <container_id>

# Try running container manually
docker run --rm xedgesim/ml-inference:latest

# Check if ONNX Runtime installed
docker run --rm xedgesim/ml-inference:latest python -c "import onnxruntime; print(onnxruntime.__version__)"
```

### Issue 4: MQTT Connection Issues

**Problem:** Container can't connect to broker on localhost

**Solution:** Use `host.docker.internal` for macOS/Windows:

Already implemented in test fixtures - check if it's working.

If not, try network mode:
```bash
# In test code, add to DockerNode config:
"extra_hosts": {"host.docker.internal": "host-gateway"}
```

### Issue 5: Model Not Found in Container

```bash
# Check volume mount
docker run --rm -v $(pwd)/models:/app/models xedgesim/ml-inference:latest ls -la /app/models/

# Verify model exists locally
ls -la models/anomaly_detector.onnx
```

### Issue 6: Inference Timeout

If inference takes too long:
- Check container logs for errors
- Verify ONNX Runtime loaded correctly
- Test model locally before container:

```bash
python -c "
import onnxruntime as ort
import numpy as np
session = ort.InferenceSession('models/anomaly_detector.onnx')
features = np.random.randn(1, 32).astype(np.float32)
result = session.run(None, {'features': features})
print(result)
"
```

### Issue 7: Test Hangs Waiting for Result

**Possible causes:**
- MQTT topic mismatch
- Container not receiving requests
- Container crashed silently

**Debug:**
```bash
# Check container status
docker ps | grep ml-inference

# Check container logs in real-time
docker logs -f <container_id>

# Manually send MQTT message
mosquitto_pub -h localhost -t ml/inference/request -m '{"device_id":"test","timestamp_us":0,"features":[0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,0.1,0.2,0.3,0.4,0.5]}'

# Subscribe to results
mosquitto_sub -h localhost -t 'ml/inference/result/#' -v
```

---

## Document Results

Create `claude/results/TASK-M3a-ml-tests.md` with:

```markdown
# Results: M3a ML Inference Container Testing

**Status:** ✅ SUCCESS / ❌ FAILED / ⚠️ PARTIAL
**Completed:** 2025-11-15T[time]
**Duration:** [X minutes]

## ML Dependencies Installation

```
[Paste pip install output]
```

Installed versions:
- PyTorch: X.X.X
- ONNX Runtime: X.X.X
- NumPy: X.X.X

## Test Model Creation

```
[Paste create_test_model.py output]
```

Model file: models/anomaly_detector.onnx (XX KB)

## Container Build

```
[Paste docker build output]
```

Image size: XX MB

## M3a Integration Tests

```
[Paste full pytest output here]
```

### Summary
- test_ml_container_starts: ✅/❌
- test_model_loads: ✅/❌
- test_mqtt_subscription: ✅/❌
- test_inference_request: ✅/❌
- test_inference_result: ✅/❌
- test_inference_latency: ✅/❌ (X.XX ms)
- test_end_to_end: ✅/❌

**Total:** X/7 passed

## Regression Tests

- M1d latency model: X/8 passed
- M1e network metrics: X/8 passed
- M2a basic: X/3 passed
- M2b socket: X/5 passed
- M2d schema: X/8 passed

**Total:** X/32 regression tests passed

## Issues Found

[List any problems discovered]

Example:
- ONNX Runtime version mismatch in container
- Model file not mounted correctly
- MQTT broker connection timeout
- Inference latency higher than expected (XXms vs <100ms target)

## Fixes Applied

[Describe code changes made, with file paths and line numbers]

Example:
- Fixed volume mount path in test_ml_inference.py:85
- Updated Dockerfile to pin ONNX Runtime version
- Added retry logic for MQTT connection
- Increased inference timeout from 2s to 5s

## Commits Made

```bash
git log --oneline -n 3
```

Example:
- abc1234 fix(M3a): Fix ONNX model volume mount
- def5678 fix(M3a): Pin ONNX Runtime to 1.16.0
- ghi9012 test: Complete M3a ML inference testing

## Performance Metrics

Inference latency (average over 10 requests):
- Mean: X.XX ms
- Min: X.XX ms
- Max: X.XX ms
- Std Dev: X.XX ms

Model accuracy (on synthetic test data):
- [If applicable, report accuracy metrics]

Container resource usage:
- Memory: XX MB
- CPU: X%
- Startup time: X seconds

## Testing Environment

- **OS:** macOS Sequoia / Linux
- **Architecture:** arm64 / x86_64
- **Docker Runtime:** Colima / Docker Desktop version
- **Python:** X.X.X
- **PyTorch:** X.X.X
- **ONNX Runtime:** X.X.X

## Next Steps for Developer Agent

[What should developer agent do next?]

Example:
- ✅ All tests pass, ready to continue with M3b (Cloud ML Service)
- ❌ Need to investigate model loading issue
- ⚠️ Tests pass but inference latency higher than expected (document as known limitation)
```

---

## Commit & Push

```bash
# Stage any code fixes
git add [files you changed]
git commit -m "fix(M3a): [description]"

# Stage results file
git add claude/results/TASK-M3a-ml-tests.md
git commit -m "test: Complete M3a ML inference testing"

# Push everything
git push -u origin claude/review-design-docs-01KCgSaGLcqbPwyPNp62vAbD
```

---

## Deliverables Checklist

When done, ensure:
- [ ] ML dependencies installed (torch, onnxruntime, numpy)
- [ ] Test ONNX model created
- [ ] ML inference container built
- [ ] All M3a tests run (7 tests)
- [ ] Any failures debugged and fixed
- [ ] Regression tests verified
- [ ] Results documented in `claude/results/TASK-M3a-ml-tests.md`
- [ ] All fixes committed with clear messages
- [ ] Everything pushed to remote
- [ ] Docker containers cleaned up

---

## Questions or Blockers?

If you encounter something unexpected that you can't fix:
1. Document it thoroughly in the results file
2. Include error messages, logs, and what you tried
3. Commit and push the results file even if incomplete
4. Developer agent will address it when resuming

---

## For Developer Agent (When You Resume)

After testing agent completes:
1. `git pull`
2. Read `claude/results/TASK-M3a-ml-tests.md`
3. **Update M3a-report.md** with delegated testing results (per claude/README.md)
4. If ✅ SUCCESS: Continue with M3b (Cloud ML Service)
5. If ❌ FAILED: Review issues and decide next steps
6. If ⚠️ PARTIAL: Address limitations, then continue

**Note:** This is the first ML test - expect some iteration on Docker networking, model loading, and MQTT patterns.
