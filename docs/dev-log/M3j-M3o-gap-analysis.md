# M3j–M3o Gap Analysis

**Review Date:** 2025-11-16
**Reviewer:** Claude (Automated Code Review)
**Branch:** develop
**Commit:** 1a1670c

## Executive Summary

This gap analysis reviews the current codebase against the M3j–M3o stabilization plan to identify missing functionality, incomplete implementations, and areas requiring attention before the platform is paper-ready.

**Overall Status:** Foundational infrastructure is largely in place, but critical gaps exist in:
1. **Bidirectional event flow** for in-process nodes (Renode)
2. **Deterministic time management** for edge/ML services
3. **Test coverage** for end-to-end integration scenarios
4. **Documentation** and release readiness artifacts

---

## M3j — Scenario Harness & Orchestration Spine

### Goal
Provide a single entry point (`run_scenario.py`) that ingests YAML, bootstraps the coordinator, and launches all declared nodes with correct socket wiring.

### ✅ What's Implemented

1. **Entry Point:** `sim/harness/run_scenario.py` exists and works as the canonical interface
   - Accepts YAML scenarios
   - Supports `--seed` override
   - Supports `--dry-run` validation mode
   - Proper CLI with argparse

2. **Orchestration Logic:** `sim/harness/launcher.py` provides comprehensive lifecycle management
   - `SimulationLauncher` class handles all component types
   - Startup sequencing: validate → start containers → create network → register nodes → connect → initialize → run
   - Clean shutdown with proper Docker container cleanup
   - Process lifecycle tracking

3. **YAML Schema:** Extended schema supports node types
   - `python_model`, `docker`, `renode_inprocess` implementations
   - Docker configuration with image, ports, environment, volumes
   - Renode configuration with platform, firmware, monitor_port

4. **Validation:** Pre-launch validation exists
   - File existence checks (firmware, platform, models)
   - Required field validation
   - Fail-fast design

### ❌ Critical Gaps

1. **Health Checks Missing**
   - YAML schema has no `health_checks` field for nodes
   - No health probe implementation for Docker containers
   - No readiness verification beyond basic socket connection
   - **Impact:** Cannot detect failed/unhealthy nodes during simulation
   - **Location:** `sim/harness/launcher.py:_start_docker_container()`

2. **Smoke Tests Incomplete**
   - No smoke tests with stubbed/mocked nodes to verify orchestration in isolation
   - Existing tests (`test_m3g_scenario.py`) use real components
   - **Impact:** Hard to debug orchestration issues separately from node issues
   - **Recommendation:** Add `tests/integration/test_orchestration_smoke.py`

3. **Documentation Gaps**
   - Invocation sequence not fully documented
   - No troubleshooting guide for common startup failures
   - Logging timestamps exist but reproducibility procedures not documented
   - **Location:** Missing `docs/orchestration.md`

### ⚠️ Minor Issues

1. **Separation of Concerns:** Generally good, but some Docker logic could be extracted to separate module
2. **Logging:** Adequate but could include more timing information for reproducibility analysis

---

## M3k — Coordinator-Compatible Container Protocol

### Goal
Align Docker nodes with the coordinator's INIT/ADVANCE/DONE protocol so containers participate in lockstep time, not wall-clock streaming.

### ✅ What's Implemented

1. **Coordinator-Side Adapter:** `sim/harness/docker_protocol_adapter.py`
   - Implements `NodeAdapter` interface
   - Uses `docker exec -i` with stdin/stdout pipes
   - Handles INIT/ADVANCE/SHUTDOWN protocol
   - Background threads for stdout/stderr to prevent buffer blocking
   - Clean error handling with stderr capture

2. **Container-Side Adapter:** `containers/protocol_adapter.py`
   - Reusable `CoordinatorProtocolAdapter` class
   - Service callback pattern: `(current_time, target_time, events) → events`
   - JSON-based event serialization
   - Proper logging to stderr (stdout reserved for protocol)

3. **JSON Schema:** Well-defined event format
   - Event fields: `timestamp_us`, `event_type`, `source`, `destination`, `payload`
   - Consistent across coordinator and containers

4. **Clean Boundaries:** Docker SDK isolated to launcher/adapter
   - Coordinator core doesn't depend on Docker
   - Protocol is transport-agnostic (could work with Podman, containerd)

### ❌ Critical Gaps

1. **Services Not Retrofitted to Use Protocol**
   - **Echo Service:** `containers/echo-service/echo_service.py` uses raw TCP sockets, not protocol
   - **ML Service:** `sim/cloud/ml_service.py` uses wall-clock time (`time.sleep()`) and external MQTT
   - **MQTT Broker:** Container exists but not protocol-aware
   - **Impact:** Services cannot participate in deterministic lockstep simulation
   - **Blocker:** M3m depends on this

2. **Sidecar Pattern Not Implemented**
   - Plan mentions "thin Python/Rust sidecar" option but not implemented
   - Could be useful for wrapping existing services without modification
   - **Recommendation:** Defer unless needed for legacy services

3. **Unit Tests for Protocol Missing**
   - No standalone tests for coordinator loops against container mocks
   - `test_m3h_docker_protocol.py` exists (10KB) - need to review its coverage
   - **Verification needed:** Does it test INIT/ADVANCE/DONE sequences?

### ⚠️ Minor Issues

1. **Protocol Documentation:** No formal spec document for JSON message formats
2. **Language Agnostic:** Python-only currently, but design supports other languages

---

## M3l — Bidirectional Device ↔ Network ↔ Edge Flow

### Goal
Restore the data plane so in-process nodes (Renode) both emit and consume routed events, enabling firmware-to-container round trips without ns-3.

### ✅ What's Implemented

1. **Renode Integration:** `sim/device/renode_node.py` fully functional
   - Manages Renode process lifecycle
   - Virtual time synchronization via `emulation RunFor`
   - UART output parsing into events
   - Events emitted with proper `src` field

2. **Network Routing:** Coordinator routes events through network models
   - `coordinator.py:run()` lines 332-347 implement routing
   - Events routed via `network_model.route_message()`
   - Delayed events from `network_model.advance_to()` delivered
   - Supports DirectNetworkModel and LatencyNetworkModel

3. **Event Structure:** Events support `dst` field
   - `Event` dataclass has `src` and `dst` fields
   - Network metadata field exists for latency/routing info

### ❌ Critical Gaps — BLOCKER

1. **Incoming Events Ignored for In-Process Nodes**
   - **Location:** `sim/harness/coordinator.py:194-204` in `InProcessNodeAdapter.send_advance()`
   - **Code:**
     ```python
     def send_advance(self, target_time_us: int, pending_events: List[Event]):
         """
         Note: pending_events are currently ignored for in-process nodes.
         M3fc focuses on device-tier emulation which doesn't receive events
         from other nodes. Future stages can extend this.
         """
         self.current_time_us = target_time_us
         # Note: pending_events handling can be added if needed in future
     ```
   - **Impact:** Renode nodes cannot receive events from network/edge/cloud
   - **Breaks:** Firmware-to-container round trips, actuator commands, cloud → device flows
   - **Severity:** CRITICAL - this is the core requirement for M3l

2. **No Renode Event Delivery Mechanism**
   - Events need to be converted to UART input or other peripheral interface
   - UART stdin injection not implemented
   - No GPIO/peripheral event injection mechanism
   - **Recommendation:** Implement UART stdin via Renode monitor commands

3. **Translation Bridge Missing**
   - No UART ↔ MQTT bridge
   - No UDP ↔ logical network mapping
   - **Example needed:** Renode firmware sends UDP packet → routed to edge MQTT topic
   - **Example needed:** MQTT message → delivered to firmware via UART

4. **Destination Metadata Not Persisted in Renode Events**
   - Renode events created with `dst=None` (line 220 in coordinator.py)
   - Firmware output doesn't specify destination
   - **Impact:** Events broadcast to all nodes instead of targeted routing
   - **Recommendation:** Firmware should output `{"dst": "gateway1", ...}` in JSON

### ❌ Testing Gaps

1. **No Regression Tests for Round Trips**
   - No test: Renode → Network → Edge → Network → Renode
   - No test: Firmware UART output → MQTT → ML service → MQTT → UART input
   - **Recommendation:** Add `tests/integration/test_device_edge_roundtrip.py`

2. **No Tests with Latency Queue Network**
   - Renode tests use DirectNetworkModel
   - Need tests with LatencyNetworkModel to verify queuing

### ⚠️ Documentation Gaps

1. **Network Bridge Architecture:** Not documented
2. **Event Format for Firmware:** No specification for JSON event format firmware should emit
3. **Debug Visibility:** Packet hand-off logging mentioned in plan but implementation unclear

---

## M3m — Deterministic Edge/ML Service Pack

### Goal
Provide reference edge and cloud services that run deterministically under coordinator control, proving the container protocol is practical.

### ✅ What's Implemented

1. **ML Service Exists:** `sim/cloud/ml_service.py`
   - PyTorch-based inference
   - MQTT integration
   - Configurable latency simulation

2. **Echo Service Exists:** `containers/echo-service/echo_service.py`
   - Simple TCP echo for testing

3. **MQTT Infrastructure:** Mosquitto container setup exists
   - `containers/mqtt-broker/` with Dockerfile and config

### ❌ Critical Gaps — BLOCKER

1. **Services Use Wall-Clock Time, Not Virtual Time**
   - **ML Service:** `sim/cloud/ml_service.py:120, 140` uses `time.sleep(self.cloud_latency_ms / 1000.0)`
   - **Echo Service:** Runs in real-time, not coordinated
   - **Impact:** Services are not deterministic and don't participate in lockstep
   - **Blocker:** Defeats the entire purpose of virtual time coordination

2. **External MQTT Broker Required**
   - ML service connects to external Mosquitto broker (`paho.mqtt.client`)
   - Not hermetic - requires external process
   - **Impact:** Cannot run in isolated CI environment
   - **Recommendation:** Coordinator should manage MQTT broker as in-process message bus OR broker must be protocol-aware container

3. **No Deterministic Seeds**
   - ML models not seeded from coordinator config
   - PyTorch inference uses default RNG
   - **Impact:** Results not reproducible across runs

4. **No Offline/Hermetic ML Workloads**
   - Models loaded from files, but no packaged test data
   - GPU dependency mentioned but not handled
   - **Recommendation:** Ship lightweight ONNX/PyTorch models with frozen test inputs

5. **No Harness Deployment Scripts**
   - Cannot deploy ML services via `run_scenario.py` with protocol integration
   - Would require retrofitting to use `protocol_adapter.py` (see M3k gap)

### ❌ Testing Gaps

1. **No Reproducibility Tests**
   - No tests that run scenario twice and diff outputs
   - No artifact capture/comparison
   - **Recommendation:** Add `tests/integration/test_ml_reproducibility.py`

2. **No Offline Tests**
   - Services require external network/brokers
   - Cannot run in isolated Docker network

---

## M3n — Integration & Determinism Test Suite

### Goal
Establish automated tests proving end-to-end flows work and remain deterministic/statistically reproducible.

### ✅ What's Implemented

1. **Integration Test Infrastructure:**
   - `tests/integration/test_m3g_scenario.py` - scenario launcher tests
   - `tests/integration/test_m3h_docker_protocol.py` - protocol tests
   - 37 total test files across codebase
   - pytest-based test organization

2. **Test Fixtures:**
   - Docker cleanup fixtures
   - Temporary directory management
   - Scenario loading utilities

3. **Test Categories:**
   - `@pytest.mark.integration` for integration tests
   - `@pytest.mark.docker` for Docker-requiring tests
   - Skip markers for missing dependencies

### ❌ Critical Gaps

1. **No Golden File Comparison**
   - No tests capture timing/packet traces
   - No baseline artifacts for regression detection
   - **Impact:** Cannot detect determinism regressions
   - **Recommendation:**
     - Add `tests/golden/` directory with reference outputs
     - Add `tests/integration/test_determinism.py` that compares traces

2. **No End-to-End Flow Tests**
   - No test: Renode → Coordinator → Network → Docker → ML → back to Renode
   - Existing tests focus on individual components
   - **Missing:** `test_e2e_sensor_edge_cloud.py`

3. **docs/testing.md Does Not Exist**
   - No test documentation
   - No failure triage procedures
   - No guidance on running subsets of tests
   - **Blocker for M3n completion**

4. **CI Gating Not Verified**
   - No evidence of GitHub Actions or CI configuration
   - Need to verify: `.github/workflows/` for test automation
   - Gate requirement not documented

5. **Fast vs. Heavy Tests Not Separated**
   - No clear distinction between:
     - Mocked/synthetic firmware tests (fast)
     - Full Renode emulation tests (heavy/nightly)
   - **Recommendation:** Use pytest markers: `@pytest.mark.heavy` for Renode tests

### ⚠️ Test Organization Issues

1. **Stage-Based vs. Feature-Based Organization:**
   - Tests organized by milestone (`M2a`, `M3g`) rather than by feature
   - As project matures, feature-based might be clearer
   - Not critical, but consider reorganization

2. **Integration Test Coverage:**
   - Docker tests skip if Docker unavailable (good)
   - But no mock-based alternatives for CI environments without Docker

---

## M3o — Scenario Library & Release Checklist

### Goal
Package a library of thoroughly documented scenarios plus a release checklist that verifies orchestrated runs, clearing the path for future ns-3 work.

### ✅ What's Implemented

1. **Scenario Library Exists:**
   - `scenarios/m0_baseline.yaml` - baseline test
   - `scenarios/m1b_minimal.yaml` - minimal 2-node scenario
   - `scenarios/m1d_latency_test.yaml` - network model test
   - `scenarios/m2d/docker_gateway.yaml`, `python_gateway.yaml` - gateway tests
   - `scenarios/m3c/edge_ml_placement.yaml`, `cloud_ml_placement.yaml` - ML placement demos
   - `scenarios/vib-monitoring/config.yaml` - application example
   - `examples/scenarios/device_emulation_*.yaml` - Renode examples

2. **Some Documentation:**
   - `README.md` - project overview
   - `README-ML-PLACEMENT.md` - ML placement documentation
   - `docs/milestones/` - milestone plans

### ❌ Critical Gaps

1. **No Analysis Scripts/Notebooks**
   - Scenarios exist but no analysis tools
   - **Missing:** Jupyter notebooks to visualize results
   - **Missing:** Python scripts to generate metrics plots
   - **Example needed:** `scripts/analyze_scenario_results.py`

2. **No Release Checklist**
   - No document defining "ready for paper" criteria
   - No verification checklist
   - **Missing:** `docs/release-checklist.md`

3. **No ns-3 Entry Criteria**
   - Plan says "Define entry criteria for the subsequent ns-3 milestone"
   - Not documented
   - **Missing:** Clear gates before starting ns-3 work

4. **CI Artifact Archiving Not Verified**
   - No evidence of `results/` directory archival
   - No CI configuration for capturing simulation outputs
   - **Impact:** Cannot track results over time for paper figures

5. **Troubleshooting Guide Missing**
   - No `docs/troubleshooting.md`
   - Common issues not documented:
     - Renode connection failures
     - Docker permission errors
     - Port conflicts
     - Firmware path issues

6. **Capabilities Documentation Outdated**
   - README may have premature checkmarks
   - ns-3 status needs clarification (deferred per plan)
   - **Need to audit:** All checkmarks in README.md

### ❌ Scenario Quality Issues

1. **Missing Scenario Metadata:**
   - No description field in YAML
   - No expected outcomes documented
   - No runtime estimates
   - **Recommendation:** Extend schema with metadata block

2. **No Runnable-via-CI Flag:**
   - Not clear which scenarios can run in automated CI
   - Some may require hardware/Renode
   - **Recommendation:** Add `ci_compatible: true/false` to scenarios

---

## Priority Matrix

### Critical (Blocks Paper-Ready Status)

| Priority | Gap | Milestone | Estimated Effort |
|----------|-----|-----------|------------------|
| 🔴 P0 | Renode incoming events ignored | M3l | 2-3 days |
| 🔴 P0 | ML services use wall-clock time | M3m | 3-5 days |
| 🔴 P0 | No end-to-end determinism tests | M3n | 2-4 days |
| 🔴 P0 | Translation bridge missing (UART↔MQTT) | M3l | 3-5 days |
| 🟡 P1 | Services not using protocol adapter | M3k | 2-3 days |
| 🟡 P1 | Golden file regression tests | M3n | 2-3 days |
| 🟡 P1 | docs/testing.md missing | M3n | 1 day |
| 🟡 P1 | Release checklist missing | M3o | 1 day |

### Important (Should Address Before ns-3)

| Priority | Gap | Milestone | Estimated Effort |
|----------|-----|-----------|------------------|
| 🟢 P2 | Health checks in orchestration | M3j | 1-2 days |
| 🟢 P2 | Scenario analysis scripts | M3o | 2-3 days |
| 🟢 P2 | Troubleshooting guide | M3o | 1-2 days |
| 🟢 P2 | Smoke tests for orchestration | M3j | 1-2 days |
| 🟢 P2 | Hermetic ML service deployment | M3m | 2-3 days |

### Nice to Have (Can Defer)

| Priority | Gap | Milestone | Estimated Effort |
|----------|-----|-----------|------------------|
| 🔵 P3 | Sidecar pattern for containers | M3k | 3-5 days |
| 🔵 P3 | Protocol documentation | M3k | 1 day |
| 🔵 P3 | Test organization refactor | M3n | 2-3 days |
| 🔵 P3 | Scenario metadata extension | M3o | 1 day |

---

## Recommendations

### Immediate Actions (This Week)

1. **Fix Renode Event Delivery (M3l P0):**
   - Implement `pending_events` handling in `InProcessNodeAdapter`
   - Add UART stdin injection mechanism
   - Write test: `test_renode_receives_events.py`

2. **Retrofit ML Service to Protocol (M3m P0):**
   - Modify `ml_service.py` to use `protocol_adapter.py`
   - Remove `time.sleep()` - use virtual time from ADVANCE
   - Write test: `test_ml_service_deterministic.py`

3. **Write docs/testing.md (M3n P1):**
   - Document test categories and markers
   - Explain how to run subsets
   - Add failure triage procedures

### Short Term (Next 2 Weeks)

4. **Implement Translation Bridge (M3l P0):**
   - Create `sim/bridge/uart_mqtt_bridge.py`
   - Map Renode UART JSON → coordinator events → MQTT topics
   - Map MQTT messages → coordinator events → Renode UART input

5. **Create End-to-End Tests (M3n P0):**
   - `test_e2e_sensor_edge_cloud.py` - full stack
   - `test_determinism_reproducibility.py` - run twice, compare outputs
   - `test_latency_network_with_renode.py` - verify queuing

6. **Golden File Infrastructure (M3n P1):**
   - Add `tests/golden/` directory
   - Capture event traces to JSON
   - Add diff utility for comparing traces

### Medium Term (Next Month)

7. **Complete M3o Artifacts:**
   - Write `docs/release-checklist.md`
   - Create `scripts/analyze_scenario.py` for metrics
   - Write troubleshooting guide
   - Audit README for accuracy

8. **Health Checks (M3j P2):**
   - Add health check support to YAML schema
   - Implement HTTP health probes for Docker containers
   - Add readiness verification to launcher

9. **Hermetic Services (M3m P2):**
   - Package MQTT broker as protocol-aware coordinator component
   - Create deterministic ML test data fixtures
   - Document offline execution requirements

### Long Term (Before ns-3)

10. **CI Integration:**
    - Set up GitHub Actions workflow
    - Gate merges on integration tests passing
    - Archive scenario results as artifacts
    - Generate coverage reports

11. **Documentation Polish:**
    - Write architecture documentation for bridges
    - Document event format specifications
    - Create developer onboarding guide
    - Update all references to ns-3 status

---

## Success Criteria for M3j-M3o Completion

Before considering these milestones complete and moving to ns-3:

### Must Have (Blocking)
- [ ] All P0 gaps closed
- [ ] End-to-end test passes: Renode firmware → edge container → cloud service → back to firmware
- [ ] Test runs twice with same seed produce identical event traces
- [ ] All services run under coordinator virtual time (no `time.sleep()`)
- [ ] `docs/testing.md` exists with full test documentation
- [ ] Release checklist completed and all items passing

### Should Have (Important)
- [ ] 80%+ of P1 gaps addressed
- [ ] Health checks working for Docker nodes
- [ ] Troubleshooting guide covers common issues
- [ ] CI pipeline running integration tests on every commit
- [ ] Golden file regression tests protecting determinism

### Nice to Have (Aspirational)
- [ ] Analysis notebooks for all example scenarios
- [ ] Comprehensive protocol specification document
- [ ] Test coverage >70% for core simulation components
- [ ] Performance benchmarks documented

---

## Conclusion

The codebase has **strong foundational infrastructure** with well-architected components for orchestration, protocol handling, and network simulation. However, **critical functionality gaps** prevent the platform from achieving its goal of deterministic, bidirectional device-edge-cloud simulation.

**The two most critical blockers are:**

1. **Renode cannot receive events** (M3l) - breaks bidirectional flow
2. **Edge/ML services use wall-clock time** (M3m) - breaks determinism

Addressing these P0 issues, plus establishing end-to-end test coverage (M3n) and release documentation (M3o), will make the platform paper-ready and provide a solid foundation for future ns-3 integration.

**Estimated effort to close all P0+P1 gaps:** 3-4 weeks with focused development.

---

**Generated:** 2025-11-16
**Next Review:** After P0 gaps closed
