# M0 Tests: Minimal Proof-of-Concept Validation

## What M0 Tests Validate

The M0 tests validate the core federated co-simulation concept:

1. **Socket-Based Coordination** (`test_m0_determinism.py`)
   - Coordinator can connect to multiple nodes via TCP sockets
   - INIT/ADVANCE/SHUTDOWN protocol works correctly
   - Nodes respond properly to time advancement commands

2. **Conservative Lockstep Algorithm**
   - All nodes advance together in synchronized steps
   - No node gets ahead of others
   - Time quantum is respected (1ms default)

3. **Determinism** (PRIMARY VALIDATION)
   - Two runs with same seed produce bit-identical results
   - All CSV output files have identical content
   - Hash-based verification of complete determinism

4. **Message Routing**
   - Messages from sensor nodes reach gateway
   - Expected message count matches actual
   - Cross-node communication works correctly

5. **Performance Baseline**
   - Simulation runs faster than realtime (target: >1x)
   - M0 achieves ~4.5x realtime for simple models

## Running M0 Tests

```bash
# From repository root
pytest tests/stages/M0/ -v

# Run specific test
pytest tests/stages/M0/test_m0_determinism.py::test_determinism -v

# Run with output
pytest tests/stages/M0/ -v -s
```

## Test Structure

**test_m0_determinism.py:**
- `SimulationRunner`: Helper class to start/stop simulation nodes
- `run_single_test()`: Runs one complete simulation
- `test_determinism()`: Main test - runs simulation twice, compares hashes
- `analyze_results()`: Post-test analysis of metrics

## Expected Results

```
✓ PASSED: Results are IDENTICAL
Hash 1: d376231ff78a8789b1b886b0476be4a2bcc626677cdbcac7b46579c4cf8fd589
Hash 2: d376231ff78a8789b1b886b0476be4a2bcc626677cdbcac7b46579c4cf8fd589
```

## Output Artifacts

After running tests, check `test_output_run*` directories:
- `coordinator.log`: Coordinator execution log
- `sensor*.log`: Sensor node logs
- `gateway.log`: Gateway node log
- `*_metrics.csv`: Metrics from each node

## Known Limitations

- Tests create output directories in repository root (not in tests/)
- No cleanup of old test_output_* directories (manual cleanup required)
- Tests require all nodes to be Python scripts (no compiled binaries yet)

## Determinism Requirements

For determinism to hold:
1. All nodes must use seeded RNG (hashlib-based, NOT Python's hash())
2. All nodes must be event-driven (no wall-clock dependencies)
3. All nodes must process events in time order
4. Coordinator must use stable message routing

Any change to node logic or coordinator that breaks these may cause determinism test to fail.
