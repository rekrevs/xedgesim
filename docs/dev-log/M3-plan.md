# M3 Plan: ML Placement Framework

**Date:** 2025-11-15
**Status:** PLANNING
**Major Stage:** M3 - Add Research Value

---

## Goal

Implement the ML placement framework - xEdgeSim's core research contribution. Enable realistic evaluation of ML inference placement decisions across device, edge, and cloud tiers.

**Key differentiator:** Unlike existing simulators (iFogSim, EdgeCloudSim), xEdgeSim runs *actual ML models* and measures *real inference latency*, not abstract models.

**M3 delivers:**
1. Edge ML inference (ONNX Runtime in Docker containers)
2. Cloud ML inference (PyTorch in Python services)
3. ML placement comparison framework
4. Metrics collection for accuracy, latency, energy trade-offs
5. Example placement experiments demonstrating the approach

**Explicitly deferred:**
- Device firmware with TFLite (requires Renode integration - defer to M4+)
- Full Pareto frontier analysis (basic comparison sufficient for M3)
- Multi-model inference pipelines
- Federated learning

---

## Context and Scope

### What M2 Delivered

- Docker container support for edge services
- Real MQTT broker integration
- Hybrid approach (Docker OR Python per scenario)
- Deployability foundation (sim-to-prod)
- YAML schema with `implementation` field

**Current state**: Can run real edge services (MQTT broker) in containers. Ready to add ML inference.

### What M3 Should Add (from architecture.md)

Per architecture.md Section 2.2.3 and implementation-guide.md Section 1:

- ML placement framework (device/edge/cloud variants)
- Run actual ML models (TFLite, ONNX, PyTorch)
- Evaluate placement variants (device-only, edge-only, cloud-only)
- Measure accuracy, latency, energy trade-offs
- Demonstrate "killer app" research contribution

### What M3 Should NOT Add

**Device TFLite integration deferred:**
- Rationale: Requires Renode firmware development (major complexity)
- M2 gap analysis showed Python device models sufficient for now
- Can add in M4+ if needed for realism

**Full Pareto frontier analysis deferred:**
- Rationale: Basic comparison demonstrates capability
- Complex analysis is post-simulation analysis (Python scripts)
- Can add automated analysis in M4+

**Production ML deployment deferred:**
- Rationale: M3 proves concept, M4 adds production polish
- Focus: Validate placement decisions in simulation
- Deployment uses M2 infrastructure

**Philosophy**: Following architecture.md Section 2 "Implementation Philosophy", we prioritize demonstrating the ML placement capability with real models while keeping the system testable.

---

## Design Decision: M3 Scope

### Key Architectural Question

**How to implement ML placement framework without Renode?**

Three options considered:

1. **Full architecture** (Device TFLite + Edge ONNX + Cloud PyTorch)
   - Pros: Complete implementation as per architecture
   - Cons: Requires Renode integration (6+ weeks)
   - Status: Too large for single milestone

2. **Edge + Cloud only** (Skip device tier)
   - Pros: Builds on M2 Docker foundation
   - Cons: Doesn't demonstrate device ML
   - Status: **RECOMMENDED FOR M3**

3. **Mocked device tier** (Python TFLite interpreter)
   - Pros: Demonstrates all three tiers
   - Cons: Device tier not realistic (defeats purpose)
   - Status: Compromise if needed

### Chosen Approach for M3: Edge + Cloud ML

**Rationale**:
- Edge tier: Docker container with ONNX Runtime (builds on M2c MQTT broker)
- Cloud tier: Python service with PyTorch (extends Python node design)
- Device tier: Python nodes forward raw data (not ML inference)
- Demonstrates placement comparison (edge vs cloud)
- Realistic: Real ONNX and PyTorch models, not mocks

**Trade-off accepted**: No device-tier ML in M3. Focus on proving the framework works for edge/cloud tiers first. Can add device TFLite in M4+ if needed.

---

## Initial Minor Stages (5 stages)

Following wow.md Section 3, here are the initial 5 minor stages. This plan will be updated incrementally as we learn from each stage.

### M3a: Edge ML Inference Container

**Objective**: Create Docker container that runs ONNX Runtime for ML inference on edge tier.

**Scope**:
- Create `containers/ml-inference/Dockerfile` with ONNX Runtime
- Simple inference service: receives data via MQTT, runs inference, publishes results
- Example model: Anomaly detector (binary classification)
- Integration test: Python node → MQTT → ML container → result

**Acceptance criteria**:
- Docker container with ONNX Runtime starts successfully
- Can load .onnx model file
- Receives sensor data via MQTT
- Runs inference and publishes results
- Inference latency measured and logged

**Deferred**: Complex models, multi-model inference, resource monitoring

### M3b: Cloud ML Service (Python)

**Objective**: Implement Python-based cloud ML service using PyTorch.

**Scope**:
- Create `sim/cloud/ml_service.py` as Python service
- Same interface as edge container (MQTT in, inference, MQTT out)
- Uses PyTorch for inference
- Simulated cloud latency (configurable delay)

**Acceptance criteria**:
- Python ML service loads PyTorch model
- Receives data via MQTT
- Runs inference with simulated cloud latency
- Publishes results via MQTT
- Integration test passes

**Deferred**: Distributed cloud services, load balancing, auto-scaling

### M3c: ML Placement YAML Schema

**Objective**: Extend YAML schema to specify ML placement configurations.

**Scope**:
- Add `ml_placement` section to YAML scenarios
- Specify model paths, inference configs, placement strategy
- Schema validation tests
- Example scenarios: edge-only, cloud-only, hybrid

**Acceptance criteria**:
- YAML supports `ml_placement: edge` or `ml_placement: cloud`
- Model file paths specified in YAML
- Inference configuration (threshold, latency targets) in YAML
- Schema tests pass

**Deferred**: Auto-selection of placement, dynamic switching

### M3d: ML Metrics Collection

**Objective**: Collect and report ML-specific metrics for placement comparison.

**Scope**:
- Extend metrics system to capture:
  - Inference latency (device/edge/cloud)
  - Prediction accuracy (vs ground truth)
  - Communication overhead (data forwarding)
  - End-to-end latency (sample → result)
- CSV output format for analysis
- Basic comparison script

**Acceptance criteria**:
- Inference latency captured for each placement
- Accuracy metrics collected
- Communication overhead measured
- CSV metrics can be plotted/analyzed

**Deferred**: Real-time dashboards, automated Pareto frontier, energy modeling

### M3e: Placement Comparison Example

**Objective**: Demonstrate ML placement framework with concrete example scenario.

**Scope**:
- Create example scenario: Vibration anomaly detection
- Three variants: edge-only, cloud-only, hybrid
- Run all variants, collect metrics
- Compare results: latency vs accuracy trade-offs
- Document findings in M3e-report.md

**Acceptance criteria**:
- Example scenario runs successfully
- All three variants produce results
- Metrics demonstrate trade-offs
- Documentation explains how to use framework

**Deferred**: Large-scale experiments, parameter sweeps, optimization

---

## Success Criteria for M3 Completion

M3 is complete when:

1. ✅ Edge ML inference container works (ONNX Runtime in Docker)
2. ✅ Cloud ML service works (PyTorch in Python)
3. ✅ YAML schema supports ML placement specification
4. ✅ ML metrics collected (latency, accuracy, overhead)
5. ✅ Example placement comparison runs successfully
6. ✅ All M0-M2-M3 tests pass
7. ✅ Documentation explains how to run ML placement experiments

---

## Known Risks and Mitigations

### Risk 1: Model Availability

**Risk**: Need actual .onnx and .pt model files for testing.

**Mitigation**:
- Use simple pre-trained models (MNIST, simple binary classifier)
- Create minimal example models if needed
- Focus on framework, not model sophistication

### Risk 2: ONNX Runtime Complexity

**Risk**: ONNX Runtime dependencies may complicate Docker container.

**Mitigation**:
- Use official ONNX Runtime Docker base image
- Start with CPU-only inference (no GPU)
- Keep model simple to minimize dependencies

### Risk 3: PyTorch Size

**Risk**: PyTorch is heavy (~1GB), may slow Docker builds.

**Mitigation**:
- Cloud service is Python (not Docker), so no container bloat
- Can use PyTorch CPU-only wheel (~200MB)
- Or use ONNX Runtime for both edge and cloud (lighter weight)

### Risk 4: Ground Truth for Accuracy

**Risk**: Need ground truth labels to measure prediction accuracy.

**Mitigation**:
- Use synthetic data with known labels
- Or use pre-labeled datasets (MNIST, etc.)
- Focus on demonstrating capability, not perfect accuracy

---

## Dependencies and Prerequisites

### Required for M3:
- M2 complete (Docker, MQTT, YAML schema) ✅
- ONNX Runtime (pip install or Docker image)
- PyTorch (pip install, CPU-only sufficient)
- Simple ML model files (.onnx, .pt)
- Test dataset (synthetic or pre-labeled)

### Not Required for M3:
- Renode (device firmware deferred)
- GPU acceleration (CPU inference sufficient)
- Production ML deployment infrastructure
- Automated Pareto analysis

---

## Alignment with Architecture Documents

This plan aligns with:

- **architecture.md Section 2.2.3**: M3 milestone goals (ML placement framework)
- **implementation-guide.md Section 1**: ML Placement Framework Architecture
- **vision.md M3 goals**: Run actual ML models, evaluate placement variants

**Deviation**: Deferring device TFLite integration (requires Renode). Focusing on edge (ONNX) + cloud (PyTorch) tiers first. This demonstrates the framework capability while keeping M3 achievable.

**Justification**:
1. Renode integration is major undertaking (6+ weeks per architecture.md)
2. Edge + cloud placement comparison still demonstrates "killer app"
3. Can add device tier in M4+ if research requires it
4. Iterative complexity growth: prove concept first, add realism later

---

## Next Steps

1. Create M3a-report.md and begin edge ML inference container
2. After M3a completion, revisit this plan and refine M3b-M3e based on learnings
3. Update plan incrementally as each minor stage completes

This plan will evolve as we learn from implementation. Following wow.md principles: small stages, tests first, iterate based on what we learn.

---

**Status:** PLANNING
**Estimated Time:** 3-4 working days (~20-24 hours)
**Started:** 2025-11-15

M3 is ambitious but achievable by building on M2 foundation and deferring Renode complexity.
