# M2 Plan: Edge Realism and Deployability

**Date:** 2025-11-15
**Status:** Planning
**Major Stage:** M2 - Add Edge Realism

---

## Goal

Add Docker container support for edge services, enabling realistic edge deployments while maintaining the option to use deterministic Python models. This milestone focuses on:

1. **Docker integration**: Run real edge services (MQTT broker, ML inference) in containers
2. **Hybrid edge tier**: Support both Docker (realism) and Python models (determinism) as user choice
3. **Deployability foundation**: Same containers used in simulation can deploy to real hardware
4. **Documentation**: Document deployment pipelines and container orchestration

**Key differentiator**: Unlike M0-M1 which uses only Python models, M2 enables running actual deployable containers in simulation, bridging the sim-to-prod gap.

---

## Context and Scope

### What M1 Delivered

- M1a: Test structure reorganization
- M1b: YAML scenario parser (basic schema)
- M1c: NetworkModel abstraction layer with DirectNetworkModel
- M1d: LatencyNetworkModel with configurable delays and packet loss
- M1e: Network metrics collection

**Current state**: Python models for devices and edge, with network abstraction layer supporting deterministic routing and latency simulation.

### What M2 Should Add (from architecture.md)

- Docker backend integration
- Container orchestration and lifecycle management
- Support for both Docker (realism) and Python models (determinism) in edge tier
- Deployability considerations and documentation
- Foundation for M3 ML placement experiments

### What M2 Should NOT Add

- Renode integration (defer to future work, Python device models are sufficient for M2)
- Full ns-3 integration (LatencyNetworkModel provides sufficient network realism for M2)
- ML placement framework (M3 scope)
- CI/CD automation (M4 scope)
- Production-grade container orchestration (M4 scope)

**Philosophy**: Following architecture.md Section 2 "Implementation Philosophy", we prioritize edge realism while keeping the system simple and testable.

---

## Decision: Docker Integration Strategy

### Key Architectural Question

**How do Docker containers integrate with the simulation?**

Three options considered:

1. **Full ns-3 + TAP/TUN integration** (from implementation-guide.md Section 5)
   - Pros: Realistic packet-level networking
   - Cons: Complex setup, requires ns-3 integration first
   - Status: Defer - ns-3 not yet implemented

2. **Socket-based integration** (simplified approach)
   - Pros: Simple, works with existing LatencyNetworkModel
   - Cons: No packet-level simulation
   - Status: **RECOMMENDED FOR M2**

3. **Hybrid approach** (socket now, TAP/TUN later)
   - Pros: Get Docker working quickly, can upgrade later
   - Cons: Two implementations to maintain
   - Status: Alternative if socket approach proves insufficient

### Chosen Approach for M2: Socket-Based Docker Integration

**Rationale**:
- M1d LatencyNetworkModel provides sufficient network realism (latency + packet loss)
- TAP/TUN integration requires ns-3, which is not yet implemented
- Socket-based approach is simpler and faster to validate
- Coordinator can mediate socket communication between containers and device models
- Can upgrade to TAP/TUN in future milestone if packet-level fidelity needed

**Trade-off accepted**: No packet-level network simulation in M2. LatencyNetworkModel provides abstract latency/loss, which is sufficient for initial Docker integration and ML placement experiments (M3).

---

## Initial Minor Stages (2-5 stages)

Following wow.md Section 3, here are the initial 2-5 minor stages. This plan will be updated incrementally as we learn from each stage.

### M2a: Docker Node Abstraction and Lifecycle ✅ COMPLETE

**Objective**: Create a DockerNode class that manages container lifecycle (create, start, stop, remove) and implements the same event-driven interface as existing Python nodes.

**Scope**:
- Implement `sim/edge/docker_node.py` with DockerNode class
- Container lifecycle management: create, start, stop, remove
- Health checks and readiness detection
- Implement `advance_to()` and `get_events()` to match Node interface
- Add unit tests for Docker lifecycle operations

**Acceptance criteria**:
- ✅ Can create, start, and stop a simple Docker container (e.g., `alpine:latest`)
- ✅ Container lifecycle managed cleanly (no orphaned containers after tests)
- ✅ DockerNode implements same interface as Python nodes (compatible with coordinator)

**Completed**: 2025-11-15 (commit 7382edd)
- DockerNode class: 196 lines
- Basic tests: 3/3 passed (no Docker required)
- Lifecycle tests: 13 written (skip without Docker)
- Regression tests: All pass (M1d, M1e)
- Optional docker dependency with graceful fallback

**Deferred to M2b**: Socket communication, event exchange with container

### M2b: Socket Communication Between Coordinator and Container

**Objective**: Enable bidirectional socket communication between coordinator and Docker container for event exchange.

**Scope**:
- Container exposes TCP socket for coordinator connection
- Coordinator sends events to container via socket
- Container sends events back to coordinator via socket
- Protocol: JSON over TCP (same as M0 protocol, but adapted for container context)
- Add integration test with simple echo container

**Acceptance criteria**:
- Coordinator can send JSON events to container
- Container can send JSON events back to coordinator
- Round-trip communication tested with simple echo service

**Deferred**: MQTT integration, network latency simulation, metrics collection

### M2c: MQTT Broker Container Integration ✅ COMPLETE

**Objective**: Run a real MQTT broker (Eclipse Mosquitto) in Docker and integrate it with the simulation.

**Scope**:
- Create `containers/mqtt-broker/Dockerfile` for Mosquitto broker
- Extend DockerNode to support MQTT-specific configuration
- Device nodes can publish to MQTT broker in container
- Gateway node can subscribe to MQTT topics
- Add integration test: sensor → MQTT broker → gateway

**Acceptance criteria**:
- ✅ Mosquitto broker runs in Docker container
- ✅ Python sensor nodes can publish MQTT messages to broker
- ✅ Python gateway node can subscribe and receive messages
- ✅ End-to-end MQTT message flow tested

**Completed**: 2025-11-15 (commit 30a4806, tested 9d02c6a)
- Mosquitto container: Dockerfile + mosquitto.conf
- SensorNode MQTT methods: connect_mqtt(), publish_reading()
- GatewayNode MQTT methods: connect_mqtt(), MQTT message handling
- Dual-mode node architecture (M0 server + M2+ direct)
- 6 integration tests: broker startup, pub/sub, end-to-end flow
- Dependency: paho-mqtt>=1.6.1
- All tests passed: 30/30 (6 M2c + 24 regression)

**Testing**: Validated by testing agent on macOS/Colima
- 2 issues found and fixed (API mismatch, networking)
- See `docs/dev-log/M2c-report.md` for details

**Deferred**: ML inference integration, complex MQTT topologies

### M2d: Hybrid Edge Tier (Docker + Python Models) ✅ COMPLETE

**Objective**: Enable YAML scenarios to specify edge tier as either Docker container OR Python model, with same behavior observable from coordinator perspective.

**Scope**:
- Extend YAML schema to support edge tier type selection (`implementation: docker` vs `implementation: python_model`)
- Document determinism differences (Docker = statistical, Python = deterministic)
- Add schema validation tests
- Create example YAML scenarios

**Acceptance criteria**:
- ✅ YAML schema supports `implementation: docker` or `implementation: python_model`
- ✅ Schema validation tests pass (8/8)
- ✅ Example scenarios demonstrate both implementations
- ✅ Determinism trade-offs documented

**Completed**: 2025-11-15 (commit f5a7d40)
- Extended `sim/config/scenario.py` with `implementation` field
- Default: `python_model` (backward compatible)
- Optional `docker` section for Docker-specific config
- Example scenarios: `scenarios/m2d/python_gateway.yaml` and `docker_gateway.yaml`
- 8 schema validation tests: all passed
- Documentation: Trade-offs table (determinism, speed, deployment, debugging)

**Deferred**: Full scenario runner (M3+), automatic node instantiation, runtime switching

### M2e: Deployability Documentation

**Objective**: Document how to deploy the same Docker containers used in simulation to real edge hardware.

**Scope**:
- Write `docs/deployability.md` covering:
  - How containers used in simulation are deployment-ready
  - Example: deploying MQTT broker container to Raspberry Pi
  - Configuration differences between simulation and production
  - Testing workflow (validate in simulation → deploy to hardware)
- Add example deployment scripts (`scripts/deploy_to_edge.sh`)
- Document container registry usage (optional Docker Hub push)

**Acceptance criteria**:
- Documented path from simulation to deployment
- Example deployment script for MQTT broker container
- Clear explanation of sim vs prod differences

**Deferred**: Full deployment automation, CI/CD integration (M4)

---

## Success Criteria for M2 Completion

M2 is complete when:

1. ✅ Docker containers can run as edge nodes in simulation
2. ✅ MQTT broker container integrated and tested end-to-end
3. ✅ Users can choose Docker OR Python models for edge tier via YAML
4. ✅ Deployability path documented with examples
5. ✅ All M0-M2 tests pass (determinism tests may need adjustments for Docker variance)
6. ✅ System ready for M3 ML placement experiments (containers can run ML inference)

---

## Known Risks and Mitigations

### Risk 1: Docker Non-Determinism

**Risk**: Docker containers run in wall-clock time, breaking determinism guarantees.

**Mitigation**:
- Accept statistical reproducibility for Docker edge tier (as per architecture.md Section 5)
- Document determinism differences clearly
- Keep Python models available for deterministic testing
- Run N trials and report mean ± confidence intervals for Docker results

### Risk 2: Container Lifecycle Complexity

**Risk**: Docker containers may not shut down cleanly, leaving orphaned containers.

**Mitigation**:
- Implement proper cleanup in DockerNode.shutdown()
- Use Docker labels to identify simulation containers
- Add cleanup script to remove orphaned containers
- Test teardown paths explicitly

### Risk 3: Socket Communication Latency

**Risk**: Socket overhead between coordinator and container may add unwanted latency.

**Mitigation**:
- Measure socket communication overhead in unit tests
- If significant, consider optimizations (connection pooling, batch messages)
- Document actual overhead vs simulated network latency

### Risk 4: ns-3 Dependency Deferred

**Risk**: Deferring ns-3/TAP/TUN integration means less realistic packet-level networking.

**Mitigation**:
- LatencyNetworkModel provides sufficient abstract latency for M2-M3
- Can upgrade to ns-3/TAP/TUN in future milestone if needed
- Socket-based approach proven simpler for getting Docker working first

---

## Dependencies and Prerequisites

### Required for M2:
- Python 3.8+ (existing)
- Docker Engine (new dependency - add to setup docs)
- `docker` Python library (new dependency - add to requirements.txt)
- Eclipse Mosquitto Docker image (pull from Docker Hub)

### Not Required for M2:
- ns-3 (deferred)
- Renode (deferred, Python device models sufficient)
- Complex orchestration tools (Kubernetes, etc.)

---

## Alignment with Architecture Documents

This plan aligns with:

- **architecture.md Section 2.3**: M2 milestone goals (Docker containers, deployability)
- **architecture.md Section 5**: Tiered determinism (Docker = statistical, models = deterministic)
- **implementation-guide.md Section 5**: Docker integration patterns (adapted for socket-based approach)
- **vision.md M2 goals**: Docker backend adapter, deployability documentation

**Deviation**: Using socket-based integration instead of ns-3/TAP/TUN for M2. Rationale: ns-3 not yet implemented, socket approach simpler and sufficient for current needs.

---

## Next Steps

1. Implement M2a (Docker Node Abstraction)
2. After M2a completion, revisit this plan and refine M2b-M2e based on learnings
3. Update plan incrementally as each minor stage completes

This plan will evolve as we learn from implementation. Following wow.md principles: small stages, tests first, iterate based on what we learn.
