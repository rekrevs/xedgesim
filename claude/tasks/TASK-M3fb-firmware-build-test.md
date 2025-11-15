# TASK: M3fb Firmware Build and Renode Testing

**Status:** PENDING
**Created:** 2025-11-15
**Stage:** M3fb - Zephyr Firmware and UART Protocol
**Priority:** HIGH (blocks M3fc)

---

## Context

M3fb has implemented minimal Zephyr firmware for nRF52840 that outputs JSON-formatted sensor data over UART. All Python tests (16/16) pass, but we need to validate that the firmware actually builds with Zephyr SDK and runs in Renode.

**What was implemented:**
- `firmware/sensor-node/src/main.c` - Main firmware (150 LOC)
- `firmware/sensor-node/CMakeLists.txt` - Zephyr build config
- `firmware/sensor-node/prj.conf` - Kernel configuration
- `firmware/sensor-node/boards/nrf52840dk_nrf52840.overlay` - Device tree
- `firmware/sensor-node/README.md` - Build and test instructions
- `tests/stages/M3fb/test_json_protocol.py` - 16 tests (all passing)
- `tests/stages/M3fb/test_standalone_renode.sh` - Renode test script

**Files involved:**
- Production code: `firmware/sensor-node/` directory
- Tests: `tests/stages/M3fb/`

---

## Your Task

Build the Zephyr firmware and test it in Renode to validate:

1. **Zephyr SDK Setup**: Install/verify Zephyr SDK and dependencies
2. **Firmware Build**: Build firmware for nRF52840 DK using west
3. **Build Verification**: Check for warnings, errors, binary size
4. **Standalone Renode Test**: Run firmware in Renode, verify JSON output
5. **Determinism Test**: Run twice with same seed, verify identical output
6. **Document Results**: Record all outputs, issues found, fixes applied

---

## Prerequisites

### Zephyr SDK Installation

**Ubuntu/Debian:**
```bash
# Install dependencies
sudo apt update
sudo apt install --no-install-recommends git cmake ninja-build gperf \
  ccache dfu-util device-tree-compiler wget python3-dev python3-pip \
  python3-setuptools python3-tk python3-wheel xz-utils file make gcc \
  gcc-multilib g++-multilib libsdl2-dev libmagic1

# Install west
pip3 install --user -U west

# Create workspace
west init ~/zephyrproject
cd ~/zephyrproject
west update
west zephyr-export

# Install Python dependencies
pip3 install --user -r ~/zephyrproject/zephyr/scripts/requirements.txt

# Download and install SDK
cd ~
wget https://github.com/zephyrproject-rtos/sdk-ng/releases/download/v0.16.5/zephyr-sdk-0.16.5_linux-x86_64.tar.xz
tar xf zephyr-sdk-0.16.5_linux-x86_64.tar.xz
cd zephyr-sdk-0.16.5
./setup.sh

# Set environment
echo 'export ZEPHYR_BASE=~/zephyrproject/zephyr' >> ~/.bashrc
echo 'source $ZEPHYR_BASE/zephyr-env.sh' >> ~/.bashrc
source ~/.bashrc
```

**macOS:**
```bash
brew install cmake ninja gperf ccache dfu-util qemu dtc python3 wget
pip3 install west
# Follow similar workspace setup as above
```

**Verification:**
```bash
west --version
# Should show west 1.2.0 or later

echo $ZEPHYR_BASE
# Should show path to zephyr
```

---

## Task Steps

### Step 1: Build Firmware

```bash
cd /path/to/xedgesim/firmware/sensor-node

# Ensure Zephyr environment is set
source $ZEPHYR_BASE/zephyr-env.sh

# Build for nRF52840 DK
west build -b nrf52840dk_nrf52840 --pristine
```

**Expected output:**
- Build completes without errors
- ELF file created: `build/zephyr/zephyr.elf`
- Binary size reasonable (< 100KB for minimal firmware)

**Capture:**
- Full build output (save to file)
- Any warnings or errors
- Binary size from build summary

### Step 2: Verify Build Artifacts

```bash
# Check ELF exists
ls -lh build/zephyr/zephyr.elf

# Check size
west build -t rom_report
# Should show code, data, BSS sizes
```

**Verify:**
- ELF file exists and is reasonable size
- No unexpected large sections
- Flash usage < 1MB (nRF52840 limit)

### Step 3: Run Standalone Renode Test

Use the provided test script:

```bash
cd /path/to/xedgesim
./tests/stages/M3fb/test_standalone_renode.sh 5
```

**Expected output:**
```
=== xEdgeSim Sensor Node ===
Firmware version: 1.0.0
...
{"type":"SAMPLE","value":25.3,"time":0}
{"type":"SAMPLE","value":26.1,"time":1000000}
{"type":"SAMPLE","value":24.7,"time":2000000}
...
```

**Verify:**
- Firmware loads without errors
- JSON output appears
- Format matches: `{"type":"SAMPLE","value":<float>,"time":<us>}`
- Values in expected range (20.0 - 30.0)
- Time increments by 1000000 us (1 second)

### Step 4: Determinism Test

Run the firmware twice with the same RNG seed and verify identical output:

```bash
# Create test script
cat > test_determinism.sh <<'EOF'
#!/bin/bash
# Run Renode test twice, capture output, compare

run_test() {
    local output_file=$1
    renode --disable-xwt <<'RESC' | grep '{"type"' > "$output_file"
mach create "sensor"
machine LoadPlatformDescription @platforms/cpus/nrf52840.repl
sysbus LoadELF @build/zephyr/zephyr.elf
showAnalyzer sysbus.uart0
start
emulation RunFor @5.0
quit
RESC
}

# Run twice
run_test output1.txt
run_test output2.txt

# Compare
echo "=== Determinism Test ==="
if diff output1.txt output2.txt; then
    echo "✅ PASS: Outputs are identical"
    exit 0
else
    echo "❌ FAIL: Outputs differ"
    echo "=== Output 1 ==="
    cat output1.txt
    echo "=== Output 2 ==="
    cat output2.txt
    exit 1
fi
EOF

chmod +x test_determinism.sh
./test_determinism.sh
```

**Expected result:**
- Both runs produce identical JSON output
- Same sensor values in same order
- Determinism confirmed

### Step 5: Integration with M3fa RenodeNode

Test that the firmware output can be parsed by RenodeNode from M3fa:

```python
# Create test_m3fa_integration.py
import json
import subprocess

# Run Renode, capture UART output
# (Implementation depends on how to capture Renode output programmatically)

# Parse with RenodeNode logic
def parse_uart_output(uart_text):
    """Simulate RenodeNode._parse_uart_output"""
    events = []
    for line in uart_text.strip().split('\n'):
        line = line.strip()
        if not line or not line.startswith('{'):
            continue
        try:
            data = json.loads(line)
            if 'type' in data and 'value' in data and 'time' in data:
                events.append(data)
        except json.JSONDecodeError:
            print(f"Warning: Malformed JSON: {line}")
    return events

# Test
uart_output = """
{"type":"SAMPLE","value":25.3,"time":0}
{"type":"SAMPLE","value":26.1,"time":1000000}
"""

events = parse_uart_output(uart_output)
print(f"Parsed {len(events)} events")
for event in events:
    print(f"  {event['type']}: {event['value']} at {event['time']}us")
```

**Run:**
```bash
python test_m3fa_integration.py
```

**Expected:**
- Events parsed successfully
- No warnings or errors

---

## Expected Results

### Success Criteria:

- [ ] Zephyr SDK installed and working
- [ ] Firmware builds without errors
- [ ] Binary size reasonable (< 100KB)
- [ ] Firmware runs in Renode
- [ ] JSON output matches specification
- [ ] Determinism test passes (identical outputs)
- [ ] RenodeNode parser compatible
- [ ] All results documented

### If Tests Fail:

#### Build Errors:

**"Cannot find ZEPHYR_BASE":**
```bash
export ZEPHYR_BASE=~/zephyrproject/zephyr
source $ZEPHYR_BASE/zephyr-env.sh
```

**"Board not found":**
```bash
# Check board name matches exactly
west boards | grep nrf52840

# Should show: nrf52840dk_nrf52840
```

**"Device tree errors":**
- Check overlay syntax in `boards/nrf52840dk_nrf52840.overlay`
- Verify compatible strings are valid
- Try removing overlay temporarily to isolate issue

**"Missing dependencies":**
```bash
# Install missing packages from prerequisites
pip3 install -r $ZEPHYR_BASE/scripts/requirements.txt
```

#### Renode Errors:

**"Cannot load ELF":**
- Verify path is absolute or use `@` prefix
- Check ELF file exists: `ls -l build/zephyr/zephyr.elf`
- Try loading manually in Renode REPL

**"No UART output":**
- Verify `showAnalyzer sysbus.uart0` was called
- Check firmware actually started (printk messages)
- Try increasing run duration

**"Garbled output":**
- Check UART baud rate (115200)
- Verify UART configuration in device tree
- Check for buffer overflow in firmware

#### Determinism Failures:

**"Outputs differ":**
- Check RNG seed is actually being set in firmware
- Verify no use of wall-clock time (should use k_usleep)
- Check for uninitialized variables
- Review firmware init_rng() function

---

## Document Results

Create `claude/results/TASK-M3fb-firmware-build-test.md` with:

### Required Sections:

1. **Status**: ✅ SUCCESS / ❌ FAILED / ⚠️ PARTIAL

2. **Environment:**
   - OS and version
   - Zephyr SDK version
   - Renode version
   - Python version

3. **Build Results:**
   ```bash
   west build -b nrf52840dk_nrf52840
   ```
   - Copy full build output (or last 100 lines)
   - Note any warnings
   - Binary size from rom_report

4. **Renode Test Results:**
   ```bash
   ./tests/stages/M3fb/test_standalone_renode.sh 5
   ```
   - Copy UART output (JSON lines)
   - Verify format correctness
   - Note any issues

5. **Determinism Test Results:**
   - Show diff output
   - ✅ PASS or ❌ FAIL
   - If failed, show both outputs for comparison

6. **Issues Found:**
   - List any bugs or issues discovered
   - Include error messages
   - Note any code that needed fixing

7. **Fixes Applied:**
   - Describe any changes made to production code
   - Show diffs for clarity
   - Explain rationale

8. **Commits Made:**
   ```bash
   git log --oneline --author="$(git config user.name)" | head -5
   ```
   - List all commits you made
   - Include commit messages

9. **Next Steps for Developer Agent:**
   - Any recommendations
   - Issues that need developer attention
   - Suggestions for M3fc (coordinator integration)

---

## Deliverables

When complete, you should have:

1. ✅ Zephyr SDK installed and verified
2. ✅ Firmware built successfully
3. ✅ `build/zephyr/zephyr.elf` artifact
4. ✅ Standalone Renode test passing
5. ✅ Determinism test passing
6. ✅ `claude/results/TASK-M3fb-firmware-build-test.md` completed
7. ✅ Code fixes committed (if any)
8. ✅ All committed and pushed to branch

---

## Timeline

**Estimated effort:** 2-3 hours
- 30-60 min: Zephyr SDK installation (if not already installed)
- 15 min: Building firmware
- 15 min: Standalone Renode test
- 15 min: Determinism test
- 15 min: Integration validation
- 30 min: Documenting results

---

## Questions or Issues?

If you encounter blockers:
1. Document the issue in results file
2. Mark status as PARTIAL
3. Explain what worked and what didn't
4. Provide enough detail for developer agent to help

---

## Notes

- **Zephyr SDK is large** (~1GB download, ~3GB installed)
  - If disk space is limited, document this
  - Can test in Docker container if needed

- **Build may take 2-5 minutes** first time
  - Subsequent builds much faster (incremental)
  - west caches dependencies

- **Renode is required** for this task
  - If Renode already installed from M3fa testing, great!
  - Same version should work

- **This validates M3fb is complete**
  - Build test: firmware compiles
  - Execution test: firmware runs
  - Protocol test: JSON output correct
  - Determinism test: RNG seeding works

---

**Status:** PENDING
**Next action:** Testing agent reads this file and begins work
