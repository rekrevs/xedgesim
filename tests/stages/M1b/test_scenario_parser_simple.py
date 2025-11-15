#!/usr/bin/env python3
"""
test_scenario_parser_simple.py - M1b Unit Tests (No pytest required)

Simple test runner that works without pytest installed.
"""

import tempfile
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from sim.config.scenario import Scenario, load_scenario


def test_parse_valid_scenario():
    """Test parsing a complete, valid YAML scenario."""
    yaml_content = """
simulation:
  duration_s: 10
  seed: 42
  time_quantum_us: 1000

nodes:
  - id: sensor1
    type: sensor_model
    port: 5001

  - id: sensor2
    type: sensor_model
    port: 5002

  - id: gateway
    type: gateway_model
    port: 5004
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(yaml_content)
        yaml_path = f.name

    try:
        scenario = load_scenario(yaml_path)

        # Verify simulation parameters
        assert scenario.duration_s == 10, f"Expected duration_s=10, got {scenario.duration_s}"
        assert scenario.seed == 42, f"Expected seed=42, got {scenario.seed}"
        assert scenario.time_quantum_us == 1000, f"Expected time_quantum_us=1000, got {scenario.time_quantum_us}"

        # Verify nodes
        assert len(scenario.nodes) == 3, f"Expected 3 nodes, got {len(scenario.nodes)}"

        # Check sensor1
        sensor1 = next(n for n in scenario.nodes if n['id'] == 'sensor1')
        assert sensor1['type'] == 'sensor_model'
        assert sensor1['port'] == 5001

        # Check gateway
        gateway = next(n for n in scenario.nodes if n['id'] == 'gateway')
        assert gateway['type'] == 'gateway_model'
        assert gateway['port'] == 5004

        print("✓ test_parse_valid_scenario PASSED")
        return True

    except AssertionError as e:
        print(f"✗ test_parse_valid_scenario FAILED: {e}")
        return False
    finally:
        os.unlink(yaml_path)


def test_parse_missing_file():
    """Test error handling for non-existent file."""
    try:
        load_scenario('nonexistent_scenario.yaml')
        print("✗ test_parse_missing_file FAILED: Should have raised FileNotFoundError")
        return False
    except FileNotFoundError:
        print("✓ test_parse_missing_file PASSED")
        return True


def test_parse_missing_simulation_section():
    """Test error handling when simulation section is missing."""
    yaml_content = """
nodes:
  - id: sensor1
    type: sensor_model
    port: 5001
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(yaml_content)
        yaml_path = f.name

    try:
        try:
            load_scenario(yaml_path)
            print("✗ test_parse_missing_simulation_section FAILED: Should have raised ValueError")
            return False
        except ValueError as e:
            if "simulation" in str(e).lower():
                print("✓ test_parse_missing_simulation_section PASSED")
                return True
            else:
                print(f"✗ test_parse_missing_simulation_section FAILED: Wrong error: {e}")
                return False
    finally:
        os.unlink(yaml_path)


def test_parse_missing_nodes_section():
    """Test error handling when nodes section is missing."""
    yaml_content = """
simulation:
  duration_s: 10
  seed: 42
  time_quantum_us: 1000
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(yaml_content)
        yaml_path = f.name

    try:
        try:
            load_scenario(yaml_path)
            print("✗ test_parse_missing_nodes_section FAILED: Should have raised ValueError")
            return False
        except ValueError as e:
            if "nodes" in str(e).lower():
                print("✓ test_parse_missing_nodes_section PASSED")
                return True
            else:
                print(f"✗ test_parse_missing_nodes_section FAILED: Wrong error: {e}")
                return False
    finally:
        os.unlink(yaml_path)


def test_parse_empty_nodes_list():
    """Test error handling when nodes list is empty."""
    yaml_content = """
simulation:
  duration_s: 10
  seed: 42
  time_quantum_us: 1000

nodes: []
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(yaml_content)
        yaml_path = f.name

    try:
        try:
            load_scenario(yaml_path)
            print("✗ test_parse_empty_nodes_list FAILED: Should have raised ValueError")
            return False
        except ValueError as e:
            if "no nodes" in str(e).lower():
                print("✓ test_parse_empty_nodes_list PASSED")
                return True
            else:
                print(f"✗ test_parse_empty_nodes_list FAILED: Wrong error: {e}")
                return False
    finally:
        os.unlink(yaml_path)


def test_scenario_dataclass_structure():
    """Test that Scenario dataclass has expected structure."""
    scenario = Scenario(
        duration_s=10,
        seed=42,
        time_quantum_us=1000,
        nodes=[
            {'id': 'test', 'type': 'sensor_model', 'port': 5001}
        ]
    )

    assert scenario.duration_s == 10
    assert scenario.seed == 42
    assert scenario.time_quantum_us == 1000
    assert len(scenario.nodes) == 1

    print("✓ test_scenario_dataclass_structure PASSED")
    return True


def test_default_time_quantum():
    """Test that time_quantum_us has a sensible default if not specified."""
    yaml_content = """
simulation:
  duration_s: 10
  seed: 42

nodes:
  - id: sensor1
    type: sensor_model
    port: 5001
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(yaml_content)
        yaml_path = f.name

    try:
        scenario = load_scenario(yaml_path)

        # Should default to 1000 (1ms)
        assert scenario.time_quantum_us == 1000, f"Expected default 1000, got {scenario.time_quantum_us}"
        print("✓ test_default_time_quantum PASSED")
        return True

    except AssertionError as e:
        print(f"✗ test_default_time_quantum FAILED: {e}")
        return False
    finally:
        os.unlink(yaml_path)


def test_load_example_scenarios():
    """Test loading the example scenario files."""
    scenarios_dir = project_root / "scenarios"

    # Test m0_baseline.yaml
    m0_baseline = scenarios_dir / "m0_baseline.yaml"
    if m0_baseline.exists():
        scenario = load_scenario(str(m0_baseline))
        assert scenario.duration_s == 10
        assert scenario.seed == 42
        assert len(scenario.nodes) == 4
        print("✓ test_load_m0_baseline PASSED")
    else:
        print("✗ m0_baseline.yaml not found")
        return False

    # Test m1b_minimal.yaml
    m1b_minimal = scenarios_dir / "m1b_minimal.yaml"
    if m1b_minimal.exists():
        scenario = load_scenario(str(m1b_minimal))
        assert scenario.duration_s == 2
        assert scenario.seed == 123
        assert len(scenario.nodes) == 2
        print("✓ test_load_m1b_minimal PASSED")
    else:
        print("✗ m1b_minimal.yaml not found")
        return False

    return True


def main():
    """Run all tests."""
    print("="*60)
    print("M1b Scenario Parser Tests")
    print("="*60)

    tests = [
        test_parse_valid_scenario,
        test_parse_missing_file,
        test_parse_missing_simulation_section,
        test_parse_missing_nodes_section,
        test_parse_empty_nodes_list,
        test_scenario_dataclass_structure,
        test_default_time_quantum,
        test_load_example_scenarios,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ {test.__name__} FAILED with exception: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("="*60)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*60)

    return failed == 0


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
