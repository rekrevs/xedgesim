# xEdgeSim

xEdgeSim is a research prototype for a cross-level IoT–edge–cloud simulator.

The vision is to generalise "COOJA-style" cross-level simulation from wireless sensor networks to modern heterogeneous systems with:

- **Devices:** MCU-based nodes running real firmware (e.g. Zephyr/FreeRTOS) in emulation.
- **Edge:** Linux gateways running real containers (e.g. MQTT broker, aggregation, ML inference).
- **Network:** A discrete-event network simulator (e.g. ns-3) modelling wireless, LAN, and WAN links.
- **Cloud:** Mocked or containerised services representing cloud-side processing and storage.
- **ML placement:** Experimentation with different placements of ML workloads (device, edge, cloud) and offloading policies.

This repository will evolve in several phases:

1. P0 — Foundations & tooling (this commit).
2. P1 — Related work & gap analysis (documentation only).
3. P2 — Architecture design.
4. P3 — Implementation in incremental milestones (M0–M4).
5. P4 — Experiment harness and evaluation scenarios.
6. P5 — Writing and packaging for publication.

At P0 the repository mostly defines structure and some initial documentation to support later development.
