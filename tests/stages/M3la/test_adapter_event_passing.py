#!/usr/bin/env python3
"""
test_adapter_event_passing.py - M3la Unit Tests

Tests that InProcessNodeAdapter correctly passes pending_events to the wrapped node.

Following WoW: Tests written BEFORE production code to define expected behavior.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock

# Add project root to path
_project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(_project_root))

from sim.harness.coordinator import InProcessNodeAdapter, Event


class TestAdapterEventPassing:
    """Test that InProcessNodeAdapter passes events to wrapped node."""

    def test_adapter_passes_empty_event_list(self):
        """Test adapter handles empty pending events list."""
        # Create mock node
        mock_node = Mock()
        mock_node.advance = Mock(return_value=[])

        # Create adapter
        adapter = InProcessNodeAdapter('test_node', mock_node)
        adapter.connect()  # No-op for in-process
        adapter.send_init({})  # No-op for in-process

        # Send advance with NO events
        adapter.send_advance(1000, [])

        # Node should receive empty list (or method should handle gracefully)
        # The current implementation will be: set_pending_events([])
        # We'll verify the node received the advance time
        events = adapter.wait_done()

        # Should not crash, should return node's events
        assert isinstance(events, list)

    def test_adapter_passes_single_event(self):
        """Test adapter passes single event to node."""
        # Create mock node with set_pending_events method
        mock_node = Mock()
        mock_node.set_pending_events = Mock()
        mock_node.advance = Mock(return_value=[])

        # Create adapter
        adapter = InProcessNodeAdapter('test_node', mock_node)
        adapter.connect()
        adapter.send_init({})

        # Create test event
        test_event = Event(
            time_us=1000,
            type='TEST_CMD',
            src='coordinator',
            dst='test_node',
            payload={'action': 'sample'}
        )

        # Send advance with one event
        adapter.send_advance(1000, [test_event])

        # Verify set_pending_events was called with the event
        mock_node.set_pending_events.assert_called_once()
        call_args = mock_node.set_pending_events.call_args[0][0]
        assert len(call_args) == 1
        assert call_args[0].type == 'TEST_CMD'
        assert call_args[0].dst == 'test_node'

    def test_adapter_passes_multiple_events(self):
        """Test adapter passes multiple events to node."""
        # Create mock node
        mock_node = Mock()
        mock_node.set_pending_events = Mock()
        mock_node.advance = Mock(return_value=[])

        # Create adapter
        adapter = InProcessNodeAdapter('test_node', mock_node)
        adapter.connect()
        adapter.send_init({})

        # Create test events
        events = [
            Event(time_us=1000, type='CMD1', src='coord', dst='node', payload={'id': 1}),
            Event(time_us=1001, type='CMD2', src='coord', dst='node', payload={'id': 2}),
            Event(time_us=1002, type='CMD3', src='coord', dst='node', payload={'id': 3}),
        ]

        # Send advance with multiple events
        adapter.send_advance(1000, events)

        # Verify all events passed
        mock_node.set_pending_events.assert_called_once()
        call_args = mock_node.set_pending_events.call_args[0][0]
        assert len(call_args) == 3
        assert call_args[0].payload['id'] == 1
        assert call_args[1].payload['id'] == 2
        assert call_args[2].payload['id'] == 3

    def test_adapter_events_cleared_after_advance(self):
        """Test that events are cleared between advance cycles."""
        # Create mock node
        mock_node = Mock()
        mock_node.set_pending_events = Mock()
        mock_node.advance = Mock(return_value=[])

        adapter = InProcessNodeAdapter('test_node', mock_node)
        adapter.connect()
        adapter.send_init({})

        # First advance with events
        event1 = Event(time_us=1000, type='CMD1', src='c', dst='n', payload={})
        adapter.send_advance(1000, [event1])
        adapter.wait_done()

        # Second advance with DIFFERENT events
        event2 = Event(time_us=2000, type='CMD2', src='c', dst='n', payload={})
        adapter.send_advance(2000, [event2])

        # Verify second call received ONLY the second event (not accumulated)
        assert mock_node.set_pending_events.call_count == 2
        second_call_args = mock_node.set_pending_events.call_args[0][0]
        assert len(second_call_args) == 1
        assert second_call_args[0].type == 'CMD2'

    def test_adapter_preserves_event_structure(self):
        """Test that all event fields are preserved when passing to node."""
        # Create mock node
        mock_node = Mock()
        mock_node.set_pending_events = Mock()
        mock_node.advance = Mock(return_value=[])

        adapter = InProcessNodeAdapter('test_node', mock_node)
        adapter.connect()
        adapter.send_init({})

        # Create event with all fields populated
        test_event = Event(
            time_us=123456,
            type='COMPLEX_CMD',
            src='edge_service',
            dst='device_123',
            payload={'temperature': 25.5, 'humidity': 60},
            size_bytes=128,
            network_metadata={'latency_us': 500, 'hop_count': 3}
        )

        adapter.send_advance(1000, [test_event])

        # Verify all fields preserved
        received = mock_node.set_pending_events.call_args[0][0][0]
        assert received.time_us == 123456
        assert received.type == 'COMPLEX_CMD'
        assert received.src == 'edge_service'
        assert received.dst == 'device_123'
        assert received.payload['temperature'] == 25.5
        assert received.payload['humidity'] == 60
        assert received.size_bytes == 128
        assert received.network_metadata['latency_us'] == 500


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
