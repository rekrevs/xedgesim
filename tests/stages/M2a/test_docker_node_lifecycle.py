#!/usr/bin/env python3
"""
test_docker_node_lifecycle.py - M2a Unit Tests for Docker Node Lifecycle

Tests Docker container creation, startup, shutdown, and cleanup.
"""

import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest

# Try to import docker, skip all tests if not available
docker = pytest.importorskip("docker", reason="Docker not installed")
from docker.errors import NotFound, ImageNotFound

from sim.edge.docker_node import DockerNode, cleanup_xedgesim_containers


# Check if Docker daemon is running
def is_docker_available():
    """Check if Docker daemon is accessible."""
    try:
        client = docker.from_env()
        client.ping()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not is_docker_available(),
    reason="Docker daemon not available"
)


@pytest.fixture(scope="function")
def docker_client():
    """Provide Docker client and cleanup after each test."""
    client = docker.from_env()

    # Pre-test cleanup (in case previous test failed)
    cleanup_xedgesim_containers(client)

    yield client

    # Post-test cleanup
    cleanup_xedgesim_containers(client)


@pytest.fixture(scope="function")
def simple_docker_config():
    """Provide simple Docker configuration for testing."""
    return {
        "image": "alpine:latest",
        "command": "sleep 60"
    }


def test_docker_node_create(simple_docker_config):
    """Test DockerNode can be created without starting container."""
    node = DockerNode("test1", simple_docker_config, seed=42)

    assert node.node_id == "test1"
    assert node.current_time_us == 0
    assert node.container is None
    assert node.config == simple_docker_config


def test_docker_node_start_container(docker_client, simple_docker_config):
    """Test DockerNode starts a Docker container."""
    node = DockerNode("test1", simple_docker_config, seed=42)

    try:
        node.start()

        assert node.container is not None
        assert node.container.status == 'created' or node.container.status == 'running'

        # Reload to get current status
        node.container.reload()
        assert node.container.status == 'running'

    finally:
        node.shutdown()


def test_docker_node_shutdown(docker_client, simple_docker_config):
    """Test DockerNode properly shuts down and removes container."""
    node = DockerNode("test1", simple_docker_config, seed=42)
    node.start()

    container_id = node.container.id

    # Shutdown should stop and remove
    node.shutdown()

    # Verify container is removed
    with pytest.raises(NotFound):
        docker_client.containers.get(container_id)


def test_docker_node_wait_for_ready(docker_client, simple_docker_config):
    """Test DockerNode wait_for_ready() detects running container."""
    node = DockerNode("test1", simple_docker_config, seed=42)

    try:
        node.start()

        # wait_for_ready should return True when container is running
        assert node.wait_for_ready(timeout_s=5) is True

    finally:
        node.shutdown()


def test_docker_node_wait_for_ready_timeout(docker_client):
    """Test wait_for_ready() times out for container that doesn't start."""
    # Use invalid image to trigger timeout
    config = {
        "image": "nonexistent_image_12345",
        "command": "sleep 60"
    }
    node = DockerNode("test1", config, seed=42)

    try:
        # This should fail because image doesn't exist
        with pytest.raises((ImageNotFound, TimeoutError)):
            node.start()
            node.wait_for_ready(timeout_s=1)

    finally:
        # Try to cleanup (may fail if container never created)
        try:
            node.shutdown()
        except:
            pass


def test_docker_node_advance_to(docker_client, simple_docker_config):
    """Test DockerNode advance_to() sleeps for appropriate duration."""
    node = DockerNode("test1", simple_docker_config, seed=42)

    try:
        node.start()
        node.wait_for_ready()

        # Advance by 100ms (100,000 microseconds)
        start = time.time()
        events = node.advance_to(100_000, incoming_events=[])
        elapsed = time.time() - start

        # Verify timing (with generous tolerance for system variance)
        assert 0.08 < elapsed < 0.15, f"Expected ~0.1s sleep, got {elapsed}s"

        # Verify no events returned (M2a doesn't have communication yet)
        assert len(events) == 0

        # Verify time updated
        assert node.current_time_us == 100_000

    finally:
        node.shutdown()


def test_docker_node_advance_to_incremental(docker_client, simple_docker_config):
    """Test multiple advance_to() calls with incremental time."""
    node = DockerNode("test1", simple_docker_config, seed=42)

    try:
        node.start()
        node.wait_for_ready()

        # First advance: 0 -> 50ms
        events1 = node.advance_to(50_000, [])
        assert len(events1) == 0
        assert node.current_time_us == 50_000

        # Second advance: 50ms -> 100ms
        events2 = node.advance_to(100_000, [])
        assert len(events2) == 0
        assert node.current_time_us == 100_000

        # Third advance: 100ms -> 150ms
        events3 = node.advance_to(150_000, [])
        assert len(events3) == 0
        assert node.current_time_us == 150_000

    finally:
        node.shutdown()


def test_docker_node_cleanup_on_exception(docker_client, simple_docker_config):
    """Test container is cleaned up even if exception occurs."""
    node = DockerNode("test1", simple_docker_config, seed=42)
    node.start()
    container_id = node.container.id

    # Simulate error during operation
    try:
        raise ValueError("Simulated error")
    except ValueError:
        pass
    finally:
        node.shutdown()

    # Verify cleanup happened
    with pytest.raises(NotFound):
        docker_client.containers.get(container_id)


def test_cleanup_xedgesim_containers(docker_client):
    """Test cleanup_xedgesim_containers() removes all xedgesim containers."""
    # Create multiple containers with xedgesim label
    containers = []
    for i in range(3):
        c = docker_client.containers.run(
            "alpine:latest",
            "sleep 60",
            detach=True,
            labels={"xedgesim": "true"},
            name=f"xedgesim-test-{i}"
        )
        containers.append(c)

    # Verify containers exist
    for c in containers:
        c.reload()
        assert c.status == 'running'

    # Cleanup
    cleanup_xedgesim_containers(docker_client)

    # Verify all removed
    for c in containers:
        with pytest.raises(NotFound):
            docker_client.containers.get(c.id)


def test_docker_node_unique_names(docker_client, simple_docker_config):
    """Test multiple DockerNodes have unique container names."""
    node1 = DockerNode("test1", simple_docker_config, seed=42)
    node2 = DockerNode("test2", simple_docker_config, seed=42)

    try:
        node1.start()
        node2.start()

        # Both should start successfully
        assert node1.container.name.startswith("xedgesim-test1")
        assert node2.container.name.startswith("xedgesim-test2")
        assert node1.container.name != node2.container.name

    finally:
        node1.shutdown()
        node2.shutdown()


def test_docker_node_container_labels(docker_client, simple_docker_config):
    """Test DockerNode containers have xedgesim label."""
    node = DockerNode("test1", simple_docker_config, seed=42)

    try:
        node.start()

        # Check labels
        labels = node.container.labels
        assert "xedgesim" in labels
        assert labels["xedgesim"] == "true"
        assert labels["xedgesim_node_id"] == "test1"

    finally:
        node.shutdown()


def main():
    """Run all Docker node lifecycle tests."""
    print("=" * 60)
    print("M2a: Docker Node Lifecycle Tests")
    print("=" * 60)

    # Note: These tests require Docker to be installed and running
    # Run with: pytest tests/stages/M2a/test_docker_node_lifecycle.py -v

    print("\nRun tests with: pytest tests/stages/M2a/ -v")


if __name__ == '__main__':
    main()
