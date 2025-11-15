# TASK: M3fc End-to-End Integration Testing

**Status:** PENDING
**Created:** 2025-11-15
**Stage:** M3fc - Coordinator Integration with RenodeNode
**Priority:** HIGH (completes M3f device emulation)

---

## Context

M3fc has implemented coordinator integration for in-process RenodeNode instances. The unit tests (11/11 passing) verify the integration logic with mocked nodes. Now we need to validate the full end-to-end flow with actual Renode execution:

**What was implemented:**
- `sim/harness/coordinator.py`: NodeAdapter abstraction, InProcessNodeAdapter
- `sim/config/scenario.py`: Support for renode_inprocess implementation type
- `examples/scenarios/device_emulation_basic.yaml`: Example scenario
- `tests/stages/M3fc/test_coordinator_renode.py`: 11 unit tests (mocked)

**Files involved:**
- Coordinator: `sim/harness/coordinator.py`
- RenodeNode: `sim/device/renode_node.py` (from M3fa)
- Firmware: `firmware/sensor-node/build/zephyr/zephyr.elf` (from M3fb)
- Example scenario: `examples/scenarios/device_emulation_basic.yaml`

---

## Your Task

Run end-to-end integration tests with actual Renode execution to validate that:

1. **Coordinator creates RenodeNode from YAML scenario**
2. **Renode process starts and loads firmware**
3. **Firmware executes and outputs JSON over UART**
4. **RenodeNode parses UART and returns events**
5. **Coordinator receives events and routes them**
6. **Simulation completes successfully with no errors**
7. **Determinism validated (same seed → same results)**

---

## Prerequisites

You should already have from previous M3fa/M3fb tasks:
- ✅ Renode 1.16.0 installed
- ✅ Zephyr SDK installed
- ✅ Firmware built (`firmware/sensor-node/build/zephyr/zephyr.elf`)
- ✅ Platform file available

If firmware needs rebuilding:
```bash
cd firmware/sensor-node
source $ZEPHYR_BASE/zephyr-env.sh
west build -b nrf52840dk_nrf52840
```

---

## Task Steps

### Step 1: Verify Prerequisites

```bash
# Check Renode
renode --version
# Should show: Renode 1.16.0 or later

# Check firmware exists
ls -lh firmware/sensor-node/build/zephyr/zephyr.elf
# Should show ELF file

# Check platform file (may need to locate Renode's platform files)
# Renode platforms usually in: /opt/renode/platforms/ or ~/.config/renode/platforms/
find /opt/renode -name "nrf52840.repl" 2>/dev/null || \
find ~/.config/renode -name "nrf52840.repl" 2>/dev/null || \
find /usr -name "nrf52840.repl" 2>/dev/null
```

### Step 2: Update Example Scenario with Correct Paths

Edit `examples/scenarios/device_emulation_basic.yaml` to use actual paths:

```yaml
nodes:
  - id: sensor_device
    type: renode
    implementation: renode_inprocess
    platform: /opt/renode/platforms/cpus/nrf52840.repl  # UPDATE THIS PATH
    firmware: firmware/sensor-node/build/zephyr/zephyr.elf  # Relative path should work
    monitor_port: 9999
    working_dir: /tmp/xedgesim/sensor_device
    seed: 42
```

**Action:** Find the correct path to `nrf52840.repl` on your system and update the YAML.

### Step 3: Create Simplified Test Scenario

Since the example scenario includes gateway and cloud nodes (which don't exist as processes), create a simplified scenario with only the Renode node:

Create `examples/scenarios/device_emulation_simple.yaml`:

```yaml
# Simplified scenario: Renode node only (no gateway/cloud)
simulation:
  duration_s: 5.0
  seed: 42
  time_quantum_us: 1000000  # 1 second (matches firmware sample interval)

nodes:
  - id: sensor_device
    type: renode
    implementation: renode_inprocess
    platform: /opt/renode/platforms/cpus/nrf52840.repl  # UPDATE PATH
    firmware: firmware/sensor-node/build/zephyr/zephyr.elf
    monitor_port: 9999
    working_dir: /tmp/xedgesim/sensor_device
    seed: 42
```

### Step 4: Create Integration Test Script

Create `tests/stages/M3fc/test_e2e_renode.sh`:

```bash
#!/bin/bash
# M3fc End-to-End Integration Test
# Tests coordinator with actual Renode process and firmware

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
SCENARIO="$PROJECT_ROOT/examples/scenarios/device_emulation_simple.yaml"

echo "=== M3fc E2E Integration Test ==="
echo "Project root: $PROJECT_ROOT"
echo "Scenario: $SCENARIO"
echo

# Check prerequisites
if ! command -v renode &> /dev/null; then
    echo "ERROR: Renode not found"
    exit 1
fi

if [ ! -f "$PROJECT_ROOT/firmware/sensor-node/build/zephyr/zephyr.elf" ]; then
    echo "ERROR: Firmware not built"
    exit 1
fi

echo "Prerequisites OK"
echo

# Run coordinator with scenario
cd "$PROJECT_ROOT"
echo "Running coordinator with Renode scenario..."
python3 sim/harness/coordinator.py "$SCENARIO"

echo
echo "=== Test Complete ==="
echo "Check output above for:"
echo "  - [Coordinator] Registered in-process Renode node"
echo "  - [Coordinator] Starting in-process node"
echo "  - [RenodeNode] Starting Renode"
echo "  - [RenodeNode] Executing: renode ..."
echo "  - [Coordinator] Simulation complete"
echo "  - No errors or exceptions"
```

```bash
chmod +x tests/stages/M3fc/test_e2e_renode.sh
```

### Step 5: Run Integration Test

```bash
cd /path/to/xedgesim
./tests/stages/M3fc/test_e2e_renode.sh
```

**Expected output:**
```
=== M3fc E2E Integration Test ===
...
============================================================
xEdgeSim Coordinator
============================================================
[Coordinator] Loading scenario from: examples/scenarios/device_emulation_simple.yaml
[Coordinator] Using DirectNetworkModel (zero-latency)
[Coordinator] Registered in-process Renode node: sensor_device
  Platform: /opt/renode/platforms/cpus/nrf52840.repl
  Firmware: firmware/sensor-node/build/zephyr/zephyr.elf
[Coordinator] Connecting to all nodes...
[Coordinator] Starting in-process node: sensor_device
[RenodeNode:sensor_device] Starting Renode...
[RenodeNode:sensor_device] Executing: renode --disable-xwt --port 9999 ...
[RenodeNode:sensor_device] Connected to Renode monitor on port 9999
[Coordinator] sensor_device initialized and ready (in-process)
[Coordinator] Starting simulation for 5.0s (virtual time)
[Coordinator] Time quantum: 1000000us
[Coordinator] Simulation complete, shutting down nodes...
[Coordinator] Shutting down in-process node: sensor_device
[RenodeNode:sensor_device] Stopping Renode...
[Coordinator] Simulation finished:
  Virtual time: 5.0s
  Wall time: X.XXs
  Steps: 5
  Speedup: X.Xx
```

**Verify:**
- ✅ No errors or exceptions
- ✅ Renode process starts and stops cleanly
- ✅ Firmware loads successfully
- ✅ Simulation completes all 5 steps
- ✅ No zombie processes (`ps aux | grep renode` after test)

### Step 6: Verify Event Generation

Modify the coordinator or add debug logging to verify events are actually generated:

Option 1: Add print statement in `sim/harness/coordinator.py` run() method:

```python
# In Phase 2 of run() loop, after collecting events:
all_events = []
for node_id, conn in self.nodes.items():
    events = conn.wait_done()
    if events:  # Add this check
        print(f"[DEBUG] Received {len(events)} events from {node_id}")
        for e in events:
            print(f"  Event: {e.type} at {e.time_us}us, value={e.payload}")
    all_events.extend(events)
```

Rerun test and verify events appear in output.

### Step 7: Determinism Test

Run the scenario twice with the same seed and verify identical event sequences:

```bash
# Run 1
python3 sim/harness/coordinator.py examples/scenarios/device_emulation_simple.yaml 2>&1 | \
    grep "Event:" > /tmp/run1.txt

# Run 2
python3 sim/harness/coordinator.py examples/scenarios/device_emulation_simple.yaml 2>&1 | \
    grep "Event:" > /tmp/run2.txt

# Compare
if diff /tmp/run1.txt /tmp/run2.txt; then
    echo "✅ Determinism test PASSED: Events identical"
else
    echo "❌ Determinism test FAILED: Events differ"
    exit 1
fi
```

### Step 8: Test with Different Seeds

Modify scenario to use different seed, verify different event sequence:

```yaml
simulation:
  seed: 99  # Changed from 42
```

Run again and verify events are different from seed=42 run.

---

## Expected Results

### Success Criteria:

- [ ] Coordinator loads scenario without errors
- [ ] RenodeNode created from YAML configuration
- [ ] Renode process starts successfully
- [ ] Firmware loads and executes
- [ ] UART output parsed into events
- [ ] Events flow through coordinator
- [ ] Simulation completes all time steps
- [ ] Renode process terminates cleanly
- [ ] No zombie processes remain
- [ ] Determinism test passes (same seed → same events)
- [ ] Different seeds produce different events
- [ ] All results documented

### If Tests Fail:

#### "Platform file not found"

```bash
# Find platform file
find /opt -name "nrf52840.repl" 2>/dev/null
find /usr -name "nrf52840.repl" 2>/dev/null
find ~/.config -name "nrf52840.repl" 2>/dev/null

# Update YAML with correct path
```

#### "Firmware file not found"

```bash
# Rebuild firmware
cd firmware/sensor-node
west build -b nrf52840dk_nrf52840 --pristine
```

#### "Renode process hangs"

- Check Renode is installed correctly: `renode --version`
- Check Renode can start manually: `renode --disable-xwt`
- Check monitor port not in use: `lsof -i :9999`
- Try different monitor port in YAML

#### "No events generated"

- Check firmware is actually outputting JSON (test with standalone Renode from M3fb)
- Add debug logging to `_parse_uart_output` in RenodeNode
- Verify UART analyzer is working in Renode
- Check time quantum matches firmware sample interval

#### "Events but incorrect format"

- Verify firmware hasn't changed from M3fb
- Check JSON parsing in RenodeNode
- Validate event conversion in InProcessNodeAdapter.wait_done()

---

## Document Results

Create `claude/results/TASK-M3fc-e2e-integration.md` with:

### Required Sections:

1. **Status**: ✅ SUCCESS / ❌ FAILED / ⚠️ PARTIAL

2. **Environment:**
   - OS and version
   - Renode version
   - Zephyr firmware build date
   - Python version

3. **Integration Test Results:**
   ```bash
   ./tests/stages/M3fc/test_e2e_renode.sh
   ```
   - Copy full output
   - Note any warnings or errors
   - Verify all expected log messages appear

4. **Event Generation Results:**
   - Show events received by coordinator
   - Verify event format and content
   - Count of events per time step

5. **Determinism Test Results:**
   - Show diff output (should be empty)
   - ✅ PASS or ❌ FAIL
   - If failed, show both outputs for comparison

6. **Seed Variation Test:**
   - Show events with seed=42
   - Show events with seed=99
   - Verify they differ

7. **Issues Found:**
   - List any bugs or issues discovered
   - Include error messages
   - Note any code that needed fixing

8. **Fixes Applied:**
   - Describe any changes made to production code
   - Show diffs for clarity
   - Explain rationale

9. **Performance Notes:**
   - Simulation wall time vs virtual time
   - Speedup factor
   - Any performance concerns

10. **Commits Made:**
    ```bash
    git log --oneline --author="$(git config user.name)" | head -5
    ```
    - List all commits you made
    - Include commit messages

11. **Next Steps for Developer Agent:**
    - Any recommendations
    - Issues that need developer attention
    - Suggestions for M3fd or future work

---

## Deliverables

When complete, you should have:

1. ✅ Platform file path identified and scenario updated
2. ✅ Simplified test scenario created
3. ✅ Integration test script created and executable
4. ✅ E2E test passing (coordinator + Renode + firmware)
5. ✅ Events verified (correct format and content)
6. ✅ Determinism validated
7. ✅ Seed variation verified
8. ✅ `claude/results/TASK-M3fc-e2e-integration.md` completed
9. ✅ Code fixes committed (if any)
10. ✅ All committed and pushed to branch

---

## Timeline

**Estimated effort:** 1-2 hours
- 15 min: Prerequisites check and platform file location
- 15 min: Scenario setup and test script creation
- 15 min: E2E test execution
- 15 min: Event verification
- 15 min: Determinism and seed variation testing
- 15 min: Documenting results

---

## Questions or Issues?

If you encounter blockers:
1. Document the issue in results file
2. Mark status as PARTIAL
3. Explain what worked and what didn't
4. Provide enough detail for developer agent to help

---

## Notes

- **This is the final integration test for M3f** - it validates that M3fa (RenodeNode), M3fb (firmware), and M3fc (coordinator) all work together

- **Platform file location varies** by Renode installation method:
  - Homebrew (macOS): `/opt/homebrew/Cellar/renode/*/share/renode/platforms/`
  - APT (Ubuntu): `/opt/renode/platforms/`
  - Manual install: Check Renode installation directory

- **Working directory** `/tmp/xedgesim/sensor_device` will contain generated .resc script - useful for debugging

- **Time quantum = sample interval** ensures coordinator advances match firmware output frequency

---

**Status:** PENDING
**Next action:** Testing agent reads this file and begins work
