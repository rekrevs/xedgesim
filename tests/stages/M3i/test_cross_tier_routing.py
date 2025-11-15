"""
test_cross_tier_routing.py - M3i Cross-Tier Event Routing Tests

Tests event routing from devices through network to edge services.

These are unit/integration tests that don't require Renode or Docker.
Full end-to-end tests with real Renode/Docker are delegated to testing agent.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
_project_root = Path(__file__).parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from sim.harness.coordinator import Event
from sim.network.latency_model import LatencyNetworkModel
from sim.config.scenario import NetworkConfig


class TestEventDataclass:
    """Test Event dataclass with network_metadata."""

    def test_event_has_network_metadata(self):
        """Test Event can store network metadata."""
        event = Event(
            time_us=1000,
            type="test",
            src="node1",
            dst="node2",
            payload={"data": "test"}
        )

        assert hasattr(event, 'network_metadata')
        assert event.network_metadata == {}

    def test_event_with_network_metadata(self):
        """Test Event with populated network metadata."""
        event = Event(
            time_us=1000,
            type="test",
            src="node1",
            dst="node2",
            payload={"data": "test"},
            network_metadata={
                'latency_us': 10000,
                'sent_time_us': 1000,
                'delivery_time_us': 11000
            }
        )

        assert event.network_metadata['latency_us'] == 10000
        assert event.network_metadata['sent_time_us'] == 1000
        assert event.network_metadata['delivery_time_us'] == 11000


class TestLatencyNetworkModelRouting:
    """Test LatencyNetworkModel populates network_metadata."""

    def test_route_message_adds_metadata(self):
        """Test route_message adds network metadata to events."""
        config = NetworkConfig(
            model="latency",
            default_latency_us=10000,
            default_loss_rate=0.0,
            links=[]
        )

        model = LatencyNetworkModel(config, seed=42)

        # Create test event
        event = Event(
            time_us=1000,
            type="mqtt_publish",
            src="device1",
            dst="gateway1",
            payload={"topic": "sensors/temp", "value": 25.3}
        )

        # Route message (returns empty list, event is queued)
        routed = model.route_message(event)

        assert routed == []  # Event queued for delayed delivery

        # Advance to delivery time
        delivered = model.advance_to(11000)

        assert len(delivered) == 1
        delivered_event = delivered[0]

        # Check network metadata was added
        assert 'latency_us' in delivered_event.network_metadata
        assert delivered_event.network_metadata['latency_us'] == 10000
        assert delivered_event.network_metadata['sent_time_us'] == 1000
        assert delivered_event.network_metadata['delivery_time_us'] == 11000

    def test_route_with_packet_loss(self):
        """Test packet loss doesn't deliver events."""
        config = NetworkConfig(
            model="latency",
            default_latency_us=10000,
            default_loss_rate=1.0,  # 100% loss
            links=[]
        )

        model = LatencyNetworkModel(config, seed=42)

        event = Event(
            time_us=1000,
            type="data",
            src="node1",
            dst="node2",
            payload={}
        )

        # Route message - should be dropped
        routed = model.route_message(event)
        assert routed == []

        # Advance time - nothing should be delivered
        delivered = model.advance_to(20000)
        assert delivered == []

    def test_route_multiple_events(self):
        """Test routing multiple events with different delivery times."""
        config = NetworkConfig(
            model="latency",
            default_latency_us=10000,
            default_loss_rate=0.0,
            links=[]
        )

        model = LatencyNetworkModel(config, seed=42)

        # Send events at different times
        event1 = Event(time_us=1000, type="data", src="n1", dst="n2", payload={})
        event2 = Event(time_us=5000, type="data", src="n1", dst="n2", payload={})
        event3 = Event(time_us=15000, type="data", src="n1", dst="n2", payload={})

        model.route_message(event1)  # Delivery at 11000
        model.route_message(event2)  # Delivery at 15000
        model.route_message(event3)  # Delivery at 25000

        # Advance to 12000 - only event1 should be delivered
        delivered = model.advance_to(12000)
        assert len(delivered) == 1
        assert delivered[0].network_metadata['sent_time_us'] == 1000

        # Advance to 16000 - event2 should be delivered
        delivered = model.advance_to(16000)
        assert len(delivered) == 1
        assert delivered[0].network_metadata['sent_time_us'] == 5000

        # Advance to 30000 - event3 should be delivered
        delivered = model.advance_to(30000)
        assert len(delivered) == 1
        assert delivered[0].network_metadata['sent_time_us'] == 15000


class TestCrossTierEventFlow:
    """Test complete event flow from device to edge."""

    def test_device_to_edge_event_flow(self):
        """Test event routing from device through network to edge."""
        # This simulates what the coordinator does in its main loop

        config = NetworkConfig(
            model="latency",
            default_latency_us=10000,  # 10ms latency
            default_loss_rate=0.0,
            links=[]
        )

        network = LatencyNetworkModel(config, seed=42)

        # Simulate device creating an event
        device_event = Event(
            time_us=1000000,  # 1 second
            type="sensor_reading",
            src="sensor_1",
            dst="gateway_1",
            payload={
                "sensor_type": "temperature",
                "value": 25.3,
                "unit": "celsius"
            }
        )

        # Route through network (coordinator does this)
        network.route_message(device_event)

        # Advance time and get ready events (coordinator does this)
        ready_events = network.advance_to(1010000)  # 1.01 seconds

        # Verify event was delivered
        assert len(ready_events) == 1
        delivered_event = ready_events[0]

        # Check event properties
        assert delivered_event.type == "sensor_reading"
        assert delivered_event.src == "sensor_1"
        assert delivered_event.dst == "gateway_1"
        assert delivered_event.payload["value"] == 25.3

        # Check network metadata was added
        assert delivered_event.network_metadata['latency_us'] == 10000
        assert delivered_event.time_us == 1010000  # Original time + latency

    def test_bidirectional_flow(self):
        """Test bidirectional event flow (device -> edge -> device)."""
        config = NetworkConfig(
            model="latency",
            default_latency_us=5000,  # 5ms latency
            default_loss_rate=0.0,
            links=[]
        )

        network = LatencyNetworkModel(config, seed=42)

        # Device -> Edge
        upload_event = Event(
            time_us=1000000,
            type="data_upload",
            src="device_1",
            dst="cloud_service",
            payload={"data": "sensor readings"}
        )

        network.route_message(upload_event)
        delivered = network.advance_to(1005000)

        assert len(delivered) == 1
        assert delivered[0].dst == "cloud_service"

        # Edge -> Device (response)
        response_event = Event(
            time_us=1005000,
            type="command",
            src="cloud_service",
            dst="device_1",
            payload={"action": "set_threshold", "value": 30.0}
        )

        network.route_message(response_event)
        delivered = network.advance_to(1010000)

        assert len(delivered) == 1
        assert delivered[0].dst == "device_1"
        assert delivered[0].payload["action"] == "set_threshold"


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
