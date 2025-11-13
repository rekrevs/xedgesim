# Related Work Notes for xEdgeSim

This document is a working space for surveying and comparing existing tools and frameworks relevant to xEdgeSim.

The aim is to map out:

- Wireless sensor network simulators and emulators (e.g. COOJA/Contiki).
- Embedded / MCU emulators used for systems research (e.g. Renode, QEMU-based setups).
- IoT and edge/fog simulators (e.g. iFogSim, EdgeCloudSim, PureEdgeSim, LEAF, EdgeAISim).
- Network simulators and co-simulation middleware (e.g. ns-3, OMNeT++, SimBricks, ns-3 co-sim libraries).
- IoT- and container-focused emulation frameworks (e.g. IoTNetEMU).

## Table of candidate systems (to be filled iteratively)

| Name          | Year | Focus (Device/Edge/Cloud) | Device realism (MCU/RTOS/binary) | Network modelling | Edge/cloud realism | ML support | Co-sim capabilities | CI/CD integration | Notes / Gaps vs xEdgeSim |
|--------------|------|----------------------------|-----------------------------------|-------------------|--------------------|------------|---------------------|--------------------|--------------------------|
| COOJA/Contiki| 2006-2008 | Device (WSN nodes) | MSP430 instruction-level (MSPSim), Contiki OS only, JNI-based native execution | UDGM, DirectedGraph, LogisticLoss radio mediums (single network type, 802.15.4) | None | None | Limited (serial socket bridge, not architectural) | Yes (headless mode, JavaScript scripting) | **Gaps:** No edge/cloud simulation; Contiki-only (no Zephyr/FreeRTOS/ARM); simplistic network models (no ns-3); no heterogeneous networks; no ML placement; monolithic Java architecture; ~50-100 node scalability limit |
| Renode       | 2010/2017 | Device (MCU emulation) | Full instruction-level: ARM Cortex-M/R, RISC-V, x86, PPC. Any RTOS (Zephyr, FreeRTOS, RIOT, bare-metal). Deployable binaries. | Basic inter-device networking (CAN, Ethernet switch model), no realistic PHY/MAC/routing | None (pure device emulator) | Can run TinyML models on-device, but no placement/offloading framework | **Excellent:** Virtual time, socket-based control, cycle-accurate determinism, designed for co-sim | Yes (Robot framework, headless, scriptable, deterministic) | **Gaps:** Device-only (no edge/cloud); needs external network simulator (ns-3) for realism; no multi-tier system support; no ML placement experiments; excellent co-sim foundation but requires integration work |
| iFogSim      |      |                            |                                   |                   |                    |            |                     |                    |                          |
| EdgeCloudSim |      |                            |                                   |                   |                    |            |                     |                    |                          |
| EdgeAISim    |      |                            |                                   |                   |                    |            |                     |                    |                          |
| IoTNetEMU    |      |                            |                                   |                   |                    |            |                     |                    |                          |
| SimBricks    |      |                            |                                   |                   |                    |            |                     |                    |                          |
| ns-3 cosim   |      |                            |                                   |                   |                    |            |                     |                    |                          |

## Notes and hypotheses

- Many existing simulators either focus on device-level fidelity or on edge/cloud resource modelling, but not both.
- Co-simulation approaches (e.g. combining QEMU or SoC emulators with ns-3) are promising building blocks for xEdgeSim.
- A key differentiator for xEdgeSim is the emphasis on:
  - deployable artefacts at both device and edge,
  - explicit ML placement experiments,
  - and CI/CD-friendly scenario definitions.

This document will be expanded as more systems are surveyed.
