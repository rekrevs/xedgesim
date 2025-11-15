# M3fc Stage Report: Coordinator Integration

**Stage:** M3fc (Minor stage of M3f)
**Created:** 2025-11-15
**Status:** IN PROGRESS
**Objective:** Integrate RenodeNode into coordinator and validate end-to-end simulation with actual firmware

---

## 1. Objective

Integrate the RenodeNode adapter (M3fa) and Zephyr firmware (M3fb) into the coordinator to enable full device-tier emulation within simulations:

1. Integrate RenodeNode class into coordinator node factory
2. Extend YAML schema to support Renode node configuration
3. Create end-to-end integration tests with actual Renode processes
4. Validate time synchronization between coordinator and Renode
5. Test determinism with real firmware execution
6. Create example scenarios demonstrating device emulation

This stage brings together M3fa and M3fb into a working system where the coordinator manages Renode processes running real firmware as part of the simulation.

---

## 2. Acceptance Criteria

**Must have:**
- [ ] Coordinator can create and manage RenodeNode instances
- [ ] YAML schema extended for Renode node type with required config
- [ ] Integration test: coordinator → RenodeNode → Renode → firmware → UART → events
- [ ] Time synchronization working: coordinator advances, Renode executes firmware
- [ ] Events from firmware flow through network model to other nodes
- [ ] Determinism test: same scenario YAML + seed → identical results
- [ ] Example scenario YAML demonstrating device emulation
- [ ] All existing M0-M3 tests still pass

**Should have:**
- [ ] Multiple Renode nodes in single simulation
- [ ] Error handling for Renode startup failures
- [ ] Graceful shutdown of all Renode processes

**Nice to have:**
- [ ] Performance metrics (time overhead vs pure Python nodes)
- [ ] Mixed node types: Renode + SensorNode + GatewayNode + CloudService

---

## 3. Design Decisions

### 3.1 Coordinator Integration Points

**Node factory extension:**
```python
# sim/coordinator.py
class Coordinator:
    def _create_node(self, node_id: str, config: dict):
        node_type = config.get('type', 'sensor')

        if node_type == 'sensor':
            return SensorNode(node_id, config)
        elif node_type == 'renode':
            return RenodeNode(node_id, config)  # NEW
        elif node_type == 'gateway':
            return GatewayNode(node_id, config)
        elif node_type == 'cloud':
            return CloudService(node_id, config)
        else:
            raise ValueError(f"Unknown node type: {node_type}")
```

**YAML schema extension:**
```yaml
nodes:
  sensor_device:
    type: renode
    platform: platforms/nrf52840.repl  # Path to Renode platform file
    firmware: firmware/sensor-node/build/zephyr/zephyr.elf
    monitor_port: 9999
    working_dir: /tmp/xedgesim/sensor_device
    seed: 42  # For deterministic RNG in firmware

  gateway_1:
    type: gateway
    # ... existing config
```

### 3.2 Time Synchronization Strategy

**Conservative synchronous lockstep (as designed in M3fa):**

1. Coordinator determines next event time across all nodes
2. For each node, call `node.advance(target_time_us)`
3. RenodeNode translates to Renode `emulation RunFor` command
4. Renode executes firmware for that duration
5. Firmware outputs JSON events over UART
6. RenodeNode parses UART, returns Event objects
7. Coordinator processes events and continues

**Key insight:** Coordinator doesn't need to know RenodeNode uses Renode internally - it just calls `advance()` like any other node.

### 3.3 Error Handling

**Renode startup failures:**
- If Renode process fails to start: log error, raise exception
- Coordinator fails fast during initialization (better than partial startup)

**Renode crashes during simulation:**
- RenodeNode detects via socket closure or process exit
- Raises RenodeConnectionError
- Coordinator catches and logs, can optionally retry or fail simulation

**Graceful shutdown:**
- Coordinator calls `node.stop()` on all nodes in destructor
- RenodeNode sends 'quit' to Renode, closes socket, terminates process
- Ensures no zombie Renode processes

### 3.4 Configuration Validation

**Required fields for Renode nodes:**
- `type: renode`
- `platform`: Path to .repl file (absolute or relative to scenario YAML)
- `firmware`: Path to .elf file (absolute or relative to scenario YAML)

**Optional fields:**
- `monitor_port`: TCP port for Renode monitor (default: auto-assign)
- `working_dir`: Directory for .resc scripts (default: /tmp/xedgesim/{node_id})
- `seed`: RNG seed for firmware (firmware must support this)

**Validation:**
- Check files exist before starting Renode
- Validate port availability
- Ensure working_dir is writable

---

## 4. Tests Designed (Test-First Approach)

### 4.1 Unit Tests (Coordinator Integration)

```python
# tests/stages/M3fc/test_coordinator_renode.py

class TestCoordinatorRenodeIntegration:
    """Test coordinator can create and manage Renode nodes."""

    def test_create_renode_node_from_yaml(self, tmp_path):
        """Test coordinator creates RenodeNode from YAML config."""
        scenario = {
            'nodes': {
                'sensor_1': {
                    'type': 'renode',
                    'platform': 'path/to/nrf52840.repl',
                    'firmware': 'path/to/zephyr.elf',
                    'seed': 42
                }
            }
        }

        # Mock file existence
        # Create coordinator
        # Verify RenodeNode instance created
        # Verify config passed correctly

    def test_coordinator_advances_renode_node(self):
        """Test coordinator can advance RenodeNode time."""
        # Create coordinator with mock RenodeNode
        # Advance to time T
        # Verify RenodeNode.advance(T) was called
        # Verify events returned
```

### 4.2 Integration Tests (End-to-End)

```python
# tests/stages/M3fc/test_e2e_renode.py

class TestEndToEndRenode:
    """Integration tests with actual Renode process."""

    @pytest.mark.integration
    @pytest.mark.skipif(not has_renode(), reason="Renode not installed")
    def test_coordinator_with_real_renode(self, firmware_path, platform_path):
        """
        Test full flow: coordinator → RenodeNode → Renode → firmware → events.

        This test requires:
        - Renode installed
        - Firmware built (zephyr.elf)
        - nRF52840 platform file
        """
        scenario = {
            'nodes': {
                'sensor_1': {
                    'type': 'renode',
                    'platform': platform_path,
                    'firmware': firmware_path,
                    'seed': 42
                }
            },
            'duration_sec': 5.0
        }

        coordinator = Coordinator(scenario)
        coordinator.run()

        # Verify:
        # - Renode process started
        # - Firmware executed
        # - Events received (JSON from UART)
        # - Coordinator completed successfully
        # - No zombie processes
```

### 4.3 Determinism Tests

```python
class TestDeterminism:
    """Test determinism with real firmware."""

    @pytest.mark.integration
    def test_same_seed_identical_results(self, scenario_file):
        """Run simulation twice with same seed, verify identical results."""

        # Run 1
        events1 = run_scenario(scenario_file, seed=42)

        # Run 2
        events2 = run_scenario(scenario_file, seed=42)

        # Compare
        assert events1 == events2  # Identical event sequences
```

### 4.4 Mixed Node Type Tests

```python
class TestMixedNodes:
    """Test simulations with both Renode and Python nodes."""

    def test_renode_sensor_with_python_gateway(self):
        """
        Test scenario:
        - Renode sensor node (firmware)
        - Python gateway node
        - Events flow: sensor → network → gateway
        """
        scenario = {
            'nodes': {
                'sensor_1': {
                    'type': 'renode',
                    'platform': 'platforms/nrf52840.repl',
                    'firmware': 'firmware/sensor-node/build/zephyr/zephyr.elf'
                },
                'gateway_1': {
                    'type': 'gateway'
                }
            },
            'connections': [
                {'from': 'sensor_1', 'to': 'gateway_1', 'latency_ms': 10}
            ]
        }

        # Run simulation
        # Verify events reach gateway from Renode sensor
```

---

## 5. Implementation

### 5.1 File Structure

```
sim/
├── coordinator.py (MODIFY: add Renode support)
└── device/
    ├── __init__.py (ALREADY UPDATED)
    └── renode_node.py (ALREADY COMPLETE)

tests/stages/M3fc/
├── __init__.py
├── test_coordinator_renode.py (unit tests)
├── test_e2e_renode.py (integration tests)
└── test_determinism.py (determinism validation)

examples/
└── scenarios/
    └── device_emulation_basic.yaml (example scenario)
```

### 5.2 Implementation Notes

(To be filled during implementation)

---

## 6. Test Results

### 6.1 Unit Tests

(To be filled)

### 6.2 Integration Tests

(To be filled)

### 6.3 Determinism Tests

(To be filled)

### 6.4 Regression Tests (M0-M3)

(To be filled)

---

## 7. Code Review Checklist

(To be completed before commit)

See: `docs/dev-log/M3fc-review-checklist.md`

---

## 8. Lessons Learned

(To be filled after completion)

**What worked well:**
- TBD

**Challenges:**
- TBD

**For next stages:**
- TBD

---

## 9. Contribution to M3f Goal

This stage completes the core Renode integration:
- ⏭️ Brings M3fa and M3fb together into working system
- ⏭️ Validates end-to-end flow with actual firmware
- ⏭️ Proves "deployable artifact" claim
- ⏭️ Enables device-tier emulation in full simulations
- ⏭️ (Optional) Prepares for ML inference (M3fd)

**Next stage:** M3fd - Device ML inference (optional) or M3f summary

---

## 10. Known Limitations and Technical Debt

(To be documented during implementation)

**Deferred to later stages:**
- TBD

**Known issues:**
- TBD

---

**Status:** IN PROGRESS
**Last updated:** 2025-11-15
