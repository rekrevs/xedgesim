# Related Work Notes for xEdgeSim

This document is a working space for surveying and comparing existing tools and frameworks relevant to xEdgeSim.

The aim is to map out:

- Wireless sensor network simulators and emulators (e.g. COOJA/Contiki).
- Embedded / MCU emulators used for systems research (e.g. Renode, QEMU-based setups).
- IoT and edge/fog simulators (e.g. iFogSim, EdgeCloudSim, PureEdgeSim, LEAF, EdgeAISim).
- Network simulators and co-simulation middleware (e.g. ns-3, OMNeT++, SimBricks, ns-3 co-sim libraries).
- IoT- and container-focused emulation frameworks (e.g. IoTNetEMU).

## Table of candidate systems

| Name          | Year | Focus (Device/Edge/Cloud) | Device realism (MCU/RTOS/binary) | Network modelling | Edge/cloud realism | ML support | Co-sim capabilities | CI/CD integration | Notes / Gaps vs xEdgeSim |
|--------------|------|----------------------------|-----------------------------------|-------------------|--------------------|------------|---------------------|--------------------|--------------------------|
| [COOJA/Contiki](https://github.com/contiki-os/contiki/wiki/An-Introduction-to-Cooja)| 2006-2008 | Device (WSN nodes) | MSP430 instruction-level (MSPSim), Contiki OS only, JNI-based native execution | UDGM, DirectedGraph, LogisticLoss radio mediums (single network type, 802.15.4) | None | None | Limited (serial socket bridge, not architectural) | Yes (headless mode, JavaScript scripting) | **Gaps:** No edge/cloud simulation; Contiki-only (no Zephyr/FreeRTOS/ARM); simplistic network models (no ns-3); no heterogeneous networks; no ML placement; monolithic Java architecture; ~50-100 node scalability limit |
| [Renode](https://renode.io/)       | 2010/2017 | Device (MCU emulation) | Full instruction-level: ARM Cortex-M/R, RISC-V, x86, PPC. Any RTOS (Zephyr, FreeRTOS, RIOT, bare-metal). Deployable binaries. | Basic inter-device networking (CAN, Ethernet switch model), no realistic PHY/MAC/routing | None (pure device emulator) | Can run TinyML models on-device, but no placement/offloading framework | **Excellent:** Virtual time, socket-based control, cycle-accurate determinism, designed for co-sim | Yes (Robot framework, headless, scriptable, deterministic) | **Gaps:** Device-only (no edge/cloud); needs external network simulator (ns-3) for realism; no multi-tier system support; no ML placement experiments; excellent co-sim foundation but requires integration work |
| [QEMU](https://www.qemu.org/) | ≈2003 | Device | High – generic machine emulator/virtualizer able to run full operating systems and user-mode binaries | Minimal – generic virtual network devices; no network simulation | None | None | None | | General-purpose emulator, not simulation-focused |
| [gem5](https://www.gem5.org/) | 2011 | Device | High – multiple CPU models, event-driven memory system and full-system simulation across several ISAs | None (focuses on processor/memory system) | None | None | Co-sim with SystemC | | Processor/memory focus, no network or edge/cloud |
| [iFogSim](https://github.com/Cloudslab/iFogSim) | 2017 | Edge/Fog | Low – models sensors, actuators and FogDevice objects representing distributed resources | Moderate – allows modelling of network latency and topology but not packet-level simulation | Models hierarchical edge/cloud resources and energy consumption | None | None | | High-level only, no binary execution |
| [EdgeCloudSim](https://github.com/CagataySonmez/EdgeCloudSim) | 2017 | Edge | Low – high-level simulation of tasks and resources | Modules for WLAN/WAN networks, device mobility and load generation | Moderate – simulates edge and cloud servers | None | None | | Abstract tasks, no firmware/containers |
| [PureEdgeSim](https://github.com/CharafeddineMechalikh/PureEdgeSim) | 2018 | Edge/Cloud/Mist | Low – simulates datacenters and servers via analytical models | Network module allocates bandwidth and models transfers | Moderate – realistic infrastructure models across edge–cloud continuum | None | None | | Analytical models, not deployable artifacts |
| [LEAF](https://github.com/dos-group/leaf) | 2022 | Fog/Energy | Low – models compute nodes abstractly | Models dynamic networks using NetworkX and SimPy | Models energy consumption for compute nodes and network traffic | None | None | | Energy focus, abstract models |
| [EdgeAISim](https://github.com/mhmd97z/EdgeAISim) | 2023 | Edge | Low – high-level simulation built on EdgeSimPy | Models network flows and mobility | Moderate – includes task scheduling, service migration and energy management | Strong – uses multi-armed bandit, DQN, graph neural networks and actor–critic models for resource management | None | | ML support but abstract device models |
| [ns-3](https://www.nsnam.org/) | 2008 | Network | None – focuses on network behaviour | Strong – detailed models for wireless and wired protocols (Wi-Fi, WiMAX, LTE) and real-time network emulation | None | None | Supports co-simulation with real systems; can act as interconnection framework | | Network-only, no device or edge/cloud |
| [OMNeT++](https://omnetpp.org/) | ≈2001 | Network | None | Modular component-based simulation with domain-specific frameworks (INET, Simu5G) | None | None | Extensible with real-time integration, network emulation, database integration via SystemC | | Network simulation framework |
| [SimBricks](https://simbricks.github.io/) | 2021 | Network & Host | High – combines QEMU/gem5 hosts and Verilator-based NICs | Integrates ns-3 or Tofino simulators to model network behaviour | None | None | Strong – co-sim between host and network simulators with time synchronization | | Promising co-sim approach but no edge/cloud |
| [IoTNetEMU](https://github.com/moradbeikie/IoTNetEMU) | 2023 | IoT & Container | Moderate – emulates IoT devices using Docker containers | Simple configurable network of emulated devices | Connects to containerised applications | None | None | | Container-based but no packet-level simulation |
| [ELIoT](https://www.ericsson.com/en/blog/2017/12/eliot--emulating-iot-devices) | 2024 | IoT & Container | Moderate – each Docker container represents an IoT device with its own network interface | No packet-level simulation; containers form a virtual network | None (focused on emulating large numbers of devices) | None | None | | Scalable container emulation but no network simulation |

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
