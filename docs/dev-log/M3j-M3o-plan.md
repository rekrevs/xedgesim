# M3j–M3o Stabilisation Plan

The code review highlighted foundational gaps around orchestration, deterministic container participation, bidirectional device traffic, and automated validation. To make the platform paper-ready, we split the "Proposed way forward" into six narrowly scoped M3j–M3o sprints that harden the current stack before revisiting ns-3 integration. Each sprint lists the goal, the concrete scope, and developer-oriented notes to keep the team aligned.

## M3j — Scenario Harness & Orchestration Spine

**Goal:** Provide a single entry point (`run_scenario.py`) that ingests YAML, bootstraps the coordinator, and launches all declared nodes (Python servers, Renode processes, Docker containers) with correct socket wiring.

**Scope:**
- Implement the orchestration harness with lifecycle management (start, monitor, shutdown) for each node type and the coordinator itself.
- Extend the YAML schema with explicit node launcher metadata (binary path, container image, env, health checks).
- Add smoke tests that simulate scenarios with stubbed nodes to verify deterministic startup ordering and teardown.

**Developer guidance:** Treat the harness as the canonical interface for future experiments. Keep orchestration logic separate from simulation logic (e.g., `scripts/run_scenario.py` vs. `sim/coordinator.py`) so tests can mock one without the other. Document the invocation sequence and ensure logs capture timestamps for reproducibility.

## M3k — Coordinator-Compatible Container Protocol

**Goal:** Align Docker nodes with the coordinator's INIT/ADVANCE/DONE protocol so containers participate in lockstep time, not wall-clock streaming.

**Scope:**
- Extend `DockerNode` to manage container lifecycle (pull/build, start, health probe, socket negotiation) and implement the node protocol shim (either native or via sidecar).
- Retrofit existing container services (echo-service, MQTT adapters, ML inference) to speak the protocol or wrap them with a thin Python/Rust sidecar that does.
- Provide unit tests that run coordinator loops against container mocks to confirm deterministic advancement and event exchange.

**Developer guidance:** Standardise on a JSON schema for INIT/ADVANCE payloads so services remain language-agnostic. Avoid leaking Docker SDK specifics into coordinator code—keep boundaries clean so alternate runtimes (Podman, containerd) could later reuse the same interface.

## M3l — Bidirectional Device ↔ Network ↔ Edge Flow

**Goal:** Restore the data plane so in-process nodes (Renode) both emit and consume routed events, enabling firmware-to-container round trips without ns-3.

**Scope:**
- Fix the coordinator’s handling of in-process nodes: deliver pending events on each ADVANCE, persist destination metadata, and update Renode adapters to set `dst` appropriately.
- Implement a translation bridge that maps Renode UART/network output into coordinator events and forwards responses back (e.g., UART ↔ MQTT or UDP ↔ logical network model).
- Create regression tests where RenodeNode exchanges packets with a logical edge node through the latency queue network model.

**Developer guidance:** Keep the network bridge modular so ns-3 can later replace the logical queue without rewriting Renode integration. Prioritise visibility—log every packet hand-off in debug mode to help debug dropped traffic.

## M3m — Deterministic Edge/ML Service Pack

**Goal:** Provide reference edge and cloud services that run deterministically under coordinator control, proving the container protocol is practical.

**Scope:**
- Rework the echo-service, MQTT helpers, and ML placement service to operate entirely within coordinator-managed virtual time (no direct Mosquitto paths outside the sim timebase).
- Ship sample ML workloads (e.g., lightweight PyTorch/ONNX inference) that can run offline using deterministic seeds and packaged test data.
- Add harness scripts that deploy these services via `run_scenario.py` and record reproducible outputs/artifacts for later analysis.

**Developer guidance:** Focus on hermetic execution: services should not require external brokers or GPUs. Capture their inputs/outputs in well-defined directories to facilitate automated diffing across runs.

## M3n — Integration & Determinism Test Suite

**Goal:** Establish automated tests proving end-to-end (Renode → coordinator → logical network → Docker/ML) flows work and remain deterministic/statistically reproducible.

**Scope:**
- Add pytest-based integration suites under `tests/integration/` that spin up lightweight fixtures of the harness, coordinator, Renode stubs, and container sidecars.
- Capture timing/packet traces during tests and compare against golden files to detect regressions.
- Gate CI on these tests and document failure triage procedures in `docs/testing.md`.

**Developer guidance:** Keep tests fast by using mocked/synthetic firmware where possible. For heavier Renode cases, run them nightly but still script them so contributors can reproduce locally with one command.

## M3o — Scenario Library & Release Checklist (Pre-ns-3)

**Goal:** Package a library of thoroughly documented scenarios plus a release checklist that verifies orchestrated runs, clearing the path for future ns-3 work.

**Scope:**
- Curate several YAML scenarios (sensor-only, sensor+edge, ML-placement) and pair each with scripts/notebooks that analyse captured metrics.
- Update README/dev logs to reflect real capabilities (no premature ✅ for ns-3) and add troubleshooting guides for the harness.
- Define entry criteria for the subsequent ns-3 milestone (e.g., harness maturity, deterministic tests passing) so the team knows when it is safe to proceed.

**Developer guidance:** Treat this sprint as a stabilization gate—no new simulators, just polish. Ensure every scenario is runnable via CI and produces artefacts archived under `results/` for future paper figures.

> **Note:** ns-3 integration remains deferred until the above sprints demonstrate a solid, testable baseline. Once M3o passes, we can reintroduce the packet-level network work with clearer requirements and lower risk.

---

## Progress Tracking

### M3l — Bidirectional Device ↔ Network ↔ Edge Flow

**Status:** IN PROGRESS

#### M3la: Fix Renode Incoming Event Delivery ✅ COMPLETE
- **Completed:** 2025-11-16
- **Commit:** 9ab01b8
- **Summary:** Implemented event delivery infrastructure allowing in-process Renode nodes to receive events from coordinator
- **Changes:**
  - Modified `InProcessNodeAdapter` to pass pending_events to nodes
  - Added `RenodeNode.set_pending_events()` and `_inject_events_via_uart()`
  - 20 unit tests + 44 regression tests passing
- **Report:** [docs/dev-log/M3la-report.md](M3la-report.md)
- **Remaining Work:** M3lb (translation layer), M3lc (end-to-end testing with real Renode)

#### M3lb: Create UART-Event Translation Layer ⏸️ PENDING
- **Goal:** Enable firmware to route events to specific destinations
- **Tasks:**
  - Extend UART JSON parsing for destination field
  - Create UART↔MQTT translation utilities
  - Test event routing

#### M3lc: Test Bidirectional Device-Edge Flow ⏸️ PENDING
- **Goal:** End-to-end integration testing with real Renode
- **Tasks:**
  - Integration test: Renode → Network → Docker → back to Renode
  - Validate determinism across bidirectional flows
  - **Requires:** Testing agent (Docker + Renode)
