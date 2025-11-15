# TASK: M2c MQTT Broker Integration Testing

**Status:** PENDING
**Created:** 2025-11-15
**Priority:** HIGH (blocks M2d implementation)
**Estimated Time:** 20-30 minutes

---

## Context

I (developer agent) have implemented M2c (MQTT broker integration) but cannot test it because Docker is not available in my environment. I need you (testing agent) to run the full MQTT integration test suite and verify everything works.

## What I've Implemented

- **Mosquitto Broker Container**: Dockerfile + mosquitto.conf for MQTT broker
- **SensorNode MQTT Support**: Dual-mode nodes that can publish to MQTT broker
- **GatewayNode MQTT Support**: Dual-mode nodes that can subscribe to MQTT topics
- **Integration Tests**: 6 tests covering broker startup, pub/sub, end-to-end flow

**Code locations:**
- `containers/mqtt-broker/` - Mosquitto broker container
- `sim/device/sensor_node.py` - SensorNode with MQTT methods
- `sim/edge/gateway_node.py` - GatewayNode with MQTT methods
- `tests/stages/M2c/test_mqtt_integration.py` - Integration tests
- `requirements-dev.txt` - Added paho-mqtt dependency

---

## Your Task

Run the M2c MQTT integration test suite and fix any issues you find.

### Step 1: Install Dependencies

```bash
pip install -r requirements-dev.txt
```

This will install `paho-mqtt>=1.6.1` (MQTT client library).

### Step 2: Build Mosquitto Broker Image

```bash
cd containers/mqtt-broker
docker build -t xedgesim/mosquitto:latest .
cd ../..
```

Expected: Image builds successfully (~10MB).

### Step 3: Run M2c Integration Tests

```bash
pytest tests/stages/M2c/test_mqtt_integration.py -v
```

This will run 6 tests:
1. `test_mosquitto_broker_starts` - Broker container starts and logs version
2. `test_mqtt_client_can_connect` - Raw MQTT client connection
3. `test_sensor_node_mqtt_publish` - Sensor publishes without errors
4. `test_gateway_node_mqtt_subscribe` - Gateway subscribes successfully
5. `test_end_to_end_mqtt_flow` - Complete sensor → broker → gateway flow
6. `test_multiple_sensors_to_gateway` - Fan-in pattern (2 sensors, 1 gateway)

### Step 4: Run Regression Tests

Verify M0-M2b still work:

```bash
# M0 tests (if they exist)
pytest tests/stages/M0/ -v || echo "No M0 tests found"

# M1d, M1e tests
pytest tests/stages/M1d/test_latency_network_model.py -v
pytest tests/stages/M1e/test_network_metrics.py -v

# M2a basic tests (no Docker)
python tests/stages/M2a/test_docker_node_basic.py

# M2b socket tests (no Docker)
python tests/stages/M2b/test_socket_interface.py
```

Expected: All regression tests still pass.

### Step 5: Expected Results

**Success Criteria:**
- ✅ Mosquitto broker image builds successfully
- ✅ All 6 M2c integration tests **PASS**
- ✅ Broker starts and accepts connections
- ✅ Sensor can publish to broker
- ✅ Gateway can subscribe and receive messages
- ✅ End-to-end MQTT flow works
- ✅ All regression tests pass (M1d, M1e, M2a basic, M2b socket)
- ✅ No orphaned containers after tests (`docker ps | grep xedgesim` returns nothing)

### Step 6: If Tests Fail

**Debug locally before reporting back:**

1. **If broker image fails to build:**
   ```bash
   # Check Docker daemon
   docker info

   # Try building with verbose output
   docker build --no-cache -t xedgesim/mosquitto:latest containers/mqtt-broker/
   ```

2. **If broker doesn't start:**
   ```bash
   # Check broker logs
   docker logs <container_id>

   # Check if port 1883 is in use
   lsof -i :1883
   ```

3. **If connection fails:**
   ```bash
   # Test broker manually
   docker run -d --name test-mqtt -p 1883:1883 xedgesim/mosquitto:latest
   sleep 2

   # Try connecting with mosquitto_pub/sub (if installed)
   mosquitto_pub -h localhost -t test -m "hello"

   # Or use Python
   python3 -c "
   import paho.mqtt.client as mqtt
   c = mqtt.Client()
   c.connect('localhost', 1883)
   print('Connected!')
   c.disconnect()
   "

   docker stop test-mqtt && docker rm test-mqtt
   ```

4. **If specific tests fail:**
   ```bash
   # Run failing test in verbose mode
   pytest tests/stages/M2c/test_mqtt_integration.py::test_name -vvs
   ```

5. **Common issues:**
   - Port 1883 already in use → Stop existing MQTT broker
   - paho-mqtt not installed → `pip install paho-mqtt`
   - Docker socket not found → Check Colima/Docker Desktop running
   - Test timeout → Increase sleep times in tests

6. **Fix the issue in code:**
   - Edit the relevant file
   - Re-run tests until they pass
   - Document what you changed

### Step 7: Document Results

Create `claude/results/TASK-M2C-mqtt-tests.md` with:

```markdown
# Results: M2c MQTT Integration Testing

**Status:** ✅ SUCCESS / ❌ FAILED / ⚠️ PARTIAL
**Completed:** 2025-11-15T[time]
**Duration:** [X minutes]

## Test Results

### Full Test Output
```
[Paste complete output of pytest tests/stages/M2c/test_mqtt_integration.py -v here]
```

### Summary
- Mosquitto broker build: ✅/❌
- M2c integration tests: [X/6 passed]
  - test_mosquitto_broker_starts: ✅/❌
  - test_mqtt_client_can_connect: ✅/❌
  - test_sensor_node_mqtt_publish: ✅/❌
  - test_gateway_node_mqtt_subscribe: ✅/❌
  - test_end_to_end_mqtt_flow: ✅/❌
  - test_multiple_sensors_to_gateway: ✅/❌
- M1d regression: [X/8 passed]
- M1e regression: [X/8 passed]
- M2a basic regression: [X/3 passed]
- M2b socket regression: [X/5 passed]

## Issues Found

[List any problems discovered during testing]

Example:
- Mosquitto image build failed due to missing mosquitto.conf
- Connection timeout: broker took >5s to start
- Gateway didn't receive messages (topic mismatch)
- Port 1883 conflict with existing broker

## Fixes Applied

[Describe code changes made, with file paths and line numbers]

Example:
- Fixed mosquitto.conf syntax error at line 5
- Increased broker startup wait from 2s to 5s in test fixtures
- Fixed topic subscription from 'sensors/#' to 'sensor/#'
- Added container cleanup in test teardown

## Commits Made

```bash
git log --oneline -n 3
```

Example:
- abc1234 fix(M2c): Fix mosquitto.conf syntax
- def5678 test(M2c): Increase broker startup timeout
- ghi9012 test: Complete M2c MQTT integration testing

## Testing Environment

- **OS:** [macOS/Linux version]
- **Architecture:** [arm64/x86_64]
- **Docker Runtime:** [Colima/Docker Desktop version]
- **Python:** [version]
- **paho-mqtt:** [version]

## Next Steps for Developer Agent

[What should developer agent do next?]

Example:
- ✅ All tests pass, ready to continue with M2d
- ❌ Need to investigate topic subscription issue (see details above)
- ⚠️ Tests pass but found edge case with multiple concurrent subscribers
```

### Step 8: Commit & Push

```bash
# Stage any code fixes you made
git add [files you changed]
git commit -m "fix(M2c): [description of what you fixed]"

# Stage the results file
git add claude/results/TASK-M2C-mqtt-tests.md
git commit -m "test: Complete M2c MQTT integration testing"

# Push everything
git push -u origin claude/review-design-docs-01KCgSaGLcqbPwyPNp62vAbD
```

---

## Deliverables Checklist

When done, ensure:
- [ ] paho-mqtt installed
- [ ] Mosquitto broker image built
- [ ] All M2c tests have been run
- [ ] Any failures have been debugged and fixed
- [ ] Regression tests verified
- [ ] Results documented in `claude/results/TASK-M2C-mqtt-tests.md`
- [ ] All fixes committed with clear messages
- [ ] Everything pushed to remote
- [ ] Docker containers cleaned up (`docker ps` shows no xedgesim containers)

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
2. Read `claude/results/TASK-M2C-mqtt-tests.md`
3. **Update M2c-report.md** with delegated testing results (per claude/README.md)
4. If ✅ SUCCESS: Continue with M2d implementation
5. If ❌ FAILED: Review issues and decide next steps
6. If ⚠️ PARTIAL: Address edge cases if needed, then continue
