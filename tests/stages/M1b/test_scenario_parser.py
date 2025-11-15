#!/usr/bin/env python3
"""
test_scenario_parser.py - M1b Unit Tests

Tests for YAML scenario parsing functionality.
Tests are written BEFORE implementation (TDD approach).
"""

import pytest
from pathlib import Path
import tempfile
import os

# Import will be added after implementation
# from sim.config.scenario import Scenario, load_scenario


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

    # Create temporary YAML file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(yaml_content)
        yaml_path = f.name

    try:
        # This import will work after implementation
        from sim.config.scenario import load_scenario

        scenario = load_scenario(yaml_path)

        # Verify simulation parameters
        assert scenario.duration_s == 10
        assert scenario.seed == 42
        assert scenario.time_quantum_us == 1000

        # Verify nodes
        assert len(scenario.nodes) == 3

        # Check sensor1
        sensor1 = next(n for n in scenario.nodes if n['id'] == 'sensor1')
        assert sensor1['type'] == 'sensor_model'
        assert sensor1['port'] == 5001

        # Check gateway
        gateway = next(n for n in scenario.nodes if n['id'] == 'gateway')
        assert gateway['type'] == 'gateway_model'
        assert gateway['port'] == 5004

    finally:
        os.unlink(yaml_path)


def test_parse_missing_file():
    """Test error handling for non-existent file."""
    from sim.config.scenario import load_scenario

    with pytest.raises(FileNotFoundError):
        load_scenario('nonexistent_scenario.yaml')


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
        from sim.config.scenario import load_scenario

        with pytest.raises(ValueError, match="Missing required.*simulation"):
            load_scenario(yaml_path)
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
        from sim.config.scenario import load_scenario

        with pytest.raises(ValueError, match="Missing required.*nodes"):
            load_scenario(yaml_path)
    finally:
        os.unlink(yaml_path)


def test_parse_invalid_yaml_syntax():
    """Test error handling for malformed YAML."""
    yaml_content = """
simulation:
  duration_s: 10
  seed: 42
  invalid syntax here: [unclosed bracket
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(yaml_content)
        yaml_path = f.name

    try:
        from sim.config.scenario import load_scenario

        # Should raise a YAML parsing error
        with pytest.raises(Exception):  # yaml.YAMLError or similar
            load_scenario(yaml_path)
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
        from sim.config.scenario import load_scenario

        with pytest.raises(ValueError, match="No nodes defined"):
            load_scenario(yaml_path)
    finally:
        os.unlink(yaml_path)


def test_parse_missing_node_fields():
    """Test error handling when node is missing required fields."""
    yaml_content = """
simulation:
  duration_s: 10
  seed: 42
  time_quantum_us: 1000

nodes:
  - id: sensor1
    type: sensor_model
    # Missing port field
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(yaml_content)
        yaml_path = f.name

    try:
        from sim.config.scenario import load_scenario

        with pytest.raises(ValueError, match="Missing required field.*port"):
            load_scenario(yaml_path)
    finally:
        os.unlink(yaml_path)


def test_scenario_dataclass_structure():
    """Test that Scenario dataclass has expected structure."""
    from sim.config.scenario import Scenario

    # Should be able to create a Scenario
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


def test_default_time_quantum():
    """Test that time_quantum_us has a sensible default if not specified."""
    yaml_content = """
simulation:
  duration_s: 10
  seed: 42
  # time_quantum_us omitted

nodes:
  - id: sensor1
    type: sensor_model
    port: 5001
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(yaml_content)
        yaml_path = f.name

    try:
        from sim.config.scenario import load_scenario

        scenario = load_scenario(yaml_path)

        # Should default to 1000 (1ms)
        assert scenario.time_quantum_us == 1000
    finally:
        os.unlink(yaml_path)


if __name__ == '__main__':
    # Run tests with pytest
    pytest.main([__file__, '-v'])
