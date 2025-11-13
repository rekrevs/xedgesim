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
| COOJA/Contiki|      |                            |                                   |                   |                    |            |                     |                    |                          |
| Renode       |      |                            |                                   |                   |                    |            |                     |                    |                          |
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
