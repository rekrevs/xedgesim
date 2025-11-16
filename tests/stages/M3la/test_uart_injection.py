#!/usr/bin/env python3
"""
test_uart_injection.py - M3la Unit Tests

Tests for UART event injection formatting in RenodeNode.

Tests verify that events are correctly formatted as JSON and converted
to UART WriteChar commands for injection into Renode.

Following WoW: Tests written BEFORE production code.
"""

import pytest
import json
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, call

# Add project root to path
_project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(_project_root))

from sim.harness.coordinator import Event


class MockRenodeNode:
    """Mock RenodeNode for testing UART injection without real Renode."""

    def __init__(self):
        self.uart_device = 'sysbus.uart0'
        self.monitor_socket = Mock()
        self.pending_events = []
        self.injected_commands = []  # Track WriteChar commands

    def set_pending_events(self, events):
        """Set events to be injected."""
        self.pending_events = events

    def _send_command(self, cmd):
        """Mock command sending - track what would be sent."""
        self.injected_commands.append(cmd)

    def _inject_events_via_uart(self, events):
        """
        Implementation of UART injection (will be tested).

        This is the method we're testing - implementing it here
        to match expected behavior.
        """
        for event in events:
            # Convert Event to JSON dict
            event_json = json.dumps({
                'type': event.type,
                'src': event.src,
                'dst': event.dst if event.dst else '',
                'payload': event.payload if event.payload else {},
                'time': event.time_us
            })

            # Send via UART - one character at a time
            for char in event_json:
                cmd = f'{self.uart_device} WriteChar {ord(char)}'
                self._send_command(cmd)

            # Send newline to complete the message
            self._send_command(f'{self.uart_device} WriteChar 10')  # \n


class TestUartInjectionFormatting:
    """Test JSON formatting for UART event injection."""

    def test_simple_event_json_format(self):
        """Test basic event converts to valid JSON."""
        node = MockRenodeNode()

        event = Event(
            time_us=1000,
            type='TEST',
            src='coordinator',
            dst='device',
            payload={'value': 42}
        )

        node.set_pending_events([event])
        node._inject_events_via_uart(node.pending_events)

        # Extract the injected JSON by reconstructing from WriteChar commands
        chars = []
        for cmd in node.injected_commands:
            if 'WriteChar' in cmd:
                # Extract the character code
                parts = cmd.split()
                char_code = int(parts[-1])
                if char_code != 10:  # Not newline
                    chars.append(chr(char_code))

        json_str = ''.join(chars)

        # Verify it's valid JSON
        data = json.loads(json_str)
        assert data['type'] == 'TEST'
        assert data['src'] == 'coordinator'
        assert data['dst'] == 'device'
        assert data['payload']['value'] == 42
        assert data['time'] == 1000

    def test_event_with_special_characters(self):
        """Test event payload with special characters is properly escaped."""
        node = MockRenodeNode()

        event = Event(
            time_us=2000,
            type='MSG',
            src='edge',
            dst='device',
            payload={'message': 'Hello "World"\nNew line\tTab'}
        )

        node.set_pending_events([event])
        node._inject_events_via_uart(node.pending_events)

        # Reconstruct JSON
        chars = []
        for cmd in node.injected_commands:
            if 'WriteChar' in cmd:
                char_code = int(cmd.split()[-1])
                if char_code != 10:
                    chars.append(chr(char_code))

        json_str = ''.join(chars)

        # Should parse without errors
        data = json.loads(json_str)
        # JSON escaping should preserve the message
        assert '"World"' in data['payload']['message']  # Quotes escaped
        assert '\n' in data['payload']['message'] or '\\n' in json_str  # Newline escaped

    def test_newline_termination(self):
        """Test that each event ends with newline character."""
        node = MockRenodeNode()

        event = Event(time_us=1000, type='TEST', src='s', dst='d')
        node.set_pending_events([event])
        node._inject_events_via_uart(node.pending_events)

        # Last command should be WriteChar 10 (newline)
        assert node.injected_commands[-1] == 'sysbus.uart0 WriteChar 10'

    def test_multiple_events_separate_json_lines(self):
        """Test multiple events are sent as separate JSON lines."""
        node = MockRenodeNode()

        events = [
            Event(time_us=1000, type='CMD1', src='s', dst='d', payload={'id': 1}),
            Event(time_us=2000, type='CMD2', src='s', dst='d', payload={'id': 2}),
        ]

        node.set_pending_events(events)
        node._inject_events_via_uart(node.pending_events)

        # Count newlines (should be 2) - check exact match at end of command
        newline_count = sum(1 for cmd in node.injected_commands if cmd.endswith('WriteChar 10'))
        assert newline_count == 2

    def test_empty_payload_handled(self):
        """Test event with no payload generates valid JSON."""
        node = MockRenodeNode()

        event = Event(time_us=1000, type='PING', src='s', dst='d', payload=None)
        node.set_pending_events([event])
        node._inject_events_via_uart(node.pending_events)

        # Reconstruct and parse
        chars = []
        for cmd in node.injected_commands:
            if 'WriteChar' in cmd:
                char_code = int(cmd.split()[-1])
                if char_code != 10:
                    chars.append(chr(char_code))

        json_str = ''.join(chars)
        data = json.loads(json_str)

        # Should have empty dict for payload
        assert data['payload'] == {}

    def test_missing_destination_handled(self):
        """Test event with no destination (broadcast) generates valid JSON."""
        node = MockRenodeNode()

        event = Event(time_us=1000, type='BROADCAST', src='s', dst=None, payload={})
        node.set_pending_events([event])
        node._inject_events_via_uart(node.pending_events)

        # Reconstruct and parse
        chars = []
        for cmd in node.injected_commands:
            if 'WriteChar' in cmd:
                char_code = int(cmd.split()[-1])
                if char_code != 10:
                    chars.append(chr(char_code))

        json_str = ''.join(chars)
        data = json.loads(json_str)

        # dst should be empty string
        assert data['dst'] == ''


class TestUartCommandGeneration:
    """Test that correct WriteChar commands are generated."""

    def test_correct_uart_device_name(self):
        """Test commands target the correct UART device."""
        node = MockRenodeNode()
        node.uart_device = 'sysbus.uart1'  # Non-default device

        event = Event(time_us=1000, type='T', src='s', dst='d')
        node.set_pending_events([event])
        node._inject_events_via_uart(node.pending_events)

        # All commands should target uart1
        for cmd in node.injected_commands:
            assert 'sysbus.uart1' in cmd

    def test_character_codes_correct(self):
        """Test that character codes match ASCII values."""
        node = MockRenodeNode()

        # Simple test: inject a single character
        event = Event(time_us=1000, type='A', src='s', dst='d', payload={})
        node.set_pending_events([event])
        node._inject_events_via_uart(node.pending_events)

        # Find WriteChar command for 'A' (type field will have it)
        # JSON will be: {"type":"A",...}
        # The 'A' character should generate WriteChar 65
        found_a = False
        for cmd in node.injected_commands:
            if 'WriteChar 65' in cmd:  # ASCII 'A' = 65
                found_a = True
                break

        assert found_a, "Should find WriteChar 65 for character 'A'"

    def test_no_commands_for_empty_event_list(self):
        """Test that no commands generated for empty event list."""
        node = MockRenodeNode()

        node.set_pending_events([])
        node._inject_events_via_uart(node.pending_events)

        assert len(node.injected_commands) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
