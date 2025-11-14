# xEdgeSim Vision

## Problem Context

Modern IoT systems span multiple tiers with fundamentally different characteristics:

- **Device tier**: Constrained MCU-based devices running real-time OSes (Zephyr, FreeRTOS, RIOT) with strict timing, energy, and resource constraints
- **Network tier**: Heterogeneous connectivity over Wi-Fi, Zigbee, LoRa, cellular, or wired networks with varying latency, bandwidth, and reliability
- **Edge tier**: Linux gateways running containers, providing local processing, aggregation, and ML inference
- **Cloud tier**: Remote services providing storage, analytics, dashboards, and compute-intensive ML pipelines

### The Abstraction Level Mismatch Problem

Existing simulation and emulation tools fall into one of two extremes:

**Device-accurate but single-tier:**
- Tools like Renode, QEMU, and gem5 provide instruction-level emulation for devices
- Excellent for firmware validation and protocol debugging
- But: No realistic network simulation, no edge/cloud tier support

**Multi-tier but abstract:**
- Tools like iFogSim, EdgeCloudSim, and PureEdgeSim model device-edge-cloud systems
- Useful for resource allocation and policy evaluation
- But: Use abstract task generators instead of real firmware, simplified network models, no deployable artifacts

**The fundamental gap:** No existing tool provides appropriate fidelity at each tier simultaneously. Each tier requires different abstraction levels for accurate modeling:
- Device tier needs instruction-level emulation → tools exist (Renode, QEMU)
- Network tier needs packet-level simulation → tools exist (ns-3, OMNeT++)
- Edge tier needs application-level containers → partial tools (Fogify, but no network simulation)
- Cloud tier needs abstract models → tools exist but too simplistic

**Developers and researchers are forced to choose:**
- Device-level realism with poor scalability and no edge/cloud modeling
- High-level multi-tier simulators with abstract, non-deployable workloads
- Ad-hoc testbeds that are costly, non-reproducible, and unsuitable for CI/CD

**xEdgeSim addresses this gap** by combining appropriate fidelity at each tier in a single, federated co-simulation platform.

## What is xEdgeSim?

xEdgeSim is a **variable-fidelity cross-tier co-simulation platform** for IoT-edge-cloud systems that combines:

- **Instruction-level device emulation** (Renode for ARM/RISC-V firmware)
- **Packet-level network simulation** (ns-3 for wireless and IP protocols)
- **Application-level edge services** (Docker containers or deterministic models)
- **Abstract cloud models** (Python mocks for remote services)

All coordinated via a **federated, socket-based architecture** with **tiered determinism**.

### Key Architectural Differentiators

**1. Federated Co-Simulation**
- Lightweight Go coordinator communicates with heterogeneous backend processes via sockets
- Language-agnostic JSON protocol enables backends in any language
- Conservative synchronous lockstep algorithm for time coordination
- Validated approach: SimBricks (OSDI 2022) demonstrates this architecture works for datacenter systems

**2. Tiered Determinism**
- **Tier 1 (Device/Network)**: Fully deterministic, cycle/timing-accurate (Renode + ns-3)
  - Enables firmware debugging and protocol validation
- **Tier 2 (Edge)**: Statistical reproducibility (Docker) OR deterministic models (user choice)
  - Balances deployment realism with debugging needs
- **Tier 3 (Cloud)**: Deterministic abstract models (Python mocks)
  - Sufficient fidelity for high-level behavior

**3. Variable Fidelity**
- Appropriate abstraction per tier (not uniform across all components)
- Mixed abstraction levels within tiers (full emulation + lightweight models, like COOJA)
- Scalability without sacrificing critical fidelity

**4. Deployable Artifacts** (Hard Constraint)
- ARM/RISC-V firmware runs in Renode **AND** on real hardware
- Docker containers run in simulation **AND** on real gateways
- This is not optional—it is an architectural requirement
- Enables sim-to-prod workflow: validate in simulation, deploy to production

**5. ML Placement as First-Class Research Concern**
- Device inference: TFLite models on ARM (quantized INT8, 10-100KB)
- Edge inference: ONNX models in Docker containers (FP16/INT8, 1-10MB)
- Cloud inference: PyTorch models in Python services (FP32, 10-100MB)
- Accuracy-latency-energy trade-off analysis across all placement options
- Pareto frontier generation for multi-objective optimization
- Policy evaluation framework for offloading decisions
- **No other tool combines device/edge/cloud simulation with ML inference placement**

**6. Protocol-Based Extensibility**
- Public protocol specification enables external backend development
- Backends can be written in any language (Go, Python, C++, Rust)
- Clean separation: coordinator coordinates time, backends handle domain-specific simulation

## High-Level Goals

xEdgeSim aims to provide a cross-tier co-simulation platform for IoT-edge-cloud systems with the following properties:

### 1. ML Placement Experimentation (Primary Research Focus)

**The "Killer App"**: No other tool enables realistic ML inference placement evaluation across device-edge-cloud tiers.

**Device inference:**
- Run actual TFLite models on ARM firmware in Renode
- Measure cycles, energy, and accuracy for quantized models (INT8, 10-100KB)
- Validate on-device inference feasibility and resource consumption

**Edge inference:**
- Run ONNX models in Docker containers (or deterministic models)
- Measure processing latency, throughput, and server resource utilization
- Evaluate local inference for privacy and low-latency requirements

**Cloud inference:**
- Run PyTorch models in Python services with simulated WAN latency
- Model high-accuracy, compute-intensive inference
- Evaluate cost-latency trade-offs for remote processing

**Trade-off analysis:**
- Accuracy-latency-energy Pareto frontiers
- Policy evaluation: static placement, dynamic offloading, hybrid/split inference
- Sensitivity analysis: network conditions, load, device heterogeneity
- Multi-objective optimization for real-world constraints

### 2. Deployable Artifacts (Architectural Requirement)

**Firmware deployability:**
- ARM/RISC-V binaries compiled for target MCU architecture
- Run in Renode for validation, deploy to real hardware for production
- Same binary, same behavior (validated through testing)

**Container deployability:**
- Docker containers with real application code and ML models
- Run in simulation for evaluation, deploy to real gateways unchanged
- Enables sim-to-prod workflow with confidence

**Value proposition:**
- Simulation results reflect real system behavior (not abstract models)
- Reduces sim-to-reality gap that plagues abstract simulators
- Accelerates development: test cheaply in simulation, deploy confidently to production

### 3. Cross-Tier Co-Simulation

**Heterogeneous component integration:**
- Device tier: Renode (MCU emulation) + models (scalability)
- Network tier: ns-3 (packet-level simulation)
- Edge tier: Docker (containers) + models (determinism)
- Cloud tier: Python mocks (abstract services)

**Mixed abstraction levels:**
- Some devices as full MCU emulations (critical nodes requiring timing accuracy)
- Others as lightweight models (bulk devices for scalability)
- Some edge services as real containers (deployment validation)
- Others as deterministic models (debugging and reproducibility)

**Coherent time domain:**
- All components advance in synchronized virtual time
- Conservative synchronous lockstep ensures causal consistency
- Deterministic execution where required (devices, network)
- Statistical reproducibility where acceptable (containers)

### 4. Cross-Tier Instrumentation and Metrics

**End-to-end measurement:**
- Device: Energy (μJ per inference, radio TX/RX), CPU cycles, memory usage
- Network: Latency (per-hop, end-to-end), packet loss, throughput, jitter
- Edge: Processing latency, resource utilization (CPU, memory, GPU), queue depths
- Cloud: Response time, cost modeling, carbon footprint

**Cross-tier metrics:**
- Total end-to-end latency (sensor sample → result delivery)
- Energy breakdown (device computation + communication + edge processing)
- Accuracy degradation due to quantization, network errors, or failures
- Cost analysis (device energy × battery life + cloud compute costs)

**Fault injection:**
- Network partitions, link degradation, packet loss
- Device failures, battery depletion
- Edge node compromises (Byzantine behavior)
- Cloud unavailability or degraded performance

### 5. Scenario-Driven Reproducible Experiments

**Configuration-as-code:**
- Scenarios defined in YAML (topology, firmware, containers, ML models, policies)
- Version-controlled, shareable, and reviewable
- JSON schema validation for correctness

**Reproducibility:**
- Deterministic execution with fixed random seeds
- Same input → same output (for deterministic tiers)
- Statistical reproducibility for container-based experiments (N trials, mean ± CI)

**CI/CD integration:**
- Command-line execution: `xedgesim run scenario.yaml --seed 42`
- Automated regression testing in GitHub Actions
- Batch experiments for parameter sweeps
- Result validation and comparison tools

### 6. Research and Development Workflow

**Iterative development:**
- Test firmware in simulation (fast, cheap, deterministic)
- Validate algorithms under controlled conditions (fault injection, parameter sweeps)
- Measure trade-offs (ML placement, offloading policies)
- Deploy to real hardware with confidence (same binaries, same containers)

**Open science:**
- Reproducible experiments (YAML configs + fixed seeds)
- Shareable scenarios (Git repositories)
- Transparent evaluation (metrics, logs, traces)
- Extensible platform (custom backends via public protocol)

## Validation and Prior Art

xEdgeSim's architectural approach is grounded in validated prior work:

**SimBricks (OSDI 2022)** validates federated socket-based co-simulation:
- Demonstrates that heterogeneous components (QEMU/gem5 hosts + ns-3 network) can be coordinated via sockets
- Conservative synchronous lockstep algorithm works at scale
- xEdgeSim adapts this proven approach from datacenter systems to IoT-edge-cloud domains

**COOJA** provides patterns for determinism and mixed abstraction:
- Deterministic event queue with (time, UUID) ordering
- Mixed abstraction levels (instruction-level MSPMote + native ContikiMote + Java motes)
- Headless execution and reproducibility for CI/CD
- Plugin system for extensibility
- xEdgeSim adopts these strengths while avoiding COOJA's monolithic architecture

**ns-3 DCE** teaches important lessons:
- Time dilation (syscall interception) is complex and fragile
- Maintenance burden is high (must track kernel changes, VDSO bypass issues)
- xEdgeSim avoids time dilation, instead using statistical reproducibility for containers

**Co-simulation frameworks** (FMI, HLA, Mosaik) inform protocol design:
- Clean separation between coordinator and simulators
- Well-defined interfaces enable tool composition
- Time synchronization as core concern
- xEdgeSim builds on these established patterns

## Initial Scope and Non-Goals

### Initial Scope

**Platform support:**
- One MCU platform (ARM Cortex-M or RISC-V dev board) via Renode
- Zephyr or FreeRTOS as primary RTOS targets
- One network simulator (ns-3) for wireless and IP-level modeling
- Docker containers for edge services (MQTT broker, aggregation, ML inference)

**Primary scenario:**
- Vibration-based condition monitoring in a factory setting
- 10-50 MCU-based sensors
- Edge gateway with MQTT broker and ML inference
- Cloud service for data storage and heavy processing
- ML placement variants: device-only, edge-only, cloud-only, hybrid

**Metrics:**
- Device energy (approximate, based on Renode power models)
- Network latency and loss (ns-3 statistics)
- Edge processing time (measured from containers or models)
- End-to-end latency and accuracy

### Explicit Non-Goals

**What xEdgeSim will NOT do:**

**Not replacing specialized tools:**
- Will use Renode (not reimplement MCU emulation)
- Will use ns-3 (not reimplement PHY/MAC protocols)
- Focus on integration and coordination, not reinventing components

**Not implementing time dilation:**
- Learned from ns-3 DCE: syscall interception is fragile and high-maintenance
- Accept statistical reproducibility for containers instead
- Provide deterministic models as alternative to Docker when determinism is required

**Not supporting all RTOSes initially:**
- Focus on Zephyr and FreeRTOS (widely used, ARM/RISC-V support)
- Not Contiki-NG (COOJA already serves this niche)
- Extensible to other RTOSes, but not initial priority

**Not GUI-first:**
- Headless, CLI-first design for automation and CI/CD
- Optional web dashboard may be added later (M4+)
- Inspired by COOJA's headless mode, not its Swing GUI

**Not targeting extreme precision:**
- Approximate energy modeling (sufficient for relative comparisons)
- No hard real-time guarantees
- Focus on system-level behavior, not cycle-exact hardware verification

**Not full cloud orchestration:**
- Simple abstract cloud models (latency, throughput, cost)
- Not simulating Kubernetes, service meshes, or distributed cloud infrastructure
- Sufficient for evaluating cloud as an inference placement option

**Not full generality from day one:**
- Start with vibration monitoring scenario
- Expand to other scenarios incrementally
- Generality emerges from validating diverse use cases, not premature abstraction

## Implementation Roadmap

### Development Phases (P0-P5)

**P0 – Foundations & Tooling** (Current)
- Repository structure established
- Initial documentation (vision, architecture, design)
- Related work analysis and gap identification
- Go module initialization

**P1 – Related Work & Gap Analysis** (Complete)
- Systematic survey of existing simulators (see `docs/related-work-notes.md`)
- Gap analysis: variable-fidelity cross-tier co-simulation
- COOJA deep-dive: patterns to adopt and avoid
- SimBricks validation of federated architecture

**P2 – Architecture Design** (Complete)
- Federated co-simulation architecture (see `docs/architecture.md`)
- Tiered determinism strategy
- Protocol specification (`docs/api/protocol.md` - to be written)
- Directory structure and Go implementation plan (see `docs/design.md`)

**P3 – Implementation Milestones** (M0-M4)

Detailed below with specific scope, LOC targets, and timelines.

**P4 – Evaluation Harness**
- Scenario configuration framework (YAML schema)
- Batch experiment runner
- Metrics collection and analysis tools (Python)
- Result validation and comparison
- Automated testing and CI/CD integration

**P5 – Publication and Packaging**
- Research paper (conference/journal submission)
- Comprehensive documentation
- Example scenarios and tutorials
- Open-source release (GitHub)
- Community engagement and dissemination

### Implementation Milestones (M0-M4)

Iterative complexity growth: "Make It Work, Make It Right, Make It Fast"

#### M0: Minimal Proof-of-Concept (2 weeks, ~450 LOC Go)

**Goal:** Prove socket-based co-simulation works

**Scope:**
- Go coordinator (~200 lines): conservative synchronous lockstep algorithm
- Renode adapter (~100 lines): socket-based control of Renode via monitor protocol
- Python edge model (~100 lines): simple deterministic processing model
- Device firmware (~50 lines): minimal sensor simulation (C for ARM)
- Analysis script (~50 lines): post-process CSV metrics

**Explicitly excludes:**
- ns-3 integration (use direct sockets instead)
- Docker containers (use Python models instead)
- YAML parsing (hardcoded configuration)
- ML placement (not relevant yet)
- Plugin system (defer to M2)

**Success criteria:**
- Renode and Python process time-synchronized via coordinator
- Deterministic execution validated (same seed → same output)
- CSV metrics collected and analyzed
- End-to-end latency measured

#### M1: Add Network Realism (4 weeks)

**Goal:** Integrate ns-3 for packet-level network simulation

**Additions:**
- ns-3 backend adapter (Go implementation)
- YAML scenario parser (simple schema)
- Structured metrics collection
- Event queue with deterministic ordering (COOJA-style)
- Protocol message types formalized

**Success criteria:**
- Device → ns-3 → Edge packet flow working
- YAML scenario configuration functional
- Multiple network types supported (WiFi, Zigbee, LoRa)
- Cross-tier latency breakdown measured

#### M2: Add Edge Realism (4 weeks)

**Goal:** Integrate Docker containers for edge services

**Additions:**
- Docker backend adapter (Go implementation)
- TAP/TUN networking (ns-3 ↔ Docker)
- Plugin system architecture
- Scenario management framework
- Python analysis tools (metrics post-processing)

**Success criteria:**
- Real MQTT broker in Docker container
- ns-3 bridges to Docker network
- Containers and models both supported (user choice)
- Deployability documented and validated

#### M3: Add Research Value (6 weeks)

**Goal:** ML placement framework (the "killer app")

**Additions:**
- ML placement plugin (Go coordinator plugin)
- TFLite integration for device inference
- ONNX Runtime integration for edge inference
- PyTorch integration for cloud inference
- Pareto frontier analysis tools (Python)
- Policy evaluation framework
- Cloud tier integration

**Success criteria:**
- All three placement options functional (device, edge, cloud)
- Accuracy-latency-energy metrics collected
- Pareto frontiers generated
- Policy comparison working
- Research paper draft in progress

#### M4: Production Polish (6 weeks)

**Goal:** Production-ready platform

**Additions:**
- CI/CD automation (GitHub Actions)
- Performance optimization
- Scalability improvements (mixed abstraction levels)
- Fault injection framework
- Comprehensive documentation
- Result validation framework
- Example scenarios beyond vibration monitoring

**Success criteria:**
- Automated testing on every commit
- Scalability validated (10 emulated + 1000 modeled devices)
- Fault injection working
- Documentation complete
- Ready for open-source release

### Technology Stack

**Coordinator:** Go (main implementation)
- Excellent concurrency (goroutines for managing backend sockets)
- Static typing and compile-time checks
- Single binary distribution
- Strong standard library

**Backends:**
- Renode (C#): MCU emulation, existing tool
- ns-3 (C++): Network simulation, existing tool
- Docker: Container runtime, existing tool
- Python: Edge/cloud models when determinism required

**Analysis:** Python
- pandas, numpy, matplotlib for metrics processing
- Pareto frontier computation
- Visualization and reporting

**Configuration:** YAML
- Human-readable scenario definitions
- JSON schema validation

**Protocol:** JSON over TCP sockets
- Language-agnostic
- Simple, widely supported
- Easy to debug and inspect

This roadmap reflects an iterative, validated approach to building xEdgeSim as a research platform for cross-tier IoT-edge-cloud co-simulation with ML placement as the primary research contribution.
