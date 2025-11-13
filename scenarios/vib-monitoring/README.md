# Vibration Monitoring Scenario (Draft)

## Motivation

A common industrial IoT use case is vibration-based condition monitoring of rotating machinery:

- Battery-powered sensor nodes mounted on machines measure vibration.
- Edge gateways aggregate and analyse data locally.
- Cloud services provide fleet-wide analytics, dashboards, and long-term storage.

This scenario will serve as the initial end-to-end example for xEdgeSim.

## High-level scenario description

- **Devices:**
  - MCU-based nodes running firmware that:
    - samples a synthetic vibration signal,
    - computes simple features (e.g. RMS, spectral features),
    - sends periodic reports to the edge (UDP / CoAP / MQTT-SN).
- **Network:**
  - A low-power wireless link from devices to edge gateways.
  - IP connectivity from gateways to a cloud endpoint with variable latency and loss.
- **Edge:**
  - Containers running:
    - a message broker (e.g. MQTT),
    - an aggregation and preprocessing service,
    - a local anomaly detection model for fast alerts.
- **Cloud:**
  - A simple mock or containerised service that:
    - receives aggregated data,
    - runs a heavier or more accurate model,
    - stores alerts and metrics.

## Planned experimental dimensions

The scenario should support experiments along several axes:

- Placement of ML inference:
  - device vs edge vs cloud, or hybrid schemes.
- Network conditions:
  - variation in latency, jitter, and loss on both device–edge and edge–cloud links.
- Load and scale:
  - number of devices,
  - sampling frequency and reporting interval.
- Faults:
  - network partitions,
  - degraded links,
  - compromised edge node behaviour (e.g. dropping or tampering with alerts).

## Status

- At P0, this document only describes the intended scenario.
- Future steps:
  - define a machine-readable configuration format (e.g. YAML),
  - implement a basic scenario runner,
  - connect the scenario to real firmware and edge components.
