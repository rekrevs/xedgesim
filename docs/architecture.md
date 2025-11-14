# xEdgeSim Architecture: Federated Co-Simulation with Variable-Fidelity Determinism

**Date:** 2025-11-13
**Status:** Working Document - Architectural Design Phase

## Document Purpose

This document serves as the primary architectural reference for xEdgeSim, guiding design decisions and implementation across all development phases (M0-M4). It consolidates analysis of federated co-simulation approaches, determinism strategies, and implementation considerations for heterogeneous IoT-edge-cloud systems.

**Important**: This is a **comprehensive long-term architecture** document. While all sections are important for understanding xEdgeSim's full vision, **not all features are implemented simultaneously**. Refer to **Section 2: Implementation Philosophy** below for guidance on phased complexity growth and minimal M0 scope.

**Companion Document**: For feature-specific implementation details (ML placement, metrics, ns-3/Docker integration, deployability, CI/CD, scalability), see `docs/implementation-guide.md`.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Implementation Philosophy: Iterative Complexity Growth](#2-implementation-philosophy-iterative-complexity-growth)
3. [Background: Rationale for Federated Co-Simulation](#3-background-rationale-for-federated-co-simulation)
4. [Understanding Time Models and Determinism](#4-understanding-time-models-and-determinism)
5. [The Tiered Determinism Solution](#5-the-tiered-determinism-solution)
6. [Component Integration Details](#6-component-integration-details)
7. [Conservative Synchronous Lockstep Algorithm](#7-conservative-synchronous-lockstep-algorithm)
8. [Achieving Variable-Fidelity Accuracy](#8-achieving-variable-fidelity-accuracy)
9. [Decision Matrix: When to Relax Determinism](#9-decision-matrix-when-to-relax-determinism)
10. [Validation and Comparison to Existing Systems](#10-validation-and-comparison-to-existing-systems)
11. [Implementation Roadmap](#11-implementation-roadmap)
12. [Risks and Mitigations](#12-risks-and-mitigations)
13. [Recommendations](#13-recommendations)

**For feature-specific implementation guidance**, see `docs/implementation-guide.md`:
- ML Placement Framework *(M3)*
- Scenario Specification *(M0-M1)*
- Metrics Collection *(M0-M1)*
- ns-3 Integration *(M1)*
- Docker Integration *(M2)*
- Deployability *(M2-M4)*
- CI/CD *(M2-M4)*
- Scalability *(M3-M4)*

---

## 1. Executive Summary

### Core Objective

The objective is to build a simulator that provides:
- **Cycle-accurate device emulation** (Renode for ARM firmware)
- **Realistic network simulation** (ns-3 for protocols)
- **Deployable edge services** (Docker containers)
- **All coordinated via sockets with deterministic time synchronization**

### Solution Approach

This objective is achievable using **federated co-simulation** with **tiered determinism**:

- **Tier 1 (Device/Network)**: Fully deterministic, cycle/timing-accurate
- **Tier 2 (Edge)**: Statistical reproducibility OR deterministic models (user choice)
- **Tier 3 (Cloud)**: Deterministic abstract models

This architecture is validated by SimBricks (datacenter systems) and adapts proven co-simulation patterns (FMI, HLA, Mosaik) to IoT-edge-cloud domains.

### Key Architectural Decisions

1. **Lightweight coordinator** (Go or Python) communicates via sockets with heterogeneous processes
2. **Conservative synchronous lockstep** for time coordination
3. **Hybrid determinism**: Full where critical, statistical where acceptable
4. **Variable fidelity**: Appropriate accuracy per tier (cycle → timing → latency → abstract)
5. **User choice**: Real containers (realism) vs models (determinism)

### Implementation Philosophy: Elegance Through Restraint

**Critical Insight**: While this document describes xEdgeSim's complete architecture, **not all features are implemented simultaneously**. Attempting to deliver all objectives simultaneously risks analysis paralysis and over-engineering.

**Phased Approach**:
- **M0 (2 weeks, ~450 LOC)**: Minimal proof-of-concept - Coordinator + Renode + Python edge model
  - Proves socket-based time synchronization works
  - Hardcoded scenario, direct sockets, no ns-3/Docker/YAML
- **M1 (4 weeks)**: Add network realism - Integrate ns-3, YAML scenarios, structured metrics
- **M2 (4 weeks)**: Add edge realism - Docker containers (optional), deployability considerations
- **M3 (6 weeks)**: Add research value - ML placement framework (the "killer app")
- **M4 (6 weeks)**: Production polish - CI/CD, scalability, optimization

**Guiding Principles**:
1. **Do One Thing Well**: Coordinator only coordinates time; components handle their own concerns
2. **Defer Decisions**: Do not commit to technologies until validated by real implementation
3. **Make It Work, Make It Right, Make It Fast**: M0 proves → M1-M2 refine → M3-M4 optimize

Refer to **Section 2** below for detailed rationale and implementation strategies.

---

## 2. Implementation Philosophy: Iterative Complexity Growth

### 2.1 The Complexity Challenge

This architecture document is comprehensive (3,874+ lines across 21 sections), covering everything from basic time synchronization to ML placement frameworks, CI/CD integration, and scalability strategies. This completeness is valuable for understanding xEdgeSim's full vision but creates a risk: **implementation paralysis**.

**The Problem**: Attempting to implement all objectives simultaneously results in:
- Cognitive overload for implementers
- Risk of over-engineering early milestones
- Loss of focus on core differentiators
- Delayed time-to-first-result
- Difficulty validating architectural assumptions

**Root Cause**: "Feature completeness bias" - the desire to specify everything upfront rather than evolve the design iteratively based on real implementation experience.

### 2.2 Core vs. Peripheral Objectives

To avoid complexity paralysis, it is necessary to distinguish essential from deferrable objectives:

| Objective | Classification | Rationale |
|-----------|---------------|-----------|
| **Federated co-simulation** | ✅ CORE | This IS xEdgeSim's architecture |
| **Tiered determinism** | ✅ CORE | Enables device/network debugging |
| **ML placement framework** | ✅ CORE | The unique research contribution |
| **Renode integration** | ✅ CORE | Realistic device emulation |
| **Scenario specification** | ✅ CORE | Enables reproducibility |
| **ns-3 integration** | 🟡 IMPORTANT | Needed for network realism (M1) |
| **Metrics collection** | 🟡 IMPORTANT | Needed for evaluation (M1) |
| **Docker integration** | 🟡 IMPORTANT | Needed for edge realism (M2) |
| **Deployability pipeline** | 🟢 NICE-TO-HAVE | Great differentiator, but M2-M4 |
| **CI/CD automation** | 🟢 NICE-TO-HAVE | Important for adoption, but M2-M4 |
| **Scalability (mixed abstraction)** | 🟢 NICE-TO-HAVE | M3-M4 concern |
| **Variable fidelity** | 🟢 NICE-TO-HAVE | Nice research feature, but M3+ |

### 2.3 Milestone-Driven Complexity Growth

Instead of implementing everything at once, xEdgeSim grows complexity iteratively:

#### M0: Minimal Viable Proof-of-Concept (2 weeks, ~450 LOC)

**Goal**: Prove socket-based co-simulation works

**Includes**:
- Coordinator (~200 lines) - only time synchronization
- Renode adapter (~100 lines) - external control via sockets
- Python edge model (~100 lines) - simple processing model
- Device firmware (~50 lines) - sensor simulation
- Analysis script (~50 lines) - post-process CSV metrics

**Explicitly Excludes**:
- ns-3 (direct sockets instead)
- Docker (Python models instead)
- YAML parsing (hardcoded config)
- ML placement (not relevant yet)
- CI/CD automation (manual testing)
- Deployability pipeline (not applicable)

**Success Criteria**: Renode and Python process time-synchronized via coordinator, deterministic execution validated.

#### M1: Add Network Realism (4 weeks)

**Adds**:
- ns-3 integration for packet-level simulation
- YAML scenario parser (simple schema)
- Structured metrics collection
- Multiple network types (WiFi, Zigbee, LoRa)

**Why M1**: Network realism is essential for cross-tier latency evaluation.

#### M2: Add Edge Realism (4 weeks)

**Adds**:
- Docker containers (optional, alongside Python models)
- TAP/TUN networking for ns-3 ↔ Docker
- Deployability considerations (documentation)
- Container orchestration

**Why M2**: Edge realism enables deployment pipeline validation.

#### M3: Add Research Value (6 weeks)

**Adds**:
- ML placement framework (device/edge/cloud variants)
- Trade-off evaluation (energy-latency-accuracy Pareto frontiers)
- Cloud tier integration
- Scalability via mixed abstraction (Renode + Python models)

**Why M3**: ML placement is the "killer app" differentiator. Requires M0-M2 infrastructure.

#### M4: Production Polish (6 weeks)

**Adds**:
- CI/CD automation (GitHub Actions)
- Result validation framework
- Full deployability pipeline
- Performance optimization
- Fault injection
- Comprehensive documentation

**Why M4**: Makes xEdgeSim production-ready for adoption.

### 2.4 Architectural Simplification Strategies

#### Strategy 1: "Dumb and Simple" Coordinator

**Problem**: Coordinator risks becoming a monolith handling time sync + metrics + faults + validation + ML logic.

**Solution**: Coordinator ONLY coordinates time.

```go
// M0 Coordinator: ~200 lines total
type Coordinator struct {
    nodes       []Node
    currentTime uint64
    timeStep    uint64
}

func (c *Coordinator) Run(duration uint64) {
    for c.currentTime < duration {
        c.currentTime += c.timeStep
        c.broadcastAdvanceTo(c.currentTime)
        c.waitForAllAcks()
    }
}
```

**Deferred concerns**:
- Metrics aggregation → components write CSV files, post-process externally
- Scenario parsing → hardcoded in M0, simple YAML in M1
- Fault injection → add in M4 if needed
- ML placement logic → in separate analysis tools (Python)

#### Strategy 2: Metrics are Just Files

**Problem**: Building a hierarchical metrics collection framework into the coordinator.

**Solution**: Components write CSV files. Post-processing operations join them.

```python
# Post-processing (~50 lines):
devices = pd.read_csv('device_metrics.csv')
network = pd.read_csv('network_metrics.csv')
edge = pd.read_csv('edge_metrics.csv')

merged = pd.merge(devices, network, on='time_us')
merged = pd.merge(merged, edge, on='time_us')
merged['end_to_end_latency'] = merged['edge_rx_time'] - merged['device_tx_time']
```

**Impact**: Coordinator does not aggregate metrics. Simple file I/O operations are used.

#### Strategy 3: Skip ns-3 in M0

**Problem**: ns-3 integration complexity from day 1.

**Solution**: M0 uses direct sockets, M1 adds ns-3.

```python
# M0: Direct socket (no network simulation)
device_socket.sendto(data, ('10.0.2.1', 1883))
```

**Impact**: M0 proves co-simulation works without network complexity.

#### Strategy 4: Python Models Before Docker

**Problem**: Docker orchestration complexity.

**Solution**: M0-M1 use Python models, M2 adds Docker as optional enhancement.

```python
# M0-M1: Simple Python edge model
class MQTTGatewayModel:
    def advance_to(self, target_time):
        # Process packets, simple 1ms/packet model
        pass
```

**Impact**: Avoid Docker until edge realism becomes critical.

#### Strategy 5: Hardcoded Configuration in M0

**Problem**: Premature YAML schema design.

**Solution**: M0 uses hardcoded configuration, M1 introduces simple YAML, M3 implements full schema if needed.

```go
// M0: Hardcoded config (~10 lines)
config := SimConfig{
    Duration: 60 * 1e6,
    Devices: []DeviceConfig{{Firmware: "sensor.elf", Count: 10}},
}
```

**Impact**: Zero YAML parsing for M0.

### 2.5 Unified Abstractions for Elegance

#### The "Node" Abstraction

All components are represented as **Nodes**. A node can:
1. Advance simulated time
2. Communicate via sockets
3. Report when ready

```go
type Node interface {
    AdvanceTo(timeUs uint64) error
    WaitForReady() error
    GetID() string
}
```

The coordinator does not distinguish between Renode, ns-3, Docker, or Python models. The design is type-agnostic.

### 2.6 Design Principles

1. **Do One Thing Well**: Coordinator coordinates time. Metrics are files. Components own their concerns.

2. **Defer Decisions**: Language choice (Go vs Python), Docker vs models, variable fidelity - decide when validated.

3. **Convention Over Configuration**: Sensible defaults, hardcode what is common, defer YAML schemas.

4. **Composition Over Inheritance**: Everything is a Node. Nodes compose. No complex type hierarchies.

5. **Make It Work, Make It Right, Make It Fast**: M0 proves → M1-M2 refine → M3-M4 optimize.

6. **YAGNI (You Are Not Going to Need It)**: Do not build fault injection unless users request it. Do not build variable fidelity unless needed for a paper.

7. **Worse Is Better**: Simple, working system beats complex, perfect system. Ship M0 with limitations, iterate.

### 2.7 Document Usage Guidelines

**For M0 Implementation**:
- Read sections 1-2 (this), 3-7 (core architecture), 11 (roadmap)
- Focus on Section 2.3 for minimal M0 scope (~450 LOC, 2 weeks)
- Ignore sections 14-21 (feature-specific details)

**For M1-M2 Implementation**:
- Re-read sections 1-13 (core architecture)
- Focus on sections 15-18 (scenario spec, metrics, ns-3, Docker)
- Defer sections 14, 19-21

**For M3-M4 Implementation**:
- Review all sections
- Deep dive into sections 14, 19-21 (ML placement, CI/CD, scalability)

**For Long-Term Architecture Understanding**:
- Read all sections to understand full vision
- Note milestone tags (M0, M1, M2, M3, M4) in sections 14-21

### 2.8 Comparison: Before vs. After Simplification

| Aspect | Comprehensive (all at once) | Simplified (phased) |
|--------|----------------------------|---------------------|
| **M0 scope** | All 12 objectives | 4 core objectives |
| **M0 LOC** | ~3,000 lines | ~450 lines |
| **M0 duration** | 6-8 weeks | 2 weeks |
| **Coordinator** | 8 responsibilities | 1 (time coordination) |
| **Metrics** | Hierarchical framework | CSV files + post-processing |
| **Scenario config** | Full YAML schema | Hardcoded (M0), simple YAML (M1) |
| **Edge services** | Docker required | Python models (M0), Docker optional (M2) |
| **ns-3** | Day 1 | M1 |
| **Deployability** | Full pipeline (M1) | Documentation (M2), automation (M4) |
| **Risk** | Analysis paralysis | Manageable |

### 2.9 Success Metrics by Milestone

**M0 Success**:
- ✅ Coordinator synchronizes Renode + Python model
- ✅ Deterministic execution validated (identical input yields identical output)
- ✅ Metrics collected and analyzed
- ✅ Blog post: "xEdgeSim M0 built in 2 weeks"

**M1 Success**:
- ✅ ns-3 integrated, realistic network simulation
- ✅ YAML scenarios work
- ✅ Cross-tier latency measured

**M2 Success**:
- ✅ Docker containers work alongside Python models
- ✅ Same containers run in simulation and on real hardware
- ✅ Deployability path documented

**M3 Success**:
- ✅ ML placement experiments working
- ✅ Pareto frontiers computed (energy-latency-accuracy)
- ✅ Paper-ready results

**M4 Success**:
- ✅ CI/CD automated
- ✅ Scalability validated (100-1000s of devices)
- ✅ Production-ready platform

---

## 3. Background: Rationale for Federated Co-Simulation

### 3.1 COOJA's Monolithic Architecture (The Problem)

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

**Limitations**:
- Tight coupling: GUI, simulation, emulation in a single process
- Single language: Java (or C via fragile JNI)
- Monolithic time: One event queue, one clock
- External tool integration not possible (ns-3, Docker)
- Simulation cannot be distributed across machines
- Difficult to extend: Adding capabilities requires Java plugins

### 3.2 Proposed Federated Architecture (The Solution)

```
┌─────────────────────────────────────────────────────────────┐
│         Lightweight Coordinator (Go or Python)              │
│  ┌──────────────────────────────────────────────────┐       │
│  │  Time Coordinator + Event Scheduler              │       │
│  │  - Maintains global virtual time                 │       │
│  │  - Sends "advance to T" to all nodes             │       │
│  │  - Collects events, routes messages              │       │
│  │  - Logs metrics, manages scenarios               │       │
│  └───────┬──────────┬──────────┬──────────┬─────────┘       │
└──────────┼──────────┼──────────┼──────────┼─────────────────┘
           │          │          │          │
       socket     socket     socket     socket
           │          │          │          │
    ┌──────▼────┐ ┌──▼──────┐ ┌─▼────────┐ ┌▼──────────┐
    │  Renode   │ │ Renode  │ │  ns-3    │ │ Docker/   │
    │ (Device1) │ │(Device2)│ │(Network) │ │ Python    │
    └───────────┘ └─────────┘ └──────────┘ └───────────┘
         ↑              ↑           ↑            ↑
    Tier 1         Tier 1      Tier 1      Tier 2/3
    Virtual        Virtual     Virtual     Wall-clock/
    Time           Time        Time        Virtual
    Deterministic  Deterministic Deterministic Statistical
```

**Characteristics**:
- **Decoupled**: Coordinator, simulators, GUI are separate processes
- **Language-agnostic**: Go/Python coordinator, C# Renode, C++ ns-3, Python analysis tools
- **Federated time**: Each component has local time, coordinator synchronizes
- **Extensible**: Add components by implementing socket protocol
- **Optional GUI**: Web-based dashboard or CLI, separate from engine

### 3.3 Benefits Over Monolithic Approach

| Aspect | Monolithic (COOJA) | Federated (xEdgeSim) |
|--------|-------------------|---------------------|
| **Modularity** | Locked into Java ecosystem | Best tool per layer |
| **Scalability** | Single JVM heap (~50-100 nodes) | Distributed processes (10 emulated + 1000s modeled) |
| **Deployability** | Firmware compiled for host (x86) | Firmware for ARM, real Docker containers |
| **Extensibility** | Java plugins required | Socket protocol interface |
| **GUI coupling** | Tightly coupled | Optional, separate process |
| **Real system integration** | Limited (serial socket hack) | Architectural (TAP/TUN, network bridges) |

---

## 4. Understanding Time Models and Determinism

### 4.1 The Fundamental Challenge

The system must coordinate fundamentally different time models:

| Component | Time Model | Deterministic? | Pausable? | Accuracy Level |
|-----------|------------|----------------|-----------|----------------|
| **Renode** | Virtual (can pause) | ✅ Yes | ✅ Yes | ✅ Cycle-accurate |
| **ns-3** | Virtual (event-driven) | ✅ Yes | ✅ Yes | ⚠️ Timing-accurate (nanosecond) |
| **Python models** | Virtual (if controlled) | ✅ Yes | ✅ Yes | ❌ Abstract |
| **Docker** | **Wall-clock** | ❌ No | ⚠️ Hard | ❌ Not applicable |

**The Core Challenge**: Fundamental incompatibility exists between virtual time (Renode, ns-3) and wall-clock time (Docker containers).

### 4.2 Docker Challenges

Docker containers are **real Linux processes**:

```
Real Process Characteristics:
- Scheduled by kernel (non-deterministic)
- gettimeofday(), clock_gettime() → returns wall-clock time
- sleep(), select() → use real timers
- I/O timing varies
- Thread scheduling is non-deterministic
```

**Consequences**:
1. **Cannot pause cleanly**: Stopping a container does not freeze its time perception
2. **Cannot single-step**: No concept of "advance by 1ms of virtual time" exists
3. **Non-deterministic**: Identical inputs do not yield identical outputs (scheduling, I/O races)

### 4.3 Historical Approaches and Lessons Learned

#### Approach 1: Time Dilation (ns-3 DCE, TimeKeeper, SimBox)

**Concept**: Intercept time syscalls, return virtual time instead of wall-clock.

```c
// LD_PRELOAD library
int clock_gettime(clockid_t clk_id, struct timespec *tp) {
    if (clk_id == CLOCK_MONOTONIC) {
        get_virtual_time_from_coordinator(tp);
        return 0;
    }
    return real_clock_gettime(clk_id, tp);
}
```

**Why it failed (ns-3 DCE abandoned)**:
- ❌ Complex: LD_PRELOAD or kernel modifications
- ❌ Fragile: VDSO, RDTSC bypass interception
- ❌ Maintenance burden: Must track kernel changes
- ❌ Incomplete: Cannot intercept all time sources
- ❌ Performance: Overhead on every syscall

**Lesson**: Avoid time interception; use architectural solutions.

#### Approach 2: Record-Replay

**Concept**: Record container behavior in testbed, replay in simulation.

**Why it is insufficient**:
- ❌ Inflexible: Cannot test new scenarios
- ❌ Not deployable: Trace does not equal real container

#### Approach 3: Accept Non-Determinism (Recommended)

**Concept**: Run containers in real-time, accept statistical reproducibility.

**Why it works**:
- ✅ Simple: No time interception
- ✅ Works with unmodified containers
- ✅ Deployable: Real containers
- ⚠️ Statistical: Report mean ± confidence interval

#### Approach 4: Use Deterministic Models

**Concept**: Replace containers with Python/C++ event-driven models.

**Trade-off**:
- ✅ Fully deterministic
- ✅ Fast
- ❌ Lose deployability

---

## 5. The Tiered Determinism Solution

### 5.1 Key Insight: Different Tiers Have Different Requirements

| Tier | What is Tested | Determinism Required? | Rationale |
|------|----------------|----------------------|-----------|
| **Device** | Firmware timing, race conditions, protocol correctness | ✅ **Full** | Debug protocol bugs, find firmware races |
| **Network** | Packet loss, latency, protocol behavior | ✅ **Full** | Deterministic protocol testing |
| **Edge** | Service behavior, processing latency | ⚠️ **Statistical** | Real deployments have variance |
| **Cloud** | High-level responses | ⚠️ **Abstract** | Latency varies in real cloud environments |

**Implication**: Uniform determinism across all tiers is not required.

### 5.2 Hybrid Determinism Architecture

```
┌─────────────────────────────────────────────────┐
│         Coordinator (Go or Python)              │
│  - Maintains global virtual time T             │
│  - Conservative synchronous lockstep            │
│  - Routes messages between tiers                │
└────┬────────┬────────┬────────┬─────────────────┘
     │        │        │        │
  Tier 1   Tier 1   Tier 2   Tier 3
  (Full    (Full   (Statistical) (Abstract)
   Determ)  Determ)
     │        │        │        │
┌────▼───┐ ┌─▼────┐ ┌─▼──────┐ ┌▼────────┐
│ Renode │ │ ns-3 │ │ Docker │ │ Python  │
│  (MCU) │ │(Net) │ │ (Edge) │ │ (Cloud) │
└────────┘ └──────┘ └────────┘ └─────────┘
 Virtual   Virtual   Wall-Clock  Virtual
  Time      Time       Time       Time
```

### 5.3 Determinism Guarantees Per Tier

**Tier 1: Full Determinism (Device + Network)**
- **Renode**: Cycle-accurate, virtual time, seeded RNG
  - Same firmware + inputs + seed → **identical execution**
  - Critical for debugging firmware race conditions
- **ns-3**: Event-driven, virtual time, seeded RNG
  - Same inputs + seed → **identical packet timing**
  - Critical for protocol validation

**Tier 2: Statistical Reproducibility (Edge)**
- **Docker (Option A)**: Real containers, wall-clock time
  - Run N trials, report mean ± confidence intervals
  - Captures real service variability
- **Models (Option B)**: Python/C++ event-driven
  - Fully deterministic
  - Trade deployability for reproducibility

**Tier 3: Abstract Determinism (Cloud)**
- **Python mocks**: Simple latency models
  - Fully deterministic
  - "Cloud inference = 50ms" is sufficient

---

## 6. Component Integration Details

### 5.1 Coordinator (Go or Python)

**Responsibilities**:
- Maintain global virtual time
- Send "advance to T" commands to all nodes
- Collect events from nodes
- Route cross-node messages
- Log metrics
- Implement scenario logic (YAML-based)

**Language Choice: To Be Decided**

Both Go and Python are viable candidates for the coordinator:

**Go advantages**:
- **Goroutines**: Excellent concurrency model for managing multiple component sockets simultaneously
- **Static typing**: Compile-time checks improve robustness and catch errors early
- **Performance**: Better for tight time synchronization loops and message routing
- **Single binary**: Easy deployment and distribution
- **Standard library**: Built-in networking, JSON/YAML parsing, excellent testing support

**Python advantages**:
- **Rapid prototyping**: Faster to write and iterate during early development
- **Rich ecosystem**: PyYAML, pandas, numpy for data handling
- **Accessibility**: Easier for students and researchers to understand and modify
- **Analysis integration**: Seamless integration with post-processing tools

**Decision deferred to M0 implementation phase**. Both languages are capable of implementing the required socket-based coordination. See `docs/architecture-language-choice.md` for detailed analysis.

### 5.2 Renode Integration (Tier 1)

**Note**: The code examples below use Go for illustration purposes, but the same interfaces can be implemented in Python using asyncio and sockets.

**Control Interface**:

```go
type RenodeNode struct {
    conn          net.Conn
    currentTimeUs uint64
    platform      string
}

func NewRenodeNode(host string, port int, platformScript string) (*RenodeNode, error) {
    conn, err := net.Dial("tcp", fmt.Sprintf("%s:%d", host, port))
    if err != nil {
        return nil, err
    }

    node := &RenodeNode{
        conn:          conn,
        currentTimeUs: 0,
        platform:      platformScript,
    }

    // Load platform and firmware
    if err := node.execute(fmt.Sprintf("machine LoadPlatformDescription %s", platformScript)); err != nil {
        return nil, err
    }
    if err := node.execute("sysbus LoadELF firmware.elf"); err != nil {
        return nil, err
    }

    return node, nil
}

func (r *RenodeNode) SendAdvanceCommand(targetTimeUs uint64) error {
    deltaUs := targetTimeUs - r.currentTimeUs
    // Execute exactly deltaUs microseconds of virtual time
    return r.execute(fmt.Sprintf("emulation RunFor %d", deltaUs))
}

func (r *RenodeNode) WaitForCompletion() ([]Event, error) {
    // Read UART output, GPIO changes, network packets
    events := []Event{}
    reader := bufio.NewReader(r.conn)

    for {
        line, err := reader.ReadString('\n')
        if err != nil {
            return nil, err
        }
        if strings.Contains(line, "EXECUTION_COMPLETE") {
            break
        }
        event := parseEvent(line)
        events = append(events, event)
    }

    r.currentTimeUs = targetTimeUs
    return events, nil
}

func (r *RenodeNode) execute(command string) error {
    _, err := r.conn.Write([]byte(command + "\n"))
    return err
}
```

**Guarantees**:
- ✅ Cycle-accurate execution
- ✅ Fully deterministic (virtual time combined with seeded RNG)
- ✅ Socket-based control (monitor protocol)

### 5.3 ns-3 Integration (Tier 1)

**Control Interface**:

```python
class Ns3Node:
    def __init__(self):
        # Start ns-3 with Python bindings or custom C++ interface
        self.simulator = ns3.Simulator()
        self.current_time_ns = 0

    def send_advance_command(self, target_time_us):
        target_time_ns = target_time_us * 1000
        # Schedule stop event
        ns.core.Simulator.Stop(ns.core.Time(target_time_ns))

    def wait_for_completion(self):
        # Run until stop event
        ns.core.Simulator.Run()
        # Collect events (packet deliveries, drops, latencies)
        events = self.collect_network_events()
        self.current_time_ns = target_time_ns
        return events
```

**Integration Options**:
- **Option A**: TAP/TUN devices (Renode network → Linux TAP → ns-3 TapBridge)
- **Option B**: Direct socket (custom ns-3 module, coordinator routes packets)

**Guarantees**:
- ✅ Timing-accurate (nanosecond packet timing)
- ✅ Fully deterministic (seeded discrete-event simulation)

### 5.4 Docker Integration (Tier 2, Option A)

**Control Interface**:

```python
class DockerNode:
    def __init__(self, container_name):
        self.container = start_container(container_name)
        self.message_queue = Queue()
        self.current_time_us = 0
        # Background thread collects messages
        self.start_message_collector()

    def send_advance_command(self, target_time_us):
        # Container runs continuously in background
        self.target_time_us = target_time_us

    def wait_for_completion(self):
        delta_us = self.target_time_us - self.current_time_us
        # Sleep for wall-clock equivalent (possibly time-scaled)
        time.sleep(delta_us / 1e6 / self.time_scale)
        # Collect any messages produced during interval
        events = []
        while not self.message_queue.empty():
            events.append(self.message_queue.get())
        self.current_time_us = self.target_time_us
        return events
```

**Guarantees**:
- ⚠️ Statistical reproducibility (run N trials, report mean ± confidence interval)
- ❌ Not cycle-accurate
- ✅ Deployable (real containers)

### 5.5 Python Models (Tier 2, Option B / Tier 3)

**Control Interface**:

```python
class MQTTBrokerModel:
    """Deterministic event-driven model"""
    def __init__(self):
        self.subscribers = {}
        self.pending_events = []

    def send_advance_command(self, target_time_us):
        self.target_time_us = target_time_us

    def wait_for_completion(self):
        # Process all events up to target_time
        events_to_deliver = [e for e in self.pending_events
                             if e.time <= self.target_time_us]
        self.pending_events = [e for e in self.pending_events
                               if e.time > self.target_time_us]
        return events_to_deliver

    def handle_publish(self, topic, message, sim_time_us):
        # Add events for each subscriber
        processing_delay = 1000  # 1ms deterministic delay
        for sub in self.subscribers.get(topic, []):
            self.pending_events.append(Event(
                time=sim_time_us + processing_delay,
                type="mqtt_deliver",
                dest=sub,
                data=message
            ))
```

**Guarantees**:
- ✅ Fully deterministic
- ✅ Fast execution
- ❌ Not deployable (model does not equal real service)

### 5.6 Communication Protocol

**Coordinator → Node**:

```json
{
  "command": "advance",
  "time_us": 1000,
  "events": [
    {"type": "packet", "data": "0x48656C6C6F", "dest": "device1"}
  ]
}
```

**Node → Coordinator**:

```json
{
  "time_us": 1000,
  "events": [
    {"type": "uart", "source": "device1", "data": "Temperature: 25C\n"},
    {"type": "packet_sent", "source": "device1", "dest": "gateway", "size": 128}
  ]
}
```

**Transport Options**:
- **Raw TCP sockets**: Simple, works everywhere
- **Unix domain sockets**: Faster for localhost
- **ZeroMQ**: Better pub/sub, message queuing
- **gRPC**: Structured, auto-generated bindings

**Recommendation**: Begin with raw TCP sockets, migrate to ZeroMQ if required.

---

## 7. Conservative Synchronous Lockstep Algorithm

### 7.1 Core Algorithm

```go
type Coordinator struct {
    nodes          map[string]Node
    globalTimeUs   uint64
    timeQuantumUs  uint64
    eventLog       *EventLogger
}

func NewCoordinator() *Coordinator {
    return &Coordinator{
        nodes: map[string]Node{
            "device1": NewRenodeNode("localhost", 1234),
            "network": NewNs3Node("localhost", 1235),
            "edge1":   NewDockerNode("mqtt_broker"),
            "cloud":   NewPythonMockNode(),
        },
        globalTimeUs:  0,
        timeQuantumUs: 1000, // 1ms time steps
        eventLog:      NewEventLogger(),
    }
}

func (c *Coordinator) RunSimulation(durationUs uint64) error {
    for c.globalTimeUs < durationUs {
        targetTime := c.globalTimeUs + c.timeQuantumUs

        // Phase 1: Send advance command to all nodes
        for _, node := range c.nodes {
            if err := node.SendAdvanceCommand(targetTime); err != nil {
                return fmt.Errorf("failed to send advance: %w", err)
            }
        }

        // Phase 2: Wait for all nodes to complete (using goroutines)
        allEvents := make(map[string][]Event)
        errChan := make(chan error, len(c.nodes))
        eventChan := make(chan NodeEvents, len(c.nodes))

        for name, node := range c.nodes {
            go func(nodeName string, n Node) {
                events, err := n.WaitForCompletion()
                if err != nil {
                    errChan <- err
                    return
                }
                eventChan <- NodeEvents{Name: nodeName, Events: events}
            }(name, node)
        }

        // Collect results
        for i := 0; i < len(c.nodes); i++ {
            select {
            case ne := <-eventChan:
                allEvents[ne.Name] = ne.Events
            case err := <-errChan:
                return fmt.Errorf("node execution failed: %w", err)
            }
        }

        // Phase 3: Route cross-node messages
        c.routeMessages(allEvents)

        // Phase 4: Log metrics
        c.logState(targetTime, allEvents)

        // Phase 5: Advance global time
        c.globalTimeUs = targetTime
    }
    return nil
}
```

### 7.2 Properties

**Conservative**:
- Each node never advances beyond the target time
- No node advances ahead of others

**Synchronous**:
- All nodes stay within time_quantum of each other
- Coordinator waits for all before advancing

**Deterministic (for Tier 1)**:
- Identical inputs combined with identical seed yield identical outputs
- Renode and ns-3 execute identically on each run

**Simple**:
- No optimistic algorithms
- No rollback/causality violation handling
- Easy to debug

### 7.3 Trade-offs

**Pros**:
- ✅ Simple to implement
- ✅ Deterministic for virtual-time components
- ✅ Easy to debug
- ✅ Proven approach (SimBricks, Mosaik)

**Cons**:
- ❌ Slowest component limits overall speed (Docker wall-clock represents the bottleneck)
- ❌ Coarse time quantum (1ms) may miss fine-grained events

**Mitigations**:
- Use mixed abstraction (models for bulk nodes)
- Adjust time quantum based on scenario needs
- Profile and optimize hot paths

---

## 8. Achieving Variable-Fidelity Accuracy

### 8.1 Definition of "Accuracy" Per Tier

**Device Tier (Renode)**:
- ✅ **Cycle-accurate**: Instruction-level emulation
- Each ARM instruction yields exact cycle count
- Total cycles can be counted: 1,234,567 cycles executed
- **This represents true cycle-accuracy**

**Network Tier (ns-3)**:
- ⚠️ **Timing-accurate** (not cycle-accurate)
- Nanosecond-level packet timing
- No CPU cycles (modeling network, not processors)
- Accurate for protocol behavior
- **Sufficient for network simulation**

**Edge Tier (Docker/Models)**:
- **Latency-accurate** (millisecond precision)
- Example: "MQTT broker forwarding: 2.3ms ± 0.5ms"
- Cycle-accuracy represents unnecessary overhead
- **Sufficient for service evaluation**

**Cloud Tier (Mocks)**:
- **Abstract timing** ("inference = 50ms")
- High-level latency sufficient
- **Sufficient for end-to-end experiments**

### 8.2 Variable-Fidelity Visualization

```
Abstraction          Fidelity Level
Level
   ^
   |  [Cloud Mocks]           (Abstract: ~50ms latency)
   |
   |  [Edge Containers/Models] (Latency: ~1-10ms precision)
   |
   |  [ns-3 Network]           (Timing: nanosecond precision)
   |
   |  [Renode Devices]         (Cycle: exact instruction count)
   |
   +--------------------------------------------------------→
                                                        Detail
```

**This represents a feature**: Appropriate fidelity per tier minimizes overhead while maintaining accuracy where required.

---

## 9. Decision Matrix: When to Relax Determinism

### 9.1 Scenario-Based Configuration

| Scenario | Device | Network | Edge | Cloud | Rationale |
|----------|--------|---------|------|-------|-----------|
| **Protocol debugging** | Renode (determ) | ns-3 (determ) | Model (determ) | Mock (determ) | Need exact reproducibility for bug hunting |
| **ML placement evaluation** | Renode (determ) | ns-3 (determ) | Docker (statistical) | Mock (determ) | Need real ML inference latencies |
| **Fault tolerance testing** | Renode (determ) | ns-3 (determ) | Docker (statistical) | Mock (determ) | Edge failures are inherently random |
| **Large-scale capacity planning** | Model (determ) | ns-3 (determ) | Model (determ) | Mock (determ) | Need speed over device fidelity |

### 9.2 User-Configurable Policy

**Phase 1 (M0-M2): YAML Configuration**

```yaml
determinism_policy:
  device:
    type: renode
    determinism: full
    cycle_accurate: true

  network:
    type: ns3
    determinism: full
    timing_accurate: true

  edge:
    type: docker  # or "model"
    determinism: statistical  # or "full" if using models
    trials: 10  # run 10 times, report mean ± CI

  cloud:
    type: python_mock
    determinism: full
```

**User Choice**:
- For determinism: Use models for edge tier
- For realism: Use Docker, accept variance
- For both: Use Docker for development, models for regression testing

### 9.3 Concrete Example: Message Flow with Hybrid Determinism

**Scenario**: Device sends MQTT message → Edge broker → Cloud

```
T=0μs:
  Device (Renode): Publishes MQTT "temp=25C"
  [DETERMINISTIC]

Coordinator: Routes packet Renode → ns-3

T=1μs:
  Network (ns-3): Simulates 802.15.4 transmission
  Packet delay: 5ms (deterministic)
  [DETERMINISTIC]

Coordinator: Packet arrives at edge at T=5000μs

T=5000μs:
  Edge (Docker MQTT broker): Receives message
  Processes in wall-clock time
  Forwards to cloud subscriber
  Measured latency: 2.3ms ± 0.5ms
  [STATISTICAL - varies between runs]

Coordinator: Routes to cloud at T=7300μs (± 500μs)

T=7300μs:
  Cloud (Python mock): Receives message
  Simulated processing: 50ms (deterministic)
  Response scheduled for T=57300μs
  [DETERMINISTIC]

... reverse path ...
```

**Result**: End-to-end latency equals 57.3ms ± 0.5ms
- Deterministic components: Device (0μs), Network (5ms), Cloud (50ms)
- Non-deterministic component: Edge processing (2.3ms ± 0.5ms)

---

## 10. Validation and Comparison to Existing Systems

### 10.1 SimBricks: Architectural Validation

**SimBricks** (OSDI 2022) uses the same federated approach for datacenter systems:
- QEMU/gem5 hosts + ns-3 network
- Socket-based time synchronization
- Conservative synchronous lockstep
- **Proves this architecture works at scale**

**xEdgeSim vs SimBricks**:

| Aspect | SimBricks | xEdgeSim |
|--------|----------|----------|
| **Domain** | Datacenter (servers, NICs, network) | IoT-edge-cloud (MCUs, containers, network) |
| **Device** | Full-system VMs (QEMU/gem5) | MCU emulation (Renode) |
| **Edge** | Not applicable | Docker containers + models |
| **Focus** | Network performance | ML placement, cross-tier optimization |
| **Determinism** | Full (all virtual time) | Hybrid (virtual + statistical) |

**Lesson**: SimBricks validates socket-based co-simulation. xEdgeSim adapts it to IoT with hybrid determinism.

### 10.2 Comparison to Monolithic Simulators

| Aspect | COOJA | iFogSim/EdgeCloudSim | xEdgeSim |
|--------|-------|---------------------|----------|
| **Architecture** | Monolithic Java | Monolithic Java (CloudSim) | Federated |
| **Device fidelity** | Instruction-level (MSP430) | Abstract tasks | Instruction-level (ARM) |
| **Network fidelity** | Simple radio models | Latency + bandwidth | Packet-level (ns-3) |
| **Edge fidelity** | None | Abstract compute | Real containers OR models |
| **Deployability** | Firmware only | None | Firmware + containers |
| **Determinism** | Full | Full (abstract) | Hybrid (realistic) |
| **Scalability** | 50-100 nodes | 1000s (abstract) | 10-50 emulated + 1000s modeled |

### 10.3 Co-Simulation Framework Comparisons

| Framework | Domain | Key Lesson for xEdgeSim |
|-----------|--------|------------------------|
| **SimBricks** | Datacenter | Socket-based coordination works, time sync is feasible |
| **FMI** | Automotive | Standard co-simulation interface enables tool composition |
| **HLA** | Defense | Federated simulation scales to large distributed systems |
| **Mosaik** | Smart grids | Lightweight Python coordinator is sufficient |
| **ns-3 DCE** | Network + apps | Time dilation is complex; avoid syscall interception |

---

## 11. Implementation Roadmap

### M0: Proof-of-Concept (Coordinator + Renode)

**Goals**:
- Validate socket-based control of Renode
- Implement basic time stepping
- Firmware prints to UART, coordinator logs

**Deliverables**:
- Python coordinator (200 lines)
- Renode integration class
- Simple firmware (blinky LED + UART)
- End-to-end test: "advance 1s, collect UART output"

---

### M1: Add ns-3 Integration

**Goals**:
- Coordinator controls Renode + ns-3
- Packets flow: Device → ns-3 → Destination

**Deliverables**:
- ns-3 integration class
- TAP/TUN or socket-based packet routing
- Test: "Device sends UDP packet via 802.15.4 → Gateway"

---

### M2: Add Docker Edge Services

**Goals**:
- ns-3 bridges to Docker network
- Edge containers receive packets
- End-to-end packet flow

**Deliverables**:
- Docker integration class
- MQTT broker container
- Test: "Device → ns-3 → MQTT broker → Cloud mock"

---

### M3: Add Metrics and ML

**Goals**:
- Coordinator logs cross-tier metrics
- Add ML inference services
- Generate latency/energy CDFs

**Deliverables**:
- Metrics collection framework
- ONNXRuntime or TFLite integration
- Test: "Measure E2E latency for ML placement variants"

---

### M4: Fault Injection and Scenarios

**Goals**:
- Coordinator injects faults (packet drops, delays, Byzantine edge)
- YAML-based scenario configs
- Batch experiment runner

**Deliverables**:
- Fault injection API
- YAML scenario parser
- Batch runner with statistical aggregation

---

## 12. Risks and Mitigations

### Risk 1: Socket Latency Overhead

**Risk**: Socket calls add overhead that slows simulation.

**Analysis**:
- Socket call: ~1-10 μs on localhost
- Time quantum: 1 ms = 1000 μs
- Overhead: ~1% per time step

**Mitigation**:
- Use Unix domain sockets (faster than TCP)
- Batch events to reduce socket calls
- Profile and optimize hot paths

---

### Risk 2: Time Synchronization Complexity

**Risk**: Conservative lockstep is too simplistic for complex scenarios.

**Analysis**:
- Conservative lockstep is simple and proven (SimBricks, Mosaik)
- No need for optimistic algorithms initially

**Mitigation**:
- Start with 1ms time quantum
- Refine if needed (e.g., 100μs for timing-critical scenarios)
- Consider optimistic algorithms only if conservative proves insufficient

---

### Risk 3: Renode Performance Bottleneck

**Risk**: Instruction-level emulation is too slow for large-scale scenarios.

**Analysis**:
- Renode can run real-time or faster for simple firmware
- Bottleneck: Complex firmware with many peripherals

**Mitigation**:
- Use **mixed abstraction levels** (like COOJA does)
  - Renode for 10-50 critical nodes
  - Python models for 1000s of bulk nodes
- Profile and optimize firmware hot paths

---

### Risk 4: Docker Non-Determinism Breaks Reproducibility

**Risk**: Edge container variance makes experiments irreproducible.

**Analysis**:
- Accurate assessment, but real edge deployments exhibit variance
- Statistical results (mean ± confidence interval) are scientifically acceptable
- Models can be used for regression testing

**Mitigation**:
- Run N trials (N=10-30), report distributions
- Provide both Docker (realism) and model (determinism) options
- Clearly document determinism guarantees per tier

---

### Risk 5: Integration Complexity

**Risk**: Coordinating 4 different technologies (Renode, ns-3, Docker, coordinator language) is too complex.

**Analysis**:
- Each component has a clean socket interface
- Coordinator is the only component that knows about all others
- Proven by SimBricks

**Mitigation**:
- Start simple (M0: Coordinator + 1 Renode)
- Add components incrementally (M1: +ns-3, M2: +Docker)
- Extensive testing at each milestone
- Clear documentation and examples

---

## 13. Recommendations

### 13.1 For M0-M2 (MVP)

1. **Choose coordinator language during M0**
   - Both Go and Python are viable candidates
   - Go: Better concurrency, performance, static typing, single binary
   - Python: Rapid prototyping, accessibility, easier for researchers to modify
   - Decision should be based on team expertise and project priorities
   - Socket-based protocol enables switching languages later if needed

2. **Implement hybrid determinism from the start**
   - Renode + ns-3: Fully deterministic
   - Edge: Provide both Docker and model options
   - Cloud: Python mocks (deterministic)

3. **Start with conservative lockstep**
   - 1ms time quantum
   - Simple, proven
   - Refine later if needed

4. **Use TCP sockets initially**
   - Simple, works everywhere
   - Migrate to Unix domain sockets or ZeroMQ if overhead is measurable

5. **Provide clear YAML configuration**
   - Users choose determinism vs realism
   - Easy to switch between Docker and models

### 13.2 For M3+ (Production)

1. **Optimize coordinator performance**
   - Profile socket communication hot paths
   - Consider connection pooling for high-scale scenarios
   - Evaluate Unix domain sockets vs TCP for localhost
   - Optimize message serialization/deserialization
   - If Python was chosen initially, consider migration to Go for performance-critical deployments

2. **Add optional time dilation**
   - Lightweight LD_PRELOAD approach
   - Only for critical use cases
   - Make it opt-in, not default

3. **Implement mixed abstraction levels**
   - Renode for critical devices
   - Python models for bulk devices
   - User-configurable per device in YAML

4. **Enhance metrics framework**
   - Cross-tier instrumentation
   - Energy, latency, accuracy tracking
   - Pareto frontier generation

### 13.3 Architectural Principles to Maintain

1. **Modularity**: Each component is replaceable
   - Renode can be swapped with QEMU
   - ns-3 can be swapped with OMNeT++
   - Docker can be swapped with Fogify

2. **Deployability**: Artifacts tested in simulation deploy to production
   - ARM firmware → real hardware
   - Docker containers → real gateways

3. **Explicitness**: Clear guarantees per tier
   - Document determinism levels
   - Document accuracy levels
   - No hidden assumptions

4. **User choice**: Flexibility over dogma
   - Provide Docker AND models
   - Let users choose fidelity vs speed
   - Support multiple use cases

---


---

## Next Steps: Feature Implementation

This document covers the core architectural principles of xEdgeSim. For detailed implementation guidance on specific features and integrations, see **`docs/implementation-guide.md`**, which covers:

- **ML Placement Framework** (M3): How to implement device/edge/cloud ML inference placement with trade-off evaluation
- **Scenario Specification** (M0-M1): From hardcoded configs to YAML-based scenario definitions
- **Metrics Collection** (M0-M1): CSV-based metrics, structured collection, and cross-tier analysis
- **ns-3 Integration** (M1): Packet-level network simulation integration details
- **Docker Integration** (M2): Container orchestration and TAP/TUN networking
- **Deployability** (M2-M4): Firmware and container deployment pipelines
- **CI/CD** (M2-M4): Automated testing and validation workflows
- **Scalability** (M3-M4): Mixed abstraction strategies for large-scale simulations

Each feature in the implementation guide is tagged with its target milestone (M0-M4) to support phased complexity growth.
