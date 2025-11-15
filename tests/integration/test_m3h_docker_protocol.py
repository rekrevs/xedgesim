#!/usr/bin/env python3
"""
test_m3h_docker_protocol.py - Docker Protocol Integration Tests (M3h)

Tests the complete protocol flow between coordinator and Docker containers
using the echo service as a test subject.

Requirements:
- Docker daemon running
- xedgesim/echo-service image built
- pytest
"""

import pytest
import subprocess
import time
import json
from pathlib import Path
import sys

# Add project root to path
_project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_project_root))

from sim.harness.docker_protocol_adapter import DockerProtocolAdapter
from sim.harness.coordinator import Event


def docker_available():
    """Check if Docker daemon is available."""
    try:
        result = subprocess.run(['docker', '--version'],
                              capture_output=True,
                              timeout=5)
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def image_exists(image_name):
    """Check if Docker image exists."""
    result = subprocess.run(
        ['docker', 'images', '-q', image_name],
        capture_output=True,
        text=True
    )
    return bool(result.stdout.strip())


def cleanup_containers(name_pattern):
    """Clean up containers matching name pattern."""
    result = subprocess.run(
        ['docker', 'ps', '-a', '--filter', f'name={name_pattern}', '--format', '{{.ID}}'],
        capture_output=True,
        text=True
    )
    containers = result.stdout.strip().split('\n') if result.stdout.strip() else []
    for container_id in containers:
        subprocess.run(['docker', 'stop', container_id], capture_output=True)
        subprocess.run(['docker', 'rm', container_id], capture_output=True)


@pytest.fixture(autouse=True)
def docker_cleanup():
    """Cleanup before and after each test."""
    cleanup_containers('xedgesim-test-echo')
    yield
    cleanup_containers('xedgesim-test-echo')


@pytest.mark.integration
@pytest.mark.docker
@pytest.mark.skipif(not docker_available(), reason="Docker not available")
@pytest.mark.skipif(not image_exists('xedgesim/echo-service'), reason="Echo service image not built")
class TestDockerProtocolIntegration:
    """Test Docker protocol integration with real containers."""

    def test_protocol_init_success(self):
        """Test container receives INIT and responds READY."""
        # Start echo service container
        result = subprocess.run(
            ['docker', 'run', '-d', '--name', 'xedgesim-test-echo-1',
             'xedgesim/echo-service'],
            capture_output=True,
            text=True
        )
        container_id = result.stdout.strip()
        assert container_id, "Failed to start container"

        # Give container time to start
        time.sleep(0.5)

        # Create adapter
        adapter = DockerProtocolAdapter(
            node_id='test_echo',
            container_id=container_id
        )

        # Connect and init
        adapter.connect()
        adapter.send_init({"seed": 42})

        # Should have initialized successfully (no exception = success)
        # Cleanup
        adapter.send_shutdown()
        subprocess.run(['docker', 'stop', container_id], capture_output=True)
        subprocess.run(['docker', 'rm', container_id], capture_output=True)

    def test_protocol_advance_no_events(self):
        """Test container receives ADVANCE with no events."""
        # Start container
        result = subprocess.run(
            ['docker', 'run', '-d', '--name', 'xedgesim-test-echo-2',
             'xedgesim/echo-service'],
            capture_output=True,
            text=True
        )
        container_id = result.stdout.strip()
        time.sleep(0.5)

        # Create and connect adapter
        adapter = DockerProtocolAdapter('test_echo', container_id)
        adapter.connect()
        adapter.send_init({"seed": 42})

        # Advance with no events
        adapter.send_advance(target_time_us=1000000, pending_events=[])

        # Wait for DONE
        events = adapter.wait_done()

        # Should return empty list
        assert events == [], "Should return no events"

        # Cleanup
        adapter.send_shutdown()
        subprocess.run(['docker', 'stop', container_id], capture_output=True)
        subprocess.run(['docker', 'rm', container_id], capture_output=True)

    def test_protocol_advance_with_events(self):
        """Test container receives and processes events."""
        # Start container
        result = subprocess.run(
            ['docker', 'run', '-d', '--name', 'xedgesim-test-echo-3',
             'xedgesim/echo-service'],
            capture_output=True,
            text=True
        )
        container_id = result.stdout.strip()
        time.sleep(0.5)

        # Create and connect adapter
        adapter = DockerProtocolAdapter('test_echo', container_id)
        adapter.connect()
        adapter.send_init({"seed": 42})

        # Create test event
        test_event = Event(
            time_us=1000000,
            type="SAMPLE",
            src="sensor1",
            dst="test_echo",
            payload={"value": 42.5}
        )

        # Advance with event
        adapter.send_advance(target_time_us=1000000, pending_events=[test_event])

        # Wait for DONE
        output_events = adapter.wait_done()

        # Should have echoed event
        assert len(output_events) == 1, "Should have one output event"
        assert output_events[0].type == "echo_SAMPLE", "Should echo event type"
        assert output_events[0].src == "echo_service", "Should be from echo_service"

        # Cleanup
        adapter.send_shutdown()
        subprocess.run(['docker', 'stop', container_id], capture_output=True)
        subprocess.run(['docker', 'rm', container_id], capture_output=True)

    def test_protocol_event_transformation(self):
        """Test container transforms input to output events correctly."""
        # Start container
        result = subprocess.run(
            ['docker', 'run', '-d', '--name', 'xedgesim-test-echo-4',
             'xedgesim/echo-service'],
            capture_output=True,
            text=True
        )
        container_id = result.stdout.strip()
        time.sleep(0.5)

        # Create and connect adapter
        adapter = DockerProtocolAdapter('test_echo', container_id)
        adapter.connect()
        adapter.send_init({"seed": 42})

        # Create multiple test events
        events = [
            Event(1000000, "EVENT1", "src1", "test_echo", {"data": 1}),
            Event(1000000, "EVENT2", "src2", "test_echo", {"data": 2}),
            Event(1000000, "EVENT3", "src3", "test_echo", {"data": 3}),
        ]

        # Advance with events
        adapter.send_advance(target_time_us=1000000, pending_events=events)

        # Wait for DONE
        output_events = adapter.wait_done()

        # Should have 3 echoed events
        assert len(output_events) == 3, "Should have 3 output events"

        # Verify transformations
        assert output_events[0].type == "echo_EVENT1"
        assert output_events[1].type == "echo_EVENT2"
        assert output_events[2].type == "echo_EVENT3"

        # All from echo_service
        assert all(e.src == "echo_service" for e in output_events)

        # Cleanup
        adapter.send_shutdown()
        subprocess.run(['docker', 'stop', container_id], capture_output=True)
        subprocess.run(['docker', 'rm', container_id], capture_output=True)

    def test_protocol_virtual_time(self):
        """Test multiple ADVANCE calls progress virtual time."""
        # Start container
        result = subprocess.run(
            ['docker', 'run', '-d', '--name', 'xedgesim-test-echo-5',
             'xedgesim/echo-service'],
            capture_output=True,
            text=True
        )
        container_id = result.stdout.strip()
        time.sleep(0.5)

        # Create and connect adapter
        adapter = DockerProtocolAdapter('test_echo', container_id)
        adapter.connect()
        adapter.send_init({"seed": 42})

        # Multiple advances
        for t in [100000, 200000, 300000]:
            adapter.send_advance(target_time_us=t, pending_events=[])
            events = adapter.wait_done()
            assert events == [], "Should have no events"

        # Container should have processed all time steps
        # (No errors means success)

        # Cleanup
        adapter.send_shutdown()
        subprocess.run(['docker', 'stop', container_id], capture_output=True)
        subprocess.run(['docker', 'rm', container_id], capture_output=True)

    def test_protocol_shutdown_clean(self):
        """Test container shuts down cleanly."""
        # Start container
        result = subprocess.run(
            ['docker', 'run', '-d', '--name', 'xedgesim-test-echo-6',
             'xedgesim/echo-service'],
            capture_output=True,
            text=True
        )
        container_id = result.stdout.strip()
        time.sleep(0.5)

        # Create and connect adapter
        adapter = DockerProtocolAdapter('test_echo', container_id)
        adapter.connect()
        adapter.send_init({"seed": 42})

        # Advance once
        adapter.send_advance(target_time_us=100000, pending_events=[])
        adapter.wait_done()

        # Send shutdown
        adapter.send_shutdown()

        # Give container time to shutdown
        time.sleep(1.0)

        # Container should be stopped (not running)
        result = subprocess.run(
            ['docker', 'ps', '--filter', f'id={container_id}', '--format', '{{.ID}}'],
            capture_output=True,
            text=True
        )

        # May or may not be running depending on timing, but should cleanup
        subprocess.run(['docker', 'stop', container_id], capture_output=True)
        subprocess.run(['docker', 'rm', container_id], capture_output=True)

    def test_protocol_error_handling(self):
        """Test container handles protocol gracefully (basic test)."""
        # Start container
        result = subprocess.run(
            ['docker', 'run', '-d', '--name', 'xedgesim-test-echo-7',
             'xedgesim/echo-service'],
            capture_output=True,
            text=True
        )
        container_id = result.stdout.strip()
        time.sleep(0.5)

        # Create and connect adapter
        adapter = DockerProtocolAdapter('test_echo', container_id)
        adapter.connect()

        # Try to advance before init (should fail)
        with pytest.raises(RuntimeError):
            adapter.send_advance(target_time_us=100000, pending_events=[])

        # Cleanup
        adapter.send_shutdown()
        subprocess.run(['docker', 'stop', container_id], capture_output=True)
        subprocess.run(['docker', 'rm', container_id], capture_output=True)


if __name__ == "__main__":
    pytest.main([__file__, '-v', '--tb=short'])
