"""
M2d: Hybrid Edge Tier Schema Tests

Tests YAML schema extension for Docker vs Python model selection.

Tests:
1. Parse node with implementation: python_model
2. Parse node with implementation: docker
3. Default implementation is python_model
4. Parse Docker-specific config section
5. Invalid implementation value raises error
6. Full scenario parsing (python_gateway.yaml)
7. Full scenario parsing (docker_gateway.yaml)
"""

try:
    import pytest
    PYTEST_AVAILABLE = True
except ImportError:
    pytest = None
    PYTEST_AVAILABLE = False

from pathlib import Path
from sim.config.scenario import load_scenario, Scenario


def test_parse_python_model_node():
    """Test parsing node with implementation: python_model"""
    scenario_yaml = """
simulation:
  duration_s: 10
  seed: 42

nodes:
  - id: test1
    type: gateway
    implementation: python_model
    port: 5000
"""
    # Write temporary YAML file
    temp_file = Path("/tmp/test_python_model.yaml")
    temp_file.write_text(scenario_yaml)

    # Parse scenario
    scenario = load_scenario(str(temp_file))

    # Verify
    assert len(scenario.nodes) == 1
    node = scenario.nodes[0]
    assert node['id'] == 'test1'
    assert node['type'] == 'gateway'
    assert node['implementation'] == 'python_model'
    assert node['docker'] is None

    # Cleanup
    temp_file.unlink()


def test_parse_docker_node():
    """Test parsing node with implementation: docker"""
    scenario_yaml = """
simulation:
  duration_s: 10
  seed: 42

nodes:
  - id: test1
    type: gateway
    implementation: docker
    port: 5000
    docker:
      image: xedgesim/gateway:latest
      build_context: containers/gateway
      ports:
        5000: 5000
"""
    temp_file = Path("/tmp/test_docker.yaml")
    temp_file.write_text(scenario_yaml)

    scenario = load_scenario(str(temp_file))

    assert len(scenario.nodes) == 1
    node = scenario.nodes[0]
    assert node['id'] == 'test1'
    assert node['type'] == 'gateway'
    assert node['implementation'] == 'docker'
    assert node['docker'] is not None
    assert node['docker']['image'] == 'xedgesim/gateway:latest'

    temp_file.unlink()


def test_default_implementation():
    """Test default implementation is python_model when not specified"""
    scenario_yaml = """
simulation:
  duration_s: 10
  seed: 42

nodes:
  - id: test1
    type: gateway
    port: 5000
"""
    temp_file = Path("/tmp/test_default.yaml")
    temp_file.write_text(scenario_yaml)

    scenario = load_scenario(str(temp_file))

    node = scenario.nodes[0]
    assert node['implementation'] == 'python_model'
    assert node['docker'] is None

    temp_file.unlink()


def test_docker_config_section():
    """Test Docker-specific config parsing with various fields"""
    scenario_yaml = """
simulation:
  duration_s: 10
  seed: 42

nodes:
  - id: test1
    type: gateway
    implementation: docker
    port: 5000
    docker:
      image: xedgesim/gateway:latest
      build_context: containers/gateway
      ports:
        5000: 5000
        8080: 8080
      environment:
        LOG_LEVEL: debug
"""
    temp_file = Path("/tmp/test_docker_config.yaml")
    temp_file.write_text(scenario_yaml)

    scenario = load_scenario(str(temp_file))

    node = scenario.nodes[0]
    docker = node['docker']
    assert docker['image'] == 'xedgesim/gateway:latest'
    assert docker['build_context'] == 'containers/gateway'
    assert docker['ports'][5000] == 5000
    assert docker['ports'][8080] == 8080
    assert docker['environment']['LOG_LEVEL'] == 'debug'

    temp_file.unlink()


def test_invalid_implementation():
    """Test error on invalid implementation value"""
    scenario_yaml = """
simulation:
  duration_s: 10
  seed: 42

nodes:
  - id: test1
    type: gateway
    implementation: invalid_value
    port: 5000
"""
    temp_file = Path("/tmp/test_invalid.yaml")
    temp_file.write_text(scenario_yaml)

    try:
        load_scenario(str(temp_file))
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "implementation must be 'python_model' or 'docker'" in str(e)

    temp_file.unlink()


def test_load_python_gateway_scenario():
    """Test loading full python_gateway.yaml scenario"""
    scenario_path = "scenarios/m2d/python_gateway.yaml"

    # Skip if scenario file doesn't exist (may not be committed yet)
    if not Path(scenario_path).exists():
        if PYTEST_AVAILABLE:
            pytest.skip(f"Scenario file not found: {scenario_path}")
        else:
            print(f"   ⚠ Skipped: Scenario file not found: {scenario_path}")
            return

    scenario = load_scenario(scenario_path)

    # Verify simulation parameters
    assert scenario.duration_s == 10
    assert scenario.seed == 42
    assert scenario.time_quantum_us == 1000

    # Verify network configuration
    assert scenario.network is not None
    assert scenario.network.model == 'latency'

    # Verify nodes
    assert len(scenario.nodes) == 2

    sensor = scenario.nodes[0]
    assert sensor['id'] == 'sensor1'
    assert sensor['type'] == 'sensor'
    assert sensor['implementation'] == 'python_model'

    gateway = scenario.nodes[1]
    assert gateway['id'] == 'gateway1'
    assert gateway['type'] == 'gateway'
    assert gateway['implementation'] == 'python_model'
    assert gateway['docker'] is None


def test_load_docker_gateway_scenario():
    """Test loading full docker_gateway.yaml scenario"""
    scenario_path = "scenarios/m2d/docker_gateway.yaml"

    if not Path(scenario_path).exists():
        if PYTEST_AVAILABLE:
            pytest.skip(f"Scenario file not found: {scenario_path}")
        else:
            print(f"   ⚠ Skipped: Scenario file not found: {scenario_path}")
            return

    scenario = load_scenario(scenario_path)

    # Verify nodes
    assert len(scenario.nodes) == 2

    sensor = scenario.nodes[0]
    assert sensor['implementation'] == 'python_model'

    gateway = scenario.nodes[1]
    assert gateway['id'] == 'gateway1'
    assert gateway['implementation'] == 'docker'
    assert gateway['docker'] is not None
    assert gateway['docker']['image'] == 'xedgesim/gateway:latest'


def test_docker_without_docker_config():
    """Test Docker node can work without docker config section (uses defaults)"""
    scenario_yaml = """
simulation:
  duration_s: 10
  seed: 42

nodes:
  - id: test1
    type: gateway
    implementation: docker
    port: 5000
"""
    temp_file = Path("/tmp/test_docker_no_config.yaml")
    temp_file.write_text(scenario_yaml)

    # Should parse successfully
    scenario = load_scenario(str(temp_file))

    node = scenario.nodes[0]
    assert node['implementation'] == 'docker'
    assert node['docker'] is None  # No config provided

    temp_file.unlink()


if __name__ == "__main__":
    # Run tests manually
    print("Running M2d hybrid schema tests...")

    print("\n1. Testing python_model node parsing...")
    test_parse_python_model_node()
    print("   ✓ Passed")

    print("\n2. Testing docker node parsing...")
    test_parse_docker_node()
    print("   ✓ Passed")

    print("\n3. Testing default implementation...")
    test_default_implementation()
    print("   ✓ Passed")

    print("\n4. Testing Docker config section...")
    test_docker_config_section()
    print("   ✓ Passed")

    print("\n5. Testing invalid implementation...")
    test_invalid_implementation()
    print("   ✓ Passed")

    print("\n6. Testing python_gateway.yaml...")
    test_load_python_gateway_scenario()
    print("   ✓ Passed")

    print("\n7. Testing docker_gateway.yaml...")
    test_load_docker_gateway_scenario()
    print("   ✓ Passed")

    print("\n8. Testing Docker without config section...")
    test_docker_without_docker_config()
    print("   ✓ Passed")

    print("\n✓ All M2d hybrid schema tests passed!")
