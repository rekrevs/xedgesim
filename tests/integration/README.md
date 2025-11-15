# Integration Tests

## Purpose

Integration tests validate end-to-end behavior across multiple major stages (M0, M1, M2, etc.).

Unlike stage-specific tests (in `tests/stages/`), integration tests:
- Test interactions between components from different stages
- Validate cumulative functionality
- Ensure new stages don't break earlier functionality

## Current Status

**M0 Complete:**
- No integration tests yet (only stage-specific tests)

**M1 Planned:**
- Integration test: Coordinator + Network Model + Nodes
- Validation: Network delays affect end-to-end latency

**M2 Planned:**
- Integration test: Full stack (Device + Network + Docker Edge + Cloud)
- Validation: Cross-tier packet flow works correctly

## Running Integration Tests

```bash
# Run all integration tests
pytest tests/integration/ -v

# Run with all stage tests
pytest tests/ -v
```

## Test Organization

Integration tests should be organized by feature/capability:
- `test_full_simulation.py`: Complete sim scenario
- `test_cross_tier_routing.py`: Multi-tier packet flow (M2+)
- `test_ml_placement.py`: ML inference placement (M3+)

## Guidelines

1. **Keep integration tests fast** (<10 seconds each)
2. **Use minimal scenarios** (few nodes, short duration)
3. **Test interfaces, not implementations** (validate behavior, not internals)
4. **Maintain independence** (each test should run standalone)
