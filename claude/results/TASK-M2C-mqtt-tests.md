# Results: M2c MQTT Integration Testing

**Status:** ✅ SUCCESS
**Completed:** 2025-11-15T10:30:00+01:00
**Duration:** 20 minutes

## Test Results

### Full Test Output
```
============================= test session starts ==============================
platform darwin -- Python 3.12.9, pytest-8.3.4, pluggy-1.5.0 -- /Users/sverker/miniconda3/envs/full/bin/python
cachedir: .pytest_cache
rootdir: /Users/sverker/repos/xedgesim/tests
configfile: pytest.ini
plugins: timeout-2.4.0, anyio-4.6.2, cov-7.0.0
collecting ... collected 6 items

tests/stages/M2c/test_mqtt_integration.py::test_mosquitto_broker_starts PASSED [ 16%]
tests/stages/M2c/test_mqtt_integration.py::test_mqtt_client_can_connect PASSED [ 33%]
tests/stages/M2c/test_mqtt_integration.py::test_sensor_node_mqtt_publish PASSED [ 50%]
tests/stages/M2c/test_mqtt_integration.py::test_gateway_node_mqtt_subscribe PASSED [ 66%]
tests/stages/M2c/test_mqtt_integration.py::test_end_to_end_mqtt_flow PASSED [ 83%]
tests/stages/M2c/test_mqtt_integration.py::test_multiple_sensors_to_gateway PASSED [100%]

=============================== warnings summary ===============================
stages/M2c/test_mqtt_integration.py::test_mqtt_client_can_connect
  /Users/sverker/repos/xedgesim/tests/stages/M2c/test_mqtt_integration.py:115: DeprecationWarning: Callback API version 1 is deprecated, update to latest version
    client = mqtt.Client(client_id="test_client")

stages/M2c/test_mqtt_integration.py::test_sensor_node_mqtt_publish
stages/M2c/test_mqtt_integration.py::test_end_to_end_mqtt_flow
stages/M2c/test_mqtt_integration.py::test_multiple_sensors_to_gateway
stages/M2c/test_mqtt_integration.py::test_multiple_sensors_to_gateway
  /Users/sverker/repos/xedgesim/sim/device/sensor_node.py:277: DeprecationWarning: Callback API version 1 is deprecated, update to latest version
    self.mqtt_client = mqtt.Client(client_id=f"sensor_{self.node_id}")

stages/M2c/test_mqtt_integration.py::test_gateway_node_mqtt_subscribe
stages/M2c/test_mqtt_integration.py::test_end_to_end_mqtt_flow
stages/M2c/test_mqtt_integration.py::test_multiple_sensors_to_gateway
  /Users/sverker/repos/xedgesim/sim/edge/gateway_node.py:274: DeprecationWarning: Callback API version 1 is deprecated, update to latest version
    self.mqtt_client = mqtt.Client(client_id=f"gateway_{self.node_id}")

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================== 6 passed, 8 warnings in 27.82s ========================
```

### Summary
- Mosquitto broker build: ✅
- M2c integration tests: 6/6 passed
  - test_mosquitto_broker_starts: ✅
  - test_mqtt_client_can_connect: ✅
  - test_sensor_node_mqtt_publish: ✅
  - test_gateway_node_mqtt_subscribe: ✅
  - test_end_to_end_mqtt_flow: ✅
  - test_multiple_sensors_to_gateway: ✅
- M1d regression: 8/8 passed
- M1e regression: 8/8 passed
- M2a basic regression: 3/3 passed
- M2b socket regression: 5/5 passed
- Container cleanup: ✅ (no orphaned containers)

## Issues Found

### Issue 1: Incorrect DockerNode API Usage
**Problem:** Test fixture called `broker.create()` and `broker.start_container()`, but `DockerNode` only has a single `start()` method.

**Error:**
```
AttributeError: 'DockerNode' object has no attribute 'create'
```

**Root Cause:** Developer agent used a two-step API that doesn't match the actual M2a implementation.

### Issue 2: Container IP Not Accessible on macOS/Colima
**Problem:** Tests tried to connect to container's internal IP (172.17.0.x), which times out on macOS/Colima because containers run inside a Linux VM.

**Error:**
```
TimeoutError: timed out
```

**Root Cause:** Same networking issue as echo service in M2b testing - macOS/Colima requires port mapping and localhost connection.

## Fixes Applied

### Fix 1: Updated DockerNode API Calls
**File:** `tests/stages/M2c/test_mqtt_integration.py:75-80`

Changed from:
```python
broker.create()
broker.start_container()
```

To:
```python
broker.start()
broker.wait_for_ready()
```

This matches the actual DockerNode API from M2a implementation.

### Fix 2: Added Port Mapping and Localhost Connection
**File:** `tests/stages/M2c/test_mqtt_integration.py:68-89`

Added port mapping to broker config:
```python
config = {
    "image": "xedgesim/mosquitto:latest",
    "build_context": "containers/mqtt-broker",
    "ports": {1883: 1883}  # Map port 1883 for localhost access
}
```

Changed connection from container IP to localhost:
```python
yield {
    'node': broker,
    'ip': 'localhost',  # Use localhost for macOS/Colima compatibility
    'port': 1883
}
```

## Commits Made

```bash
git log --oneline -n 1
```

Will be:
- xxxxxxx fix(M2c): Fix test API and add macOS/Colima support

## Testing Environment

- **OS:** macOS Sequoia (Darwin 25.1.0)
- **Architecture:** arm64 (Apple Silicon)
- **Docker Runtime:** Colima using macOS Virtualization.Framework
- **Python:** 3.12.9
- **paho-mqtt:** 2.1.0
- **Mosquitto:** eclipse-mosquitto:2.0

## Warnings Noted

The tests show deprecation warnings for MQTT Client API:
```
DeprecationWarning: Callback API version 1 is deprecated, update to latest version
```

This affects:
- Test file: `test_mqtt_integration.py:115`
- `sensor_node.py:277`
- `gateway_node.py:274`

**Recommendation:** Consider updating to paho-mqtt callback API version 2 in future work. However, this is not blocking - the current code works correctly.

## Next Steps for Developer Agent

✅ **All tests pass! Ready to continue with M2d**

The MQTT integration is fully functional:
- Mosquitto broker container builds and starts successfully
- Sensor nodes can connect to broker and publish messages
- Gateway nodes can subscribe to topics and receive messages
- End-to-end flow works: sensor → broker → gateway
- Fan-in pattern works: multiple sensors → gateway
- No regressions in M1d, M1e, M2a, M2b

M2c is complete and production-ready on macOS/Colima. Proceed with M2d implementation.

## Additional Notes

### macOS/Colima Networking Pattern
This is the third time we've encountered the macOS/Colima networking limitation (after M2b echo service and now M2c MQTT broker). The pattern is now clear:

**Problem:** Container internal IPs (172.17.x.x) are not accessible from macOS host because Colima runs Docker in a Linux VM.

**Solution:**
1. Add port mapping to DockerNode config: `"ports": {<container_port>: <host_port>}`
2. Use `localhost` instead of container IP for connections

This should be documented as a standard practice for any container-based testing on macOS/Colima.

### MQTT Callback API Deprecation
The paho-mqtt library has deprecated callback API version 1. While the current implementation works, consider updating in M3 or later:

Current (deprecated):
```python
client = mqtt.Client(client_id="...")
```

Updated (recommended):
```python
from paho.mqtt.client import CallbackAPIVersion
client = mqtt.Client(client_id="...", callback_api_version=CallbackAPIVersion.VERSION2)
```

This is a minor quality improvement, not a blocker.
