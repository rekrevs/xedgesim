#!/usr/bin/env python3
"""
Unit tests for RenodeNode class.

These tests validate the RenodeNode adapter without requiring Renode to be
installed. They use mocking to simulate Renode process and monitor protocol.

Integration tests with actual Renode are in test_renode_integration.py and
are delegated to the testing agent.

Test strategy:
- Unit tests: Configuration, script generation, time conversion, protocol
- Mock-based tests: Process management, socket communication
- Integration tests: Actual Renode execution (delegated)

Author: xEdgeSim Project
Stage: M3fa
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, mock_open
from sim.device.renode_node import (
    RenodeNode,
    Event,
    RenodeConnectionError,
    RenodeTimeoutError
)


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def temp_dir():
    """Temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_platform_file(temp_dir):
    """Mock platform description file."""
    platform_file = temp_dir / "nrf52840.repl"
    platform_file.write_text("# Mock platform description\n")
    return platform_file


@pytest.fixture
def mock_firmware_file(temp_dir):
    """Mock firmware ELF file."""
    firmware_file = temp_dir / "sensor.elf"
    firmware_file.write_text("Mock ELF content\n")
    return firmware_file


@pytest.fixture
def basic_config(mock_platform_file, mock_firmware_file, temp_dir):
    """Basic valid configuration for RenodeNode."""
    return {
        'platform': str(mock_platform_file),
        'firmware': str(mock_firmware_file),
        'monitor_port': 9999,
        'working_dir': str(temp_dir)
    }


@pytest.fixture
def renode_node(basic_config):
    """RenodeNode instance with basic config."""
    return RenodeNode('test_sensor', basic_config)


# ==============================================================================
# Configuration and Initialization Tests
# ==============================================================================

class TestRenodeNodeInitialization:
    """Test RenodeNode initialization and configuration."""

    def test_init_with_valid_config(self, basic_config):
        """Test successful initialization with valid configuration."""
        node = RenodeNode('test_sensor', basic_config)

        assert node.node_id == 'test_sensor'
        assert node.current_time_us == 0
        assert node.monitor_port == 9999
        assert node.platform_file == Path(basic_config['platform'])
        assert node.firmware_path == Path(basic_config['firmware'])
        assert node.renode_process is None
        assert node.monitor_socket is None

    def test_init_missing_required_key(self):
        """Test initialization fails with missing required configuration."""
        invalid_config = {
            'platform': 'some_file.repl'
            # Missing 'firmware' key
        }

        with pytest.raises(ValueError, match="Missing required config key: firmware"):
            RenodeNode('test_sensor', invalid_config)

    def test_init_with_defaults(self, mock_platform_file, mock_firmware_file):
        """Test initialization uses default values for optional config."""
        minimal_config = {
            'platform': str(mock_platform_file),
            'firmware': str(mock_firmware_file)
        }

        node = RenodeNode('test_sensor', minimal_config)

        # Check defaults
        assert node.monitor_port == 1234  # Default port
        assert node.renode_path == 'renode'  # Default executable
        assert node.uart_device == 'sysbus.uart0'  # Default UART
        assert node.time_quantum_us == 10  # Default quantum

    def test_node_id_storage(self, basic_config):
        """Test node ID is correctly stored and accessible."""
        node = RenodeNode('sensor_42', basic_config)
        assert node.node_id == 'sensor_42'

        node2 = RenodeNode('gateway_1', basic_config)
        assert node2.node_id == 'gateway_1'


# ==============================================================================
# Script Generation Tests
# ==============================================================================

class TestRenodeScriptGeneration:
    """Test Renode .resc script generation."""

    def test_create_renode_script_content(self, renode_node):
        """Test generated script contains required elements."""
        script_path = renode_node._create_renode_script()

        assert script_path.exists()

        content = script_path.read_text()

        # Check key components are present
        assert 'mach create "test_sensor"' in content
        assert 'LoadPlatformDescription' in content
        assert 'LoadELF' in content
        assert 'showAnalyzer' in content
        assert 'SetGlobalQuantum' in content
        assert 'SetAdvanceImmediately false' in content

    def test_create_renode_script_platform_path(self, renode_node):
        """Test script contains correct platform file path."""
        script_path = renode_node._create_renode_script()
        content = script_path.read_text()

        # Should use absolute path
        assert str(renode_node.platform_file.absolute()) in content
        assert '@' in content  # Renode syntax for file path

    def test_create_renode_script_firmware_path(self, renode_node):
        """Test script contains correct firmware file path."""
        script_path = renode_node._create_renode_script()
        content = script_path.read_text()

        # Should use absolute path
        assert str(renode_node.firmware_path.absolute()) in content
        assert 'sysbus LoadELF' in content

    def test_create_renode_script_node_id(self, renode_node):
        """Test script uses node ID for machine name."""
        script_path = renode_node._create_renode_script()
        content = script_path.read_text()

        assert f'mach create "{renode_node.node_id}"' in content

    def test_create_renode_script_time_quantum(self, basic_config):
        """Test script uses correct time quantum."""
        # Custom quantum
        basic_config['time_quantum_us'] = 100  # 100 microseconds
        node = RenodeNode('test', basic_config)

        script_path = node._create_renode_script()
        content = script_path.read_text()

        # 100us = 0.0001 seconds
        assert '0.0001' in content
        assert 'SetGlobalQuantum' in content

    def test_create_renode_script_file_location(self, renode_node):
        """Test script is created in working directory."""
        script_path = renode_node._create_renode_script()

        expected_name = f'xedgesim_{renode_node.node_id}.resc'
        assert script_path.name == expected_name
        assert script_path.parent == renode_node.working_dir


# ==============================================================================
# Time Conversion Tests
# ==============================================================================

class TestTimeConversion:
    """Test microsecond to virtual seconds conversion."""

    def test_us_to_virtual_seconds_basic(self, renode_node):
        """Test basic time conversions."""
        # 1 second = 1,000,000 microseconds
        assert renode_node._us_to_virtual_seconds(1_000_000) == 1.0

        # 1 millisecond = 1,000 microseconds
        assert renode_node._us_to_virtual_seconds(1_000) == 0.001

        # 100 microseconds
        assert renode_node._us_to_virtual_seconds(100) == 0.0001

        # 10 seconds
        assert renode_node._us_to_virtual_seconds(10_000_000) == 10.0

    def test_us_to_virtual_seconds_precision(self, renode_node):
        """Test conversion maintains precision."""
        # Test sub-millisecond precision
        result = renode_node._us_to_virtual_seconds(1)  # 1 microsecond
        assert result == pytest.approx(0.000001, abs=1e-9)

        result = renode_node._us_to_virtual_seconds(10)  # 10 microseconds
        assert result == pytest.approx(0.00001, abs=1e-9)

    def test_us_to_virtual_seconds_zero(self, renode_node):
        """Test zero time conversion."""
        assert renode_node._us_to_virtual_seconds(0) == 0.0

    def test_us_to_virtual_seconds_large_values(self, renode_node):
        """Test conversion of large time values."""
        # 1 hour = 3,600,000,000 microseconds
        result = renode_node._us_to_virtual_seconds(3_600_000_000)
        assert result == pytest.approx(3600.0, abs=0.001)


# ==============================================================================
# UART Parsing Tests
# ==============================================================================

class TestUARTOutputParsing:
    """Test parsing of UART output into events."""

    def test_parse_uart_simple_json(self, renode_node):
        """Test parsing simple JSON event from UART."""
        uart_text = '{"type":"SAMPLE","value":25.5,"time":1000000}\n'

        events = renode_node._parse_uart_output(uart_text, 1000000)

        assert len(events) == 1
        event = events[0]
        assert event.type == 'SAMPLE'
        assert event.time_us == 1000000
        assert event.src == 'test_sensor'
        assert event.payload['value'] == 25.5

    def test_parse_uart_multiple_events(self, renode_node):
        """Test parsing multiple events from UART output."""
        uart_text = """
{"type":"SAMPLE","value":25.5,"time":1000000}
{"type":"SAMPLE","value":26.0,"time":2000000}
{"type":"SAMPLE","value":24.8,"time":3000000}
"""

        events = renode_node._parse_uart_output(uart_text, 3000000)

        assert len(events) == 3
        assert events[0].payload['value'] == 25.5
        assert events[1].payload['value'] == 26.0
        assert events[2].payload['value'] == 24.8

    def test_parse_uart_mixed_output(self, renode_node):
        """Test parsing JSON from mixed output (with debug messages)."""
        uart_text = """
[DEBUG] Starting sensor...
{"type":"SAMPLE","value":25.5,"time":1000000}
[INFO] Sample collected
{"type":"METRIC","cpu":42,"time":1100000}
Some other non-JSON output
"""

        events = renode_node._parse_uart_output(uart_text, 1100000)

        # Should extract only the 2 JSON events
        assert len(events) == 2
        assert events[0].type == 'SAMPLE'
        assert events[1].type == 'METRIC'

    def test_parse_uart_malformed_json(self, renode_node):
        """Test handling of malformed JSON in UART output."""
        uart_text = """
{"type":"SAMPLE","value":25.5  MISSING BRACE
{"type":"VALID","value":26.0,"time":1000000}
"""

        events = renode_node._parse_uart_output(uart_text, 1000000)

        # Should skip malformed JSON, parse valid one
        assert len(events) == 1
        assert events[0].type == 'VALID'
        assert events[0].payload['value'] == 26.0

        # Note: Warning message is printed but not asserted here
        # as it can be difficult to capture in test fixtures

    def test_parse_uart_empty_output(self, renode_node):
        """Test parsing empty UART output."""
        events = renode_node._parse_uart_output('', 1000000)
        assert len(events) == 0

        events = renode_node._parse_uart_output('   \n\n  ', 1000000)
        assert len(events) == 0

    def test_parse_uart_no_timestamp_uses_current(self, renode_node):
        """Test events without timestamp use current_time parameter."""
        uart_text = '{"type":"SAMPLE","value":25.5}\n'  # No 'time' field

        events = renode_node._parse_uart_output(uart_text, 5000000)

        assert len(events) == 1
        assert events[0].time_us == 5000000  # Uses current_time parameter

    def test_parse_uart_buffer_accumulation(self, renode_node):
        """Test UART buffer accumulates incomplete lines."""
        # First call with incomplete line
        events = renode_node._parse_uart_output('{"type":"SAM', 1000000)
        assert len(events) == 0
        assert renode_node.uart_buffer == '{"type":"SAM'

        # Second call completes the line
        events = renode_node._parse_uart_output('PLE","value":25.5}\n', 1000000)
        assert len(events) == 1
        assert events[0].type == 'SAMPLE'

    def test_parse_uart_event_source(self, renode_node):
        """Test all parsed events have correct source node ID."""
        uart_text = """
{"type":"SAMPLE","value":25.5}
{"type":"METRIC","cpu":42}
"""

        events = renode_node._parse_uart_output(uart_text, 1000000)

        # All events should have node's ID as source
        for event in events:
            assert event.src == renode_node.node_id


# ==============================================================================
# Mock-Based Process Management Tests
# ==============================================================================

class TestProcessManagement:
    """Test Renode process lifecycle management (mocked)."""

    @patch('subprocess.Popen')
    @patch.object(RenodeNode, '_connect_monitor')
    @patch.object(RenodeNode, '_send_command')
    def test_start_creates_process(
        self,
        mock_send_command,
        mock_connect_monitor,
        mock_popen,
        renode_node
    ):
        """Test start() creates Renode process with correct arguments."""
        # Setup mocks
        mock_process = MagicMock()
        mock_process.poll.return_value = None  # Process running
        mock_popen.return_value = mock_process

        # Start node
        renode_node.start()

        # Verify Popen called with correct arguments
        mock_popen.assert_called_once()
        args, kwargs = mock_popen.call_args

        cmd = args[0]
        assert cmd[0] == 'renode'
        assert '--disable-xwt' in cmd
        assert '--port' in cmd
        assert '9999' in cmd

    @patch('subprocess.Popen')
    @patch.object(RenodeNode, '_connect_monitor')
    @patch.object(RenodeNode, '_send_command')
    def test_start_connects_to_monitor(
        self,
        mock_send_command,
        mock_connect_monitor,
        mock_popen,
        renode_node
    ):
        """Test start() connects to monitor port."""
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process

        renode_node.start()

        # Verify monitor connection attempted
        mock_connect_monitor.assert_called_once()

    @patch('subprocess.Popen')
    @patch.object(RenodeNode, '_connect_monitor')
    @patch.object(RenodeNode, '_send_command')
    def test_start_sends_start_command(
        self,
        mock_send_command,
        mock_connect_monitor,
        mock_popen,
        renode_node
    ):
        """Test start() sends 'start' command to Renode."""
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process

        renode_node.start()

        # Verify 'start' command sent
        mock_send_command.assert_called_once_with('start')

    def test_start_missing_platform_file(self, basic_config, temp_dir):
        """Test start() fails if platform file doesn't exist."""
        # Point to non-existent file
        basic_config['platform'] = str(temp_dir / 'missing.repl')
        node = RenodeNode('test', basic_config)

        with pytest.raises(FileNotFoundError, match="Platform file not found"):
            node.start()

    def test_start_missing_firmware_file(self, basic_config, temp_dir):
        """Test start() fails if firmware file doesn't exist."""
        # Point to non-existent file
        basic_config['firmware'] = str(temp_dir / 'missing.elf')
        node = RenodeNode('test', basic_config)

        with pytest.raises(FileNotFoundError, match="Firmware file not found"):
            node.start()

    @patch.object(RenodeNode, '_send_command')
    def test_stop_sends_quit_command(self, mock_send_command, renode_node):
        """Test stop() sends 'quit' command to monitor."""
        # Mock monitor socket
        renode_node.monitor_socket = MagicMock()

        renode_node.stop()

        # Verify quit command sent
        mock_send_command.assert_called_once_with('quit')

    @patch.object(RenodeNode, '_send_command')
    def test_stop_closes_socket(self, mock_send_command, renode_node):
        """Test stop() closes monitor socket."""
        mock_socket = MagicMock()
        renode_node.monitor_socket = mock_socket

        renode_node.stop()

        # Verify socket closed
        mock_socket.close.assert_called_once()
        assert renode_node.monitor_socket is None

    def test_stop_terminates_process(self, renode_node):
        """Test stop() terminates Renode process."""
        mock_process = MagicMock()
        mock_process.terminate = MagicMock()
        mock_process.wait = MagicMock()
        renode_node.renode_process = mock_process

        renode_node.stop()

        # Verify process terminated
        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_called()

    def test_stop_is_idempotent(self, renode_node):
        """Test stop() can be called multiple times safely."""
        # Should not raise exceptions
        renode_node.stop()
        renode_node.stop()
        renode_node.stop()


# ==============================================================================
# Advance Method Tests
# ==============================================================================

class TestAdvanceMethod:
    """Test virtual time advancement."""

    def test_advance_backwards_raises_error(self, renode_node):
        """Test advancing backwards in time raises ValueError."""
        renode_node.current_time_us = 1000000  # 1 second

        with pytest.raises(ValueError, match="Cannot advance backwards"):
            renode_node.advance(500000)  # Try to go back to 0.5 seconds

    def test_advance_zero_delta_returns_empty(self, renode_node):
        """Test advancing to same time returns no events."""
        renode_node.current_time_us = 1000000

        events = renode_node.advance(1000000)  # Same time

        assert len(events) == 0
        assert renode_node.current_time_us == 1000000  # No change

    @patch.object(RenodeNode, '_send_command')
    def test_advance_sends_correct_command(self, mock_send_command, renode_node):
        """Test advance() sends correct RunFor command."""
        mock_send_command.return_value = "(monitor) "

        renode_node.current_time_us = 0
        renode_node.advance(1000000)  # Advance 1 second

        # Should send "emulation RunFor @1.0"
        mock_send_command.assert_called_once()
        call_args = mock_send_command.call_args[0]
        assert 'emulation RunFor @1.0' == call_args[0]

    @patch.object(RenodeNode, '_send_command')
    def test_advance_updates_current_time(self, mock_send_command, renode_node):
        """Test advance() updates current_time_us."""
        mock_send_command.return_value = "(monitor) "

        renode_node.current_time_us = 0
        renode_node.advance(1000000)

        assert renode_node.current_time_us == 1000000

        renode_node.advance(2500000)
        assert renode_node.current_time_us == 2500000

    @patch.object(RenodeNode, '_send_command')
    @patch.object(RenodeNode, '_parse_uart_output')
    def test_advance_parses_uart_output(
        self,
        mock_parse_uart,
        mock_send_command,
        renode_node
    ):
        """Test advance() parses UART output from response."""
        uart_response = 'Some UART output\n{"type":"SAMPLE"}\n(monitor) '
        mock_send_command.return_value = uart_response
        mock_parse_uart.return_value = [Event('SAMPLE', 1000000, 'test')]

        events = renode_node.advance(1000000)

        # Verify UART parsing called with response
        mock_parse_uart.assert_called_once_with(uart_response, 1000000)
        assert len(events) == 1


# ==============================================================================
# Error Handling Tests
# ==============================================================================

class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_connection_error_raised_on_failed_connect(self, renode_node):
        """Test RenodeConnectionError raised when connection fails."""
        with patch('socket.socket') as mock_socket_class:
            mock_socket = MagicMock()
            mock_socket.connect.side_effect = ConnectionRefusedError()
            mock_socket_class.return_value = mock_socket

            with pytest.raises(RenodeConnectionError):
                renode_node._connect_monitor(max_retries=1, retry_delay=0.01)

    def test_timeout_error_raised_on_command_timeout(self, renode_node):
        """Test RenodeTimeoutError raised when command times out."""
        # Mock socket that continuously returns data without the prompt
        mock_socket = MagicMock()
        # Return data but never the prompt marker
        mock_socket.recv.return_value = b'some output without prompt\n'
        renode_node.monitor_socket = mock_socket

        with pytest.raises(RenodeTimeoutError, match="timed out"):
            renode_node._send_command('test', timeout=0.1)

    def test_send_command_without_connection_raises_error(self, renode_node):
        """Test sending command without connection raises error."""
        # No socket connected
        assert renode_node.monitor_socket is None

        with pytest.raises(RenodeConnectionError, match="not connected"):
            renode_node._send_command('test')


# ==============================================================================
# Representation and String Tests
# ==============================================================================

class TestStringRepresentation:
    """Test string representation of RenodeNode."""

    def test_repr(self, renode_node):
        """Test __repr__ provides useful debugging information."""
        repr_str = repr(renode_node)

        assert 'RenodeNode' in repr_str
        assert 'test_sensor' in repr_str
        assert 'sensor.elf' in repr_str  # Firmware name
        assert '0us' in repr_str  # Initial time


# ==============================================================================
# Integration with Existing Code Tests
# ==============================================================================

class TestIntegrationPatterns:
    """Test RenodeNode follows existing code patterns."""

    def test_implements_standard_node_interface(self, renode_node):
        """Test RenodeNode has methods compatible with other nodes."""
        # Should have standard methods similar to SensorNode
        assert hasattr(renode_node, 'start')
        assert hasattr(renode_node, 'stop')
        assert hasattr(renode_node, 'advance')
        assert callable(renode_node.start)
        assert callable(renode_node.stop)
        assert callable(renode_node.advance)

    def test_advance_returns_event_list(self, renode_node):
        """Test advance() returns list of Event objects."""
        with patch.object(RenodeNode, '_send_command', return_value='(monitor) '):
            events = renode_node.advance(1000000)

            assert isinstance(events, list)
            # Events should be Event instances (empty list is OK)
            for event in events:
                assert isinstance(event, Event)

    def test_event_has_required_fields(self):
        """Test Event dataclass has required fields."""
        event = Event(
            type='TEST',
            time_us=1000000,
            src='node_1',
            dst='node_2',
            payload={'data': 'test'},
            size_bytes=100
        )

        assert event.type == 'TEST'
        assert event.time_us == 1000000
        assert event.src == 'node_1'
        assert event.dst == 'node_2'
        assert event.payload == {'data': 'test'}
        assert event.size_bytes == 100


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
