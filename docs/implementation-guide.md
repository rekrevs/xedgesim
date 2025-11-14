# xEdgeSim Implementation Guide

**Date:** 2025-11-13
**Status:** Implementation Reference
**Companion to:** `docs/architecture.md`

## Document Purpose

This document provides detailed implementation guidance for xEdgeSim's feature-specific components. While `architecture.md` covers the core architectural principles (federated co-simulation, tiered determinism, time synchronization), this guide focuses on **how to implement** specific features across milestones M0-M4.

**Note:** Features are tagged by milestone. Not all features need to be implemented simultaneously. See `architecture.md` Section 2 for the phased implementation approach.

---

## Table of Contents

1. [ML Placement Framework Architecture](#1-ml-placement-framework-architecture) *(M3)*
2. [Scenario Specification and Execution](#2-scenario-specification-and-execution) *(M0: hardcoded, M1: YAML)*
3. [Metrics Collection Architecture](#3-metrics-collection-architecture) *(M0: simple CSVs, M1: structured)*
4. [ns-3 Integration Details](#4-ns-3-integration-details) *(M1)*
5. [Docker Network Integration](#5-docker-network-integration) *(M2)*
6. [Deployability Architecture](#6-deployability-architecture) *(M2-M4)*
7. [CI/CD Integration](#7-cicd-integration) *(M2-M4)*
8. [Scalability Architecture](#8-scalability-architecture) *(M3-M4)*

---

## 1. ML Placement Framework Architecture

**Milestone:** M3 (the "killer app" research contribution)

### 1.1 Overview and Motivation

**The Problem:** Existing simulators (iFogSim, EdgeCloudSim) model ML placement abstractly. Device emulators (Renode, COOJA) cannot run edge/cloud components. No tool enables realistic evaluation of ML inference placement decisions.

**xEdgeSim's Solution:** First-class ML placement framework that:
- Runs actual ML models (TFLite on device, ONNX on edge, PyTorch on cloud)
- Evaluates placement variants (device-only, edge-only, cloud-only, hybrid)
- Measures accuracy, latency, and energy trade-offs across tiers
- Enables Pareto frontier exploration

**This is the primary differentiator vs existing work.**

---

### 1.2 ML Model Lifecycle

```
┌─────────────────────────────────────────────────────────────┐
│                   ML Model Lifecycle                        │
└─────────────────────────────────────────────────────────────┘

1. Develop & Train (offline, before simulation)
   ├─ Train model (PyTorch/TensorFlow)
   ├─ Validate accuracy on test set
   └─ Save full-precision model

2. Quantize & Optimize (per deployment tier)
   ├─ Device: TFLite quantized (INT8, 10-100KB)
   ├─ Edge: ONNX optimized (FP16/INT8, 1-10MB)
   └─ Cloud: PyTorch/ONNX (FP32, 10-100MB)

3. Package (embed in firmware or container)
   ├─ Device: Compiled into firmware ELF
   ├─ Edge: Mounted into Docker container
   └─ Cloud: Loaded by Python service

4. Deploy (in simulation)
   ├─ Renode loads firmware with embedded model
   ├─ Docker container has model in /app/models/
   └─ Python mock loads model from file

5. Inference (during simulation)
   ├─ Device: TFLite interpreter in firmware
   ├─ Edge: ONNX Runtime in container
   └─ Cloud: PyTorch in Python service

6. Evaluate (post-simulation analysis)
   ├─ Measure accuracy (prediction vs ground truth)
   ├─ Measure latency (sample → result)
   └─ Measure energy (device + communication)
```

---

### 1.3 Placement Specification

**Scenario YAML Example:**

```yaml
scenario:
  name: vibration-ml-placement-comparison

# Variant 1: Device-only inference
devices:
  - id: sensors_device_inference
    count: 10
    platform: nrf52840
    firmware: builds/vib_sensor_device.elf
    ml_placement: device
    ml_model: models/anomaly_detector_quantized.tflite  # 50KB INT8
    config:
      sample_rate: 1000Hz
      inference_interval: 1s  # Run inference every second

# Variant 2: Edge inference
  - id: sensors_edge_inference
    count: 10
    platform: nrf52840
    firmware: builds/vib_sensor_forward.elf
    ml_placement: edge
    config:
      sample_rate: 1000Hz
      forward_interval: 1s  # Send data to edge every second

edge:
  - id: gateway_ml
    type: docker
    image: xedgesim/mqtt-ml-inference:latest
    ml_model: models/anomaly_detector.onnx  # 2MB FP16
    services:
      - mqtt_broker
      - ml_inference_service

# Variant 3: Cloud inference
  - id: sensors_cloud_inference
    count: 10
    platform: nrf52840
    firmware: builds/vib_sensor_forward.elf
    ml_placement: cloud

cloud:
  - id: cloud_ml
    type: python_service
    ml_model: models/anomaly_detector_full.pt  # 10MB FP32
    latency: 50ms  # Network latency to cloud
```

---

### 1.4 ML Inference Orchestration

**Device-Only Inference (Firmware):**

```c
// Device firmware with embedded TFLite model
#include <tensorflow/lite/micro/micro_interpreter.h>

void run_inference() {
    // 1. Sample vibration data
    float samples[1000];
    adc_read_samples(samples, 1000);

    // 2. Preprocess (compute RMS, FFT, etc.)
    float features[32];
    compute_features(samples, features);

    // 3. Run TFLite inference on-device
    tflite::MicroInterpreter interpreter(model, tensor_arena, kTensorArenaSize);
    interpreter.AllocateTensors();

    memcpy(interpreter.input(0)->data.f, features, sizeof(features));
    interpreter.Invoke();

    float anomaly_score = interpreter.output(0)->data.f[0];

    // 4. Act on result
    if (anomaly_score > THRESHOLD) {
        gpio_set_pin(ALARM_PIN);
        uart_printf("ANOMALY: %.2f\n", anomaly_score);
    }

    // 5. Log metrics for coordinator
    log_energy(INFERENCE_ENERGY_UJ);
    log_latency_us(get_timestamp() - start_timestamp);
}
```

**Edge Inference (Docker Container):**

```python
# ml_inference_service.py running in Docker container

import paho.mqtt.client as mqtt
import onnxruntime as ort
import numpy as np

# Load ONNX model
session = ort.InferenceSession('/app/models/anomaly_detector.onnx')

def on_message(client, userdata, msg):
    """Handle incoming sensor data from MQTT"""
    start_time = time.time()

    # 1. Parse sensor data
    data = json.loads(msg.payload)
    features = np.array(data['features'], dtype=np.float32)

    # 2. Run inference on edge
    inputs = {session.get_inputs()[0].name: features.reshape(1, -1)}
    outputs = session.run(None, inputs)
    anomaly_score = outputs[0][0]

    # 3. Publish result back to MQTT
    result = {
        'device_id': data['device_id'],
        'anomaly_score': float(anomaly_score),
        'inference_time_ms': (time.time() - start_time) * 1000
    }
    client.publish(f"results/{data['device_id']}", json.dumps(result))

    # 4. Log metrics
    log_inference_time(time.time() - start_time)

# Connect to MQTT broker
client = mqtt.Client()
client.on_message = on_message
client.connect("localhost", 1883)
client.subscribe("sensor/data/#")
client.loop_forever()
```

**Cloud Inference (Python Mock):**

```python
# cloud_ml_service.py (Python mock)

class CloudMLService:
    def __init__(self, model_path, latency_ms):
        self.model = torch.load(model_path)
        self.latency_ms = latency_ms  # Simulated network latency

    def infer(self, features):
        """Simulate cloud inference with network latency"""
        start_time = time.time()

        # Add network latency (send data to cloud)
        time.sleep(self.latency_ms / 1000.0)

        # Run inference
        with torch.no_grad():
            result = self.model(torch.tensor(features))

        # Add network latency (receive result from cloud)
        time.sleep(self.latency_ms / 1000.0)

        return result, (time.time() - start_time) * 1000
```

---

### 1.5 Trade-Off Evaluation Framework

**Metrics Collected per Placement:**

| Metric | Device Inference | Edge Inference | Cloud Inference |
|--------|------------------|----------------|-----------------|
| **Accuracy** | 85% (quantized) | 92% (FP16) | 95% (FP32) |
| **Latency** | 5ms (on-device) | 50ms (device→edge→device) | 150ms (device→cloud→device) |
| **Energy** | 100μJ (inference) | 10μJ (idle) + 500μJ (TX) | 5μJ (idle) + 800μJ (TX+wait) |
| **Reliability** | 100% (no network) | 98% (edge reachable) | 90% (cloud reachable) |

**Cross-Tier Latency Breakdown:**

```
Device Inference:
  Sample (1ms) → Inference (5ms) → Result
  Total: 6ms

Edge Inference:
  Sample (1ms) → TX (2ms) → Network (10ms) → Edge Inference (8ms) →
  Network (10ms) → RX (2ms) → Result
  Total: 33ms

Cloud Inference:
  Sample (1ms) → TX (2ms) → Network (20ms) → Edge Forward (5ms) →
  WAN (50ms) → Cloud Inference (10ms) → WAN (50ms) → Edge (5ms) →
  Network (20ms) → RX (2ms) → Result
  Total: 165ms
```

**Pareto Frontier Computation:**

```python
# scripts/analyze_ml_placement.py

import pandas as pd
import matplotlib.pyplot as plt
from sklearn.metrics import accuracy_score

def compute_pareto_frontier(results_dir):
    """Compute Pareto frontier for ML placement variants"""

    # Load results from all variants
    device_metrics = pd.read_csv(f'{results_dir}/device_inference/metrics.csv')
    edge_metrics = pd.read_csv(f'{results_dir}/edge_inference/metrics.csv')
    cloud_metrics = pd.read_csv(f'{results_dir}/cloud_inference/metrics.csv')

    # Compute aggregate metrics per variant
    variants = []

    # Device variant
    variants.append({
        'name': 'Device',
        'accuracy': compute_accuracy(device_metrics, ground_truth),
        'latency_ms': device_metrics['latency_ms'].mean(),
        'energy_mJ': device_metrics['energy_uJ'].sum() / 1000,
    })

    # Edge variant
    variants.append({
        'name': 'Edge',
        'accuracy': compute_accuracy(edge_metrics, ground_truth),
        'latency_ms': edge_metrics['e2e_latency_ms'].mean(),
        'energy_mJ': (edge_metrics['device_energy_uJ'].sum() +
                      edge_metrics['communication_energy_uJ'].sum()) / 1000,
    })

    # Cloud variant
    variants.append({
        'name': 'Cloud',
        'accuracy': compute_accuracy(cloud_metrics, ground_truth),
        'latency_ms': cloud_metrics['e2e_latency_ms'].mean(),
        'energy_mJ': (cloud_metrics['device_energy_uJ'].sum() +
                      cloud_metrics['communication_energy_uJ'].sum()) / 1000,
    })

    # Plot Pareto frontier
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # Accuracy vs Latency
    for v in variants:
        axes[0].scatter(v['latency_ms'], v['accuracy'], s=100, label=v['name'])
    axes[0].set_xlabel('Latency (ms)')
    axes[0].set_ylabel('Accuracy')
    axes[0].set_title('Accuracy vs Latency Trade-off')
    axes[0].legend()
    axes[0].grid(True)

    # Accuracy vs Energy
    for v in variants:
        axes[1].scatter(v['energy_mJ'], v['accuracy'], s=100, label=v['name'])
    axes[1].set_xlabel('Energy (mJ)')
    axes[1].set_ylabel('Accuracy')
    axes[1].set_title('Accuracy vs Energy Trade-off')
    axes[1].legend()
    axes[1].grid(True)

    plt.tight_layout()
    plt.savefig('figures/ml_placement_pareto.png')

    return variants

def compute_accuracy(metrics_df, ground_truth_df):
    """Compare predictions to ground truth"""
    predictions = metrics_df['prediction'].values
    true_labels = ground_truth_df['label'].values
    return accuracy_score(true_labels, predictions)
```

---

### 1.6 Hybrid Placement (Advanced)

**Split Inference:** Run part of model on device, part on edge.

```yaml
ml_placement: hybrid
ml_split:
  device_layers: [0, 1, 2]  # First 3 layers on device
  edge_layers: [3, 4, 5]    # Last 3 layers on edge
  intermediate_size: 128    # Size of intermediate tensor
```

**Adaptive Placement:** Change placement based on runtime conditions.

```python
# Adaptive placement logic in firmware
if (battery_level < LOW_BATTERY_THRESHOLD):
    placement = EDGE_INFERENCE  # Conserve energy
elif (network_quality < POOR_NETWORK_THRESHOLD):
    placement = DEVICE_INFERENCE  # Avoid network
else:
    placement = EDGE_INFERENCE  # Best accuracy
```

---

### 1.7 Implementation Roadmap

**M3 Milestone:** ML Placement Framework

1. **Week 1-2:** Model preparation
   - Train baseline anomaly detection model for vibration data
   - Quantize for TFLite (device), optimize for ONNX (edge)
   - Embed models in firmware and containers

2. **Week 3-4:** Placement implementation
   - Implement TFLite inference in device firmware
   - Implement ONNX inference in edge container
   - Implement cloud mock service

3. **Week 5-6:** Orchestration and metrics
   - Extend coordinator to track ML-specific metrics
   - Implement cross-tier latency tracking
   - Implement energy attribution (device vs communication vs computation)

4. **Week 7-8:** Evaluation framework
   - Implement Pareto frontier computation
   - Create visualization scripts
   - Run comparison experiments (device vs edge vs cloud)

---

## 2. Scenario Specification and Execution

**Milestone:** M0 (hardcoded), M1 (YAML parser)

### 2.1 Overview

**Problem:** Without formal scenario specification, reproducibility and CI/CD claims are unvalidated.

**Solution:** YAML-based scenario schema that completely specifies:
- Device topology and firmware
- Network configuration
- Edge and cloud services
- Fault injection timeline
- Metrics collection requirements

---

### 2.2 Scenario YAML Schema

**Complete Example:**

```yaml
scenario:
  name: vibration-monitoring-baseline
  description: "Baseline vibration monitoring with 20 sensors, 1 gateway, MQTT broker"
  duration: 300s  # 5 minutes
  seed: 42        # For reproducible randomness

devices:
  - id: vibration_sensors
    count: 20
    platform: nrf52840dk
    firmware: builds/vib_sensor.elf
    placement:
      topology: grid
      spacing: 10m  # 10 meters apart
    config:
      sample_rate: 1000Hz
      report_interval: 1s
      tx_power: 0dBm
    ml_placement: edge

network:
  type: ns3
  topology: star  # All devices connect to single gateway

  wireless:
    protocol: 802.15.4
    channel: 26
    channel_model: LogDistancePropagationLoss
    path_loss_exponent: 3.0
    reference_distance: 1.0
    reference_loss: 40.0

  wired:
    gateway_to_cloud:
      type: ethernet
      latency: 20ms
      bandwidth: 100Mbps
      jitter: 5ms
      loss_rate: 0.01%

edge:
  - id: gateway_1
    type: docker
    image: xedgesim/mqtt-ml:v1.0
    network_mode: bridge
    volumes:
      - ./models:/app/models:ro
    environment:
      MQTT_PORT: 1883
      ML_MODEL: /app/models/anomaly_detector.onnx
    services:
      - mqtt_broker
      - ml_inference_service
      - data_aggregator

cloud:
  - id: cloud_backend
    type: python_mock
    latency: 50ms
    services:
      - data_store
      - analytics_dashboard

metrics:
  collection_interval: 100ms
  collect:
    - device_energy
    - packet_latency
    - packet_loss
    - end_to_end_latency
    - ml_inference_time
    - ml_accuracy
  output_dir: results/vibration-baseline/
  formats:
    - csv
    - json

faults:
  - time: 150s
    type: edge_failure
    target: gateway_1
    duration: 30s
    description: "Simulate gateway crash"

  - time: 200s
    type: network_partition
    target: [device_1, device_2, device_3]
    duration: 20s
    description: "Simulate radio interference"

validation:
  assertions:
    - metric: total_packets_sent
      min: 5000
      description: "Expect ~20 devices * 300s / 1s = 6000 packets"
    - metric: packet_delivery_rate
      min: 0.95
      description: "Expect >95% delivery in good conditions"
    - metric: ml_accuracy
      min: 0.85
      description: "Expect >85% anomaly detection accuracy"
```

---

### 2.3 Scenario Parser and Validator

**Coordinator Scenario Loader:**

```go
// scenario.go

package coordinator

import (
    "gopkg.in/yaml.v3"
    "os"
)

type Scenario struct {
    Meta      ScenarioMeta      `yaml:"scenario"`
    Devices   []DeviceGroup     `yaml:"devices"`
    Network   NetworkConfig     `yaml:"network"`
    Edge      []EdgeNode        `yaml:"edge"`
    Cloud     []CloudNode       `yaml:"cloud"`
    Metrics   MetricsConfig     `yaml:"metrics"`
    Faults    []FaultInjection  `yaml:"faults"`
    Validation ValidationConfig `yaml:"validation"`
}

type ScenarioMeta struct {
    Name        string `yaml:"name"`
    Description string `yaml:"description"`
    Duration    string `yaml:"duration"`  // Parse to microseconds
    Seed        int    `yaml:"seed"`
}

type DeviceGroup struct {
    ID            string            `yaml:"id"`
    Count         int               `yaml:"count"`
    Platform      string            `yaml:"platform"`
    Firmware      string            `yaml:"firmware"`
    Placement     PlacementConfig   `yaml:"placement"`
    Config        map[string]interface{} `yaml:"config"`
    MLPlacement   string            `yaml:"ml_placement"`
}

type NetworkConfig struct {
    Type     string            `yaml:"type"`  // "ns3"
    Topology string            `yaml:"topology"` // "star", "mesh", "tree"
    Wireless WirelessConfig    `yaml:"wireless"`
    Wired    map[string]LinkConfig `yaml:"wired"`
}

type EdgeNode struct {
    ID          string            `yaml:"id"`
    Type        string            `yaml:"type"`  // "docker" or "model"
    Image       string            `yaml:"image"`
    NetworkMode string            `yaml:"network_mode"`
    Volumes     []string          `yaml:"volumes"`
    Environment map[string]string `yaml:"environment"`
    Services    []string          `yaml:"services"`
}

type FaultInjection struct {
    Time        string   `yaml:"time"`  // Parse to microseconds
    Type        string   `yaml:"type"`  // "edge_failure", "network_partition", etc.
    Target      interface{} `yaml:"target"`  // string or []string
    Duration    string   `yaml:"duration"`
    Description string   `yaml:"description"`
}

func LoadScenario(path string) (*Scenario, error) {
    data, err := os.ReadFile(path)
    if err != nil {
        return nil, fmt.Errorf("failed to read scenario file: %w", err)
    }

    var scenario Scenario
    if err := yaml.Unmarshal(data, &scenario); err != nil {
        return nil, fmt.Errorf("failed to parse scenario YAML: %w", err)
    }

    if err := scenario.Validate(); err != nil {
        return nil, fmt.Errorf("invalid scenario: %w", err)
    }

    return &scenario, nil
}

func (s *Scenario) Validate() error {
    // Validate required fields
    if s.Meta.Name == "" {
        return fmt.Errorf("scenario name is required")
    }

    if s.Meta.Duration == "" {
        return fmt.Errorf("scenario duration is required")
    }

    // Validate device firmware files exist
    for _, devGroup := range s.Devices {
        if _, err := os.Stat(devGroup.Firmware); err != nil {
            return fmt.Errorf("firmware not found: %s", devGroup.Firmware)
        }
    }

    // Validate Docker images exist (or can be pulled)
    for _, edge := range s.Edge {
        if edge.Type == "docker" {
            // Check if image exists locally or can be pulled
            // (implementation details omitted)
        }
    }

    // Validate fault injection times are within scenario duration
    duration := parseDuration(s.Meta.Duration)
    for _, fault := range s.Faults {
        faultTime := parseDuration(fault.Time)
        if faultTime > duration {
            return fmt.Errorf("fault at %s exceeds scenario duration %s",
                fault.Time, s.Meta.Duration)
        }
    }

    return nil
}
```

---

### 2.4 Scenario Execution Flow

```
┌────────────────────────────────────────────────────────────┐
│                  Scenario Execution Flow                   │
└────────────────────────────────────────────────────────────┘

1. User Invokes:
   $ xedgesim run scenarios/vibration-baseline/config.yaml

2. Coordinator Parses YAML
   ├─ Load and validate schema
   ├─ Parse device configurations
   ├─ Parse network topology
   ├─ Parse edge/cloud services
   ├─ Parse fault injection timeline
   └─ Parse metrics requirements

3. Coordinator Initializes Components
   ├─ Spawn Renode instances (20x for vibration_sensors)
   │  └─ Load firmware, configure peripherals
   ├─ Spawn ns-3 process
   │  └─ Create star topology, configure 802.15.4
   ├─ Start Docker containers (gateway_1)
   │  └─ Pull image, mount volumes, start services
   └─ Initialize Python mocks (cloud_backend)

4. Coordinator Initializes Metrics Collectors
   ├─ Create output directory
   ├─ Open CSV files for each metric type
   └─ Initialize aggregators

5. Coordinator Runs Simulation Loop
   for t = 0 to 300s (step = 10ms):
       ├─ Send "ADVANCE 10000" to all nodes
       ├─ Wait for all nodes to complete
       ├─ Collect events from all nodes
       ├─ Route cross-node messages
       ├─ Check for scheduled faults (at t=150s, t=200s)
       │  └─ If fault scheduled, inject fault
       ├─ Log metrics (every 100ms)
       └─ Advance global time

6. At t=150s: Inject Edge Failure
   ├─ Coordinator pauses gateway_1 container
   │  $ docker pause gateway_1
   ├─ Continue simulation (devices cannot reach edge)
   └─ At t=180s: Resume gateway_1
      $ docker unpause gateway_1

7. At t=300s: Simulation Complete
   ├─ Coordinator shuts down all components
   │  ├─ Stop Renode instances
   │  ├─ Stop ns-3 process
   │  ├─ Stop Docker containers
   │  └─ Cleanup Python mocks
   ├─ Close metrics files
   └─ Write summary.json

8. Coordinator Validates Results
   ├─ Load metrics from CSV files
   ├─ Check assertions from validation config
   │  ├─ total_packets_sent >= 5000 ✓
   │  ├─ packet_delivery_rate >= 0.95 ✓
   │  └─ ml_accuracy >= 0.85 ✓
   └─ Exit with code 0 (success) or 1 (failure)

9. User Analyzes Results:
   $ xedgesim analyze results/vibration-baseline/
   $ python scripts/plot_metrics.py results/vibration-baseline/
```

---

### 2.5 CLI Interface

```bash
# Run a single scenario
$ xedgesim run scenarios/vibration-baseline/config.yaml

# Run multiple scenarios (batch mode)
$ xedgesim batch scenarios/batch-config.yaml

# Validate scenario without running
$ xedgesim validate scenarios/vibration-baseline/config.yaml

# Analyze results
$ xedgesim analyze results/vibration-baseline/

# Generate plots
$ xedgesim plot results/vibration-baseline/ --output figures/

# Compare multiple scenarios
$ xedgesim compare results/device-inference/ results/edge-inference/ results/cloud-inference/
```

**Batch Configuration:**

```yaml
# scenarios/batch-config.yaml

batch:
  name: ml-placement-comparison
  scenarios:
    - scenarios/device-inference/config.yaml
    - scenarios/edge-inference/config.yaml
    - scenarios/cloud-inference/config.yaml
  parallel: 3  # Run 3 scenarios in parallel
  output_dir: results/ml-placement-comparison/
```

---

## 3. Metrics Collection Architecture

**Milestone:** M0 (simple CSVs), M1 (structured collection)

### 3.1 Overview

**Problem:** Cross-tier metrics collection is mentioned but not architected.

**Solution:** Hierarchical metrics framework that collects device, network, edge, and cloud metrics, then computes cross-tier aggregations.

---

### 3.2 Metrics Taxonomy

```
┌─────────────────────────────────────────────────────────────┐
│                      Metrics Hierarchy                      │
└─────────────────────────────────────────────────────────────┘

Tier 1: Component Metrics (collected by each simulator/emulator)
├─ Device Metrics (from Renode)
│  ├─ Cycles executed
│  ├─ Energy consumed (model-based estimation)
│  ├─ Memory usage
│  ├─ UART TX/RX bytes
│  ├─ GPIO state changes
│  └─ Sleep/wake transitions
│
├─ Network Metrics (from ns-3)
│  ├─ Packets sent/received/dropped per node
│  ├─ Per-packet latency (queuing + transmission + propagation)
│  ├─ Channel utilization
│  ├─ Collision count
│  ├─ RSSI, SNR (PHY-layer)
│  └─ Per-link throughput
│
├─ Edge Metrics (from Docker)
│  ├─ CPU usage per container
│  ├─ Memory usage per container
│  ├─ Network I/O (bytes TX/RX)
│  ├─ Request processing time
│  └─ Queue depth (e.g., MQTT broker queue)
│
└─ Cloud Metrics (from Python mocks)
   ├─ Request count
   ├─ Simulated processing time
   └─ Simulated latency

Tier 2: Cross-Tier Metrics (computed by coordinator)
├─ End-to-End Latency
│  └─ device_sample_timestamp → result_received_timestamp
├─ Total Energy per Sample
│  └─ device_energy + communication_energy
├─ ML Accuracy
│  └─ predictions vs ground_truth
├─ System Throughput
│  └─ samples_processed / time
└─ Pareto Frontiers
   └─ accuracy vs latency, accuracy vs energy, etc.
```

---

### 3.3 Metrics Collection API

**Per-Component Metrics:**

```go
// metrics.go

package coordinator

// Metrics interface implemented by all node types
type MetricsProvider interface {
    GetMetrics() Metrics
}

// Base metrics structure
type Metrics struct {
    NodeID    string
    TimeUs    uint64
    Component string  // "device", "network", "edge", "cloud"
    Data      map[string]interface{}
}

// Device-specific metrics
type DeviceMetrics struct {
    NodeID         string
    TimeUs         uint64
    CyclesExecuted uint64
    EnergyMicroJ   uint64
    MemoryUsageKB  uint64
    TxBytes        uint64
    RxBytes        uint64
    SleepTimeUs    uint64
    ActiveTimeUs   uint64
}

// Network-specific metrics
type NetworkMetrics struct {
    TimeUs             uint64
    PacketsSent        uint64
    PacketsDelivered   uint64
    PacketsDropped     uint64
    AvgLatencyUs       uint64
    MaxLatencyUs       uint64
    Collisions         uint64
    ChannelUtilization float64
}

// Edge-specific metrics
type EdgeMetrics struct {
    ContainerID         string
    TimeUs              uint64
    CPUUsagePercent     float64
    MemoryUsageMB       uint64
    NetworkTxBytes      uint64
    NetworkRxBytes      uint64
    RequestsProcessed   uint64
    AvgProcessingTimeUs uint64
    QueueDepth          uint64
}

// Cross-tier metrics (computed)
type CrossTierMetrics struct {
    TimeUs                 uint64
    EndToEndLatencyUs      uint64
    TotalEnergyMicroJ      uint64
    MLAccuracy             float64
    SamplesProcessed       uint64
    PacketDeliveryRate     float64
    SystemThroughput       float64
}
```

**Metrics Collector in Coordinator:**

```go
type MetricsCollector struct {
    deviceMetrics  map[string][]*DeviceMetrics  // keyed by node ID
    networkMetrics []*NetworkMetrics
    edgeMetrics    map[string][]*EdgeMetrics    // keyed by container ID
    crossTier      []*CrossTierMetrics

    // Output files
    deviceCSV    *csv.Writer
    networkCSV   *csv.Writer
    edgeCSV      *csv.Writer
    crossTierCSV *csv.Writer
}

func NewMetricsCollector(outputDir string) (*MetricsCollector, error) {
    os.MkdirAll(outputDir, 0755)

    // Open CSV files
    deviceFile, _ := os.Create(filepath.Join(outputDir, "device_metrics.csv"))
    networkFile, _ := os.Create(filepath.Join(outputDir, "network_metrics.csv"))
    edgeFile, _ := os.Create(filepath.Join(outputDir, "edge_metrics.csv"))
    crossTierFile, _ := os.Create(filepath.Join(outputDir, "cross_tier_metrics.csv"))

    mc := &MetricsCollector{
        deviceMetrics:  make(map[string][]*DeviceMetrics),
        edgeMetrics:    make(map[string][]*EdgeMetrics),
        deviceCSV:      csv.NewWriter(deviceFile),
        networkCSV:     csv.NewWriter(networkFile),
        edgeCSV:        csv.NewWriter(edgeFile),
        crossTierCSV:   csv.NewWriter(crossTierFile),
    }

    // Write CSV headers
    mc.deviceCSV.Write([]string{"node_id", "time_us", "cycles", "energy_uJ", "tx_bytes", "rx_bytes"})
    mc.networkCSV.Write([]string{"time_us", "packets_sent", "packets_delivered", "packets_dropped", "avg_latency_us"})
    mc.edgeCSV.Write([]string{"container_id", "time_us", "cpu_percent", "memory_mb", "requests_processed"})
    mc.crossTierCSV.Write([]string{"time_us", "e2e_latency_us", "total_energy_uJ", "ml_accuracy", "samples_processed"})

    return mc, nil
}

func (mc *MetricsCollector) Collect(targetTime uint64, allEvents map[string][]Event) {
    // Collect from devices
    for nodeID, events := range allEvents {
        for _, event := range events {
            switch event.Type {
            case "device_metrics":
                metrics := parseDeviceMetrics(event)
                mc.deviceMetrics[nodeID] = append(mc.deviceMetrics[nodeID], metrics)
                mc.writeDeviceMetricToCSV(metrics)

            case "network_metrics":
                metrics := parseNetworkMetrics(event)
                mc.networkMetrics = append(mc.networkMetrics, metrics)
                mc.writeNetworkMetricToCSV(metrics)

            case "edge_metrics":
                metrics := parseEdgeMetrics(event)
                mc.edgeMetrics[nodeID] = append(mc.edgeMetrics[nodeID], metrics)
                mc.writeEdgeMetricToCSV(metrics)
            }
        }
    }

    // Compute cross-tier metrics
    crossTier := mc.ComputeCrossTierMetrics(targetTime)
    mc.crossTier = append(mc.crossTier, crossTier)
    mc.writeCrossTierMetricToCSV(crossTier)
}

func (mc *MetricsCollector) ComputeCrossTierMetrics(targetTime uint64) *CrossTierMetrics {
    // Aggregate device energy
    totalEnergy := uint64(0)
    for _, deviceMetricsList := range mc.deviceMetrics {
        for _, m := range deviceMetricsList {
            totalEnergy += m.EnergyMicroJ
        }
    }

    // Compute end-to-end latency (from sample timestamps to result timestamps)
    avgE2ELatency := mc.computeAvgE2ELatency()

    // Compute ML accuracy (compare predictions to ground truth)
    mlAccuracy := mc.computeMLAccuracy()

    // Compute system throughput
    samplesProcessed := mc.countSamplesProcessed()

    return &CrossTierMetrics{
        TimeUs:            targetTime,
        EndToEndLatencyUs: avgE2ELatency,
        TotalEnergyMicroJ: totalEnergy,
        MLAccuracy:        mlAccuracy,
        SamplesProcessed:  samplesProcessed,
    }
}
```

---

### 3.4 Energy Modeling

**Device Energy Model:**

Renode doesn't natively track energy, so we use cycle-based estimation:

```go
// Energy model for nRF52840

const (
    ENERGY_PER_CYCLE_ACTIVE_NJ = 10   // ~10nJ per cycle at 64MHz
    ENERGY_SLEEP_MODE_UW       = 5    // 5μW in sleep mode
    ENERGY_TX_0DBM_UJ          = 50   // 50μJ per transmission at 0dBm
    ENERGY_RX_UJ               = 30   // 30μJ per reception
)

func (d *DeviceMetrics) EstimateEnergy() uint64 {
    // Active energy = cycles * energy_per_cycle
    activeEnergy := d.CyclesExecuted * ENERGY_PER_CYCLE_ACTIVE_NJ / 1000

    // Sleep energy = sleep_time * sleep_power
    sleepEnergy := d.SleepTimeUs * ENERGY_SLEEP_MODE_UW / 1000

    // Communication energy (from UART TX/RX events)
    commEnergy := d.TxPacketCount * ENERGY_TX_0DBM_UJ +
                  d.RxPacketCount * ENERGY_RX_UJ

    return activeEnergy + sleepEnergy + commEnergy
}
```

**Network Energy Model:**

Communication energy depends on packet size, TX power, and protocol overhead:

```go
func EstimateCommunicationEnergy(packetSize int, txPowerDbm int) uint64 {
    // Base TX energy at 0dBm
    baseTxEnergy := 50  // μJ

    // Adjust for TX power
    powerFactor := math.Pow(10, float64(txPowerDbm)/10.0)
    txEnergy := uint64(float64(baseTxEnergy) * powerFactor)

    // Add overhead for packet size
    sizeOverhead := uint64(packetSize) / 10  // ~0.1μJ per byte

    return txEnergy + sizeOverhead
}
```

---

### 3.5 Output Formats

**CSV Format (Primary):**

```csv
# device_metrics.csv
node_id,time_us,cycles,energy_uJ,tx_bytes,rx_bytes,sleep_time_us
sensor_1,10000,640000,320,64,0,0
sensor_1,20000,640000,320,0,32,0
sensor_2,10000,640000,320,64,0,0
...
```

```csv
# network_metrics.csv
time_us,packets_sent,packets_delivered,packets_dropped,avg_latency_us,channel_utilization
10000,20,20,0,1500,0.12
20000,20,19,1,1800,0.15
...
```

```csv
# cross_tier_metrics.csv
time_us,e2e_latency_us,total_energy_uJ,ml_accuracy,samples_processed,packet_delivery_rate
100000,5000,6400,0.92,20,1.0
200000,5200,12800,0.91,40,0.98
...
```

**JSON Format (Summary):**

```json
{
  "scenario": "vibration-baseline",
  "duration_s": 300,
  "summary": {
    "total_samples": 6000,
    "total_energy_mJ": 1920,
    "avg_e2e_latency_ms": 5.2,
    "ml_accuracy": 0.91,
    "packet_delivery_rate": 0.97
  },
  "per_device": {
    "sensor_1": {
      "samples": 300,
      "energy_mJ": 96,
      "tx_packets": 300,
      "rx_packets": 298
    }
  }
}
```

---

### 3.6 Analysis Scripts

**Python Analysis Tooling:**

```python
# scripts/analyze_metrics.py

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

class MetricsAnalyzer:
    def __init__(self, results_dir):
        self.results_dir = results_dir
        self.device_df = pd.read_csv(f'{results_dir}/device_metrics.csv')
        self.network_df = pd.read_csv(f'{results_dir}/network_metrics.csv')
        self.cross_tier_df = pd.read_csv(f'{results_dir}/cross_tier_metrics.csv')

    def plot_energy_over_time(self):
        """Plot cumulative energy consumption over time"""
        # Group by time and sum energy across all devices
        energy_by_time = self.device_df.groupby('time_us')['energy_uJ'].sum()
        energy_cumulative = energy_by_time.cumsum() / 1000  # Convert to mJ

        plt.figure(figsize=(10, 6))
        plt.plot(energy_cumulative.index / 1e6, energy_cumulative.values)
        plt.xlabel('Time (s)')
        plt.ylabel('Cumulative Energy (mJ)')
        plt.title('Total System Energy Consumption')
        plt.grid(True)
        plt.savefig(f'{self.results_dir}/energy_over_time.png')

    def plot_latency_distribution(self):
        """Plot end-to-end latency distribution"""
        plt.figure(figsize=(10, 6))
        plt.hist(self.cross_tier_df['e2e_latency_us'] / 1000, bins=50)
        plt.xlabel('End-to-End Latency (ms)')
        plt.ylabel('Frequency')
        plt.title('Latency Distribution')
        plt.grid(True)
        plt.savefig(f'{self.results_dir}/latency_distribution.png')

    def compute_summary_stats(self):
        """Compute summary statistics"""
        stats = {
            'total_samples': self.cross_tier_df['samples_processed'].sum(),
            'total_energy_mJ': self.device_df['energy_uJ'].sum() / 1000,
            'avg_e2e_latency_ms': self.cross_tier_df['e2e_latency_us'].mean() / 1000,
            'p95_latency_ms': self.cross_tier_df['e2e_latency_us'].quantile(0.95) / 1000,
            'ml_accuracy': self.cross_tier_df['ml_accuracy'].mean(),
            'packet_delivery_rate': (self.network_df['packets_delivered'].sum() /
                                      self.network_df['packets_sent'].sum())
        }
        return stats

    def generate_report(self):
        """Generate markdown report"""
        stats = self.compute_summary_stats()

        report = f"""
# Simulation Results: {self.results_dir}

## Summary Statistics

- **Total Samples Processed:** {stats['total_samples']}
- **Total Energy Consumed:** {stats['total_energy_mJ']:.2f} mJ
- **Average End-to-End Latency:** {stats['avg_e2e_latency_ms']:.2f} ms
- **P95 Latency:** {stats['p95_latency_ms']:.2f} ms
- **ML Accuracy:** {stats['ml_accuracy']:.2%}
- **Packet Delivery Rate:** {stats['packet_delivery_rate']:.2%}

## Figures

![Energy Over Time](energy_over_time.png)
![Latency Distribution](latency_distribution.png)
"""

        with open(f'{self.results_dir}/REPORT.md', 'w') as f:
            f.write(report)

if __name__ == '__main__':
    analyzer = MetricsAnalyzer(sys.argv[1])
    analyzer.plot_energy_over_time()
    analyzer.plot_latency_distribution()
    analyzer.generate_report()
    print(f"✅ Report generated: {sys.argv[1]}/REPORT.md")
```

---

## 4. ns-3 Integration Details

**Milestone:** M1 (network realism)

### 4.1 Overview

**Problem:** Current architecture.md mentions ns-3 but lacks concrete integration design.

**Solution:** Define ns-3 virtual time control, packet routing, and socket protocol.

---

### 4.2 ns-3 Virtual Time Control

**ns-3 Simulation Scheduler:**

ns-3 uses an event-driven simulator with virtual time. We need to control it from the coordinator:

```cpp
// ns3_wrapper.cc
// Custom ns-3 program that acts as socket-based simulation node

#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/internet-module.h"
#include "ns3/mobility-module.h"
#include "ns3/lr-wpan-module.h"
#include "ns3/applications-module.h"
#include <sys/socket.h>
#include <netinet/in.h>

using namespace ns3;

class Ns3CoordinatorInterface {
public:
    Ns3CoordinatorInterface(int port) {
        // Create socket server
        m_socketFd = socket(AF_INET, SOCK_STREAM, 0);

        struct sockaddr_in addr;
        addr.sin_family = AF_INET;
        addr.sin_port = htons(port);
        addr.sin_addr.s_addr = INADDR_ANY;

        bind(m_socketFd, (struct sockaddr*)&addr, sizeof(addr));
        listen(m_socketFd, 1);

        // Accept connection from coordinator
        m_clientFd = accept(m_socketFd, nullptr, nullptr);
    }

    void LoadTopology(std::string topologyFile) {
        // Parse topology YAML and create ns-3 nodes/links
        // (implementation details omitted for brevity)

        // Example: Create 20 device nodes + 1 gateway node
        NodeContainer devices;
        devices.Create(20);

        NodeContainer gateway;
        gateway.Create(1);

        // Install 802.15.4 on devices
        LrWpanHelper lrWpanHelper;
        NetDeviceContainer deviceNetDevices = lrWpanHelper.Install(devices);
        NetDeviceContainer gatewayNetDevice = lrWpanHelper.Install(gateway);

        // Set up mobility (grid topology)
        MobilityHelper mobility;
        mobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");
        mobility.Install(devices);
        mobility.Install(gateway);

        // Configure PHY/MAC parameters
        // (channel model, TX power, etc.)
    }

    void AdvanceTime(uint64_t targetTimeUs) {
        Time target = MicroSeconds(targetTimeUs);

        // Stop simulator at target time
        Simulator::Stop(target);

        // Run simulator until target
        Simulator::Run();

        // Now at target time, paused
        m_currentTimeUs = targetTimeUs;
    }

    void InjectPacket(std::string sourceNode, std::string destNode, std::vector<uint8_t> data) {
        // Find ns-3 nodes by ID
        Ptr<Node> src = GetNodeByID(sourceNode);
        Ptr<Node> dst = GetNodeByID(destNode);

        // Create packet
        Ptr<Packet> packet = Create<Packet>(data.data(), data.size());

        // Inject into ns-3 simulation
        // (send via source node's net device)
        Ptr<NetDevice> device = src->GetDevice(0);
        device->Send(packet, dst->GetDevice(0)->GetAddress(), 0x0800);
    }

    std::vector<Event> GetEvents() {
        // Return packets transmitted, received, dropped during last time step
        std::vector<Event> events;

        // Trace through ns-3 trace sources
        // (implementation uses ns-3 trace callbacks)

        return events;
    }

    void SendResponse(std::vector<Event> events) {
        // Serialize events to JSON and send via socket
        std::string json = SerializeEvents(events);
        send(m_clientFd, json.c_str(), json.size(), 0);
        send(m_clientFd, "\n", 1, 0);  // Delimiter
    }

    void ProcessCommands() {
        // Main loop: read commands from coordinator
        char buffer[4096];
        while (true) {
            ssize_t n = recv(m_clientFd, buffer, sizeof(buffer), 0);
            if (n <= 0) break;

            std::string command(buffer, n);

            if (command.starts_with("INIT")) {
                std::string topologyFile = ParseInitCommand(command);
                LoadTopology(topologyFile);
                send(m_clientFd, "OK\n", 3, 0);

            } else if (command.starts_with("ADVANCE")) {
                uint64_t targetTime = ParseAdvanceCommand(command);
                AdvanceTime(targetTime);

                std::vector<Event> events = GetEvents();
                SendResponse(events);

            } else if (command.starts_with("INJECT_PACKET")) {
                auto [src, dst, data] = ParseInjectCommand(command);
                InjectPacket(src, dst, data);
                send(m_clientFd, "OK\n", 3, 0);
            }
        }
    }

private:
    int m_socketFd;
    int m_clientFd;
    uint64_t m_currentTimeUs = 0;
};

int main(int argc, char *argv[]) {
    CommandLine cmd;
    int port = 5555;
    cmd.AddValue("port", "Coordinator socket port", port);
    cmd.Parse(argc, argv);

    Ns3CoordinatorInterface interface(port);
    interface.ProcessCommands();

    return 0;
}
```

**Build ns-3 Wrapper:**

```bash
# Build custom ns-3 program
cd ns-3-dev/scratch/
cp ~/xedgesim/sim/network/ns3_wrapper.cc .
cd ..
./waf build
./waf --run "scratch/ns3_wrapper --port=5555"
```

---

### 4.3 Packet Routing Architecture

**Device → ns-3 → Edge Flow:**

```
┌───────────────────────────────────────────────────────────┐
│              Packet Flow: Device → Edge                   │
└───────────────────────────────────────────────────────────┘

1. Device (Renode) sends packet via UART:
   Firmware calls: uart_send("PKT:1,10,64,<data>")

2. Coordinator receives UART event:
   Event{Type: "uart_tx", Source: "device_1", Data: "PKT:1,10,64,..."}

3. Coordinator parses packet:
   Packet{SrcID: 1, DstID: 10, Size: 64, Payload: <data>}

4. Coordinator injects into ns-3:
   ns3Node.InjectPacket("device_1", "gateway_1", data)

5. ns-3 simulates packet transmission:
   - Queue at device node
   - MAC protocol (CSMA/CA)
   - PHY transmission (radio model)
   - Propagation delay
   - Reception at gateway node

6. ns-3 returns packet RX event:
   Event{Type: "packet_rx", Source: "gateway_1", Latency: 15000us}

7. Coordinator forwards packet to edge:
   dockerNode.InjectPacket(data)

8. Edge container receives packet on TAP device:
   Container's eth0 receives raw Ethernet frame

9. Container processes packet:
   MQTT broker receives message, ML service runs inference

10. Container sends response packet:
    TX via eth0 (TAP device)

11. Coordinator reads TAP device:
    Response packet read from TAP

12. Coordinator injects response into ns-3:
    ns3Node.InjectPacket("gateway_1", "device_1", responseData)

13. ns-3 simulates return transmission

14. Coordinator forwards to device:
    renodeNode.InjectUART(responseData)

15. Device receives via UART:
    Firmware UART RX interrupt fires
```

---

### 4.4 ns-3 Coordinator Adapter

```go
// ns3_node.go

package coordinator

import (
    "bufio"
    "encoding/json"
    "fmt"
    "net"
)

type Ns3Node struct {
    conn          net.Conn
    currentTimeUs uint64
    topology      string
    nodeMap       map[string]int  // xEdgeSim node ID → ns-3 node index
}

func NewNs3Node(host string, port int, topologyFile string) (*Ns3Node, error) {
    conn, err := net.Dial("tcp", fmt.Sprintf("%s:%d", host, port))
    if err != nil {
        return nil, fmt.Errorf("failed to connect to ns-3: %w", err)
    }

    node := &Ns3Node{
        conn:          conn,
        currentTimeUs: 0,
        topology:      topologyFile,
        nodeMap:       make(map[string]int),
    }

    // Initialize ns-3 topology
    if err := node.execute(fmt.Sprintf("INIT %s", topologyFile)); err != nil {
        return nil, fmt.Errorf("failed to init ns-3: %w", err)
    }

    // Read "OK" response
    reader := bufio.NewReader(node.conn)
    response, _ := reader.ReadString('\n')
    if response != "OK\n" {
        return nil, fmt.Errorf("ns-3 init failed: %s", response)
    }

    return node, nil
}

func (n *Ns3Node) SendAdvanceCommand(targetTimeUs uint64) error {
    deltaUs := targetTimeUs - n.currentTimeUs
    return n.execute(fmt.Sprintf("ADVANCE %d", deltaUs))
}

func (n *Ns3Node) InjectPacket(srcNodeID, dstNodeID string, data []byte) error {
    // Convert node IDs to ns-3 node indices
    srcIdx := n.nodeMap[srcNodeID]
    dstIdx := n.nodeMap[dstNodeID]

    // Send inject command
    cmd := fmt.Sprintf("INJECT_PACKET %d %d %d %s",
        srcIdx, dstIdx, len(data), string(data))
    return n.execute(cmd)
}

func (n *Ns3Node) WaitForCompletion() ([]Event, error) {
    events := []Event{}
    reader := bufio.NewReader(n.conn)

    for {
        line, err := reader.ReadString('\n')
        if err != nil {
            return nil, err
        }

        // Parse JSON event
        if line == "SIMULATION_COMPLETE\n" {
            break
        }

        var event Event
        if err := json.Unmarshal([]byte(line), &event); err != nil {
            return nil, fmt.Errorf("failed to parse ns-3 event: %w", err)
        }

        events = append(events, event)
    }

    n.currentTimeUs = targetTimeUs
    return events, nil
}

func (n *Ns3Node) execute(command string) error {
    _, err := n.conn.Write([]byte(command + "\n"))
    return err
}
```

---

### 4.5 Decision: ns-3 as Separate Process

**Confirmed Architectural Decision:**

✅ **Use ns-3 as separate process with socket-based communication**

**Rationale:**
- **Isolation**: Crash in ns-3 doesn't crash coordinator
- **Language flexibility**: ns-3 is C++, coordinator can be Go or Python
- **Modularity**: Can swap ns-3 for OMNeT++ without changing coordinator
- **Debugging**: Easier to debug ns-3 separately
- **Distribution**: Can run ns-3 on different machine for scale

**Trade-off:**
- ❌ Socket overhead (~1-10μs per call)
- ✅ But negligible compared to time quantum (10ms = 10,000μs)

---

## 5. Docker Network Integration

**Milestone:** M2 (edge container realism)

### 5.1 Overview

**Problem:** How do Docker containers connect to ns-3 simulated network?

**Solution:** Use TAP/TUN devices with coordinator-mediated packet forwarding.

---

### 5.2 Network Architecture

```
┌─────────────────────────────────────────────────────────────┐
│           Docker ↔ ns-3 Network Integration                 │
└─────────────────────────────────────────────────────────────┘

┌──────────────────────────┐
│ Docker Container         │
│ (MQTT Broker + ML)       │
│   eth0: 10.0.1.1/24      │
└───────────┬──────────────┘
            │ veth pair
┌───────────▼──────────────┐
│  br-xedgesim (bridge)    │
└───────────┬──────────────┘
            │
┌───────────▼──────────────┐
│  tap-edge (TAP device)   │  Created by coordinator
└───────────┬──────────────┘
            │ Packets read/written by coordinator
            │
┌───────────▼──────────────┐
│   Coordinator            │  Forwards packets between TAP ↔ ns-3
│   (Go or Python)         │
└───────────┬──────────────┘
            │ Socket communication
┌───────────▼──────────────┐
│   ns-3 Simulator         │  Simulates network (delay, loss, etc.)
│   Gateway Node           │
└──────────────────────────┘
```

---

### 5.3 TAP Device Setup

**Coordinator TAP Device Management:**

```go
// tap_device.go

package coordinator

import (
    "os/exec"
    "github.com/songgao/water"
)

type TAPDevice struct {
    iface     *water.Interface
    ipAddress string
    bridge    string
}

func CreateTAPDevice(name, ipAddress, bridge string) (*TAPDevice, error) {
    // Create TAP device
    config := water.Config{
        DeviceType: water.TAP,
    }
    config.Name = name

    iface, err := water.New(config)
    if err != nil {
        return nil, fmt.Errorf("failed to create TAP: %w", err)
    }

    // Configure TAP device
    exec.Command("ip", "link", "set", name, "up").Run()
    exec.Command("ip", "addr", "add", ipAddress, "dev", name).Run()

    // Add to bridge
    exec.Command("ip", "link", "set", name, "master", bridge).Run()

    return &TAPDevice{
        iface:     iface,
        ipAddress: ipAddress,
        bridge:    bridge,
    }, nil
}

func (tap *TAPDevice) ReadPacket() ([]byte, error) {
    packet := make([]byte, 1522)  // Max Ethernet frame size
    n, err := tap.iface.Read(packet)
    if err != nil {
        return nil, err
    }
    return packet[:n], nil
}

func (tap *TAPDevice) WritePacket(packet []byte) error {
    _, err := tap.iface.Write(packet)
    return err
}

func (tap *TAPDevice) Close() error {
    exec.Command("ip", "link", "delete", tap.iface.Name()).Run()
    return tap.iface.Close()
}
```

---

### 5.4 Docker Container Network Setup

**Docker Network Creation:**

```bash
# Coordinator creates bridge network for xEdgeSim
docker network create \
    --driver bridge \
    --subnet 10.0.1.0/24 \
    --gateway 10.0.1.254 \
    xedgesim-net
```

**Container Launch:**

```go
// docker_node.go

package coordinator

import (
    "context"
    "github.com/docker/docker/api/types"
    "github.com/docker/docker/api/types/container"
    "github.com/docker/docker/api/types/network"
    "github.com/docker/docker/client"
)

type DockerNode struct {
    containerID   string
    tapDevice     *TAPDevice
    ipAddress     string
    dockerClient  *client.Client
    packetBuffer  [][]byte
}

func NewDockerNode(image, ipAddress string) (*DockerNode, error) {
    ctx := context.Background()
    cli, err := client.NewClientWithOpts(client.FromEnv)
    if err != nil {
        return nil, err
    }

    // Create TAP device
    tapDev, err := CreateTAPDevice("tap-edge", "10.0.1.253/24", "br-xedgesim")
    if err != nil {
        return nil, err
    }

    // Create container
    resp, err := cli.ContainerCreate(ctx,
        &container.Config{
            Image: image,
            Env: []string{
                "MQTT_PORT=1883",
                "ML_MODEL=/app/models/anomaly.onnx",
            },
        },
        &container.HostConfig{
            NetworkMode: "xedgesim-net",
        },
        &network.NetworkingConfig{
            EndpointsConfig: map[string]*network.EndpointSettings{
                "xedgesim-net": {
                    IPAMConfig: &network.EndpointIPAMConfig{
                        IPv4Address: ipAddress,
                    },
                },
            },
        },
        nil,
        "xedgesim-edge-"+generateID(),
    )
    if err != nil {
        return nil, err
    }

    // Start container
    if err := cli.ContainerStart(ctx, resp.ID, types.ContainerStartOptions{}); err != nil {
        return nil, err
    }

    return &DockerNode{
        containerID:  resp.ID,
        tapDevice:    tapDev,
        ipAddress:    ipAddress,
        dockerClient: cli,
        packetBuffer: make([][]byte, 0),
    }, nil
}

func (d *DockerNode) SendAdvanceCommand(targetTimeUs uint64) error {
    // Advance container execution (wall-clock time, not controlled)
    // Simply let it run for deltaUs in real time
    deltaUs := targetTimeUs - d.currentTimeUs
    time.Sleep(time.Microsecond * time.Duration(deltaUs))

    // Meanwhile, read any packets from TAP device (non-blocking)
    d.readPacketsFromTAP()

    return nil
}

func (d *DockerNode) readPacketsFromTAP() {
    // Non-blocking read from TAP device
    // (use select with timeout or non-blocking I/O)
    for {
        packet, err := d.tapDevice.ReadPacketNonBlocking()
        if err != nil || packet == nil {
            break  // No more packets
        }
        d.packetBuffer = append(d.packetBuffer, packet)
    }
}

func (d *DockerNode) InjectPacket(packet []byte) error {
    // Write packet to TAP device
    // Container receives it on eth0
    return d.tapDevice.WritePacket(packet)
}

func (d *DockerNode) WaitForCompletion() ([]Event, error) {
    // Return buffered packets as events
    events := []Event{}

    for _, packet := range d.packetBuffer {
        events = append(events, Event{
            Type:   "packet_from_edge",
            Source: d.containerID,
            Data:   packet,
        })
    }

    // Clear buffer
    d.packetBuffer = d.packetBuffer[:0]

    // Also collect Docker container metrics
    stats, err := d.getContainerStats()
    if err == nil {
        events = append(events, Event{
            Type: "edge_metrics",
            Data: stats,
        })
    }

    return events, nil
}

func (d *DockerNode) getContainerStats() (*EdgeMetrics, error) {
    ctx := context.Background()
    stats, err := d.dockerClient.ContainerStats(ctx, d.containerID, false)
    if err != nil {
        return nil, err
    }
    defer stats.Body.Close()

    // Parse stats JSON
    // (implementation details omitted)

    return &EdgeMetrics{
        ContainerID:     d.containerID,
        CPUUsagePercent: cpuPercent,
        MemoryUsageMB:   memoryMB,
    }, nil
}
```

---

### 5.5 Packet Forwarding Loop

**Coordinator Packet Router:**

```go
func (c *Coordinator) routeMessages(allEvents map[string][]Event) {
    for nodeName, events := range allEvents {
        for _, event := range events {
            switch event.Type {
            case "packet_from_device":
                // Device sent packet → inject into ns-3
                ns3Node := c.nodes["network"].(*Ns3Node)
                ns3Node.InjectPacket(event.Source, event.Dest, event.Data)

            case "packet_from_ns3_to_edge":
                // ns-3 delivered packet to gateway → inject into Docker
                edgeNode := c.nodes["edge1"].(*DockerNode)
                edgeNode.InjectPacket(event.Data)

            case "packet_from_edge":
                // Docker sent packet → inject back into ns-3
                ns3Node := c.nodes["network"].(*Ns3Node)
                ns3Node.InjectPacket("gateway_1", event.Dest, event.Data)

            case "packet_from_ns3_to_device":
                // ns-3 delivered packet to device → inject into Renode
                deviceNode := c.nodes[event.Dest].(*RenodeNode)
                deviceNode.InjectUART(event.Data)
            }
        }
    }
}
```

---

## 6. Deployability Architecture

**Milestone:** M2 (documentation), M4 (automation)

### 6.1 Overview

**Promise:** "Deployable artifacts: Same firmware/containers used in simulation deploy to production"

**Delivery:** Architect build pipelines and configuration management for firmware and containers.

---

### 6.2 Firmware Deployability Pipeline

**Build System (Zephyr Example):**

```makefile
# sim/device/firmware/Makefile

BOARD ?= nrf52840dk_nrf52840
BUILD_DIR = build/$(BOARD)

.PHONY: all clean flash simulate

all: $(BUILD_DIR)/zephyr/zephyr.elf

$(BUILD_DIR)/zephyr/zephyr.elf: src/*.c prj.conf
	west build -b $(BOARD) src/ -d $(BUILD_DIR)

flash: all
	# Flash to real hardware
	west flash -d $(BUILD_DIR)

simulate: all
	# Run in Renode (simulation)
	renode -e "include @sim/device/renode/nrf52840.resc; \
	           sysbus LoadELF @$(BUILD_DIR)/zephyr/zephyr.elf; \
	           start"

clean:
	rm -rf build/
```

**No Simulation-Specific Code in Firmware:**

```c
// src/main.c - Same code runs on hardware and simulation

#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/drivers/uart.h>
#include <zephyr/drivers/gpio.h>

// No #ifdef SIMULATION - same code path everywhere

void main(void) {
    const struct device *uart = DEVICE_DT_GET(DT_NODELABEL(uart0));
    const struct device *gpio = DEVICE_DT_GET(DT_NODELABEL(gpio0));

    // Initialize peripherals (same on HW and simulation)
    uart_configure(uart, &uart_cfg);
    gpio_pin_configure(gpio, LED_PIN, GPIO_OUTPUT);

    // Main loop (same on HW and simulation)
    while (1) {
        float data = read_sensor();
        transmit_data(uart, data);
        k_sleep(K_SECONDS(1));
    }
}
```

**Key Principle:** Hardware Abstraction Layer (Zephyr Device Tree) handles differences between simulation and real hardware transparently.

---

### 6.3 Container Deployability Pipeline

**Dockerfile (Same for Simulation and Production):**

```dockerfile
# edge/mqtt-ml-inference/Dockerfile

FROM python:3.11-slim

# Install MQTT broker
RUN apt-get update && \
    apt-get install -y mosquitto && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy application code
COPY ml_inference_service.py /app/
COPY config/ /app/config/

# Expose MQTT port
EXPOSE 1883

# Start services
CMD ["sh", "-c", "mosquitto -c /app/config/mosquitto.conf & python /app/ml_inference_service.py"]
```

**Configuration Abstraction:**

Use environment variables for simulation vs production differences:

```yaml
# docker-compose.simulation.yml
services:
  mqtt_broker:
    image: xedgesim/mqtt-ml:latest
    environment:
      - MQTT_HOST=0.0.0.0
      - MQTT_PORT=1883
      - LOG_LEVEL=DEBUG  # More verbose in simulation
      - SIMULATION=true
    networks:
      - xedgesim-net
```

```yaml
# docker-compose.production.yml
services:
  mqtt_broker:
    image: xedgesim/mqtt-ml:latest
    environment:
      - MQTT_HOST=0.0.0.0
      - MQTT_PORT=1883
      - LOG_LEVEL=INFO
      - SIMULATION=false
    network_mode: host  # Use host network in production
    restart: always
```

**Application Code Adapts to Environment:**

```python
# ml_inference_service.py

import os

SIMULATION = os.getenv('SIMULATION', 'false').lower() == 'true'
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

if SIMULATION:
    # In simulation: log more, accept test certificates, etc.
    logger.setLevel(logging.DEBUG)
    mqtt_client.tls_insecure_set(True)
else:
    # In production: normal logging, strict security
    logger.setLevel(logging.INFO)
    mqtt_client.tls_set(ca_certs="/etc/ssl/certs/ca-certificates.crt")
```

---

### 6.4 Deployment Workflow

**1. Development → Simulation:**

```bash
# Developer builds firmware
cd sim/device/firmware
make all BOARD=nrf52840dk

# Developer builds container
cd edge/mqtt-ml-inference
docker build -t xedgesim/mqtt-ml:dev .

# Run simulation
xedgesim run scenarios/test-deployment/config.yaml
```

**2. Simulation → Staging:**

```bash
# Deploy to staging environment (real gateway hardware, test network)
# Flash firmware to real nRF52840 boards
cd sim/device/firmware
make flash BOARD=nrf52840dk

# Deploy container to staging gateway
ssh gateway-staging
docker pull xedgesim/mqtt-ml:dev
docker-compose -f docker-compose.staging.yml up -d
```

**3. Staging → Production:**

```bash
# Tag and push Docker image
docker tag xedgesim/mqtt-ml:dev xedgesim/mqtt-ml:v1.0.0
docker push xedgesim/mqtt-ml:v1.0.0

# Deploy to production gateways
ansible-playbook deploy-production.yml \
    -e "docker_image=xedgesim/mqtt-ml:v1.0.0"

# Flash firmware to production sensors
./scripts/flash-all-sensors.sh firmware.elf
```

---

### 6.5 Testing Strategy

**Simulation → Staging → Production Pipeline:**

```
┌─────────────────────────────────────────────────────────────┐
│              Deployment Testing Pipeline                    │
└─────────────────────────────────────────────────────────────┘

Stage 1: Simulation (xEdgeSim)
├─ Fast iteration (~minutes)
├─ Deterministic, repeatable
├─ Test edge cases, faults, scale
└─ Validate: functionality, correctness

Stage 2: Staging (Real Hardware, Test Network)
├─ 1-10 real sensor nodes
├─ 1 real gateway
├─ Test network
├─ Moderate iteration (~hours)
└─ Validate: hardware compatibility, timing, integration

Stage 3: Production (Real Deployment)
├─ 100s-1000s of sensors
├─ Multiple gateways
├─ Real network
├─ Slow iteration (~days/weeks)
└─ Validate: performance at scale, reliability, security
```

**Continuous Integration:**

```yaml
# .github/workflows/deploy-pipeline.yml

name: Deployment Pipeline

on: [push]

jobs:
  test-in-simulation:
    runs-on: ubuntu-latest
    steps:
      - name: Build firmware
        run: make all
      - name: Build containers
        run: docker build -t xedgesim/mqtt-ml:${{ github.sha }} .
      - name: Run xEdgeSim simulation
        run: xedgesim run scenarios/ci-test/config.yaml
      - name: Validate results
        run: python scripts/validate_results.py results/ci-test/

  deploy-to-staging:
    needs: test-in-simulation
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - name: Push Docker image
        run: docker push xedgesim/mqtt-ml:${{ github.sha }}
      - name: Deploy to staging
        run: ./scripts/deploy-staging.sh ${{ github.sha }}

  deploy-to-production:
    needs: deploy-to-staging
    if: github.ref == 'refs/tags/v*'
    runs-on: ubuntu-latest
    steps:
      - name: Tag Docker image
        run: docker tag xedgesim/mqtt-ml:${{ github.sha }} xedgesim/mqtt-ml:${{ github.ref_name }}
      - name: Deploy to production
        run: ansible-playbook deploy-production.yml
```

---

## 7. CI/CD Integration

**Milestone:** M2-M4 (incremental automation)

### 7.1 Overview

**Promise:** "CI/CD friendliness: xEdgeSim will integrate with continuous integration pipelines"

**Delivery:** Headless execution, result validation, GitHub Actions integration.

---

### 7.2 Headless Execution

**CLI Design:**

```bash
# Run simulation (no GUI)
$ xedgesim run scenarios/test.yaml

# Output:
[2025-01-13 10:00:00] Loading scenario: test.yaml
[2025-01-13 10:00:01] Spawning 20 Renode instances...
[2025-01-13 10:00:05] Starting ns-3 simulator...
[2025-01-13 10:00:06] Launching Docker containers...
[2025-01-13 10:00:08] Simulation running... (0%)
[2025-01-13 10:01:08] Simulation running... (20%)
[2025-01-13 10:02:08] Simulation running... (40%)
[2025-01-13 10:03:08] Simulation running... (60%)
[2025-01-13 10:04:08] Simulation running... (80%)
[2025-01-13 10:05:08] Simulation complete (100%)
[2025-01-13 10:05:09] Shutting down components...
[2025-01-13 10:05:12] Validating results...
[2025-01-13 10:05:13] ✅ All assertions passed
[2025-01-13 10:05:13] Results: results/test/2025-01-13_10-00-00/

# Exit code: 0 (success)
```

**Exit Codes:**

- `0`: Success (all assertions passed)
- `1`: Simulation error (crash, timeout)
- `2`: Validation error (assertions failed)
- `3`: Configuration error (invalid YAML)

---

### 7.3 Result Validation Framework

**Validation Config in Scenario YAML:**

```yaml
validation:
  assertions:
    - metric: total_packets_sent
      operator: gte  # >=
      value: 5000
      description: "Expect ~6000 packets from 20 devices over 5 minutes"

    - metric: packet_delivery_rate
      operator: gte
      value: 0.95
      description: "Expect >95% delivery rate in good conditions"

    - metric: ml_accuracy
      operator: gte
      value: 0.85
      description: "Expect >85% ML accuracy"

    - metric: avg_e2e_latency_ms
      operator: lte  # <=
      value: 100
      description: "Expect <100ms end-to-end latency"
```

**Validation Engine:**

```go
// validator.go

package coordinator

type Assertion struct {
    Metric      string
    Operator    string  // "eq", "gte", "lte", "gt", "lt"
    Value       float64
    Description string
}

func ValidateResults(resultsDir string, assertions []Assertion) error {
    // Load metrics
    crossTierDF, err := loadCSV(filepath.Join(resultsDir, "cross_tier_metrics.csv"))
    if err != nil {
        return err
    }

    // Compute actual values
    actualMetrics := map[string]float64{
        "total_packets_sent":    computeTotalPackets(crossTierDF),
        "packet_delivery_rate":  computeDeliveryRate(crossTierDF),
        "ml_accuracy":           computeMLAccuracy(crossTierDF),
        "avg_e2e_latency_ms":    computeAvgLatency(crossTierDF),
    }

    // Check each assertion
    failed := []string{}

    for _, assertion := range assertions {
        actualValue, ok := actualMetrics[assertion.Metric]
        if !ok {
            return fmt.Errorf("metric not found: %s", assertion.Metric)
        }

        passed := checkAssertion(actualValue, assertion.Operator, assertion.Value)

        if passed {
            log.Printf("✅ PASS: %s (%.2f %s %.2f) - %s",
                assertion.Metric, actualValue, assertion.Operator, assertion.Value, assertion.Description)
        } else {
            log.Printf("❌ FAIL: %s (%.2f %s %.2f) - %s",
                assertion.Metric, actualValue, assertion.Operator, assertion.Value, assertion.Description)
            failed = append(failed, assertion.Metric)
        }
    }

    if len(failed) > 0 {
        return fmt.Errorf("validation failed: %d assertions failed: %v", len(failed), failed)
    }

    return nil
}

func checkAssertion(actual float64, op string, expected float64) bool {
    switch op {
    case "eq": return actual == expected
    case "gte": return actual >= expected
    case "lte": return actual <= expected
    case "gt": return actual > expected
    case "lt": return actual < expected
    default: return false
    }
}
```

---

### 7.4 GitHub Actions Integration

**Complete CI Workflow:**

```yaml
# .github/workflows/test-scenarios.yml

name: Test xEdgeSim Scenarios

on:
  push:
    branches: [main, dev]
  pull_request:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v4

    - name: Set up Go
      uses: actions/setup-go@v4
      with:
        go-version: '1.21'

    - name: Install Renode
      run: |
        wget https://github.com/renode/renode/releases/download/v1.15.0/renode_1.15.0_amd64.deb
        sudo apt install -y ./renode_1.15.0_amd64.deb

    - name: Install ns-3
      run: |
        git clone https://gitlab.com/nsnam/ns-3-dev.git
        cd ns-3-dev
        ./ns3 configure --enable-examples --enable-tests
        ./ns3 build

    - name: Build coordinator
      run: |
        cd sim/coordinator
        go build -o xedgesim-coordinator

    - name: Build firmware
      run: |
        pip install west
        west init -l sim/device/firmware
        west update
        cd sim/device/firmware
        west build -b nrf52840dk_nrf52840

    - name: Build Docker images
      run: |
        cd edge/mqtt-ml-inference
        docker build -t xedgesim/mqtt-ml:ci .

    - name: Run M0 scenario (device-only)
      run: |
        ./sim/coordinator/xedgesim-coordinator run scenarios/m0-device-only/config.yaml
      timeout-minutes: 10

    - name: Run M1 scenario (with network)
      run: |
        ./sim/coordinator/xedgesim-coordinator run scenarios/m1-with-network/config.yaml
      timeout-minutes: 15

    - name: Run M2 scenario (with edge)
      run: |
        ./sim/coordinator/xedgesim-coordinator run scenarios/m2-with-edge/config.yaml
      timeout-minutes: 20

    - name: Run ML placement comparison
      run: |
        ./sim/coordinator/xedgesim-coordinator batch scenarios/ml-placement-batch.yaml
      timeout-minutes: 30

    - name: Generate analysis reports
      run: |
        python scripts/analyze_batch_results.py results/ml-placement-comparison/

    - name: Upload results as artifacts
      uses: actions/upload-artifact@v3
      with:
        name: simulation-results-${{ github.sha }}
        path: results/

    - name: Upload plots
      uses: actions/upload-artifact@v3
      with:
        name: plots-${{ github.sha }}
        path: figures/

    - name: Comment PR with results
      if: github.event_name == 'pull_request'
      uses: actions/github-script@v6
      with:
        script: |
          const fs = require('fs');
          const summary = fs.readFileSync('results/ml-placement-comparison/SUMMARY.md', 'utf8');
          github.rest.issues.createComment({
            issue_number: context.issue.number,
            owner: context.repo.owner,
            repo: context.repo.repo,
            body: `## Simulation Results\n\n${summary}`
          });
```

---

### 7.5 Docker-Based Testing Environment

**Reproducible CI Environment:**

```dockerfile
# Dockerfile.ci

FROM ubuntu:22.04

# Install dependencies
RUN apt-get update && apt-get install -y \
    git \
    cmake \
    build-essential \
    python3 \
    python3-pip \
    wget \
    mono-complete \
    docker.io

# Install Renode
RUN wget https://github.com/renode/renode/releases/download/v1.15.0/renode_1.15.0_amd64.deb && \
    apt install -y ./renode_1.15.0_amd64.deb

# Install ns-3
RUN git clone https://gitlab.com/nsnam/ns-3-dev.git /ns-3 && \
    cd /ns-3 && \
    ./ns3 configure && \
    ./ns3 build

# Install Go
RUN wget https://go.dev/dl/go1.21.6.linux-amd64.tar.gz && \
    tar -C /usr/local -xzf go1.21.6.linux-amd64.tar.gz

ENV PATH="/usr/local/go/bin:${PATH}"

# Copy xEdgeSim
COPY . /xedgesim
WORKDIR /xedgesim

# Build coordinator
RUN cd sim/coordinator && go build -o xedgesim-coordinator

CMD ["./sim/coordinator/xedgesim-coordinator", "run", "scenarios/test.yaml"]
```

**Run in Docker:**

```bash
# Build CI image
docker build -t xedgesim-ci -f Dockerfile.ci .

# Run tests in container
docker run --rm xedgesim-ci
```

---

## 8. Scalability Architecture

**Milestone:** M3-M4 (mixed abstraction, optimization)

### 8.1 Overview

**Promise:** "Scalability studies: Testing with 100-1000+ devices (COOJA limited to ~50-100)"

**Delivery:** Mixed abstraction levels with Python models for bulk devices.

---

### 8.2 Mixed Abstraction Strategy

**Principle:** Use expensive emulation (Renode) for critical devices, fast models for bulk devices.

```
┌─────────────────────────────────────────────────────────────┐
│              Mixed Abstraction Architecture                 │
└─────────────────────────────────────────────────────────────┘

Tier 1: Full Emulation (10-50 devices)
├─ Renode instruction-level emulation
├─ Real firmware (ELF binary)
├─ Cycle-accurate
└─ Use for: Devices under test, protocol debugging

Tier 2: Behavioral Models (100-1000 devices)
├─ Python/Go event-driven models
├─ Model behavior, not implementation
├─ ~1000x faster than emulation
└─ Use for: Background traffic, network load

Example:
  10 Renode nodes (critical sensors)
  + 990 Model nodes (bulk sensors)
  = 1000 total devices in simulation
```

---

### 8.3 Device Model API

**Model Node Interface:**

```python
# models/device_model.py

import random
import time

class DeviceModel:
    """
    Abstract device model for scalability.

    Models device behavior without instruction-level emulation:
    - Periodic sampling and transmission
    - Energy consumption estimation
    - Simple radio protocol
    """

    def __init__(self, node_id, config):
        self.node_id = node_id
        self.sample_rate = config['sample_rate']  # Hz
        self.report_interval = config['report_interval']  # seconds
        self.packet_size = config['packet_size']  # bytes
        self.tx_power_dbm = config['tx_power']

        # Energy model parameters
        self.energy_per_sample_uJ = 10
        self.energy_per_tx_uJ = 50 * (10 ** (self.tx_power_dbm / 10.0))
        self.energy_idle_uw = 5  # μW in idle

        # State
        self.current_time_us = 0
        self.next_report_time_us = self.report_interval * 1e6
        self.samples_buffer = []

    def advance(self, target_time_us):
        """
        Advance model from current_time to target_time.

        Returns list of events that occurred during this time period.
        """
        events = []
        delta_us = target_time_us - self.current_time_us

        # How many samples in this time window?
        num_samples = int((delta_us / 1e6) * self.sample_rate)

        for i in range(num_samples):
            # Generate synthetic sample
            sample = self.generate_sample()
            self.samples_buffer.append(sample)

            # Energy for sampling
            events.append({
                'type': 'energy',
                'node_id': self.node_id,
                'amount_uJ': self.energy_per_sample_uJ
            })

        # Check if it's time to report
        if target_time_us >= self.next_report_time_us:
            # Generate packet
            packet = self.create_packet(self.samples_buffer)

            events.append({
                'type': 'packet_tx',
                'node_id': self.node_id,
                'size': len(packet),
                'data': packet,
                'dest': 'gateway',
                'tx_power_dbm': self.tx_power_dbm
            })

            # Energy for transmission
            events.append({
                'type': 'energy',
                'node_id': self.node_id,
                'amount_uJ': self.energy_per_tx_uJ
            })

            # Clear buffer and schedule next report
            self.samples_buffer = []
            self.next_report_time_us += self.report_interval * 1e6

        # Idle energy
        idle_energy_uJ = (delta_us / 1e6) * self.energy_idle_uw
        events.append({
            'type': 'energy',
            'node_id': self.node_id,
            'amount_uJ': idle_energy_uJ
        })

        self.current_time_us = target_time_us
        return events

    def generate_sample(self):
        """Generate synthetic vibration sample"""
        # Simple synthetic data (normal + anomaly)
        if random.random() < 0.05:  # 5% anomaly rate
            return random.gauss(100, 20)  # Anomalous vibration
        else:
            return random.gauss(10, 2)    # Normal vibration

    def create_packet(self, samples):
        """Create packet from buffered samples"""
        # Simplified packet format
        packet = {
            'node_id': self.node_id,
            'timestamp': self.current_time_us,
            'samples': samples[:10],  # Send last 10 samples
            'rms': sum(samples) / len(samples) if samples else 0
        }
        return json.dumps(packet).encode()
```

---

### 8.4 Coordinator Integration

**Unified Node Interface:**

```go
// node.go

package coordinator

// All node types (Renode, ns-3, Docker, Model) implement this interface
type Node interface {
    SendAdvanceCommand(targetTimeUs uint64) error
    WaitForCompletion() ([]Event, error)
    Shutdown() error
}

// Model node wraps Python model
type ModelNode struct {
    pythonProcess *exec.Cmd
    conn          net.Conn
    nodeID        string
    currentTimeUs uint64
}

func NewModelNode(nodeID string, modelScript string, config map[string]interface{}) (*ModelNode, error) {
    // Start Python model as subprocess
    cmd := exec.Command("python3", modelScript, "--node-id", nodeID)

    // Set up socket communication
    // (Python model acts as socket server)
    conn, err := net.Dial("tcp", fmt.Sprintf("localhost:%d", getAvailablePort()))
    if err != nil {
        return nil, err
    }

    // Send config to model
    configJSON, _ := json.Marshal(config)
    conn.Write(configJSON)
    conn.Write([]byte("\n"))

    return &ModelNode{
        pythonProcess: cmd,
        conn:          conn,
        nodeID:        nodeID,
        currentTimeUs: 0,
    }, nil
}

func (m *ModelNode) SendAdvanceCommand(targetTimeUs uint64) error {
    // Send advance command to Python model
    cmd := fmt.Sprintf("ADVANCE %d\n", targetTimeUs)
    _, err := m.conn.Write([]byte(cmd))
    return err
}

func (m *ModelNode) WaitForCompletion() ([]Event, error) {
    // Read events from Python model
    reader := bufio.NewReader(m.conn)
    var events []Event

    for {
        line, err := reader.ReadString('\n')
        if err != nil {
            return nil, err
        }

        if line == "DONE\n" {
            break
        }

        var event Event
        json.Unmarshal([]byte(line), &event)
        events = append(events, event)
    }

    m.currentTimeUs = targetTimeUs
    return events, nil
}
```

**Scenario with Mixed Nodes:**

```yaml
# scenarios/scalability-test/config.yaml

scenario:
  name: scalability-1000-devices
  duration: 300s

devices:
  # 10 critical devices with full emulation
  - id: critical_sensors
    count: 10
    type: renode  # Full instruction-level emulation
    platform: nrf52840dk
    firmware: builds/vib_sensor.elf
    config:
      sample_rate: 1000Hz
      report_interval: 1s

  # 990 bulk devices with behavioral models
  - id: bulk_sensors
    count: 990
    type: model  # Fast behavioral model
    model: models/device_model.py
    config:
      sample_rate: 1000Hz
      report_interval: 1s
      packet_size: 64
      tx_power: 0

network:
  type: ns3
  topology: star
  wireless:
    protocol: 802.15.4
```

---

### 8.5 Performance Budget

**Execution Time Estimates:**

| Component | 1 Device | 10 Devices | 100 Devices | 1000 Devices |
|-----------|----------|------------|-------------|--------------|
| **Renode** | 1-10x real-time | 10-100x | — | — |
| **Model** | 1000x | 1000x | 100x | 10x |
| **ns-3** | — | 1-10x | 10x | 100x |
| **Coordinator** | Negligible | <1% | <5% | <10% |

**Bottleneck Analysis:**

- **10 devices**: Renode is bottleneck (~10x real-time)
- **100 devices**: ns-3 is bottleneck (~10x real-time)
- **1000 devices**: ns-3 is primary bottleneck (~100x real-time)

**With Mixed Abstraction:**
- 10 Renode + 990 models: ~10x real-time (dominated by Renode)
- ns-3 with 1000 nodes: ~100x real-time

**Total for 1000 devices: ~100-200x real-time (~8-16 hours for 5-minute simulation)**

---

### 8.6 Scalability Validation

**Scenario for Scalability Test:**

```yaml
scenarios:
  - name: scale-10
    devices: 10 Renode
  - name: scale-100
    devices: 10 Renode + 90 models
  - name: scale-1000
    devices: 10 Renode + 990 models
  - name: scale-10000
    devices: 10 Renode + 9990 models
```

**Expected Results:**

| Scale | Wall-Clock Time (5min sim) | Memory Usage | Validates |
|-------|----------------------------|--------------|-----------|
| 10 | ~50 minutes | ~2 GB | Basic functionality |
| 100 | ~80 minutes | ~4 GB | Network protocols under load |
| 1000 | ~8 hours | ~8 GB | Edge gateway scalability |
| 10000 | ~24 hours | ~16 GB | Cloud backend scalability |

---

## Conclusion

**The federated co-simulation architecture with tiered determinism is the right approach for xEdgeSim.**

**Key strengths (existing)**:
1. ✅ Proven by SimBricks for datacenter systems
2. ✅ Adapts to IoT-edge-cloud domain
3. ✅ Balances realism (deployability) with reproducibility (determinism)
4. ✅ Extensible (add components via socket protocol)
5. ✅ Scalable (distributed processes, mixed abstraction)

**Key innovations (existing)**:
1. **Hybrid determinism**: Full where critical, statistical where acceptable
2. **Variable fidelity**: Appropriate accuracy per tier
3. **Deployable artifacts**: Firmware + containers tested in simulation deploy to production
4. **ML placement focus**: First-class support for device/edge/cloud inference experiments

**New architectural components (added in this extension)**:
5. **ML placement framework** (Section 13): Complete architecture for device/edge/cloud ML experiments
6. **Scenario specification** (Section 14): YAML schema and execution flow
7. **Metrics collection** (Section 15): Cross-tier metrics aggregation and analysis
8. **ns-3 integration** (Section 16): Virtual time control and packet routing
9. **Docker networking** (Section 17): TAP/TUN-based network integration
10. **Deployability pipeline** (Section 18): Firmware and container deployment workflows
11. **CI/CD integration** (Section 19): Headless execution, validation, GitHub Actions
12. **Scalability architecture** (Section 20): Mixed abstraction with Python models

**This extended architecture now fully delivers on the promises made in related-work-notes.md and positions xEdgeSim as the first variable-fidelity cross-tier co-simulation platform for IoT–edge–cloud systems with comprehensive ML placement support.**

---

**Document Status**: ✅ Extended with comprehensive architectural details covering all identified gaps. Ready for M0 implementation with clear guidance on ML placement framework (M3), scenario specification, metrics collection, ns-3 integration, Docker networking, deployability, CI/CD, and scalability.
