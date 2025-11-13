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
| [COOJA/Contiki](https://github.com/contiki-ng/cooja)| 2006-2008 | Device (WSN nodes) | MSP430 instruction-level (MSPSim), Contiki OS only, JNI-based native execution | UDGM, DirectedGraph, LogisticLoss radio mediums (single network type, 802.15.4) | None | None | Limited (serial socket bridge, not architectural) | Yes (headless mode, JavaScript scripting) | **Gaps:** No edge/cloud simulation; Contiki-only (no Zephyr/FreeRTOS/ARM); simplistic network models (no ns-3); no heterogeneous networks; no ML placement; monolithic Java architecture; ~50-100 node scalability limit |
| [Renode](https://renode.io/)       | 2017 | Device (MCU emulation) | Full instruction-level: ARM Cortex-M/R, RISC-V, x86, PPC. Any RTOS (Zephyr, FreeRTOS, RIOT, bare-metal). Deployable binaries. | Basic inter-device networking (CAN, Ethernet switch model), no realistic PHY/MAC/routing | None (pure device emulator) | Can run TinyML models on-device, but no placement/offloading framework | **Excellent:** Virtual time, socket-based control, cycle-accurate determinism, designed for co-sim | Yes (Robot framework, headless, scriptable, deterministic) | **Gaps:** Device-only (no edge/cloud); needs external network simulator (ns-3) for realism; no multi-tier system support; no ML placement experiments; excellent co-sim foundation but requires integration work |
| [QEMU](https://www.qemu.org/) | ≈2003 | Device | High – generic machine emulator/virtualizer able to run full operating systems and user-mode binaries | Minimal – generic virtual network devices; no network simulation | None | None | None | Yes (widely used in CI/CD) | General-purpose emulator, not simulation-focused |
| [gem5](https://www.gem5.org/) | 2011 | Device | High – multiple CPU models, event-driven memory system and full-system simulation across several ISAs | None (focuses on processor/memory system) | None | None | Co-sim with SystemC | Yes (research CI pipelines) | Processor/memory focus, no network or edge/cloud |
| [iFogSim / iFogSim2](https://github.com/Cloudslab/iFogSim) | 2016/2022 | Edge/Fog/Cloud (abstract resource management) | Sensors/actuators as abstract data generators (MIPS-based), no real firmware or MCU emulation | Simplified: latency + bandwidth, no packet-level or PHY/MAC modeling | Abstract FogDevice models (MIPS/RAM/storage), no real containers or OS. iFogSim2 adds microservice abstractions | Can model ML as application modules, but no built-in ML placement framework or inference-specific metrics | None (monolithic CloudSim-based Java simulator) | Moderate (Java-based, can integrate with CloudSim tools) | **Gaps:** No device firmware (abstract data generators); no real containers (abstract compute); simplified network (no ns-3/protocol stack); no deployable artifacts; application-layer only (no low-level system behavior); good for resource allocation policies but not for validating real implementations |
| [EdgeCloudSim](https://github.com/CagataySonmez/EdgeCloudSim) | 2018 | Edge/Cloud (mobile edge computing) | Abstract task generators with Poisson distributions, no real firmware or device emulation | WLAN/WAN delay modeling (single-server queue model), nomadic mobility support, no packet-level simulation | Abstract edge/cloud servers (MIPS/RAM), no real containers or OS. Modular factory pattern for extensibility | Can be used for ML offloading research, but no built-in ML framework | None (monolithic CloudSim-based Java simulator) | Moderate (Java-based, supports custom scenarios) | **Gaps:** No device firmware; abstract task execution (no real code); simplified network (no ns-3); no deployable containers; lacks energy/cost models in default implementation; good for offloading policy evaluation but not system validation |
| [PureEdgeSim](https://github.com/CharafeddineMechalikh/PureEdgeSim) | 2020 | Edge/Cloud/Mist | Low – simulates datacenters and servers via analytical models | Network module allocates bandwidth and models transfers | Moderate – realistic infrastructure models across edge–cloud continuum | None | None | Moderate (Java-based) | Analytical models, not deployable artifacts |
| [LEAF](https://github.com/dos-group/leaf) | 2022 | Fog/Energy | Low – models compute nodes abstractly | Models dynamic networks using NetworkX and SimPy | Models energy consumption for compute nodes and network traffic | None | None | Moderate (Python-based, supports scripting) | Energy focus, abstract models |
| [EdgeAISim](https://github.com/mhmd97z/EdgeAISim) | 2023 | Edge | Low – high-level simulation built on EdgeSimPy | Models network flows and mobility | Moderate – includes task scheduling, service migration and energy management | Strong – uses multi-armed bandit, DQN, graph neural networks and actor–critic models for resource management | None | Moderate (Python-based) | ML support but abstract device models |
| [ns-3](https://www.nsnam.org/) | 2008 | Network | None – focuses on network behaviour | Strong – detailed models for wireless and wired protocols (Wi-Fi, WiMAX, LTE) and real-time network emulation | None | None | Supports co-simulation with real systems; can act as interconnection framework. **Note:** ns-3 DCE (Direct Code Execution, 2012-2016) attempted time-dilated Linux apps but is now deprecated | Yes (widely used in research) | Network-only, no device or edge/cloud. DCE showed real code in simulators is possible but maintenance was too complex |
| [OMNeT++](https://omnetpp.org/) | ≈2001 | Network | None | Modular component-based simulation with domain-specific frameworks (INET, Simu5G) | None | None | Extensible with real-time integration, network emulation, database integration via SystemC | | Network simulation framework |
| [SimBricks](https://simbricks.github.io/) | 2022 | Network & Host | High – combines QEMU/gem5 hosts and Verilator-based NICs | Integrates ns-3 or Tofino simulators to model network behaviour | None | None | **Strong** – federated co-sim with socket-based time synchronization between host and network simulators | Yes (designed for reproducible experiments) | **Architecturally closest to xEdgeSim**: Validates federated co-simulation approach. **Gaps:** Datacenter focus (full VMs not MCUs); no edge containers; no IoT/ML placement focus |
| [IoTNetEMU](https://github.com/moradbeikie/IoTNetEMU) | 2023 | IoT & Container | Moderate – emulates IoT devices using Docker containers | Simple configurable network of emulated devices | Connects to containerised applications | None | None | Moderate (Docker-based, scriptable) | Container-based but no packet-level simulation |
| [Fogify](https://github.com/UCY-LINC-LAB/fogify) | 2020 | Fog & Container | Moderate – Docker containers with QoS control and resource limits | Network emulation with configurable delay, bandwidth, packet loss via Linux tc | Real containerized fog/edge services with resource management | Limited – can model workloads but no ML placement framework | None (container-based emulation) | Yes (Docker-based, topology YAML configs) | Real containers provide deployability but uses wall-clock time (not deterministic); no packet-level simulation; no device firmware support |
| [ELIoT](https://www.ericsson.com/en/blog/2017/12/eliot--emulating-iot-devices) | 2017 | IoT & Container | Moderate – each Docker container represents an IoT device with its own network interface | No packet-level simulation; containers form a virtual network | None (focused on emulating large numbers of devices) | None | None | Yes (Docker-based, scalable testing) | Scalable container emulation but no network simulation |

## Gap Analysis

### The Abstraction Level Alignment Problem

Existing simulators fall into one of two extremes: **hardware-accurate device emulators** (Renode, QEMU, gem5) or **high-level edge/fog/network models** (iFogSim, EdgeCloudSim, PureEdgeSim, LEAF, EdgeAISim). Device emulators provide binary-level fidelity but have little or no network and edge/cloud modelling, while high-level simulators model resource allocation and communication but cannot execute real firmware or container images.

A fundamental issue is the **abstraction level mismatch**: each system tier requires different fidelity for accurate modeling:
- **Device tier**: Instruction-level emulation needed for firmware validation → Tools available (Renode, QEMU, gem5)
- **Network tier**: Packet-level simulation needed for protocol behavior → Tools available (ns-3, OMNeT++)
- **Edge tier**: Application-level (containers) needed for service deployment → Partial tools (Fogify, IoTNetEMU, but without network simulation)
- **Cloud tier**: Abstract models sufficient for high-level behavior → Tools available but too abstract (iFogSim, EdgeCloudSim)

**No existing tool provides appropriate fidelity at each tier simultaneously.** Tools either go deep in one tier or wide but shallow across all tiers. SimBricks demonstrates federated co-simulation for datacenter systems but focuses on full-system VMs rather than MCU firmware and lacks edge container support.

### Key gaps that xEdgeSim aims to fill:

1. **Variable-fidelity co-simulation**: None of the surveyed systems provide appropriate abstraction levels across all tiers simultaneously. xEdgeSim will integrate instruction-level device emulation (Renode), packet-level network simulation (ns-3), and application-level edge services (Docker) in a single coherent platform, similar to SimBricks' approach but for IoT-edge-cloud systems.

2. **Deployable artefacts**: Existing fog/edge simulators use abstract tasks rather than deployable firmware and containers. xEdgeSim will run actual MCU binaries and container images, producing results that better reflect real deployments and enabling direct transition from simulation to production.

3. **ML placement experiments**: None of the surveyed tools combine device/edge/cloud simulation with machine-learning offloading and placement decisions. xEdgeSim will support ML models (e.g. via ONNX Runtime) and provide a framework to evaluate where inference should run (device/edge/cloud) with concrete metrics.

4. **Hybrid determinism**: xEdgeSim will provide full determinism where critical (device firmware and network protocols via Renode + ns-3) while accepting statistical reproducibility where needed (edge/cloud containers), balancing debugging requirements with deployment realism.

5. **Cross-tier instrumentation**: Most tools provide metrics for a single tier. xEdgeSim will enable end-to-end measurement spanning device energy consumption, network latency/loss, edge processing time, and cloud response delays in unified experiments.

6. **Federated time synchronisation**: Building on SimBricks' validated approach, xEdgeSim will enforce coherent simulated time across heterogeneous components (Renode, ns-3, Docker) via socket-based coordination, enabling accurate latency and energy evaluations across the full system.

7. **CI/CD friendliness**: While Renode has good CI support, edge/fog simulators lack automated testing workflows. xEdgeSim will package scenarios as reproducible YAML configurations and integrate with continuous integration pipelines to encourage open, automated experimentation.

These capabilities will make xEdgeSim the first **variable-fidelity cross-tier co-simulation platform** for IoT–edge–cloud systems, filling the gap between specialized single-tier tools and overly abstract multi-tier simulators.

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
