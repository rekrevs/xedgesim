#!/usr/bin/env python3
"""
test_m3g_scenario.py - M3g Scenario Integration Tests

Tests end-to-end scenario execution with the launcher:
- Simple Python-only scenarios
- Scenarios with Docker containers
- Dry-run validation mode
- Seed overrides

Requirements:
- pytest
- Docker (for docker tests)
"""

import pytest
import subprocess
import time
import tempfile
import yaml
from pathlib import Path
import sys

# Add project root to path
_project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_project_root))

from sim.harness.launcher import SimulationLauncher, run_scenario
from sim.config.scenario import Scenario, load_scenario


def docker_available():
    """Check if Docker daemon is available."""
    try:
        result = subprocess.run(['docker', '--version'],
                              capture_output=True,
                              timeout=5)
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def cleanup_xedgesim_containers():
    """Clean up any leftover xedgesim containers."""
    result = subprocess.run(
        ['docker', 'ps', '-a', '--filter', 'name=xedgesim-', '--format', '{{.ID}}'],
        capture_output=True,
        text=True
    )
    containers = result.stdout.strip().split('\n') if result.stdout.strip() else []
    for container_id in containers:
        subprocess.run(['docker', 'stop', container_id], capture_output=True)
        subprocess.run(['docker', 'rm', container_id], capture_output=True)


@pytest.fixture(autouse=True)
def docker_cleanup():
    """Cleanup Docker containers before and after tests."""
    cleanup_xedgesim_containers()
    yield
    cleanup_xedgesim_containers()


@pytest.mark.integration
class TestSimpleScenarios:
    """Test simple scenario execution."""

    def test_validate_simple_scenario(self, tmp_path):
        """Test scenario validation without execution."""
        # Create a simple scenario
        scenario = Scenario(
            duration_s=0.1,
            seed=42,
            time_quantum_us=10000,
            nodes=[
                {
                    'id': 'sensor1',
                    'type': 'sensor',
                    'implementation': 'python_model',
                    'port': 5001
                }
            ]
        )

        launcher = SimulationLauncher(scenario)

        # Validate (should not raise)
        errors = launcher.validate_scenario()
        assert errors == [], f"Validation should pass, got errors: {errors}"

    def test_validate_catches_missing_renode_files(self, tmp_path):
        """Test validation catches missing Renode files."""
        scenario = Scenario(
            duration_s=0.1,
            seed=42,
            time_quantum_us=10000,
            nodes=[
                {
                    'id': 'device1',
                    'type': 'renode',
                    'implementation': 'renode_inprocess',
                    'firmware': '/nonexistent/firmware.elf',
                    'platform': '/nonexistent/platform.repl',
                    'monitor_port': 9999
                }
            ]
        )

        launcher = SimulationLauncher(scenario)
        errors = launcher.validate_scenario()

        assert len(errors) > 0, "Should have validation errors"
        assert any('firmware' in e.lower() for e in errors), "Should mention firmware"
        assert any('platform' in e.lower() for e in errors), "Should mention platform"


@pytest.mark.integration
@pytest.mark.docker
@pytest.mark.skipif(not docker_available(), reason="Docker not available")
class TestDockerScenarios:
    """Test scenarios with Docker containers."""

    def test_run_scenario_with_docker_node(self, tmp_path):
        """Test running scenario with a Docker container."""
        # Create scenario with Docker node
        scenario_dict = {
            'simulation': {
                'duration_s': 0.1,
                'seed': 42,
                'time_quantum_us': 100000
            },
            'nodes': [
                {
                    'id': 'alpine_node',
                    'type': 'docker',
                    'implementation': 'docker',
                    'port': 5001,  # Required field
                    'docker': {
                        'image': 'alpine:latest',
                        'command': ['sleep', '5']
                    }
                }
            ]
        }

        # Write to YAML file
        scenario_file = tmp_path / "test_scenario.yaml"
        with open(scenario_file, 'w') as f:
            yaml.dump(scenario_dict, f)

        # Load scenario
        scenario = load_scenario(str(scenario_file))

        launcher = SimulationLauncher(scenario)

        # Validate
        errors = launcher.validate_scenario()
        assert errors == [], f"Validation should pass, got: {errors}"

        # Start Docker container
        launcher._start_docker_container(scenario.nodes[0])

        # Verify container is running
        assert len(launcher.docker_containers) == 1, "Should have 1 container"

        # Cleanup
        launcher.shutdown()

        # Wait for cleanup
        time.sleep(0.5)

        # Verify cleanup
        result = subprocess.run(
            ['docker', 'ps', '-a', '--filter', 'name=xedgesim-alpine_node'],
            capture_output=True,
            text=True
        )
        assert 'xedgesim-alpine_node' not in result.stdout, "Container should be removed"


@pytest.mark.integration
class TestDryRunMode:
    """Test dry-run validation mode."""

    def test_dry_run_validates_without_execution(self, tmp_path):
        """Test that validation works in dry-run mode."""
        # Create a valid scenario
        scenario_dict = {
            'simulation': {
                'duration_s': 10.0,
                'seed': 42,
                'time_quantum_us': 1000000
            },
            'nodes': [
                {
                    'id': 'sensor1',
                    'type': 'sensor',
                    'implementation': 'python_model',
                    'port': 5001
                }
            ]
        }

        scenario_file = tmp_path / "valid_scenario.yaml"
        with open(scenario_file, 'w') as f:
            yaml.dump(scenario_dict, f)

        # Load and validate
        scenario = load_scenario(str(scenario_file))
        launcher = SimulationLauncher(scenario)

        errors = launcher.validate_scenario()
        assert errors == [], "Valid scenario should have no errors"

    def test_dry_run_catches_errors(self, tmp_path):
        """Test that dry-run catches validation errors."""
        # Create an invalid scenario (missing required fields)
        scenario_dict = {
            'simulation': {
                'duration_s': 10.0,
                'seed': 42,
                'time_quantum_us': 1000000
            },
            'nodes': [
                {
                    'id': 'renode1',
                    'type': 'renode',
                    'implementation': 'renode_inprocess',
                    # Missing firmware and platform
                }
            ]
        }

        scenario_file = tmp_path / "invalid_scenario.yaml"
        with open(scenario_file, 'w') as f:
            yaml.dump(scenario_dict, f)

        # Load and validate
        scenario = load_scenario(str(scenario_file))
        launcher = SimulationLauncher(scenario)

        errors = launcher.validate_scenario()
        assert len(errors) > 0, "Invalid scenario should have errors"


@pytest.mark.integration
class TestSeedOverride:
    """Test seed override functionality."""

    def test_run_scenario_with_seed_override(self, tmp_path):
        """Test that seed can be overridden."""
        # Create scenario with default seed
        scenario_dict = {
            'simulation': {
                'duration_s': 0.1,
                'seed': 42,
                'time_quantum_us': 100000
            },
            'nodes': [
                {
                    'id': 'sensor1',
                    'type': 'sensor',
                    'implementation': 'python_model',
                    'port': 5001
                }
            ]
        }

        scenario_file = tmp_path / "scenario.yaml"
        with open(scenario_file, 'w') as f:
            yaml.dump(scenario_dict, f)

        # Load with override
        scenario = load_scenario(str(scenario_file))
        assert scenario.seed == 42, "Should have default seed"

        # Override seed
        scenario.seed = 999

        assert scenario.seed == 999, "Seed should be overridden"


@pytest.mark.integration
class TestScenarioFileLoading:
    """Test loading scenarios from YAML files."""

    def test_load_scenario_from_yaml(self, tmp_path):
        """Test loading a scenario from a YAML file."""
        scenario_dict = {
            'simulation': {
                'duration_s': 5.0,
                'seed': 123,
                'time_quantum_us': 500000
            },
            'nodes': [
                {
                    'id': 'sensor1',
                    'type': 'sensor',
                    'implementation': 'python_model',
                    'port': 5001
                },
                {
                    'id': 'sensor2',
                    'type': 'sensor',
                    'implementation': 'python_model',
                    'port': 5002
                }
            ],
            'network': {
                'model': 'latency',
                'default_latency_us': 5000,
                'default_loss_rate': 0.01
            }
        }

        scenario_file = tmp_path / "complex_scenario.yaml"
        with open(scenario_file, 'w') as f:
            yaml.dump(scenario_dict, f)

        # Load scenario
        scenario = load_scenario(str(scenario_file))

        # Verify loaded correctly
        assert scenario.duration_s == 5.0
        assert scenario.seed == 123
        assert scenario.time_quantum_us == 500000
        assert len(scenario.nodes) == 2
        assert scenario.network.model == 'latency'
        assert scenario.network.default_latency_us == 5000
        assert scenario.network.default_loss_rate == 0.01


if __name__ == "__main__":
    pytest.main([__file__, '-v', '--tb=short'])
