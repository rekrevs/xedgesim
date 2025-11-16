"""
test_protocol_adapter.py - Unit Tests for Protocol Adapter (M3h)

Tests the coordinator protocol adapter for containers WITHOUT requiring Docker.
Uses mock stdin/stdout to simulate protocol communication.
"""

import pytest
import sys
import json
from io import StringIO
from pathlib import Path

# Add project root to path
_project_root = Path(__file__).parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from containers.protocol_adapter import (
    CoordinatorProtocolAdapter,
    Event,
    run_service
)


class TestEvent:
    """Test Event dataclass."""

    def test_event_to_dict(self):
        """Test Event serialization to dict."""
        event = Event(
            timestamp_us=1000,
            event_type="test_event",
            source="sensor1",
            destination="gateway1",
            payload={"value": 42}
        )

        result = event.to_dict()

        assert result['timestamp_us'] == 1000
        assert result['event_type'] == "test_event"
        assert result['source'] == "sensor1"
        assert result['destination'] == "gateway1"
        assert result['payload'] == {"value": 42}

    def test_event_from_dict(self):
        """Test Event deserialization from dict."""
        data = {
            'timestamp_us': 2000,
            'event_type': "sensor_reading",
            'source': "temp_sensor",
            'destination': "aggregator",
            'payload': {"temperature": 25.3}
        }

        event = Event.from_dict(data)

        assert event.timestamp_us == 2000
        assert event.event_type == "sensor_reading"
        assert event.source == "temp_sensor"
        assert event.destination == "aggregator"
        assert event.payload == {"temperature": 25.3}

    def test_event_roundtrip(self):
        """Test Event serialization roundtrip."""
        original = Event(
            timestamp_us=5000,
            event_type="mqtt_message",
            source="device",
            destination="cloud",
            payload={"topic": "sensors/temp", "data": "25.5"}
        )

        # Serialize
        data = original.to_dict()

        # Deserialize
        restored = Event.from_dict(data)

        assert restored.timestamp_us == original.timestamp_us
        assert restored.event_type == original.event_type
        assert restored.source == original.source
        assert restored.destination == original.destination
        assert restored.payload == original.payload


class TestProtocolAdapter:
    """Test CoordinatorProtocolAdapter logic."""

    def test_adapter_initialization(self):
        """Test adapter initializes correctly."""
        def dummy_callback(current, target, events):
            return []

        adapter = CoordinatorProtocolAdapter(dummy_callback, node_id="test_node")

        assert adapter.service_callback == dummy_callback
        assert adapter.node_id == "test_node"
        assert adapter.current_time_us == 0
        assert adapter.running == False
        assert adapter.config == {}

    def test_handle_init(self):
        """Test INIT message handling."""
        def dummy_callback(current, target, events):
            return []

        adapter = CoordinatorProtocolAdapter(dummy_callback)

        # Mock stdout
        output = StringIO()
        sys.stdout = output

        try:
            # Handle INIT with config
            config_data = {"seed": 42, "model_path": "/models/test.onnx"}
            adapter._handle_init(json.dumps(config_data))

            # Check response
            response = output.getvalue()
            assert "READY" in response

            # Check state
            assert adapter.config == config_data
            assert adapter.current_time_us == 0

        finally:
            sys.stdout = sys.__stdout__

    def test_handle_advance_no_events(self):
        """Test ADVANCE with no input events."""
        output_events = []

        def callback(current, target, events):
            # Verify virtual time parameters
            assert current == 0
            assert target == 1000
            assert events == []
            return output_events

        adapter = CoordinatorProtocolAdapter(callback)

        # Mock stdout
        output = StringIO()
        sys.stdout = output

        try:
            # Handle ADVANCE
            adapter._handle_advance(1000, "[]")

            # Check response
            response = output.getvalue()
            assert "DONE" in response
            assert "[]" in response  # Empty events array

            # Check state updated
            assert adapter.current_time_us == 1000

        finally:
            sys.stdout = sys.__stdout__

    def test_handle_advance_with_events(self):
        """Test ADVANCE with input and output events."""
        def callback(current, target, events):
            # Verify input event
            assert len(events) == 1
            assert events[0].event_type == "input_event"
            assert events[0].payload["value"] == 123

            # Return output event
            return [Event(
                timestamp_us=target,
                event_type="output_event",
                payload={"result": 456}
            )]

        adapter = CoordinatorProtocolAdapter(callback)

        # Mock stdout
        output = StringIO()
        sys.stdout = output

        try:
            # Input event
            input_event = Event(
                timestamp_us=1000,
                event_type="input_event",
                payload={"value": 123}
            )
            events_json = json.dumps([input_event.to_dict()])

            # Handle ADVANCE
            adapter._handle_advance(1000, events_json)

            # Check response
            response = output.getvalue()
            assert "DONE" in response

            # Parse output events
            lines = response.strip().split('\n')
            assert lines[0] == "DONE"
            output_events_data = json.loads(lines[1])
            assert len(output_events_data) == 1
            assert output_events_data[0]['event_type'] == "output_event"
            assert output_events_data[0]['payload']['result'] == 456

        finally:
            sys.stdout = sys.__stdout__

    def test_handle_advance_time_progression(self):
        """Test multiple ADVANCE calls progress time correctly."""
        def callback(current, target, events):
            return []

        adapter = CoordinatorProtocolAdapter(callback)

        # Mock stdout
        output = StringIO()
        sys.stdout = output

        try:
            # First advance
            adapter._handle_advance(1000, "[]")
            assert adapter.current_time_us == 1000

            # Second advance
            adapter._handle_advance(2000, "[]")
            assert adapter.current_time_us == 2000

            # Third advance
            adapter._handle_advance(5000, "[]")
            assert adapter.current_time_us == 5000

        finally:
            sys.stdout = sys.__stdout__

    def test_handle_shutdown(self):
        """Test SHUTDOWN message handling."""
        def dummy_callback(current, target, events):
            return []

        adapter = CoordinatorProtocolAdapter(dummy_callback)
        adapter.running = True

        # Handle shutdown
        adapter._handle_shutdown()

        # Verify adapter stopped
        assert adapter.running == False

    def test_service_callback_receives_correct_params(self):
        """Test service callback receives correct time and events."""
        received_params = []

        def callback(current, target, events):
            received_params.append({
                'current': current,
                'target': target,
                'events': events
            })
            return []

        adapter = CoordinatorProtocolAdapter(callback)

        # Mock stdout
        output = StringIO()
        sys.stdout = output

        try:
            # Initial state: current_time = 0
            input_event = Event(timestamp_us=1000, event_type="test")
            adapter._handle_advance(1000, json.dumps([input_event.to_dict()]))

            # Check callback received correct params
            assert len(received_params) == 1
            assert received_params[0]['current'] == 0
            assert received_params[0]['target'] == 1000
            assert len(received_params[0]['events']) == 1

            # Next advance: current_time = 1000
            received_params.clear()
            adapter._handle_advance(2000, "[]")

            assert len(received_params) == 1
            assert received_params[0]['current'] == 1000
            assert received_params[0]['target'] == 2000

        finally:
            sys.stdout = sys.__stdout__


class TestProtocolIntegration:
    """Integration tests for protocol communication."""

    def test_full_protocol_sequence(self):
        """Test complete INIT -> ADVANCE -> SHUTDOWN sequence."""
        call_log = []

        def callback(current, target, events):
            call_log.append(('ADVANCE', current, target, len(events)))
            return []

        adapter = CoordinatorProtocolAdapter(callback, node_id="test")

        # Mock stdout
        output = StringIO()
        sys.stdout = output

        try:
            # INIT
            adapter._handle_init('{"seed": 42}')
            assert adapter.config['seed'] == 42

            # ADVANCE 1
            adapter._handle_advance(1000, "[]")
            assert adapter.current_time_us == 1000

            # ADVANCE 2
            adapter._handle_advance(2000, "[]")
            assert adapter.current_time_us == 2000

            # SHUTDOWN
            adapter._handle_shutdown()
            assert adapter.running == False

            # Verify callback was called correctly
            assert len(call_log) == 2
            assert call_log[0] == ('ADVANCE', 0, 1000, 0)
            assert call_log[1] == ('ADVANCE', 1000, 2000, 0)

        finally:
            sys.stdout = sys.__stdout__

    def test_event_transformation(self):
        """Test service can transform input events to output events."""
        def transformation_callback(current, target, events):
            # Transform input events
            output_events = []
            for event in events:
                if event.event_type == "sensor_reading":
                    # Transform to processed event
                    output_events.append(Event(
                        timestamp_us=target,
                        event_type="processed_reading",
                        payload={
                            "original_value": event.payload.get("value"),
                            "processed_value": event.payload.get("value", 0) * 2
                        }
                    ))
            return output_events

        adapter = CoordinatorProtocolAdapter(transformation_callback)

        # Mock stdout
        output = StringIO()
        sys.stdout = output

        try:
            # Send sensor reading
            input_event = Event(
                timestamp_us=1000,
                event_type="sensor_reading",
                payload={"value": 10}
            )

            adapter._handle_advance(1000, json.dumps([input_event.to_dict()]))

            # Parse output
            lines = output.getvalue().strip().split('\n')
            output_events_data = json.loads(lines[1])

            # Verify transformation
            assert len(output_events_data) == 1
            assert output_events_data[0]['event_type'] == "processed_reading"
            assert output_events_data[0]['payload']['original_value'] == 10
            assert output_events_data[0]['payload']['processed_value'] == 20

        finally:
            sys.stdout = sys.__stdout__


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
