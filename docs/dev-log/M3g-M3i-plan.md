# M3g-M3i Plan: Integration and Orchestration Completion

**Major Stage:** M3 (continuation)
**Minor Stages:** M3g, M3h, M3i
**Created:** 2025-11-15
**Status:** PLANNING

---

## Context

Following the completion of M3a-M3e (ML Placement Framework) and M3fa-M3fc (Renode Integration), a comprehensive analysis of the implementation status relative to design documents has identified three critical gaps that prevent end-to-end reproducible experiments:

1. **Missing automated scenario harness** - Cannot execute full scenarios from YAML
2. **Container protocol mismatch** - Docker services run on wall-clock, not coordinator virtual time
3. **Incomplete event routing** - Device and network events do not reach edge/cloud services

These gaps prevent the system from achieving its core research goal: **reproducible federated co-simulation experiments for paper results**.

---

## Major Stage Goal (M3 Extensions)

**Complete the federated co-simulation infrastructure** to enable reproducible end-to-end experiments that combine:
- Renode device emulation (M3fa-M3fc)
- Network simulation (M1)
- Edge containers (M2)
- ML services (M3a-M3b)
- Cloud services (M3b)

All coordinated through deterministic virtual time with proper event routing across tiers.

---

## Analysis Summary

### Current State

**What works:**
- ✅ Coordinator implements conservative lockstep protocol
- ✅ Python models follow deterministic event-loop structure
- ✅ Scenario loader enforces rich schema
- ✅ Docker containers exist for edge services
- ✅ RenodeNode can start and advance Renode processes
- ✅ ML inference works in edge containers (ONNX) and cloud (PyTorch)

**What doesn't work:**
- ❌ Experiment harness (run_scenario.py) is a P0 stub - only prints placeholders
- ❌ Cannot launch scenarios automatically from YAML
- ❌ Docker containers run on wall-clock time, not virtual time
- ❌ Edge containers lack coordinator protocol (INIT/ADVANCE/DONE)
- ❌ Device events from Renode don't reach network model
- ❌ Network events don't reach edge/cloud services
- ❌ No ns-3 integration despite being M1 goal
- ❌ No end-to-end integration tests

**Impact:**
- Cannot run reproducible experiments for paper results
- Manual setup required for every scenario
- Deterministic architecture compromised by wall-clock edge services
- Cross-tier message routing incomplete

---

## Proposed Minor Stages

### M3g: Build Scenario-Driven Orchestration Harness

**Objective:** Implement executable scenario harness that launches all node types from YAML

**Issue:** The repository lacks an executable scenario harness that can launch nodes (Python, Docker, Renode) and the coordinator from YAML, so end-to-end runs require manual setup.

**Key tasks:**
1. Extend `sim/harness/run_scenario.py` to load `sim.config.scenario.Scenario`
2. Instantiate node adapters (socket-based, Docker, Renode) from scenario config
3. Implement lifecycle helpers in `sim/harness/launcher.py`:
   - Spawn Python node processes
   - Build/run Docker containers
   - Create in-process Renode nodes
4. Add coordinator startup/shutdown management
5. Integration tests: execute short scenario (Python nodes + latency network) with deterministic outputs

**Success criteria:**
- `run_scenario.py scenarios/test/basic.yaml` executes full simulation
- All node types can be launched from YAML
- Coordinator manages lifecycle of all nodes
- Clean shutdown with no zombie processes
- Integration test proves deterministic execution

**Files:**
- `sim/harness/run_scenario.py` (extend from stub)
- `sim/harness/launcher.py` (new)
- `tests/integration/test_scenario_harness.py` (new)
- Scenarios for testing

**Estimated complexity:** Medium (2-3 days)

---

### M3h: Unify Container Protocol with Coordinator Timebase

**Objective:** Implement coordinator protocol in Docker containers for deterministic co-simulation

**Issue:** Dockerized edge services and MQTT/ML components run on wall-clock time and lack the coordinator protocol, preventing deterministic co-simulation across tiers.

**Key tasks:**
1. Implement INIT/ADVANCE/DONE protocol in container services:
   - Wrap ML inference with protocol adapter
   - Wrap MQTT gateways with protocol adapter
   - Python adapter for coordinator communication
2. Update `DockerNode` to marshal events between coordinator and container:
   - Replace `time.sleep` logic with message-driven advancement
   - Implement bidirectional event flow
3. Provide staged tests:
   - Unit tests for protocol adapter
   - Integration tests proving coordinator can drive Docker node deterministically
   - Validate MQTT/ML pipelines honour virtual time

**Success criteria:**
- Docker containers advance using virtual time (not wall-clock sleep)
- Containers implement INIT/ADVANCE/DONE protocol
- `DockerNode` marshals events correctly
- MQTT/ML services operate within coordinator timebase
- Determinism test: same YAML + seed → identical outputs (including Docker nodes)

**Files:**
- `containers/protocol_adapter.py` (new - generic adapter for containers)
- `containers/ml-inference/inference_service.py` (extend with protocol)
- `containers/mqtt-gateway/gateway_service.py` (extend with protocol)
- `sim/nodes/docker_node.py` (replace time.sleep with event-driven advancement)
- `tests/stages/M3h/test_container_protocol.py` (new)
- `tests/integration/test_docker_determinism.py` (new)

**Estimated complexity:** Medium-High (3-4 days)

---

### M3i: Integrate Realistic Network and Device Event Routing

**Objective:** Enable cross-tier event routing from devices through network to edge/cloud services

**Issue:** The network layer and device adapters do not yet interact with ns-3 or deliver cross-tier traffic, limiting experimental fidelity.

**Key tasks:**
1. Introduce ns-3 co-simulation adapter OR enrich `LatencyNetworkModel`:
   - As interim step: enhance `LatencyNetworkModel` to exchange events with MQTT/ML services
   - Ensure device outputs from `RenodeNode` can reach edge/cloud nodes
2. Implement message routing hooks:
   - RenodeNode: forward parsed UART events to network model
   - Coordinator: route network events to edge services
   - Network model: deliver packets to destination nodes
3. Validate pipeline with end-to-end integration test:
   - Renode firmware → network model → edge inference container → metrics
   - Capture cross-tier latency measurements

**Success criteria:**
- Device events from RenodeNode reach network model
- Network model routes events to edge/cloud nodes
- Edge ML containers receive device data
- End-to-end integration test: Renode → Network → Edge → Metrics
- Cross-tier latency measured correctly
- (Optional) ns-3 adapter foundation for M4

**Files:**
- `sim/network/latency_model.py` (extend for cross-tier routing)
- `sim/device/renode_node.py` (implement event forwarding)
- `sim/coordinator.py` (implement cross-tier routing logic)
- `sim/network/ns3_adapter.py` (new - optional, foundation for M4)
- `tests/stages/M3i/test_device_routing.py` (new)
- `tests/integration/test_e2e_cross_tier.py` (new)

**Estimated complexity:** Medium (2-3 days)

---

## Dependency Graph

```
M3g: Scenario Harness
 ↓
M3h: Container Protocol  ← depends on M3g (need harness to test containers)
 ↓
M3i: Event Routing       ← depends on M3g+M3h (need full stack to test routing)
```

**Execution order:** M3g → M3h → M3i (sequential, each builds on previous)

---

## Acceptance Criteria (Overall)

### For M3g-M3i Complete:

**Must have:**
- [ ] Scenarios execute fully automatically from YAML
- [ ] All node types (Python, Docker, Renode) can be launched
- [ ] Docker containers use virtual time, not wall-clock
- [ ] Containers implement coordinator protocol
- [ ] Device events route through network to edge/cloud
- [ ] End-to-end integration test: Renode → Network → Edge ML → Metrics
- [ ] Determinism test: same YAML + seed → identical outputs (all tiers)
- [ ] No zombie processes after scenario completion
- [ ] All M0-M3 tests still pass

**Should have:**
- [ ] Multiple concurrent Renode nodes
- [ ] Multiple edge containers in single scenario
- [ ] Error handling for node startup failures
- [ ] Performance metrics (execution time, overhead)

**Nice to have:**
- [ ] ns-3 adapter foundation (for M4)
- [ ] Scenario validation tool
- [ ] Progress reporting during execution

---

## Testing Strategy

### Unit Tests
- Node factory logic (M3g)
- Protocol adapter implementation (M3h)
- Event routing logic (M3i)

### Integration Tests
- Scenario harness with Python nodes (M3g)
- Docker containers with coordinator protocol (M3h)
- Cross-tier event flow (M3i)

### End-to-End Tests
- Full scenario: Renode + Network + Edge + Cloud + ML (all stages)
- Determinism validation across all tiers
- Performance benchmarking

### Regression Tests
- All M0-M3 tests must pass
- No breaking changes to existing scenarios

---

## Risks and Mitigations

### Risk 1: Container Protocol Complexity

**Risk:** Implementing coordinator protocol in containers is complex and error-prone

**Mitigation:**
- Create reusable protocol adapter library
- Extensive testing with simple containers first
- Incremental rollout (one container type at a time)

### Risk 2: Cross-Tier Event Routing

**Risk:** Event routing across Renode → ns-3 → Docker is complex

**Mitigation:**
- Start with simplified network model (LatencyNetworkModel)
- Defer ns-3 full integration to M4 if needed
- Extensive logging and debugging support

### Risk 3: Time Synchronization Issues

**Risk:** Virtual time synchronization across containers may have bugs

**Mitigation:**
- Comprehensive determinism tests
- Time tracking assertions
- Detailed logging of time advancement

### Risk 4: Integration Test Flakiness

**Risk:** End-to-end tests with Docker + Renode may be flaky

**Mitigation:**
- Proper setup/teardown with timeouts
- Retry logic for container startup
- Clear error messages for debugging

---

## Definition of Done (M3g-M3i)

**Code:**
- [ ] All production code implemented and reviewed
- [ ] All tests written and passing
- [ ] Code reviewed against checklist
- [ ] No dead code or unused parameters

**Testing:**
- [ ] Unit tests for all new components (>80% coverage)
- [ ] Integration tests for each stage
- [ ] End-to-end test covering full stack
- [ ] Determinism test validates reproducibility
- [ ] All M0-M3 regression tests pass

**Documentation:**
- [ ] Stage reports completed (M3g, M3h, M3i)
- [ ] Review checklists completed
- [ ] Architecture decisions documented
- [ ] Known limitations documented

**Git:**
- [ ] Commits follow naming convention (M3g:, M3h:, M3i:)
- [ ] Clean commit history
- [ ] Pushed to feature branch
- [ ] No zombie processes or leftover temp files

---

## Success Metrics

### Functional Success
- ✅ Can run complete scenarios from YAML without manual setup
- ✅ All tiers (device, network, edge, cloud) participate in virtual time
- ✅ Events flow correctly across all tiers
- ✅ Deterministic execution across full stack

### Research Success
- ✅ Can generate paper figures from automated experiments
- ✅ Reproducible results (same YAML + seed → same outputs)
- ✅ End-to-end latency measurements accurate

### Quality Success
- ✅ All tests passing (unit + integration + regression)
- ✅ No known blocking bugs
- ✅ Clean shutdown (no zombie processes)
- ✅ Code reviewed and documented

---

## Next Steps After M3g-M3i

**Potential M4 priorities:**
1. **ns-3 full integration** - Replace LatencyNetworkModel with ns-3 packet simulation
2. **Large-scale experiments** - Parameter sweeps, batch execution
3. **Hybrid ML placement** - Dynamic routing logic
4. **Energy modeling** - Power consumption simulation
5. **Fault injection** - Network failures, Byzantine nodes
6. **Device-tier ML** - TFLite on Renode (deferred from M3)

**Recommendation:** ns-3 integration (completes M1 original goal) OR large-scale experiments (enables paper results)

---

## Timeline Estimate

| Stage | Duration | Cumulative |
|-------|----------|------------|
| M3g | 2-3 days | 2-3 days |
| M3h | 3-4 days | 5-7 days |
| M3i | 2-3 days | 7-10 days |
| **Total** | **7-10 days** | **~2 weeks** |

**Note:** Assumes serial execution, full-time work, includes testing and documentation

---

## Status Tracking

- [ ] M3g-M3i-plan.md created
- [ ] M3g-report.md created
- [ ] M3h-report.md created
- [ ] M3i-report.md created
- [ ] M3g implementation started
- [ ] M3g tests passing
- [ ] M3g complete
- [ ] M3h implementation started
- [ ] M3h tests passing
- [ ] M3h complete
- [ ] M3i implementation started
- [ ] M3i tests passing
- [ ] M3i complete
- [ ] M3g-M3i-summary.md written

**Current status:** PLANNING

---

**Last updated:** 2025-11-15
