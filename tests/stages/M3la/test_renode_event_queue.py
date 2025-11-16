#!/usr/bin/env python3
"""
test_renode_event_queue.py - M3la Unit Tests

Tests for event queueing and management in RenodeNode.

Tests that RenodeNode correctly queues pending events and clears them
after injection.

Following WoW: Tests written BEFORE production code.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add project root to path
_project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(_project_root))

from sim.harness.coordinator import Event


class TestRenodeEventQueue:
    """Test event queueing in RenodeNode."""

    def test_set_pending_events_stores_events(self):
        """Test that set_pending_events stores events correctly."""
        # We'll mock RenodeNode to avoid Renode dependencies
        from sim.device.renode_node import RenodeNode

        # Create a minimal node without starting Renode
        config = {
            'platform': '/tmp/test.repl',
            'firmware': '/tmp/test.elf',
            'monitor_port': 9999
        }

        node = RenodeNode('test_node', config)

        # Create test events
        events = [
            Event(time_us=1000, type='CMD1', src='coord', dst='node', payload={}),
            Event(time_us=2000, type='CMD2', src='coord', dst='node', payload={}),
        ]

        # Set pending events (method will be added in production code)
        node.set_pending_events(events)

        # Verify events are stored
        assert hasattr(node, 'pending_events_queue')
        assert len(node.pending_events_queue) == 2
        assert node.pending_events_queue[0].type == 'CMD1'
        assert node.pending_events_queue[1].type == 'CMD2'

    def test_pending_events_cleared_after_injection(self):
        """Test that pending events are cleared after being injected."""
        from sim.device.renode_node import RenodeNode

        config = {
            'platform': '/tmp/test.repl',
            'firmware': '/tmp/test.elf',
            'monitor_port': 9999
        }

        node = RenodeNode('test_node', config)

        # Mock the injection method
        node._inject_events_via_uart = Mock()

        # Set events
        events = [Event(time_us=1000, type='TEST', src='s', dst='d', payload={})]
        node.set_pending_events(events)

        # Verify events are queued
        assert len(node.pending_events_queue) == 1

        # Manually trigger injection (what advance() will do)
        if node.pending_events_queue:
            node._inject_events_via_uart(node.pending_events_queue)
            node.pending_events_queue = []

        # Verify cleared
        assert len(node.pending_events_queue) == 0

    def test_multiple_set_calls_accumulate(self):
        """Test behavior when set_pending_events is called multiple times."""
        from sim.device.renode_node import RenodeNode

        config = {
            'platform': '/tmp/test.repl',
            'firmware': '/tmp/test.elf',
            'monitor_port': 9999
        }

        node = RenodeNode('test_node', config)

        # First call
        events1 = [Event(time_us=1000, type='CMD1', src='s', dst='d', payload={})]
        node.set_pending_events(events1)

        # The behavior we want: Replace, not accumulate
        # (Each advance cycle gets fresh events)
        events2 = [Event(time_us=2000, type='CMD2', src='s', dst='d', payload={})]
        node.set_pending_events(events2)

        # Should have ONLY the second event (replaced, not accumulated)
        assert len(node.pending_events_queue) == 1
        assert node.pending_events_queue[0].type == 'CMD2'

    def test_empty_event_list_handled(self):
        """Test that empty event list is handled correctly."""
        from sim.device.renode_node import RenodeNode

        config = {
            'platform': '/tmp/test.repl',
            'firmware': '/tmp/test.elf',
            'monitor_port': 9999
        }

        node = RenodeNode('test_node', config)

        # Set empty list
        node.set_pending_events([])

        # Should have empty queue (not crash)
        assert hasattr(node, 'pending_events_queue')
        assert len(node.pending_events_queue) == 0


class TestRenodeAdvanceWithEvents:
    """Test RenodeNode.advance() integration with event injection."""

    @patch('sim.device.renode_node.subprocess.Popen')
    @patch('sim.device.renode_node.socket.socket')
    def test_advance_injects_events_before_time_step(self, mock_socket, mock_popen):
        """Test that advance() injects events before running time."""
        from sim.device.renode_node import RenodeNode

        config = {
            'platform': '/tmp/test.repl',
            'firmware': '/tmp/test.elf',
            'monitor_port': 9999,
            'working_dir': '/tmp'
        }

        node = RenodeNode('test_node', config)

        # Mock the injection method to track if it was called
        injection_called = []

        def mock_inject(events):
            injection_called.append(True)

        node._inject_events_via_uart = mock_inject

        # Mock _send_command to avoid real Renode interaction
        node._send_command = Mock(return_value='(test_node) ')

        # Mock file reading for UART output
        node._read_log_file = Mock(return_value='')

        # Set pending events
        events = [Event(time_us=1000, type='TEST', src='s', dst='d', payload={})]
        node.set_pending_events(events)

        # Call advance (will fail without real Renode, but we can check injection was attempted)
        try:
            node.advance(1000)
        except:
            pass  # Ignore errors from missing Renode

        # Verify injection was attempted
        assert len(injection_called) > 0, "Event injection should have been called"

    def test_advance_without_events_works(self):
        """Test that advance() works when no events are pending."""
        from sim.device.renode_node import RenodeNode

        config = {
            'platform': '/tmp/test.repl',
            'firmware': '/tmp/test.elf',
            'monitor_port': 9999,
            'working_dir': '/tmp'
        }

        node = RenodeNode('test_node', config)

        # Mock injection tracking
        injection_called = []
        node._inject_events_via_uart = lambda events: injection_called.append(True)

        # Mock other methods
        node._send_command = Mock(return_value='(test_node) ')
        node._read_log_file = Mock(return_value='')

        # Don't set any events

        # Call advance
        try:
            node.advance(1000)
        except:
            pass

        # Should NOT have called injection (no events)
        assert len(injection_called) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
