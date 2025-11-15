# M3f: Renode Integration Plan

**Milestone:** M3f - Device Tier Emulation with Renode
**Duration:** 3-4 weeks
**Effort:** ~800-1000 LOC
**Status:** PLANNED

---

## 1. Objective

Integrate Renode (instruction-level ARM/RISC-V emulator) to enable:
- Real firmware execution (Zephyr/FreeRTOS)
- Cycle-accurate timing for device ML inference
- True deployability validation (same binary runs in sim and on hardware)

**Why this matters:** Completes Tier 1 device emulation, validates the "deployable artifacts" claim, enables realistic device ML inference measurements.

---

## 2. Architecture Overview

### 2.1 Current State (Python Sensor Model)

```
┌─────────────────────────────────────────┐
│ Coordinator (coordinator.py)            │
│  - Conservative synchronous lockstep    │
└─────────────┬───────────────────────────┘
              │ socket
    ┌─────────▼────────┐
    │ SensorNode.py    │ ← Python model (abstract)
    │  - Simulated data│
    │  - No real firmware
    └──────────────────┘
```

### 2.2 Target State (Renode Integration)

```
┌─────────────────────────────────────────┐
│ Coordinator (coordinator.py)            │
│  - Conservative synchronous lockstep    │
└─────────────┬───────────────────────────┘
              │ socket (Renode monitor protocol)
    ┌─────────▼────────┐
    │ Renode Process   │ ← C# emulator
    │  ┌────────────┐  │
    │  │ ARM Cortex │  │   Real firmware:
    │  │ -M4 MCU    │  │   - Zephyr RTOS
    │  │            │  │   - Sensor drivers
    │  │ firmware.  │  │   - TFLite inference
    │  │ elf        │  │   - UART output
    │  └────────────┘  │
    └──────────────────┘
```

---

## 3. Technical Components

### 3.1 Renode Adapter (`sim/device/renode_node.py`)

**Responsibilities:**
- Start Renode process with monitor protocol
- Send time advancement commands
- Collect UART output and events
- Track virtual time synchronization

**Implementation:**

```python
# sim/device/renode_node.py
import socket
import subprocess
import time
from typing import List, Optional
from sim.network.network_model import Event

class RenodeNode:
    """Adapter for Renode emulated device."""

    def __init__(self, node_id: str, config: dict):
        self.node_id = node_id
        self.config = config
        self.current_time_us = 0

        # Renode configuration
        self.platform_file = config['platform']  # .repl file
        self.firmware_path = config['firmware']  # .elf file
        self.monitor_port = config.get('monitor_port', 1234)

        # Process and socket
        self.renode_process: Optional[subprocess.Popen] = None
        self.monitor_socket: Optional[socket.socket] = None

    def start(self):
        """Start Renode emulator process."""
        # Create Renode script
        script_path = self._create_renode_script()

        # Start Renode in headless mode
        cmd = [
            'renode',
            '--disable-xwt',  # No GUI
            '--port', str(self.monitor_port),
            script_path
        ]

        self.renode_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # Wait for Renode to start
        time.sleep(2)

        # Connect to monitor port
        self.monitor_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.monitor_socket.connect(('localhost', self.monitor_port))

        # Initialize emulation
        self._send_command('start')

    def _create_renode_script(self) -> str:
        """Generate Renode .resc script."""
        script_content = f"""
# xEdgeSim Renode Script - {self.node_id}

# Load platform description
mach create "{self.node_id}"
machine LoadPlatformDescription @{self.platform_file}

# Load firmware
sysbus LoadELF @{self.firmware_path}

# Configure UART analyzer (for output capture)
showAnalyzer sysbus.uart0

# Enable external time source (for coordinator control)
emulation SetGlobalQuantum "0.00001"  # 10us quantum
emulation SetAdvanceImmediately false

# Ready for time stepping
"""
        script_path = f'/tmp/xedgesim_{self.node_id}.resc'
        with open(script_path, 'w') as f:
            f.write(script_content)
        return script_path

    def _send_command(self, cmd: str) -> str:
        """Send command to Renode monitor."""
        self.monitor_socket.sendall(f"{cmd}\n".encode())

        # Read response (until prompt)
        response = b''
        while b'(monitor)' not in response:
            chunk = self.monitor_socket.recv(4096)
            if not chunk:
                break
            response += chunk

        return response.decode('utf-8')

    def advance(self, target_time_us: int) -> List[Event]:
        """Advance emulation to target time."""
        delta_us = target_time_us - self.current_time_us

        if delta_us <= 0:
            return []

        # Convert to Renode time unit (virtual seconds)
        virtual_seconds = delta_us / 1_000_000.0

        # Execute for specified virtual time
        response = self._send_command(
            f'emulation RunFor @{virtual_seconds}'
        )

        # Collect events from UART output
        events = self._parse_uart_output(response)

        self.current_time_us = target_time_us
        return events

    def _parse_uart_output(self, uart_text: str) -> List[Event]:
        """Parse UART output into simulation events."""
        events = []

        # Look for structured output (JSON over UART)
        # Example firmware output: {"type":"SAMPLE","temp":25.3,"time":1000000}
        import re
        import json

        for line in uart_text.split('\n'):
            # Try to parse as JSON
            json_match = re.search(r'\{.*\}', line)
            if json_match:
                try:
                    data = json.loads(json_match.group())
                    event = Event(
                        type=data.get('type', 'UART'),
                        time_us=self.current_time_us,
                        src=self.node_id,
                        payload=data,
                        size_bytes=len(line)
                    )
                    events.append(event)
                except json.JSONDecodeError:
                    pass

        return events

    def stop(self):
        """Stop Renode emulator."""
        if self.monitor_socket:
            self._send_command('quit')
            self.monitor_socket.close()

        if self.renode_process:
            self.renode_process.terminate()
            self.renode_process.wait(timeout=5)

    def __del__(self):
        self.stop()
```

### 3.2 Firmware Implementation (Zephyr)

**Directory:** `firmware/sensor-node/`

**Files:**
- `CMakeLists.txt` - Zephyr build configuration
- `prj.conf` - Zephyr project configuration
- `src/main.c` - Main firmware code
- `boards/` - Board-specific configuration

**Example Firmware (`src/main.c`):**

```c
#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/drivers/uart.h>
#include <zephyr/random/random.h>
#include <stdio.h>

// Configuration
#define SAMPLE_INTERVAL_MS 1000
#define UART_DEVICE_NODE DT_CHOSEN(zephyr_console)

static const struct device *uart_dev = DEVICE_DT_GET(UART_DEVICE_NODE);

// Simulated sensor reading
float read_temperature(void) {
    // Use deterministic RNG for simulation
    uint32_t rand = sys_rand32_get();
    float temp = 20.0f + (rand % 100) / 10.0f;  // 20-30°C
    return temp;
}

// Send structured JSON over UART
void send_sample(float temperature, uint64_t time_us) {
    char buffer[128];
    int len = snprintf(buffer, sizeof(buffer),
        "{\"type\":\"SAMPLE\",\"temp\":%.2f,\"time\":%llu}\n",
        temperature, time_us);

    for (int i = 0; i < len; i++) {
        uart_poll_out(uart_dev, buffer[i]);
    }
}

void main(void) {
    if (!device_is_ready(uart_dev)) {
        return;
    }

    printk("xEdgeSim Sensor Node - Starting\n");

    uint64_t time_us = 0;

    while (1) {
        // Read sensor
        float temp = read_temperature();

        // Send to coordinator via UART
        send_sample(temp, time_us);

        // Sleep (this will be controlled by virtual time)
        k_msleep(SAMPLE_INTERVAL_MS);

        time_us += SAMPLE_INTERVAL_MS * 1000;
    }
}
```

**Build Configuration (`CMakeLists.txt`):**

```cmake
cmake_minimum_required(VERSION 3.20.0)

find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(xedgesim_sensor_node)

target_sources(app PRIVATE src/main.c)
```

**Project Configuration (`prj.conf`):**

```ini
# Console/UART
CONFIG_SERIAL=y
CONFIG_UART_CONSOLE=y
CONFIG_PRINTK=y

# Random number generator (deterministic for simulation)
CONFIG_TEST_RANDOM_GENERATOR=y

# Logging
CONFIG_LOG=y
CONFIG_LOG_DEFAULT_LEVEL=3
```

### 3.3 Coordinator Integration

**File:** `sim/harness/coordinator.py`

**Changes:**

```python
# Add Renode node support
from sim.device.renode_node import RenodeNode

class Coordinator:
    def _create_node(self, node_config: dict):
        """Factory method for node creation."""
        node_type = node_config['type']

        if node_type == 'renode':
            return RenodeNode(node_config['id'], node_config)
        elif node_type == 'sensor':
            return SensorNode(node_config['id'], node_config)
        # ... other types
```

### 3.4 YAML Schema Extension

**File:** `scenarios/vib-monitoring/renode-scenario.yaml`

```yaml
simulation:
  duration_us: 60000000  # 60 seconds
  time_step_us: 10000    # 10ms steps (coarser for Renode)

nodes:
  - type: renode
    id: sensor_1
    platform: firmware/sensor-node/boards/nrf52840dk_nrf52840.repl
    firmware: firmware/sensor-node/build/zephyr/zephyr.elf
    monitor_port: 1234

  - type: renode
    id: sensor_2
    platform: firmware/sensor-node/boards/nrf52840dk_nrf52840.repl
    firmware: firmware/sensor-node/build/zephyr/zephyr.elf
    monitor_port: 1235

  - type: gateway
    id: edge_gateway
    config:
      processing_rate_mbps: 100

network:
  model: latency
  base_latency_ms: 5
  packet_loss_rate: 0.01
```

---

## 4. Implementation Phases

### Phase 1: Basic Renode Control (Week 1)

**Objectives:**
- [ ] Install and test Renode locally
- [ ] Implement `RenodeNode` adapter with monitor protocol
- [ ] Test time advancement commands
- [ ] Validate UART output capture

**Deliverables:**
- `sim/device/renode_node.py` (basic version)
- Manual test: Start Renode, advance time, read UART

**Testing:**
```bash
# Manual test
renode --disable-xwt --port 1234 test.resc
telnet localhost 1234
> emulation RunFor @0.001
```

### Phase 2: Zephyr Firmware (Week 2)

**Objectives:**
- [ ] Set up Zephyr development environment
- [ ] Build basic sensor firmware for nRF52840
- [ ] Implement JSON-over-UART protocol
- [ ] Test firmware in standalone Renode

**Deliverables:**
- `firmware/sensor-node/` directory structure
- Working `.elf` file
- Standalone test script

**Testing:**
```bash
cd firmware/sensor-node
west build -b nrf52840dk_nrf52840
renode test.resc
```

### Phase 3: Integration (Week 3)

**Objectives:**
- [ ] Integrate `RenodeNode` into coordinator
- [ ] Test determinism (same seed → same output)
- [ ] Measure performance overhead
- [ ] Compare Python model vs Renode timing

**Deliverables:**
- Updated `coordinator.py`
- Integration test in `tests/stages/M3f/`
- Performance benchmarks

**Testing:**
```python
# tests/stages/M3f/test_renode_integration.py
def test_renode_basic_execution():
    coordinator = Coordinator('scenarios/renode-basic.yaml')
    coordinator.run()

    # Verify determinism
    run1_events = coordinator.get_events()

    coordinator = Coordinator('scenarios/renode-basic.yaml')
    coordinator.run()
    run2_events = coordinator.get_events()

    assert run1_events == run2_events
```

### Phase 4: Device ML Inference (Week 4)

**Objectives:**
- [ ] Add TensorFlow Lite Micro to firmware
- [ ] Implement on-device anomaly detection
- [ ] Measure cycle counts for inference
- [ ] Compare device/edge/cloud latency

**Deliverables:**
- Firmware with TFLite inference
- Cycle-count measurements
- Updated ML placement comparison

**Firmware changes:**
```c
#include <tensorflow/lite/micro/all_ops_resolver.h>
#include <tensorflow/lite/micro/micro_interpreter.h>

// Model data (included from .cc file)
#include "anomaly_model_data.h"

void run_inference(float* input_data, int input_size) {
    // TFLite Micro setup
    static tflite::MicroInterpreter* interpreter;

    // Run inference
    uint32_t start_cycles = k_cycle_get_32();
    interpreter->Invoke();
    uint32_t end_cycles = k_cycle_get_32();

    // Report timing
    printk("{\"type\":\"INFERENCE\",\"cycles\":%u}\n",
           end_cycles - start_cycles);
}
```

---

## 5. Testing Strategy

### 5.1 Unit Tests

```python
# tests/stages/M3f/test_renode_node.py

def test_renode_node_starts():
    """Test that Renode process starts successfully."""
    node = RenodeNode('test_sensor', {
        'platform': 'path/to/platform.repl',
        'firmware': 'path/to/firmware.elf',
        'monitor_port': 9999
    })
    node.start()
    assert node.renode_process is not None
    assert node.monitor_socket is not None
    node.stop()

def test_renode_time_advancement():
    """Test virtual time advancement."""
    node = RenodeNode('test_sensor', config)
    node.start()

    events = node.advance(1000000)  # 1 second

    assert node.current_time_us == 1000000
    node.stop()

def test_uart_parsing():
    """Test UART output parsing."""
    node = RenodeNode('test_sensor', config)

    uart_text = 'garbage\n{"type":"SAMPLE","temp":25.5,"time":1000000}\nmore garbage'
    events = node._parse_uart_output(uart_text)

    assert len(events) == 1
    assert events[0].type == 'SAMPLE'
    assert events[0].payload['temp'] == 25.5
```

### 5.2 Integration Tests

```python
# tests/stages/M3f/test_renode_coordinator.py

def test_renode_in_simulation():
    """Test Renode node in full simulation."""
    scenario = {
        'simulation': {'duration_us': 10000000, 'time_step_us': 10000},
        'nodes': [{
            'type': 'renode',
            'id': 'sensor_1',
            'platform': 'firmware/sensor-node/boards/nrf52840dk_nrf52840.repl',
            'firmware': 'firmware/sensor-node/build/zephyr/zephyr.elf'
        }]
    }

    coordinator = Coordinator(scenario)
    coordinator.run()

    events = coordinator.get_events()

    # Should have ~10 samples (1 per second)
    sample_events = [e for e in events if e.type == 'SAMPLE']
    assert 8 <= len(sample_events) <= 12

def test_renode_determinism():
    """Test that Renode execution is deterministic."""
    scenario_file = 'scenarios/renode-determinism-test.yaml'

    # Run 1
    coordinator1 = Coordinator(scenario_file)
    coordinator1.run()
    events1 = coordinator1.get_events()

    # Run 2 (same seed)
    coordinator2 = Coordinator(scenario_file)
    coordinator2.run()
    events2 = coordinator2.get_events()

    # Should be identical
    assert events1 == events2
```

### 5.3 Performance Tests

```python
# tests/stages/M3f/test_renode_performance.py

def test_renode_overhead():
    """Measure Renode simulation overhead."""
    import time

    coordinator = Coordinator('scenarios/renode-perf-test.yaml')

    wall_start = time.time()
    coordinator.run()  # 10 seconds virtual time
    wall_duration = time.time() - wall_start

    # Should be < 5x slowdown (10s sim in < 50s wall time)
    assert wall_duration < 50

    print(f"Slowdown: {wall_duration / 10:.2f}x")
```

---

## 6. Dependencies and Prerequisites

### 6.1 Software Requirements

**Renode:**
```bash
# Ubuntu/Debian
wget https://github.com/renode/renode/releases/download/v1.14.0/renode_1.14.0_amd64.deb
sudo apt install ./renode_1.14.0_amd64.deb

# macOS
brew install renode

# Verify installation
renode --version
```

**Zephyr SDK:**
```bash
# Install Zephyr SDK
wget https://github.com/zephyrproject-rtos/sdk-ng/releases/download/v0.16.5/zephyr-sdk-0.16.5_linux-x86_64.tar.xz
tar xvf zephyr-sdk-0.16.5_linux-x86_64.tar.xz
cd zephyr-sdk-0.16.5
./setup.sh

# Install West (Zephyr build tool)
pip3 install west

# Initialize Zephyr workspace
west init ~/zephyrproject
cd ~/zephyrproject
west update
```

**Python Dependencies:**
```bash
pip install pyserial  # For UART communication if needed
```

### 6.2 Board Selection

**Recommended:** Nordic nRF52840 DK
- Well-supported in Zephyr and Renode
- ARM Cortex-M4F @ 64MHz
- 1MB Flash, 256KB RAM
- Sufficient for TFLite Micro models

**Alternative:** STM32F4 Discovery
- ARM Cortex-M4 @ 168MHz
- Also well-supported

---

## 7. Risks and Mitigations

### Risk 1: Renode Monitor Protocol Complexity

**Risk:** Renode's monitor protocol may have undocumented quirks.

**Mitigation:**
- Start with manual testing (telnet to monitor port)
- Study Renode documentation and examples
- Consider using Renode's Python API as alternative

### Risk 2: Time Synchronization Accuracy

**Risk:** Renode's virtual time may drift from coordinator time.

**Mitigation:**
- Use Renode's external time source mode
- Verify time advancement with test cases
- Add time drift monitoring and warnings

### Risk 3: Performance Overhead

**Risk:** Renode instruction-level emulation may be too slow.

**Mitigation:**
- Use coarser time quantum (10ms instead of 1ms)
- Run fewer Renode instances (2-5 max)
- Use Python models for bulk nodes

### Risk 4: Firmware Build Complexity

**Risk:** Zephyr build system has steep learning curve.

**Mitigation:**
- Start with minimal example from Zephyr samples
- Use pre-built board configuration (nRF52840 DK)
- Document build process thoroughly

### Risk 5: Determinism Challenges

**Risk:** Renode may have non-deterministic behavior.

**Mitigation:**
- Seed Renode's RNG deterministically
- Disable any randomized features
- Test determinism early and often

---

## 8. Success Criteria

### Must Have (M3f Complete)

- [ ] Renode node adapter working
- [ ] Basic Zephyr firmware running in Renode
- [ ] Time synchronization with coordinator validated
- [ ] UART output parsed into simulation events
- [ ] At least 2 Renode nodes in single simulation
- [ ] Determinism verified (identical runs produce identical output)
- [ ] Integration tests passing

### Should Have (Stretch Goals)

- [ ] TFLite Micro inference in firmware
- [ ] Cycle-count measurements for ML inference
- [ ] Device vs edge vs cloud ML comparison working
- [ ] Performance overhead < 10x slowdown

### Nice to Have (Future Work)

- [ ] Multiple board targets (nRF52840, STM32F4)
- [ ] Energy consumption modeling
- [ ] Network packet injection from coordinator to firmware

---

## 9. Documentation Updates

### Files to Update:

1. **docs/architecture.md**
   - Update "Device Emulation" section with Renode implementation
   - Add Renode integration diagram

2. **docs/implementation-guide.md**
   - Add "Renode Integration" section
   - Include firmware build instructions

3. **README.md**
   - Add Renode installation instructions
   - Update feature list to show Renode support

4. **scenarios/vib-monitoring/README.md**
   - Add Renode scenario example
   - Document firmware build process

### New Documentation:

1. **docs/firmware-development-guide.md**
   - Zephyr setup
   - Firmware architecture
   - Building and flashing
   - Debugging with Renode

2. **firmware/sensor-node/README.md**
   - Build instructions
   - Board configuration
   - Testing procedures

---

## 10. Deliverables Checklist

### Code:
- [ ] `sim/device/renode_node.py` - Renode adapter
- [ ] `firmware/sensor-node/` - Zephyr firmware project
- [ ] Updated `sim/harness/coordinator.py`
- [ ] YAML schema extensions

### Tests:
- [ ] `tests/stages/M3f/test_renode_node.py`
- [ ] `tests/stages/M3f/test_renode_coordinator.py`
- [ ] `tests/stages/M3f/test_renode_determinism.py`
- [ ] `tests/stages/M3f/test_renode_performance.py`

### Documentation:
- [ ] M3f milestone summary document
- [ ] Updated architecture.md
- [ ] Firmware development guide
- [ ] Renode scenario examples

### Scenarios:
- [ ] `scenarios/renode-basic.yaml`
- [ ] `scenarios/renode-ml-placement.yaml`

---

## 11. Timeline and Effort Estimate

| Phase | Tasks | Duration | LOC |
|-------|-------|----------|-----|
| **Phase 1** | Renode adapter, monitor protocol | 1 week | ~300 |
| **Phase 2** | Zephyr firmware, UART protocol | 1 week | ~200 |
| **Phase 3** | Integration, determinism testing | 1 week | ~200 |
| **Phase 4** | TFLite inference (optional) | 1 week | ~300 |
| **Total** | | **3-4 weeks** | **~1000** |

---

## 12. Next Steps After M3f

With Renode integration complete, the system will have:
- ✅ True device-tier emulation (Tier 1)
- ✅ Deployable firmware (validated claim)
- ✅ Cycle-accurate timing
- ⚠️ Still missing ns-3 for network realism

**Recommended:** Proceed to M3g (ns-3 integration) to complete the full architectural vision.

---

## Notes

- **Hardware-in-the-loop:** With Renode integration, future work could include real hardware testing (flash firmware to actual nRF52840 DK)
- **Scalability:** Keep Renode node count low (2-10 max), use Python models for bulk
- **Alternative:** If Renode proves too complex, could use QEMU as fallback (less device-specific but well-supported)

---

**Status:** READY FOR IMPLEMENTATION
**Owner:** TBD
**Reviewer:** TBD
