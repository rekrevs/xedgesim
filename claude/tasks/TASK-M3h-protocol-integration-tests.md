# TASK: M3h Protocol Integration Tests

**Task ID:** M3h-protocol-integration-tests
**Created:** 2025-11-15
**Assigned to:** Testing Agent
**Priority:** P0 (blocks M3h completion)
**Type:** Integration Testing

---

## Context

**Stage:** M3h - Container Protocol Unification
**Goal:** Test the complete protocol-based communication between coordinator and Docker containers

The development agent has implemented:
1. **Container-side protocol adapter** (`containers/protocol_adapter.py`):
   - Implements INIT/ADVANCE/SHUTDOWN protocol over stdin/stdout
   - Event-driven virtual time (no wall-clock dependencies)
   - Unit tested locally (12/12 tests passing)

2. **Coordinator-side Docker adapter** (`sim/harness/docker_protocol_adapter.py`):
   - Implements NodeAdapter interface for protocol-based containers
   - Uses subprocess pipes for stdin/stdout communication
   - Unit tests written but cannot run locally (missing dependencies)

3. **Launcher integration** (`sim/harness/launcher.py`):
   - Updated to use DockerProtocolAdapter for docker nodes
   - Tracks node_id -> container_id mapping
   - Registers protocol-based adapters with coordinator

**What needs testing:** Full end-to-end protocol flow with real Docker containers

---

## Objectives

1. **Run DockerProtocolAdapter unit tests** (tests/stages/M3h/test_docker_protocol_adapter.py)
   - Fix any environment issues (yaml module, etc.)
   - Verify all mocked protocol tests pass

2. **Create sample containerized service**
   - Build a simple test service that uses `containers/protocol_adapter.py`
   - Example: Echo service that receives events and sends them back
   - Should demonstrate event-driven virtual time advancement

3. **Create Docker integration tests**
   - Test INIT/ADVANCE/SHUTDOWN protocol flow
   - Test event passing (coordinator → container → coordinator)
   - Test virtual time progression (no wall-clock sleep)
   - Test clean shutdown and error handling

4. **Create end-to-end scenario test**
   - YAML scenario with protocol-based Docker node
   - Run full simulation via launcher
   - Verify deterministic execution (same seed → same results)

---

## Test Requirements

### Test 1: DockerProtocolAdapter Unit Tests

**File:** `tests/stages/M3h/test_docker_protocol_adapter.py` (already created)

**Requirements:**
- Fix environment dependencies (install yaml, etc.)
- All tests must pass
- Coverage: connect, init, advance, done, shutdown

### Test 2: Sample Container Service

**File:** `containers/examples/echo_service.py` (create)

**Requirements:**
- Imports and uses `CoordinatorProtocolAdapter`
- Implements simple echo behavior (input events → output events)
- Can run standalone: `python -m containers.examples.echo_service`
- Dockerfile provided for containerization

**Example implementation:**
```python
from containers.protocol_adapter import CoordinatorProtocolAdapter, Event

def echo_service(current_time_us, target_time_us, events):
    """Echo service: returns input events as output events."""
    output_events = []
    for event in events:
        output_events.append(Event(
            timestamp_us=target_time_us,
            event_type=f"echo_{event.event_type}",
            source="echo_service",
            payload=event.payload
        ))
    return output_events

if __name__ == "__main__":
    adapter = CoordinatorProtocolAdapter(echo_service, node_id="echo")
    adapter.run()
```

### Test 3: Docker Protocol Integration Tests

**File:** `tests/integration/test_m3h_docker_protocol.py` (create)

**Tests to include:**
1. `test_protocol_init_success`: Container receives INIT and responds READY
2. `test_protocol_advance_no_events`: Container receives ADVANCE with no events
3. `test_protocol_advance_with_events`: Container receives and processes events
4. `test_protocol_event_transformation`: Container transforms input → output events
5. `test_protocol_virtual_time`: Multiple ADVANCE calls progress virtual time
6. `test_protocol_shutdown_clean`: Container shuts down cleanly
7. `test_protocol_error_handling`: Container handles invalid messages gracefully

**Requirements:**
- Use echo_service container
- Build container image before tests
- Clean up containers after tests
- Assert on protocol message format and content

### Test 4: End-to-End Scenario Test

**File:** `tests/integration/test_m3h_scenario.py` (create)

**Test scenario:**
```yaml
duration_s: 1.0
seed: 42
time_quantum_us: 10000

nodes:
  - id: echo_node
    type: echo
    implementation: docker
    docker:
      image: xedgesim/echo-service
      build_context: containers/examples
      dockerfile: containers/examples/Dockerfile.echo

network:
  model: direct
```

**Tests to include:**
1. `test_run_docker_protocol_scenario`: Run scenario with protocol-based container
2. `test_deterministic_execution`: Same seed produces same events
3. `test_event_delivery`: Events delivered to/from container correctly
4. `test_coordinator_integration`: Coordinator manages container lifecycle

---

## Success Criteria

**All tests must pass:**
- [ ] DockerProtocolAdapter unit tests: All pass
- [ ] Docker protocol integration tests: All pass
- [ ] End-to-end scenario test: All pass
- [ ] Deterministic execution verified (same seed → same results)

**Documentation:**
- [ ] Results documented in `claude/results/TASK-M3h-protocol-integration-tests.md`
- [ ] Any bugs found and fixed (or reported to dev agent)
- [ ] Performance notes (container startup time, protocol overhead)

**Code quality:**
- [ ] No zombie processes after tests
- [ ] Clean Docker container cleanup (no orphans)
- [ ] Tests are isolated (can run individually)
- [ ] Clear error messages on failures

---

## Files to Test

**Created by development agent:**
- `containers/protocol_adapter.py` - Container-side protocol adapter
- `sim/harness/docker_protocol_adapter.py` - Coordinator-side adapter
- `sim/harness/launcher.py` - Updated for protocol nodes
- `sim/harness/coordinator.py` - Added add_adapter() method
- `tests/stages/M3h/test_protocol_adapter.py` - Protocol adapter unit tests (PASSING)
- `tests/stages/M3h/test_docker_protocol_adapter.py` - Docker adapter unit tests (NEEDS ENV)

**To be created by testing agent:**
- `containers/examples/echo_service.py` - Sample protocol service
- `containers/examples/Dockerfile.echo` - Dockerfile for echo service
- `tests/integration/test_m3h_docker_protocol.py` - Protocol integration tests
- `tests/integration/test_m3h_scenario.py` - End-to-end scenario tests
- `claude/results/TASK-M3h-protocol-integration-tests.md` - Test results

---

## Expected Issues and Mitigations

**Issue 1: Container startup latency**
- Mitigation: Use pre-built images, health checks, reasonable timeouts

**Issue 2: Protocol synchronization**
- Mitigation: Ensure buffered I/O, line-delimited JSON, proper flush()

**Issue 3: Subprocess pipe deadlocks**
- Mitigation: Use select() for non-blocking reads, separate stderr handling

**Issue 4: Container cleanup on test failure**
- Mitigation: Robust pytest fixtures with cleanup in finally blocks

---

## Notes from Development Agent

**Design decisions:**
- Protocol uses stdin/stdout (not sockets) for cleaner lifecycle management
- Container runs service via `python -m service` entrypoint
- Coordinator uses `docker exec -i` to attach stdin/stdout pipes
- Event format matches coordinator Event dataclass but with different field names:
  - `time_us` → `timestamp_us`
  - `type` → `event_type`
  - `src` → `source`
  - `dst` → `destination`

**Testing strategy:**
- Unit tests mock subprocess (development agent, DONE)
- Integration tests use real Docker (testing agent, THIS TASK)
- Delegation allows dev agent to continue with M3i while testing happens

**Regression testing:**
- All M0-M3g tests must still pass
- Protocol adapter unit tests (12/12) must still pass

---

## Deliverables

1. **All tests passing** (unit + integration + scenario)
2. **Sample echo service** with Dockerfile
3. **Test results documentation** in `claude/results/`
4. **Any bug fixes** committed to branch
5. **Update M3h report** (`docs/dev-log/M3h-report.md`) with test results

---

**Estimated time:** 3-4 hours
**Dependencies:** Docker daemon, pytest, Docker Python library
**Blocks:** M3h completion, M3i start

---

**Development agent:** Waiting for test results before marking M3h complete and starting M3i.
