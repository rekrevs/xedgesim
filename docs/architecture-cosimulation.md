# Co-Simulation Architecture for xEdgeSim

**Date:** 2025-11-13

## Architectural Question

Should xEdgeSim use a **lightweight simulation engine** decoupled from GUI, with socket-based communication to heterogeneous processes (Renode, ns-3, Docker)? Can this provide deterministic, cycle-accurate control?

**TL;DR: Yes, this is the right architecture. It's how modern co-simulation works (SimBricks, FMI, HLA). Renode supports this model explicitly.**

---

## Part 1: Benefits Over COOJA's Monolithic Architecture

### COOJA's Architecture (Monolithic)

```
┌─────────────────────────────────────────────────┐
│           Single Java Process (JVM)             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │   GUI    │  │  Radio   │  │  Motes   │      │
│  │ (Swing)  │←→│  Medium  │←→│ (MSPSim/ │      │
│  │          │  │          │  │  JNI)    │      │
│  └──────────┘  └──────────┘  └──────────┘      │
│         ↑            ↑              ↑           │
│         └────────────┴──────────────┘           │
│           Shared EventQueue                     │
│           Single Simulation Time                │
└─────────────────────────────────────────────────┘
```

**Characteristics:**
- Tight coupling: GUI, simulation logic, and emulation in one process
- Single language: Everything in Java (or C via JNI)
- Monolithic time: One event queue, one clock
- Hard to extend: Adding new mote types or mediums requires Java plugin

**Limitations:**
- Can't integrate external tools (ns-3, real containers)
- GUI and simulation can't be separated (memory overhead)
- JNI boundary is fragile and performance-limited
- Can't distribute simulation across machines

---

### Proposed Architecture (Federated Co-Simulation)

```
┌─────────────────────────────────────────────────────────────┐
│               Lightweight Coordinator (Python/C++)          │
│  ┌──────────────────────────────────────────────────┐       │
│  │  Time Coordinator + Event Scheduler              │       │
│  │  - Global virtual time                           │       │
│  │  - Send "advance to T" to all simulators         │       │
│  │  - Collect events, resolve, advance              │       │
│  └───────┬──────────┬──────────┬──────────┬─────────┘       │
└──────────┼──────────┼──────────┼──────────┼─────────────────┘
           │          │          │          │
       socket     socket     socket     TAP/TUN
           │          │          │          │
    ┌──────▼────┐ ┌──▼──────┐ ┌─▼────────┐ ┌▼──────────┐
    │  Renode   │ │ Renode  │ │  ns-3    │ │  Docker   │
    │ (Device1) │ │(Device2)│ │(Network) │ │  (Edge)   │
    └───────────┘ └─────────┘ └──────────┘ └───────────┘
         ↑                          ↑            ↑
    Deterministic              Deterministic  Non-deterministic
    cycle-accurate             discrete-event  (real process)
```

**Characteristics:**
- **Decoupled**: Coordinator, simulators, and GUI are separate processes
- **Language-agnostic**: Python coordinator, C# Renode, C++ ns-3
- **Federated time**: Each simulator has local time, coordinator synchronizes
- **Extensible**: Add new simulators by implementing socket protocol
- **Optional GUI**: Web-based dashboard or CLI, separate from engine

---

## Part 2: Massive Benefits Over COOJA

### ✅ Benefit 1: Modularity and Tool Selection

**COOJA**: Locked into MSPSim (MSP430), Contiki, Java implementations
**xEdgeSim**: Use best tool for each layer:
- **Device**: Renode (ARM Cortex-M, RISC-V, comprehensive peripheral models)
- **Network**: ns-3 (mature, validated, extensive protocol support)
- **Edge**: Docker (real containers, deployable)
- **Coordinator**: Python (easy to develop, rich ecosystem)

**Impact**: Can swap Renode→QEMU, or ns-3→OMNeT++ without rewriting entire system.

---

### ✅ Benefit 2: Scalability

**COOJA**: Single JVM, all motes share heap, limited to ~50-100 emulated motes
**xEdgeSim**:
- Distribute Renode instances across machines
- Use process isolation (each Renode instance is separate)
- Mix abstraction levels: Full emulation for critical nodes, models for bulk nodes

**Impact**: Could simulate 10 fully emulated devices + 1000 abstract device models.

---

### ✅ Benefit 3: Realism and Deployability

**COOJA**:
- Firmware compiled for host (x86) via JNI, not target architecture
- Can't test hardware-specific code (DMA, interrupts)
- No real containers (everything is simulation)

**xEdgeSim**:
- **Firmware**: Compiled for ARM, runs in Renode, bit-identical to hardware
- **Edge services**: Real Docker containers, deploy directly to gateways
- **Network**: ns-3 provides validated protocol models

**Impact**: "Deploy what you simulate, simulate what you deploy" - critical for industrial adoption.

---

### ✅ Benefit 4: Separation of Concerns

**COOJA**: GUI tightly coupled to simulation (can't run GUI-less without modifications)
**xEdgeSim**:
- Coordinator runs headless (no GUI dependency)
- Optional web-based dashboard (connects via websocket)
- Can run in CI/CD, cloud, HPC cluster

**Impact**: Lower memory footprint, better for batch experiments, cloud-friendly.

---

### ✅ Benefit 5: Integration with Real Systems

**COOJA**: Serial socket bridge is a hack, not architectural
**xEdgeSim**:
- Containers can expose real network interfaces
- Could replace simulated ns-3 with real network (testbed integration)
- Renode can connect to real peripherals via USB/SPI bridges

**Impact**: Hybrid simulation-testbed scenarios, gradual transition from sim to deployment.

---

## Part 3: Renode's Deterministic Control Capabilities

### Can Renode Be Controlled Cycle-Accurately?

**Answer: YES.** Renode is designed for this.

#### Renode's Time Framework

Renode has a **virtual time system** separate from wall-clock time:

```python
# Renode monitor commands
emulation RunFor "00:00:01.000"  # Run for 1 second of virtual time
emulation RunFor "1000000"        # Run for 1M virtual time quanta

# Single-stepping
sysbus.cpu Step                   # Execute one instruction
sysbus.cpu Step 1000              # Execute 1000 instructions

# Pause and inspect
emulation Pause
sysbus.cpu PC                     # Read program counter
sysbus ReadDoubleWord 0x20000000  # Read memory

# Resume
emulation Start
```

#### Deterministic Execution

Renode guarantees determinism via:
1. **Virtual time**: No dependency on wall-clock time
2. **Deterministic peripherals**: Timers, interrupts are virtual-time based
3. **Deterministic randomness**: Seeded RNGs
4. **Replay**: Can record and replay execution

**Example**: Same firmware + same inputs + same seed → **identical execution**

#### Socket-Based Control

Renode exposes **monitor interface** over sockets:

```bash
# Start Renode with socket monitor
renode --console --port 1234

# Connect from Python
import socket
s = socket.socket()
s.connect(('localhost', 1234))
s.send(b'emulation RunFor "0.001"\n')
response = s.recv(4096)
```

Can also use **robot framework** for higher-level control:

```robot
*** Test Cases ***
Should Boot And Print
    Execute Command    emulation CreateServerSocketTerminal 3456 "term"
    Execute Command    mach create
    Execute Command    machine LoadPlatformDescription @platforms/cpus/cortex-m3.repl
    Execute Command    sysbus LoadELF @firmware.elf
    Execute Command    start
    Wait For Line On Uart    "Boot complete"    timeout=10
```

---

## Part 4: Co-Simulation Time Synchronization

### The Challenge

Each simulator has its own time scale:
- **Renode**: Virtual time in microseconds/cycles
- **ns-3**: Simulation time in nanoseconds
- **Docker**: Wall-clock time (real processes)

Need to keep them synchronized.

### Solution: Conservative Synchronous Lockstep

**Algorithm**:
```
Global time T_global = 0
Delta T = 1ms  # Time step

Loop:
  1. Coordinator sends to all simulators: "Advance to T_global + Delta"

  2. Each simulator:
     - Renode: "emulation RunFor 0.001" (1ms virtual time)
     - ns-3: "Simulator::Stop(MilliSeconds(1))" then Run()
     - Docker: Wait 1ms wall-clock (or time-scaled)

  3. Simulators execute until T_global + Delta

  4. Simulators pause and send events back:
     - Renode: "UART output", "GPIO change", "DMA complete"
     - ns-3: "Packet arrived at interface X"
     - Docker: "HTTP request completed"

  5. Coordinator processes cross-simulator events:
     - Route packets from Renode → ns-3 → Docker
     - Update state, log metrics

  6. T_global += Delta
```

**Properties**:
- **Conservative**: Each simulator never advances beyond T_global + Delta
- **Deterministic**: Same inputs → same outputs (if simulators are deterministic)
- **Synchronous**: All simulators stay within Delta of each other

**Trade-off**:
- ✅ Simple to implement
- ✅ Deterministic
- ✅ Easy to debug
- ❌ Slowest simulator limits speed (Docker wall-clock time is the bottleneck)

---

### Handling Non-Deterministic Components (Docker)

**Problem**: Docker containers run real Linux processes on wall-clock time.

**Solutions**:

1. **Time dilation/scaling** (used by tools like TimeKeeper, SimBox):
   - Intercept time syscalls (gettimeofday, clock_gettime)
   - Return virtual time instead of wall-clock
   - Containers think they're running in real-time, but actually slowed down
   - **Pros**: Containers behave naturally
   - **Cons**: Requires kernel modifications or LD_PRELOAD hacks

2. **Record-replay**:
   - Record container behavior in a real testbed
   - Replay traces in simulation
   - **Pros**: Fast, deterministic
   - **Cons**: Less flexible, can't test new scenarios

3. **Mock services**:
   - Replace containers with Python/C++ models that respond deterministically
   - **Pros**: Fast, deterministic
   - **Cons**: Loses deployability benefit

4. **Accept non-determinism for edge/cloud**:
   - Focus determinism on device tier (Renode + ns-3)
   - Edge/cloud provide "statistical realism" (run multiple times, report distributions)
   - **Pros**: Pragmatic, matches reality (real cloud has variability)
   - **Cons**: Reproducibility is weaker

**Recommendation**: Use approach #4 initially (accept edge non-determinism), explore #1 (time dilation) if needed.

---

## Part 5: Comparison to Existing Co-Simulation Frameworks

### Similar Systems

| Framework | Domain | Architecture | Relevant Insights |
|-----------|--------|--------------|-------------------|
| **SimBricks** | Datacenter networks | Socket-based, time-synchronized simulators | Uses PCIe and Ethernet adapters to connect simulators |
| **FMI** | Automotive | Functional Mock-up Interface standard | Defines API for co-simulation units |
| **HLA** | Defense simulations | High-Level Architecture, federated | Complex but handles large-scale distributed sim |
| **Mosaik** | Smart grids | Python-based, event-driven co-sim | Lightweight coordinator, similar to our proposal |
| **ns-3 DCE** | Network + apps | Runs real Linux apps in ns-3 | Time dilation for deterministic execution |

**Key Lesson**: Socket-based co-simulation is proven for heterogeneous systems. xEdgeSim would follow established patterns.

---

## Part 6: Proposed xEdgeSim Architecture (Detailed)

### Components

#### 1. **Coordinator (Python)**
- Maintains global virtual time
- Sends "advance" commands to simulators
- Collects and routes events
- Logs metrics
- Implements scenario logic (YAML-based)

**Why Python:**
- Rapid development
- Rich ecosystem (PyYAML, pandas, matplotlib)
- Good for glue code and orchestration

#### 2. **Renode Instances (C# .NET)**
- One instance per emulated device (or group of devices)
- Controlled via socket (monitor commands)
- Runs ARM Cortex-M firmware (Zephyr, FreeRTOS)
- Reports events: UART output, network packets, GPIO, timers

**Integration**:
```python
class RenodeSimulator:
    def __init__(self, host, port, script):
        self.socket = connect(host, port)
        self.execute(f"machine LoadPlatformDescription {script}")
        self.execute(f"sysbus LoadELF firmware.elf")

    def advance(self, delta_us):
        self.execute(f"emulation RunFor {delta_us}")

    def get_uart_output(self):
        # Read from UART terminal socket
        pass
```

#### 3. **ns-3 Simulator (C++)**
- Models network (802.15.4, Wi-Fi, LTE, IP backbone)
- Integrated via TAP/TUN devices or custom C++ interface
- Reports packet deliveries, drops, latencies

**Integration Options**:
- **Option A**: TAP/TUN (Renode network → Linux TAP → ns-3 TapBridge)
- **Option B**: Direct socket (custom ns-3 module listens for packets)

#### 4. **Docker Containers (Real Linux)**
- Edge services: MQTT broker, aggregator, ML inference
- Cloud services: Mocked as simple Python HTTP servers
- Non-deterministic but realistic

**Integration**:
- Connect to ns-3 via bridged network
- Or: Use Docker's user-defined networks

#### 5. **Optional GUI/Dashboard (Web-based)**
- Separate process, connects to coordinator via WebSocket
- Real-time visualization of topology, metrics
- Not required for headless runs

---

### Communication Protocol (Simplified)

**Coordinator → Simulator**:
```json
{
  "command": "advance",
  "time_us": 1000,
  "events": [
    {"type": "packet", "data": "0x48656C6C6F", "dest": "device1"}
  ]
}
```

**Simulator → Coordinator**:
```json
{
  "time_us": 1000,
  "events": [
    {"type": "uart", "source": "device1", "data": "Temperature: 25C\n"},
    {"type": "packet_sent", "source": "device1", "dest": "gateway", "size": 128}
  ]
}
```

Could use:
- **Raw sockets** (TCP/Unix domain)
- **ZeroMQ** (message queue, better for pub/sub)
- **gRPC** (structured, auto-generated bindings)

**Recommendation**: Start with raw TCP sockets for simplicity, migrate to ZeroMQ if needed.

---

## Part 7: Determinism Analysis

### What Can Be Deterministic?

| Component | Deterministic? | Notes |
|-----------|----------------|-------|
| Renode | ✅ Yes | Virtual time, seeded RNG |
| ns-3 | ✅ Yes | Discrete-event simulator, deterministic if seeded |
| Coordinator | ✅ Yes | Python is deterministic for same inputs |
| Docker | ❌ No* | Real Linux processes, scheduling variability |

**Overall**: Device and network layers can be fully deterministic. Edge/cloud layers provide statistical realism.

### Determinism Guarantees

**Tier 1 (Strong)**: Device behavior
- Same firmware + same inputs → identical execution
- Critical for protocol debugging, regression testing

**Tier 2 (Statistical)**: End-to-end metrics
- Multiple runs → stable mean/variance
- Enough for performance evaluation papers

**Tier 3 (Qualitative)**: Edge failure scenarios
- Demonstrate phenomena (e.g., "edge drop causes alert loss")
- Don't need exact reproducibility

---

## Part 8: Implementation Roadmap

### M0: Proof-of-Concept (Coordinator + Renode)
- Simple Python coordinator
- Control one Renode instance via socket
- Firmware prints to UART, coordinator logs output
- **Goal**: Validate socket-based control works

### M1: Add ns-3 Integration
- Coordinator controls both Renode and ns-3
- Use TAP/TUN for packet routing
- **Goal**: Packets flow Device → ns-3 → Gateway

### M2: Add Docker Edge Services
- ns-3 bridges to Docker network
- Edge containers receive packets
- **Goal**: End-to-end packet flow

### M3: Add Metrics and ML
- Coordinator logs latencies, energy estimates
- Add ML inference services
- **Goal**: Generate E2E latency CDFs

### M4: Fault Injection and Scenarios
- Coordinator can inject faults (packet drops, delays)
- YAML-based scenario configs
- **Goal**: Run experiments from config files

---

## Part 9: Comparison - COOJA vs Proposed xEdgeSim

| Aspect | COOJA | xEdgeSim (Proposed) |
|--------|-------|---------------------|
| **Architecture** | Monolithic Java | Federated co-simulation |
| **GUI** | Swing (coupled) | Optional web dashboard |
| **Device emulation** | MSPSim (MSP430) | Renode (ARM Cortex-M, RISC-V) |
| **RTOS** | Contiki only | Zephyr, FreeRTOS, any |
| **Network** | Simple radio mediums | ns-3 (validated models) |
| **Edge/cloud** | ❌ None | ✅ Docker + mocks |
| **Determinism** | ✅ Full | ✅ Device tier, ⚠ Statistical edge/cloud |
| **Scalability** | 50-100 motes | 10-50 emulated + 1000s modeled |
| **Extensibility** | Java plugins | Add simulators via socket protocol |
| **Deployability** | Firmware only | Firmware + containers |
| **CI/CD** | ✅ Headless mode | ✅ Headless + YAML configs |

---

## Part 10: Risks and Mitigations

### Risk 1: "Socket latency will kill performance"

**Analysis**:
- Socket call ~1-10 µs on localhost
- Time step Delta = 1 ms = 1000 µs
- Overhead is ~1% per step

**Mitigation**: Use Unix domain sockets (faster than TCP), batch events.

---

### Risk 2: "Time synchronization is too complex"

**Analysis**:
- Conservative lockstep is simple (used by SimBricks, Mosaik)
- No need for optimistic algorithms initially

**Mitigation**: Start with coarse time steps (1 ms), refine if needed.

---

### Risk 3: "Renode will be too slow"

**Analysis**:
- Renode can run real-time or faster for simple firmware
- Bottleneck is instruction-level emulation for complex code

**Mitigation**:
- Use **mixed abstraction**: Renode for critical nodes, models for bulk
- Profile and optimize hot paths

---

### Risk 4: "Docker non-determinism breaks experiments"

**Analysis**:
- True, but edge services have inherent variability in real deployments
- Statistical results (mean + confidence intervals) are acceptable

**Mitigation**: Run multiple trials, report distributions.

---

## Conclusion

### Should xEdgeSim Use This Architecture?

**YES.**

**Key Benefits:**
1. ✅ **Modularity**: Best tool for each layer (Renode, ns-3, Docker)
2. ✅ **Realism**: Deployable firmware and containers
3. ✅ **Scalability**: Distributed, process-isolated
4. ✅ **Extensibility**: Add simulators without rewriting core
5. ✅ **Proven pattern**: Follows SimBricks, FMI, HLA

**Renode Compatibility:**
- ✅ Supports cycle-accurate deterministic execution
- ✅ Socket-based control (monitor + robot framework)
- ✅ Virtual time, pausable, inspectable
- ✅ Designed for co-simulation

**Determinism:**
- ✅ Device + network tiers: Fully deterministic
- ⚠ Edge/cloud: Statistical (acceptable for research)

**Recommendation**:
- Implement lightweight Python coordinator
- Control Renode via socket (monitor protocol)
- Integrate ns-3 via TAP/TUN
- Accept Docker non-determinism, provide statistical confidence

This architecture positions xEdgeSim as a **modern, extensible, realistic** platform - a generational leap over COOJA's monolithic design.
