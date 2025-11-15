# M2d: Hybrid Edge Tier (Docker + Python Models)

**Stage:** M2d
**Date:** 2025-11-15
**Status:** PLANNING

---

## Objective

Enable YAML scenarios to specify edge tier nodes as either Docker containers (realism) or Python models (determinism), allowing users to choose the appropriate trade-off for their experiments.

**Scope:**
- Extend YAML schema with `implementation` field for nodes
- Document how to select Docker vs Python model for edge tier
- Create integration test demonstrating hybrid approach
- Document determinism trade-offs

**Explicitly excluded:**
- Full YAML-based scenario runner (deferred)
- Automatic model selection logic
- Complex container configurations
- Hybrid simulation (Docker + Python in same scenario)

---

## Acceptance Criteria

1. ⬜ YAML schema supports `implementation: docker` or `implementation: python_model`
2. ⬜ Integration test shows both Docker and Python implementations work
3. ⬜ Integration test verifies functional equivalence
4. ⬜ Documentation explains when to use Docker vs Python models
5. ⬜ Determinism differences documented

---

## Design Decisions

### Current State Analysis

**Existing Infrastructure:**
- YAML parser: `sim/config/scenario.py` (M1b)
- Node types: Defined by `type` field (`sensor_model`, etc.)
- Execution: Socket-based protocol (nodes run as separate processes)

**M2 Additions:**
- DockerNode: Generic Docker container wrapper (M2a)
- Dual-mode nodes: SensorNode/GatewayNode support both server and direct modes (M2c)
- MQTT integration: Works with both Python nodes and Docker containers (M2c)

**Gap:** No way to specify in YAML whether edge tier should use Docker or Python model.

### YAML Schema Extension

**Current node configuration:**
```yaml
nodes:
  - id: gateway1
    type: gateway_model
    port: 5002
```

**Proposed extension:**
```yaml
nodes:
  - id: gateway1
    type: gateway
    implementation: python_model  # or "docker"
    port: 5002

    # Docker-specific config (only if implementation: docker)
    docker:
      image: xedgesim/gateway:latest
      build_context: containers/gateway
      ports:
        5000: 5000
```

**Design rationale:**
- `type` describes **what** the node does (sensor, gateway, broker)
- `implementation` describes **how** it's implemented (python_model, docker)
- Docker nodes can have additional `docker` section for container config
- Default `implementation: python_model` for backward compatibility

### Implementation Approach for M2d

Since run_scenario.py is still a P0 stub, M2d will focus on:

1. **Schema definition**: Extend `sim/config/scenario.py` to parse `implementation` field
2. **Integration test**: Create test showing both implementations work
3. **Documentation**: Explain trade-offs and usage

**NOT implementing in M2d:**
- Full YAML-based scenario runner (beyond M2 scope)
- Automatic instantiation based on YAML (requires runner)
- End-to-end scenario execution with YAML

This keeps M2d focused and testable without building infrastructure better suited for M3+.

### Docker vs Python Model Trade-offs

**Python Model (Deterministic):**
- ✅ Fully deterministic (virtual time, seeded RNG)
- ✅ Fast execution (no container overhead)
- ✅ Easy debugging (Python debugger)
- ✅ Reproducible results (exact same output every run)
- ❌ Not deployment-ready
- ❌ Simplified behavior (models, not real services)

**Docker Container (Realistic):**
- ✅ Deployment-ready (same container in sim and prod)
- ✅ Realistic behavior (real services, real implementations)
- ✅ Can test actual ML models, MQTT brokers, etc.
- ❌ Non-deterministic (wall-clock time, threading)
- ❌ Slower (container startup, network overhead)
- ❌ Statistical reproducibility only (need N trials + confidence intervals)

**When to use each:**
- **Python models**: Algorithm validation, deterministic testing, rapid iteration
- **Docker containers**: Deployment validation, realistic testing, integration testing

---

## Implementation Plan

**Step 1:** Extend YAML Schema
- Update `sim/config/scenario.py` to parse `implementation` field
- Add validation: `implementation` must be "python_model" or "docker"
- Add optional `docker` section for Docker-specific config
- Default to `python_model` if not specified

**Step 2:** Create Example YAML Scenarios
- `scenarios/m2d_python_gateway.yaml`: Gateway as Python model
- `scenarios/m2d_docker_gateway.yaml`: Gateway as Docker container
- Both scenarios should be functionally equivalent

**Step 3:** Create Integration Test
- `tests/stages/M2d/test_hybrid_edge.py`
- Test: Parse both YAML scenarios
- Test: Verify schema parsing works
- Test: Document expected behavior differences

**Step 4:** Document Trade-offs
- Update M2d-report.md with determinism discussion
- Add examples to documentation

---

## Tests to Add

### Schema Tests (tests/stages/M2d/)

**test_hybrid_schema.py:**
```python
def test_parse_python_model_node():
    """Test parsing node with implementation: python_model"""

def test_parse_docker_node():
    """Test parsing node with implementation: docker"""

def test_default_implementation():
    """Test default implementation is python_model"""

def test_docker_config_section():
    """Test Docker-specific config parsing"""

def test_invalid_implementation():
    """Test error on invalid implementation value"""
```

---

## Known Limitations

**Intentional for M2d:**
- No automatic instantiation (requires full scenario runner)
- No mixed scenarios (all nodes same implementation)
- No runtime switching between implementations
- No resource limits or container orchestration

**Rationale:** M2d focuses on schema and documentation. Full scenario runner is M3+ scope.

---

**Status:** PLANNING
**Estimated Time:** 2-3 hours (schema + tests + docs)
**Started:** 2025-11-15
