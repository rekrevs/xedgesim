#!/usr/bin/env python3
"""
test_docker_integration.py - Docker Container Lifecycle Tests (M3g)

Tests the launcher's Docker container management:
- Starting containers
- Stopping containers
- Cleanup (no orphans)
- Configuration handling

Requirements:
- Docker daemon running
- pytest
"""

import pytest
import subprocess
import time
from pathlib import Path
import sys

# Add project root to path
_project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(_project_root))

from sim.harness.launcher import SimulationLauncher
from sim.config.scenario import Scenario


def docker_available():
    """Check if Docker daemon is available."""
    try:
        result = subprocess.run(['docker', '--version'],
                              capture_output=True,
                              timeout=5)
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def get_all_xedgesim_containers():
    """Get list of all xedgesim containers (running or stopped)."""
    result = subprocess.run(
        ['docker', 'ps', '-a', '--filter', 'name=xedgesim-', '--format', '{{.ID}}'],
        capture_output=True,
        text=True
    )
    return result.stdout.strip().split('\n') if result.stdout.strip() else []


def get_running_containers():
    """Get list of running xedgesim containers."""
    result = subprocess.run(
        ['docker', 'ps', '--filter', 'name=xedgesim-', '--format', '{{.ID}}'],
        capture_output=True,
        text=True
    )
    return result.stdout.strip().split('\n') if result.stdout.strip() else []


def cleanup_xedgesim_containers():
    """Clean up any leftover xedgesim containers (running or stopped)."""
    containers = get_all_xedgesim_containers()
    for container_id in containers:
        subprocess.run(['docker', 'stop', container_id], capture_output=True)
        subprocess.run(['docker', 'rm', container_id], capture_output=True)


@pytest.fixture(autouse=True)
def docker_cleanup():
    """Cleanup before and after each test."""
    cleanup_xedgesim_containers()
    yield
    cleanup_xedgesim_containers()


@pytest.mark.docker
@pytest.mark.skipif(not docker_available(), reason="Docker not available")
class TestDockerContainerLifecycle:
    """Test Docker container lifecycle management."""

    def test_launcher_starts_simple_container(self):
        """Test launcher can start a simple Docker container."""
        scenario = Scenario(
            duration_s=0.1,
            seed=42,
            time_quantum_us=100000,
            nodes=[
                {
                    'id': 'test_node',
                    'type': 'docker',
                    'implementation': 'docker',
                    'docker': {
                        'image': 'alpine:latest',
                        'command': ['sleep', '30']
                    }
                }
            ]
        )

        launcher = SimulationLauncher(scenario)

        # Start container (via launcher's internal method)
        launcher._start_docker_container(scenario.nodes[0])

        # Verify container is running
        containers = get_running_containers()
        assert len(containers) == 1, "Container should be running"
        assert len(launcher.docker_containers) == 1, "Launcher should track container"

        # Cleanup
        launcher.shutdown()

        # Verify container is stopped and removed
        time.sleep(0.5)  # Give Docker time to cleanup
        containers = get_running_containers()
        assert len(containers) == 0, "Container should be stopped and removed"

    def test_launcher_handles_port_mapping(self):
        """Test launcher configures port mappings correctly."""
        scenario = Scenario(
            duration_s=0.1,
            seed=42,
            time_quantum_us=100000,
            nodes=[
                {
                    'id': 'web_server',
                    'type': 'docker',
                    'implementation': 'docker',
                    'docker': {
                        'image': 'nginx:alpine',
                        'ports': ['8080:80']
                    }
                }
            ]
        )

        launcher = SimulationLauncher(scenario)
        launcher._start_docker_container(scenario.nodes[0])

        # Verify container has port mapping
        container_id = launcher.docker_containers[0]
        result = subprocess.run(
            ['docker', 'port', container_id],
            capture_output=True,
            text=True
        )

        assert '80/tcp' in result.stdout, "Port mapping should be configured"
        assert '8080' in result.stdout, "Port 8080 should be mapped"

        # Cleanup
        launcher.shutdown()

    def test_launcher_handles_environment_variables(self):
        """Test launcher passes environment variables to container."""
        scenario = Scenario(
            duration_s=0.1,
            seed=42,
            time_quantum_us=100000,
            nodes=[
                {
                    'id': 'env_test',
                    'type': 'docker',
                    'implementation': 'docker',
                    'docker': {
                        'image': 'alpine:latest',
                        'command': ['sleep', '30'],
                        'environment': {
                            'TEST_VAR': 'test_value',
                            'ANOTHER_VAR': '42'
                        }
                    }
                }
            ]
        )

        launcher = SimulationLauncher(scenario)
        launcher._start_docker_container(scenario.nodes[0])

        # Verify environment variables are set
        container_id = launcher.docker_containers[0]
        result = subprocess.run(
            ['docker', 'exec', container_id, 'env'],
            capture_output=True,
            text=True
        )

        assert 'TEST_VAR=test_value' in result.stdout, "TEST_VAR should be set"
        assert 'ANOTHER_VAR=42' in result.stdout, "ANOTHER_VAR should be set"

        # Cleanup
        launcher.shutdown()

    def test_launcher_cleanup_removes_all_containers(self):
        """Test launcher cleanup stops and removes all containers."""
        scenario = Scenario(
            duration_s=0.1,
            seed=42,
            time_quantum_us=100000,
            nodes=[
                {
                    'id': f'container_{i}',
                    'type': 'docker',
                    'implementation': 'docker',
                    'docker': {
                        'image': 'alpine:latest',
                        'command': ['sleep', '30']
                    }
                }
                for i in range(3)
            ]
        )

        launcher = SimulationLauncher(scenario)

        # Start all containers
        for node in scenario.nodes:
            launcher._start_docker_container(node)

        # Verify all are running
        assert len(launcher.docker_containers) == 3, "Should track 3 containers"
        containers = get_running_containers()
        assert len(containers) == 3, "Should have 3 running containers"

        # Cleanup
        launcher.shutdown()

        # Verify all are gone
        time.sleep(0.5)
        containers = get_running_containers()
        assert len(containers) == 0, "All containers should be removed"

    def test_launcher_handles_missing_image_error(self):
        """Test launcher raises error when Docker config is invalid."""
        scenario = Scenario(
            duration_s=0.1,
            seed=42,
            time_quantum_us=100000,
            nodes=[
                {
                    'id': 'bad_node',
                    'type': 'docker',
                    'implementation': 'docker',
                    'docker': {
                        # Missing 'image' field
                        'command': ['sleep', '30']
                    }
                }
            ]
        )

        launcher = SimulationLauncher(scenario)

        # Should raise ValueError for missing image
        with pytest.raises(ValueError, match="requires 'image'"):
            launcher._start_docker_container(scenario.nodes[0])

    def test_launcher_shutdown_is_idempotent(self):
        """Test launcher shutdown can be called multiple times safely."""
        scenario = Scenario(
            duration_s=0.1,
            seed=42,
            time_quantum_us=100000,
            nodes=[
                {
                    'id': 'test_node',
                    'type': 'docker',
                    'implementation': 'docker',
                    'docker': {
                        'image': 'alpine:latest',
                        'command': ['sleep', '30']
                    }
                }
            ]
        )

        launcher = SimulationLauncher(scenario)
        launcher._start_docker_container(scenario.nodes[0])

        # First shutdown
        launcher.shutdown()

        # Second shutdown should not raise errors
        launcher.shutdown()

        # Verify no containers running
        containers = get_running_containers()
        assert len(containers) == 0, "No containers should be running"


@pytest.mark.docker
@pytest.mark.skipif(not docker_available(), reason="Docker not available")
def test_docker_detection():
    """Test Docker detection functionality."""
    # This should not raise an error since Docker is available
    result = subprocess.run(['docker', '--version'],
                          capture_output=True,
                          timeout=5)
    assert result.returncode == 0, "Docker should be available"
    assert b'Docker version' in result.stdout, "Should show Docker version"


if __name__ == "__main__":
    pytest.main([__file__, '-v', '--tb=short'])
