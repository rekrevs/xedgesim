# xEdgeSim Vision

## Problem context

Modern IoT systems rarely stop at low-power wireless sensor nodes. They typically span:

- Constrained MCU-based devices running real-time OSes (Zephyr, FreeRTOS, RIOT, etc.).
- Edge gateways running Linux, containers, and orchestration tooling.
- Wide-area connectivity over Wi-Fi, cellular, or wired networks.
- Cloud services (storage, analytics, dashboards, and ML pipelines).

Today, developers and researchers often have to choose between:

- **Device-level realism** (MCU emulation, full OS stacks) with poor scalability and limited network/cloud realism.
- **High-level network or edge simulators** with abstracted devices and synthetic workloads.
- **Ad-hoc testbeds** that are costly to build, hard to reproduce, and difficult to integrate into CI/CD.

We want a tool that can bridge these levels in a controlled, repeatable way.

## High-level goals

xEdgeSim aims to provide a cross-level simulator for IoT–edge–cloud systems with the following properties:

1. **Deployable artefacts at multiple levels**
   - The same firmware image that runs in the simulator should be deployable on real MCU hardware.
   - The same container images used at the edge in the simulator should be deployable on real gateways.

2. **Cross-level co-simulation**
   - Device, network, edge, and cloud components should be able to participate in the same simulation run.
   - Different abstraction levels can be mixed:
     - some devices as full MCU emulations,
     - others as logical or traffic-generating models,
     - some edge services as real containers,
     - others as simple mocks.

3. **Experimentation with ML placement and offloading**
   - Built-in support for placing ML inference on device, edge, or cloud.
   - Ability to express and test policies for offloading (e.g. based on latency, energy, or load).

4. **Performance, energy, and reliability insight**
   - Measurement of latency, throughput, resource use, and (approximate) energy consumption across the stack.
   - Fault injection facilities for network partitions, link degradation, and node compromises.

5. **CI/CD-friendly workflow**
   - Scenarios expressed as configuration files.
   - Simulations runnable from the command line and suitable for automated regression testing.

## Initial scope and non-goals

Initial scope:

- Support one MCU platform (e.g. a Cortex-M or RISC-V dev board) via an existing emulator.
- Integrate with ns-3 or a similar network simulator to model wireless and IP-level effects.
- Run basic edge services as containers (e.g. MQTT broker, aggregator, simple ML inference service).
- Focus on one primary scenario: vibration-based condition monitoring in a factory setting.

Explicit non-goals for early stages:

- Full generality across all IoT protocols and hardware.
- Extremely precise energy modelling or real-time guarantees.
- Sophisticated cloud orchestration (a simple model is sufficient to start).

## Planned phases

- **P0 – Foundations & tooling:** Repo structure, basic scripts, initial docs (this file).
- **P1 – Related work & gap analysis:** Systematic survey of existing simulators and co-sim frameworks.
- **P2 – Architecture design:** Detailed design of components, interfaces, and time synchronisation.
- **P3 – Implementation milestones:**
  - M0 – Single-device MCU emulation sending packets over a simple link.
  - M1 – Integration with a network simulator.
  - M2 – Edge containers and basic data flow.
  - M3 – Cloud mock and ML placement.
  - M4 – Security and fault injection hooks.
- **P4 – Evaluation harness:** Scenario configuration, batch runner, metrics collection and analysis.
- **P5 – Publication and packaging:** Paper, documentation, examples, and open-source release.

This document should be updated as the project evolves.
