"""
test_docker_protocol_adapter.py - Unit Tests for DockerProtocolAdapter (M3h)

Tests the coordinator-side Docker protocol adapter WITHOUT requiring Docker.
Uses mocks to simulate subprocess communication.
"""

import pytest
import sys
import json
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call
from io import StringIO

# Add project root to path
_project_root = Path(__file__).parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from sim.harness.docker_protocol_adapter import DockerProtocolAdapter
from sim.harness.coordinator import Event


class TestDockerProtocolAdapterInit:
    """Test DockerProtocolAdapter initialization."""

    def test_adapter_initialization(self):
        """Test adapter initializes with node_id and container_id."""
        adapter = DockerProtocolAdapter("test_node", "container_123")

        assert adapter.node_id == "test_node"
        assert adapter.container_id == "container_123"
        assert adapter.process is None
        assert adapter.connected is False


class TestDockerProtocolAdapterConnect:
    """Test connection to Docker container."""

    @patch('subprocess.run')
    @patch('subprocess.Popen')
    def test_connect_success(self, mock_popen, mock_run):
        """Test successful connection to running container."""
        # Mock docker inspect to return container is running
        mock_run.return_value = Mock(
            returncode=0,
            stdout='true\n'
        )

        # Mock Popen for docker exec
        mock_process = Mock()
        mock_process.stdin = StringIO()
        mock_process.stdout = StringIO()
        mock_process.stderr = StringIO()
        mock_popen.return_value = mock_process

        adapter = DockerProtocolAdapter("test_node", "container_abc")
        adapter.connect()

        # Verify docker inspect was called
        assert mock_run.called
        inspect_call = mock_run.call_args
        assert 'docker' in inspect_call[0][0]
        assert 'inspect' in inspect_call[0][0]
        assert 'container_abc' in inspect_call[0][0]

        # Verify docker exec was called
        assert mock_popen.called
        exec_call = mock_popen.call_args
        assert 'docker' in exec_call[0][0]
        assert 'exec' in exec_call[0][0]
        assert 'container_abc' in exec_call[0][0]

        # Verify adapter is connected
        assert adapter.connected is True
        assert adapter.process is mock_process

    @patch('subprocess.run')
    def test_connect_container_not_running(self, mock_run):
        """Test connection fails if container not running."""
        # Mock docker inspect to return container is not running
        mock_run.return_value = Mock(
            returncode=0,
            stdout='false\n'
        )

        adapter = DockerProtocolAdapter("test_node", "container_xyz")

        with pytest.raises(RuntimeError, match="not running"):
            adapter.connect()

    @patch('subprocess.run')
    def test_connect_container_not_found(self, mock_run):
        """Test connection fails if container not found."""
        # Mock docker inspect to return error
        mock_run.return_value = Mock(
            returncode=1,
            stdout=''
        )

        adapter = DockerProtocolAdapter("test_node", "nonexistent")

        with pytest.raises(RuntimeError, match="not running"):
            adapter.connect()

    @patch('subprocess.run')
    @patch('subprocess.Popen')
    def test_connect_idempotent(self, mock_popen, mock_run):
        """Test connect is idempotent (can be called multiple times)."""
        mock_run.return_value = Mock(returncode=0, stdout='true\n')
        mock_popen.return_value = Mock(stdin=StringIO(), stdout=StringIO(), stderr=StringIO())

        adapter = DockerProtocolAdapter("test_node", "container_123")
        adapter.connect()
        adapter.connect()  # Second call should be no-op

        # Should only call docker exec once
        assert mock_popen.call_count == 1


class TestDockerProtocolAdapterInit:
    """Test INIT message handling."""

    @patch('subprocess.run')
    @patch('subprocess.Popen')
    def test_send_init_success(self, mock_popen, mock_run):
        """Test sending INIT message to container."""
        # Setup mocks
        mock_run.return_value = Mock(returncode=0, stdout='true\n')

        mock_stdin = StringIO()
        mock_stdout = StringIO("READY\n")
        mock_stderr = StringIO()

        mock_process = Mock()
        mock_process.stdin = mock_stdin
        mock_process.stdout = mock_stdout
        mock_process.stderr = mock_stderr
        mock_process.poll.return_value = None  # Process still running
        mock_popen.return_value = mock_process

        # Connect and send init
        adapter = DockerProtocolAdapter("test_node", "container_123")
        adapter.connect()

        # Reset stdin for INIT message
        mock_stdin.seek(0)
        mock_stdin.truncate()

        adapter.send_init({"seed": 42, "config_value": "test"})

        # Verify INIT message was written to stdin
        written = mock_stdin.getvalue()
        assert "INIT" in written
        assert '"seed": 42' in written
        assert '"config_value": "test"' in written

    @patch('subprocess.run')
    @patch('subprocess.Popen')
    def test_send_init_not_connected(self, mock_popen, mock_run):
        """Test send_init fails if not connected."""
        adapter = DockerProtocolAdapter("test_node", "container_123")

        with pytest.raises(RuntimeError, match="Not connected"):
            adapter.send_init({"seed": 42})

    @patch('subprocess.run')
    @patch('subprocess.Popen')
    def test_send_init_invalid_response(self, mock_popen, mock_run):
        """Test send_init fails if container doesn't respond READY."""
        # Setup mocks
        mock_run.return_value = Mock(returncode=0, stdout='true\n')

        mock_stdin = StringIO()
        mock_stdout = StringIO("ERROR\n")  # Invalid response
        mock_stderr = StringIO("Container error details")

        mock_process = Mock()
        mock_process.stdin = mock_stdin
        mock_process.stdout = mock_stdout
        mock_process.stderr = mock_stderr
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process

        adapter = DockerProtocolAdapter("test_node", "container_123")
        adapter.connect()

        with pytest.raises(RuntimeError, match="Expected READY"):
            adapter.send_init({"seed": 42})


class TestDockerProtocolAdapterAdvance:
    """Test ADVANCE message handling."""

    @patch('subprocess.run')
    @patch('subprocess.Popen')
    def test_send_advance_no_events(self, mock_popen, mock_run):
        """Test sending ADVANCE with no events."""
        # Setup mocks
        mock_run.return_value = Mock(returncode=0, stdout='true\n')

        mock_stdin = StringIO()
        mock_stdout = StringIO("READY\nDONE\n[]\n")
        mock_stderr = StringIO()

        mock_process = Mock()
        mock_process.stdin = mock_stdin
        mock_process.stdout = mock_stdout
        mock_process.stderr = mock_stderr
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process

        adapter = DockerProtocolAdapter("test_node", "container_123")
        adapter.connect()
        adapter.send_init({"seed": 42})

        # Reset stdin
        mock_stdin.seek(0)
        mock_stdin.truncate()

        # Send ADVANCE
        adapter.send_advance(1000, [])

        # Verify ADVANCE message
        written = mock_stdin.getvalue()
        assert "ADVANCE 1000" in written
        assert "[]" in written  # Empty events array

    @patch('subprocess.run')
    @patch('subprocess.Popen')
    def test_send_advance_with_events(self, mock_popen, mock_run):
        """Test sending ADVANCE with events."""
        # Setup mocks
        mock_run.return_value = Mock(returncode=0, stdout='true\n')

        mock_stdin = StringIO()
        mock_stdout = StringIO("READY\nDONE\n[]\n")
        mock_stderr = StringIO()

        mock_process = Mock()
        mock_process.stdin = mock_stdin
        mock_process.stdout = mock_stdout
        mock_process.stderr = mock_stderr
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process

        adapter = DockerProtocolAdapter("test_node", "container_123")
        adapter.connect()
        adapter.send_init({"seed": 42})

        # Reset stdin
        mock_stdin.seek(0)
        mock_stdin.truncate()

        # Create input events
        events = [
            Event(time_us=1000, type="sensor_reading", src="sensor1", dst="test_node", payload={"value": 25.3}),
            Event(time_us=1000, type="mqtt_message", src="gateway1", dst="test_node", payload={"topic": "data"})
        ]

        adapter.send_advance(1000, events)

        # Verify ADVANCE message
        written = mock_stdin.getvalue()
        assert "ADVANCE 1000" in written

        # Verify events JSON
        lines = written.strip().split('\n')
        events_json = lines[1]  # Second line is events
        events_data = json.loads(events_json)

        assert len(events_data) == 2
        assert events_data[0]['event_type'] == 'sensor_reading'
        assert events_data[0]['timestamp_us'] == 1000
        assert events_data[0]['source'] == 'sensor1'
        assert events_data[1]['event_type'] == 'mqtt_message'


class TestDockerProtocolAdapterDone:
    """Test DONE response handling."""

    @patch('subprocess.run')
    @patch('subprocess.Popen')
    @patch('select.select')
    def test_wait_done_no_events(self, mock_select, mock_popen, mock_run):
        """Test receiving DONE with no output events."""
        # Setup mocks
        mock_run.return_value = Mock(returncode=0, stdout='true\n')

        mock_stdin = StringIO()
        mock_stdout = StringIO("READY\nDONE\n[]\n")
        mock_stderr = StringIO()

        mock_process = Mock()
        mock_process.stdin = mock_stdin
        mock_process.stdout = mock_stdout
        mock_process.stderr = mock_stderr
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process

        # Mock select to return stdout is ready
        mock_select.return_value = ([mock_stdout], [], [])

        adapter = DockerProtocolAdapter("test_node", "container_123")
        adapter.connect()
        adapter.send_init({"seed": 42})

        # Wait for DONE
        events = adapter.wait_done()

        assert events == []

    @patch('subprocess.run')
    @patch('subprocess.Popen')
    @patch('select.select')
    def test_wait_done_with_events(self, mock_select, mock_popen, mock_run):
        """Test receiving DONE with output events."""
        # Setup mocks
        mock_run.return_value = Mock(returncode=0, stdout='true\n')

        output_events = [
            {
                'timestamp_us': 1500,
                'event_type': 'processed_data',
                'source': 'test_node',
                'destination': 'gateway1',
                'payload': {'result': 42}
            }
        ]

        mock_stdin = StringIO()
        mock_stdout = StringIO(f"READY\nDONE\n{json.dumps(output_events)}\n")
        mock_stderr = StringIO()

        mock_process = Mock()
        mock_process.stdin = mock_stdin
        mock_process.stdout = mock_stdout
        mock_process.stderr = mock_stderr
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process

        # Mock select to return stdout is ready
        mock_select.return_value = ([mock_stdout], [], [])

        adapter = DockerProtocolAdapter("test_node", "container_123")
        adapter.connect()
        adapter.send_init({"seed": 42})

        # Wait for DONE
        events = adapter.wait_done()

        assert len(events) == 1
        assert events[0].time_us == 1500
        assert events[0].type == 'processed_data'
        assert events[0].src == 'test_node'
        assert events[0].dst == 'gateway1'
        assert events[0].payload == {'result': 42}


class TestDockerProtocolAdapterShutdown:
    """Test SHUTDOWN message handling."""

    @patch('subprocess.run')
    @patch('subprocess.Popen')
    def test_send_shutdown_clean(self, mock_popen, mock_run):
        """Test clean shutdown of container process."""
        # Setup mocks
        mock_run.return_value = Mock(returncode=0, stdout='true\n')

        mock_process = Mock()
        mock_process.stdin = StringIO()
        mock_process.stdout = StringIO("READY\n")
        mock_process.stderr = StringIO()
        mock_process.poll.return_value = None
        mock_process.wait = Mock()
        mock_popen.return_value = mock_process

        adapter = DockerProtocolAdapter("test_node", "container_123")
        adapter.connect()

        # Send shutdown
        adapter.send_shutdown()

        # Verify SHUTDOWN was written
        assert "SHUTDOWN" in mock_process.stdin.getvalue()

        # Verify process.wait was called
        assert mock_process.wait.called

        # Verify adapter is disconnected
        assert adapter.connected is False

    @patch('subprocess.run')
    @patch('subprocess.Popen')
    def test_send_shutdown_timeout(self, mock_popen, mock_run):
        """Test shutdown with timeout kills process."""
        # Setup mocks
        mock_run.return_value = Mock(returncode=0, stdout='true\n')

        mock_process = Mock()
        mock_process.stdin = StringIO()
        mock_process.stdout = StringIO("READY\n")
        mock_process.stderr = StringIO()
        mock_process.poll.return_value = None

        # First wait times out, second succeeds
        import subprocess
        mock_process.wait.side_effect = [subprocess.TimeoutExpired('cmd', 5), None]
        mock_process.terminate = Mock()
        mock_process.kill = Mock()

        mock_popen.return_value = mock_process

        adapter = DockerProtocolAdapter("test_node", "container_123")
        adapter.connect()

        # Send shutdown
        adapter.send_shutdown()

        # Verify terminate was called after timeout
        assert mock_process.terminate.called

    @patch('subprocess.run')
    @patch('subprocess.Popen')
    def test_send_shutdown_idempotent(self, mock_popen, mock_run):
        """Test shutdown is idempotent (can be called multiple times)."""
        # Setup mocks
        mock_run.return_value = Mock(returncode=0, stdout='true\n')

        mock_process = Mock()
        mock_process.stdin = StringIO()
        mock_process.stdout = StringIO("READY\n")
        mock_process.stderr = StringIO()
        mock_process.poll.return_value = None
        mock_process.wait = Mock()
        mock_popen.return_value = mock_process

        adapter = DockerProtocolAdapter("test_node", "container_123")
        adapter.connect()

        adapter.send_shutdown()
        adapter.send_shutdown()  # Second call should be no-op

        # Verify process.wait only called once
        assert mock_process.wait.call_count == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
