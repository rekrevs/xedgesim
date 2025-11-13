# Related Work Notes for xEdgeSim

This document is a working space for surveying and comparing existing tools and frameworks relevant to xEdgeSim.

The aim is to map out:

- Wireless sensor network simulators and emulators (e.g. COOJA/Contiki).
- Embedded / MCU emulators used for systems research (e.g. Renode, QEMU-based setups).
- IoT and edge/fog simulators (e.g. iFogSim, EdgeCloudSim, PureEdgeSim, LEAF, EdgeAISim).
- Network simulators and co-simulation middleware (e.g. ns-3, OMNeT++, SimBricks, ns-3 co-sim libraries).
- IoT- and container-focused emulation frameworks (e.g. IoTNetEMU).

## Table of candidate systems

| Name | Year | Focus (Device/Edge/Cloud) | Device realism (MCU/RTOS/binary) | Network modelling | Edge/cloud realism | ML support | Co-sim capabilities | CI/CD integration | Notes / Gaps vs xEdgeSim |
|------|------|---------------------------|----------------------------------|-------------------|--------------------|-----------|--------------------|-------------------|--------------------------|
| COOJA/Contiki | ≈2003 | Device (WSN) | Emulates wireless-sensor motes; supports real radio chips such as TR 1100 and TI CC2420 | Constant/distance loss UDGM, DGRM and Ray-tracer propagation models | None | None | None | | No edge/cloud, no ML |
| Renode | ≈2015 | Device | High – deterministic multi-node simulation of MCU/SoC systems; binary-level emulation with rich model abstractions | Limited – basic link abstractions; no built-in network simulator | None | None | Can integrate with external simulators; supports CI scenarios | Good CI support | No network sim, no edge/cloud, no ML |
| QEMU | ≈2003 | Device | High – generic machine emulator/virtualizer able to run full operating systems and user-mode binaries | Minimal – generic virtual network devices; no network simulation | None | None | None | | General-purpose emulator, not simulation-focused |
| gem5 | 2011 | Device | High – multiple CPU models, event-driven memory system and full-system simulation across several ISAs | None (focuses on processor/memory system) | None | None | Co-sim with SystemC | | Processor/memory focus, no network or edge/cloud |
| iFogSim | 2017 | Edge/Fog | Low – models sensors, actuators and FogDevice objects representing distributed resources | Moderate – allows modelling of network latency and topology but not packet-level simulation | Models hierarchical edge/cloud resources and energy consumption | None | None | | High-level only, no binary execution |
| EdgeCloudSim | 2017 | Edge | Low – high-level simulation of tasks and resources | Modules for WLAN/WAN networks, device mobility and load generation | Moderate – simulates edge and cloud servers | None | None | | Abstract tasks, no firmware/containers |
| PureEdgeSim | 2018 | Edge/Cloud/Mist | Low – simulates datacenters and servers via analytical models | Network module allocates bandwidth and models transfers | Moderate – realistic infrastructure models across edge–cloud continuum | None | None | | Analytical models, not deployable artifacts |
| LEAF | 2022 | Fog/Energy | Low – models compute nodes abstractly | Models dynamic networks using NetworkX and SimPy | Models energy consumption for compute nodes and network traffic | None | None | | Energy focus, abstract models |
| EdgeAISim | 2023 | Edge | Low – high-level simulation built on EdgeSimPy | Models network flows and mobility | Moderate – includes task scheduling, service migration and energy management | Strong – uses multi-armed bandit, DQN, graph neural networks and actor–critic models for resource management | None | | ML support but abstract device models |
| ns-3 | 2008 | Network | None – focuses on network behaviour | Strong – detailed models for wireless and wired protocols (Wi-Fi, WiMAX, LTE) and real-time network emulation | None | None | Supports co-simulation with real systems; can act as interconnection framework | | Network-only, no device or edge/cloud |
| OMNeT++ | ≈2001 | Network | None | Modular component-based simulation with domain-specific frameworks (INET, Simu5G) | None | None | Extensible with real-time integration, network emulation, database integration via SystemC | | Network simulation framework |
| SimBricks | 2021 | Network & Host | High – combines QEMU/gem5 hosts and Verilator-based NICs | Integrates ns-3 or Tofino simulators to model network behaviour | None | None | Strong – co-sim between host and network simulators with time synchronization | | Promising co-sim approach but no edge/cloud |
| IoTNetEMU | 2023 | IoT & Container | Moderate – emulates IoT devices using Docker containers | Simple configurable network of emulated devices | Connects to containerised applications | None | None | | Container-based but no packet-level simulation |
| ELIoT | 2024 | IoT & Container | Moderate – each Docker container represents an IoT device with its own network interface | No packet-level simulation; containers form a virtual network | None (focused on emulating large numbers of devices) | None | None | | Scalable container emulation but no network simulation |

## Gap Analysis

Existing simulators fall into one of two extremes: **hardware-accurate device emulators** (Renode, QEMU, gem5) or **high-level edge/fog/network models** (iFogSim, EdgeCloudSim, PureEdgeSim, LEAF, EdgeAISim, ns-3, OMNeT++, SimBricks). Device emulators provide binary-level fidelity but have little or no network and edge/cloud modelling, while high-level simulators model resource allocation and communication but cannot execute real firmware or container images.

### Key gaps that xEdgeSim aims to fill:

1. **Cross-level integration**: None of the surveyed systems simultaneously emulate microcontroller firmware, simulate realistic networks and run containerised edge/cloud services. xEdgeSim will integrate device emulators with ns-3 and Docker to produce end-to-end scenarios.

2. **Deployable artefacts**: Existing fog/edge simulators use abstract tasks rather than deployable firmware and containers. xEdgeSim will run actual MCU binaries and container images, producing results that better reflect real deployments.

3. **ML placement experiments**: None of the surveyed tools combine device/edge/cloud simulation with machine-learning offloading and placement decisions. xEdgeSim will support ML models (e.g. via ONNX Runtime) and evaluate where inference should run.

4. **CI/CD friendliness**: Renode has good CI support but other frameworks lack automated testing workflows. xEdgeSim will package scenarios as reproducible scripts and integrate with continuous integration pipelines to encourage open, automated experimentation.

5. **Edge/cloud realism with time synchronisation**: Many tools ignore time synchronisation between device emulators and network simulators. xEdgeSim will enforce a coherent simulated time across device, network and edge/cloud layers, enabling accurate latency and energy evaluations.

These capabilities will make xEdgeSim a unique cross-level simulator for IoT–edge–cloud systems in 2025.

## References

1. Renode: https://renode.io/
2. Renode Features: https://renode.io/#features
3. QEMU: https://www.qemu.org/
4. gem5: https://www.gem5.org/about/
5. iFogSim2.pdf: https://clouds.cis.unimelb.edu.au/papers/iFogSim2.pdf
6. EdgeCloudSim: https://github.com/purdue-dcsl/EdgeCloudSim
7. PureEdgeSim: https://github.com/CharafeddineMechalikh/PureEdgeSim
8. LEAF: https://leaf.readthedocs.io/en/latest/
9. EdgeAISim: https://arxiv.org/pdf/2310.05605.pdf
10. ns-3: https://www.nsnam.org/about/
11. OMNeT++: https://omnetpp.org/intro/
12. SimBricks: https://pure.mpg.de/rest/items/item_3383868_1/component/file_3383869/content
13. IoTNetEMU: https://www.researchgate.net/publication/375085339_IoTNetEMU_-_A_Framework_to_Emulate_and_Test_IoT_Applications
14. ELIoT: https://www.ericsson.com/en/blog/2017/12/eliot--emulating-iot-devices
