# TASK: M3fc Final Validation - Firmware Rebuild and Testing

**Status:** PENDING
**Created:** 2025-11-15
**Stage:** M3fc - Final Validation
**Priority:** HIGH (completes M3fc)

---

## Context

M3fc E2E integration is 90% complete. The testing agent successfully:
- ✅ Integrated coordinator + Renode + firmware
- ✅ Fixed 4 critical bugs in RenodeNode
- ✅ Created emulation mode firmware code
- ✅ Validated determinism with current firmware

**What remains:** Rebuild firmware with new emulation mode code and run final validation tests.

**Files modified (ready for rebuild):**
- `firmware/sensor-node/src/main.c` - Emulation mode implementation added
- `firmware/sensor-node/prj.conf` - `CONFIG_XEDGESIM_EMULATION=y` enabled
- `firmware/sensor-node/Kconfig` - Configuration option defined
- `firmware/sensor-node/prj_emulation.conf` - Emulation-specific config

---

## Your Task

Rebuild the firmware and run final validation tests to complete M3fc.

---

## Prerequisites

You already have from previous tasks:
- ✅ Zephyr SDK installed
- ✅ Renode installed
- ✅ Build environment configured

---

## Task Steps

### Step 1: Rebuild Firmware

```bash
cd firmware/sensor-node

# Clean build with new emulation mode code
make pristine
```

**Expected output:**
```
Pristine build (clean + configure + build)...
Building firmware...
...
Build complete:
-rw-r--r--  1 user  staff   XXX KB zephyr.elf
  ✅ Emulation mode: ENABLED
```

**Verify emulation mode is enabled:**
```bash
make info
```

Should show: `Mode: EMULATION`

### Step 2: Run E2E Integration Test

```bash
cd ../..  # Back to project root
./tests/stages/M3fc/test_e2e_renode.sh
```

**Expected output (with emulation firmware):**
```
[RenodeNode:sensor_device] Advancing 1000000us (virtual 1.0s)...
[RenodeNode:sensor_device] Advanced to 1000000us, 1 events  ✅
[RenodeNode:sensor_device] Advancing 1000000us (virtual 1.0s)...
[RenodeNode:sensor_device] Advanced to 2000000us, 1 events  ✅
```

**Key difference from before:** Should get **1 event per time step** (not 1, 0).

### Step 3: Determinism Test

```bash
# Run 1
./tests/stages/M3fc/test_e2e_renode.sh
cat /tmp/xedgesim/sensor_device/uart_data.txt | grep '{"type"' > /tmp/det_run1.txt

# Run 2
./tests/stages/M3fc/test_e2e_renode.sh
cat /tmp/xedgesim/sensor_device/uart_data.txt | grep '{"type"' > /tmp/det_run2.txt

# Compare
diff /tmp/det_run1.txt /tmp/det_run2.txt
```

**Expected:** Empty diff (byte-for-byte identical events)

### Step 4: Extended Duration Test

Edit `examples/scenarios/device_emulation_simple.yaml`:
```yaml
simulation:
  duration_s: 10.0  # Changed from 2.0
```

Run test:
```bash
./tests/stages/M3fc/test_e2e_renode.sh
```

**Expected:**
- 10 time steps
- 10 events (1 per step)
- All values in range [20.0, 30.0]
- Event timestamps: 0, 1s, 2s, ..., 9s

Verify event count:
```bash
cat /tmp/xedgesim/sensor_device/uart_data.txt | grep '{"type"' | wc -l
```

Should show: **10**

### Step 5: Verify Event Values

```bash
cat /tmp/xedgesim/sensor_device/uart_data.txt | grep '{"type"'
```

**Expected output:**
```json
{"type":"SAMPLE","value":28.9,"time":0}
{"type":"SAMPLE","value":22.5,"time":1000000}
{"type":"SAMPLE","value":26.4,"time":2000000}
{"type":"SAMPLE","value":22.2,"time":3000000}
{"type":"SAMPLE","value":27.0,"time":4000000}
{"type":"SAMPLE","value":29.2,"time":5000000}
{"type":"SAMPLE","value":28.8,"time":6000000}
{"type":"SAMPLE","value":20.4,"time":7000000}
{"type":"SAMPLE","value":20.5,"time":8000000}
{"type":"SAMPLE","value":23.9,"time":9000000}
```

(Exact values should match those documented in previous test results)

---

## Expected Results

### Success Criteria:

- [ ] Firmware rebuilds successfully with emulation mode
- [ ] Emulation mode enabled (verified with `make info`)
- [ ] E2E test passes with 1 event per time step (2 events for 2-second scenario)
- [ ] Determinism test passes (identical events across runs)
- [ ] Extended duration test (10 seconds) captures all 10 events
- [ ] Event values match expected deterministic sequence
- [ ] No errors or exceptions
- [ ] No zombie Renode processes

---

## Document Results

Create or update `claude/results/M3fc-FINAL-VALIDATION.md` with:

### Required Sections:

1. **Status**: ✅ SUCCESS / ❌ FAILED

2. **Firmware Rebuild:**
   - Copy output from `make pristine`
   - Show `make info` output
   - Confirm emulation mode enabled

3. **E2E Test Results:**
   - Copy full test output
   - Highlight event counts per time step
   - Verify 1 event per step

4. **Determinism Test:**
   - Show diff output (should be empty)
   - ✅ PASS or ❌ FAIL

5. **Extended Duration Test:**
   - Show all 10 events
   - Verify timestamps are correct
   - Confirm event values match expected sequence

6. **Performance Notes:**
   - Simulation wall time vs virtual time
   - Speedup factor
   - Any observations

7. **Issues Found (if any):**
   - List any problems
   - Include error messages
   - Note any workarounds

8. **Final Status:**
   - M3fc completion status
   - All acceptance criteria met?
   - Ready for developer agent review?

---

## Deliverables

When complete, you should have:

1. ✅ Firmware rebuilt with emulation mode
2. ✅ `make info` confirms emulation mode enabled
3. ✅ E2E test passing (1 event per time step)
4. ✅ Determinism test passing
5. ✅ Extended duration test passing (10 events)
6. ✅ `claude/results/M3fc-FINAL-VALIDATION.md` completed
7. ✅ All committed and pushed to branch

---

## Timeline

**Estimated effort:** 15-20 minutes
- 5 min: Firmware rebuild
- 5 min: E2E test
- 3 min: Determinism test
- 3 min: Extended duration test
- 4 min: Documentation

---

## Notes

- **This is the final validation for M3fc** - once these tests pass, M3fc is complete

- **Emulation mode firmware** outputs exactly 10 samples then exits, ensuring consistent testing

- **All code changes are already committed** - this task is just build and validate

- **Reference previous results** - event values should match those from earlier testing (28.9, 22.5, 26.4, etc.)

---

**Status:** PENDING
**Next action:** Testing agent reads this file and begins final validation
