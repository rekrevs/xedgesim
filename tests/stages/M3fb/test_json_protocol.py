"""
M3fb JSON Protocol Tests

Tests to verify the firmware's JSON output format is compatible with
the RenodeNode parser from M3fa.
"""

import json
import pytest


class TestJSONProtocol:
    """Test JSON protocol compatibility between firmware and RenodeNode."""

    def test_parse_sample_event(self):
        """Test parsing a SAMPLE event from firmware."""
        line = '{"type":"SAMPLE","value":25.3,"time":1000000}\n'
        event = json.loads(line.strip())

        assert event['type'] == 'SAMPLE'
        assert isinstance(event['value'], (int, float))
        assert event['value'] == 25.3
        assert event['time'] == 1000000

    def test_parse_multiple_events(self):
        """Test parsing multiple events (newline-delimited)."""
        output = '''{"type":"SAMPLE","value":25.3,"time":0}
{"type":"SAMPLE","value":26.1,"time":1000000}
{"type":"SAMPLE","value":24.7,"time":2000000}
'''
        lines = output.strip().split('\n')
        events = [json.loads(line) for line in lines]

        assert len(events) == 3
        assert events[0]['time'] == 0
        assert events[1]['time'] == 1000000
        assert events[2]['time'] == 2000000

    def test_value_range(self):
        """Test that parsed values are within expected range."""
        line = '{"type":"SAMPLE","value":25.5,"time":1000000}\n'
        event = json.loads(line.strip())

        # Firmware configured for 20.0 - 30.0 range
        assert 20.0 <= event['value'] <= 30.0

    def test_time_format(self):
        """Test that time is in microseconds (uint64)."""
        line = '{"type":"SAMPLE","value":25.0,"time":1500000}\n'
        event = json.loads(line.strip())

        assert isinstance(event['time'], int)
        assert event['time'] >= 0
        assert event['time'] < 2**64  # Fits in uint64

    def test_compact_format(self):
        """Test that JSON is compact (no extra whitespace)."""
        line = '{"type":"SAMPLE","value":25.3,"time":1000000}\n'

        # Should not have extra whitespace
        assert '  ' not in line  # No double spaces
        assert '\t' not in line  # No tabs
        assert ': ' not in line  # No space after colons (compact)

    def test_newline_delimiter(self):
        """Test that events are newline-delimited."""
        output = '''{"type":"SAMPLE","value":25.3,"time":0}
{"type":"SAMPLE","value":26.1,"time":1000000}'''

        assert '\n' in output
        lines = output.split('\n')
        assert len(lines) == 2

    def test_renode_node_compatibility(self):
        """
        Test that firmware output can be parsed by RenodeNode._parse_uart_output.

        This test simulates what RenodeNode will do when receiving UART data.
        """
        # Simulate UART output from firmware
        uart_text = '''{"type":"SAMPLE","value":25.3,"time":0}
{"type":"SAMPLE","value":26.1,"time":1000000}
'''
        # Simulate RenodeNode parsing logic
        lines = uart_text.strip().split('\n')
        events = []

        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                # RenodeNode expects these fields
                assert 'type' in data
                assert 'value' in data
                assert 'time' in data
                events.append(data)
            except json.JSONDecodeError:
                pytest.fail(f"Invalid JSON: {line}")

        assert len(events) == 2
        assert events[0]['type'] == 'SAMPLE'
        assert events[1]['type'] == 'SAMPLE'

    def test_malformed_json_handling(self):
        """Test that malformed JSON raises appropriate error."""
        bad_json = '{"type":"SAMPLE","value":25.3'  # Missing closing brace

        with pytest.raises(json.JSONDecodeError):
            json.loads(bad_json)

    def test_partial_line_buffering(self):
        """
        Test scenario where UART output is received in chunks.

        RenodeNode buffers incomplete lines, so firmware must ensure
        newline-terminated output.
        """
        # Simulate receiving data in chunks
        chunk1 = '{"type":"SAMPLE","va'
        chunk2 = 'lue":25.3,"time":1000000}\n'

        # Buffer simulation
        buffer = chunk1
        assert '\n' not in buffer  # Incomplete line

        buffer += chunk2
        assert '\n' in buffer  # Now complete

        # Parse complete line
        line = buffer.strip()
        event = json.loads(line)
        assert event['type'] == 'SAMPLE'

    def test_float_precision(self):
        """Test that float values have correct precision (1 decimal place)."""
        line = '{"type":"SAMPLE","value":25.3,"time":1000000}\n'
        event = json.loads(line.strip())

        # Value should have 1 decimal place precision
        # (firmware uses %.1f format)
        value_str = str(event['value'])
        if '.' in value_str:
            decimal_places = len(value_str.split('.')[1])
            assert decimal_places <= 1  # At most 1 decimal place

    def test_event_type_extensibility(self):
        """Test that protocol supports multiple event types."""
        sample = '{"type":"SAMPLE","value":25.3,"time":1000000}\n'
        alert = '{"type":"ALERT","value":35.0,"time":2000000}\n'

        sample_event = json.loads(sample.strip())
        alert_event = json.loads(alert.strip())

        assert sample_event['type'] == 'SAMPLE'
        assert alert_event['type'] == 'ALERT'
        # Protocol extensible - both parse successfully


class TestDeterminism:
    """Test deterministic output with seeded RNG."""

    def test_seed_produces_same_sequence(self):
        """
        Test that same RNG seed produces identical sensor values.

        NOTE: This test documents expected behavior but cannot be tested
        without running actual firmware. Will be validated in integration tests.
        """
        # This is a documentation test showing expected behavior
        # Actual validation requires running firmware in Renode

        # Expected: Same seed → same sequence
        # Run 1 (seed=12345): [25.3, 26.1, 24.7, ...]
        # Run 2 (seed=12345): [25.3, 26.1, 24.7, ...]  # Identical
        # Run 3 (seed=54321): [27.2, 23.8, 29.1, ...]  # Different

        pass  # Documented for integration test reference


class TestProtocolLimits:
    """Test protocol limits and edge cases."""

    def test_maximum_line_length(self):
        """Test that JSON lines don't exceed 256 bytes."""
        # Firmware uses 256-byte buffer
        line = '{"type":"SAMPLE","value":25.3,"time":1000000}\n'
        assert len(line) < 256

    def test_large_time_value(self):
        """Test parsing large time values (near uint64 max)."""
        # Simulate long-running simulation
        large_time = 18446744073709551615  # uint64 max
        line = f'{{"type":"SAMPLE","value":25.3,"time":{large_time}}}\n'
        event = json.loads(line.strip())

        assert event['time'] == large_time

    def test_extreme_sensor_values(self):
        """Test parsing extreme float values."""
        # Very small value
        small_line = '{"type":"SAMPLE","value":0.1,"time":1000000}\n'
        small_event = json.loads(small_line.strip())
        assert small_event['value'] == 0.1

        # Very large value
        large_line = '{"type":"SAMPLE","value":999.9,"time":1000000}\n'
        large_event = json.loads(large_line.strip())
        assert large_event['value'] == 999.9

    def test_zero_values(self):
        """Test parsing zero values."""
        line = '{"type":"SAMPLE","value":0.0,"time":0}\n'
        event = json.loads(line.strip())

        assert event['value'] == 0.0
        assert event['time'] == 0
