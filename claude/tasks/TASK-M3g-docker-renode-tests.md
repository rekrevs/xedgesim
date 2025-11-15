# TASK-M3g-docker-renode-tests

**Status:** PENDING
**Stage:** M3g (Scenario-Driven Orchestration Harness)
**Created:** 2025-11-15
**Assigned to:** Testing Agent (has Docker + Renode)

---

## Context

The development agent has implemented M3g (Scenario-Driven Orchestration Harness) which provides:
- `SimulationLauncher` class for managing all node lifecycles
- Updated `run_scenario.py` CLI for YAML scenario execution
- Unit tests that run locally without Docker/Renode

**What's committed:**
- `sim/harness/launcher.py` (full implementation)
- `sim/harness/run_scenario.py` (full implementation)
- `sim/harness/__init__.py` (exports)
- `tests/stages/M3g/test_launcher_unit.py` (14 local unit tests)

**What needs testing:**
- Docker container lifecycle management
- Renode process management (if needed for M3g)
- Integration tests with actual Docker containers
- Full scenario execution with mixed node types

**Delegation reason:**
Testing agent has Docker daemon and can test container functionality.

---

## Your Task

Test the M3g implementation with Docker containers and write integration tests.

### Phase 1: Run Local Unit Tests

```bash
# Verify local tests pass
pytest tests/stages/M3g/test_launcher_unit.py -v
```

Expected: All 14 tests pass

### Phase 2: Test Docker Container Management

The launcher has Docker container lifecycle stubs that need testing:

1. **Test Docker detection:**
   ```bash
   python3 -c "import subprocess; print(subprocess.run(['docker', '--version'], capture_output=True))"
   ```

2. **Create test Docker integration:**
   Write `tests/stages/M3g/test_docker_integration.py` with:
   - Test starting a simple Docker container via launcher
   - Test container appears in `docker ps`
   - Test launcher can stop the container
   - Test cleanup works (no orphan containers)

3. **Test with existing containers:**
   If possible, test launcher with existing xEdgeSim containers:
   - `xedgesim/ml-inference` (from M3a)
   - `xedgesim/mqtt-gateway` (if exists)

### Phase 3: Integration Tests

Write `tests/integration/test_m3g_scenario.py`:

```python
@pytest.mark.integration
def test_run_simple_python_scenario(tmp_path):
    """Test running simple Python-only scenario end-to-end."""
    # Create YAML scenario with Python nodes only
    # Use launcher to execute
    # Verify completion and metrics

@pytest.mark.integration
@pytest.mark.docker
def test_run_scenario_with_docker_nodes(tmp_path):
    """Test running scenario with Docker containers."""
    # Create YAML with Docker node
    # Use launcher to execute
    # Verify Docker container lifecycle

@pytest.mark.integration
def test_dry_run_mode(tmp_path):
    """Test --dry-run validation mode."""
    # Create YAML scenario
    # Run with --dry-run
    # Verify validates but doesn't execute
```

### Phase 4: Test run_scenario.py CLI

```bash
# Test CLI with a simple scenario
cat > /tmp/test_scenario.yaml <<EOF
simulation:
  duration_s: 0.1
  seed: 42
  time_quantum_us: 1000

nodes:
  - id: sensor1
    type: sensor
    implementation: python_model
    port: 5001

network:
  model: direct
EOF

# Test execution (will fail without nodes running, but should validate)
python3 sim/harness/run_scenario.py /tmp/test_scenario.yaml --dry-run

# Verify output shows validation
```

---

## Expected Results

### Success Criteria

- [ ] All local unit tests pass (14/14)
- [ ] Docker container lifecycle works:
  - [ ] Launcher can detect Docker
  - [ ] Can start containers
  - [ ] Can stop containers
  - [ ] Clean shutdown (no orphans)
- [ ] Integration tests written and passing:
  - [ ] Python-only scenario runs
  - [ ] Docker scenario runs (if containers available)
  - [ ] Dry-run validation works
- [ ] CLI works correctly:
  - [ ] Loads YAML scenarios
  - [ ] --dry-run validates without executing
  - [ ] --seed override works
  - [ ] Error messages are clear

### Test Output

Should see something like:
```
tests/stages/M3g/test_launcher_unit.py::TestScenarioValidation::test_validate_simple_scenario_passes PASSED
tests/stages/M3g/test_launcher_unit.py::TestScenarioValidation::test_validate_renode_missing_firmware PASSED
...
tests/stages/M3g/test_docker_integration.py::test_docker_container_lifecycle PASSED
tests/integration/test_m3g_scenario.py::test_run_simple_python_scenario PASSED
...

M3g Testing: X/Y tests passed
```

---

## If Tests Fail

### Docker Not Available
If Docker daemon isn't running:
```bash
# Start Docker (macOS with Colima)
colima start

# Verify Docker works
docker run hello-world
```

### Container Startup Fails
- Check Docker logs: `docker logs <container_id>`
- Check launcher error messages
- Verify container image exists or can be built

### Integration Test Issues
- Add verbose logging: modify launcher to print more details
- Check process cleanup: `ps aux | grep python`
- Check container cleanup: `docker ps -a`

### Port Conflicts
- Tests might fail if ports already in use
- Use dynamic port allocation or check/kill conflicting processes

---

## Document Results

Create `claude/results/TASK-M3g-docker-renode-tests.md` with:

```markdown
# TASK-M3g-docker-renode-tests Results

**Status:** ✅ SUCCESS / ❌ FAILED / ⚠️ PARTIAL
**Completed:** YYYY-MM-DD
**Tested by:** Testing Agent

## Test Results

### Local Unit Tests
- Command: `pytest tests/stages/M3g/test_launcher_unit.py -v`
- Result: X/14 passed
- Output:
```
[paste full output]
```

### Docker Integration Tests
- Command: `pytest tests/stages/M3g/test_docker_integration.py -v`
- Result: X/Y passed
- Output:
```
[paste output]
```

### Integration Tests
- Command: `pytest tests/integration/test_m3g_scenario.py -v`
- Result: X/Y passed
- Output:
```
[paste output]
```

### CLI Tests
- Dry-run test: [PASS/FAIL]
- Output:
```
[paste output]
```

## Issues Found

1. [Issue description]
   - Severity: [CRITICAL / MAJOR / MINOR]
   - Location: [file:line]
   - Details: ...

## Fixes Applied

1. [Fix description]
   - Files modified: ...
   - Commit: [hash]
   - Rationale: ...

## Commits Made

```bash
git log --oneline [hash range]
```

## Next Steps for Developer Agent

- [ ] Review test results
- [ ] Integrate findings into M3g-report.md
- [ ] Address any critical issues
- [ ] Proceed to M3h if all tests pass

## Notes

[Any additional observations, performance notes, suggestions]
```

---

## Deliverables

When complete, you should have:

1. **Test results file:** `claude/results/TASK-M3g-docker-renode-tests.md`
2. **New test files:**
   - `tests/stages/M3g/test_docker_integration.py`
   - `tests/integration/test_m3g_scenario.py`
3. **Commits** (if fixes needed):
   - Fix commits with descriptive messages
   - Test commits
4. **All changes pushed** to the same branch

Then notify the user that M3g testing is complete.

---

**Remember:**
- Run all existing M0-M3 regression tests to ensure no breakage
- Document all issues found, even minor ones
- If you make code fixes, explain why in the results file
- Push all changes before completing the task

---

**Created by:** Development Agent
**For stage:** M3g (Scenario-Driven Orchestration Harness)
**Blocks:** M3h implementation
