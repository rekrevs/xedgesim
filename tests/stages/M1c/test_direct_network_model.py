#!/usr/bin/env python3
"""
test_direct_network_model.py - M1c Unit Tests for DirectNetworkModel

Tests the zero-latency direct routing implementation.
DirectNetworkModel should behave identically to M0 inline routing.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from sim.network.direct_model import DirectNetworkModel
from sim.harness.coordinator import Event


def test_direct_routing_returns_event_immediately():
    """Test that DirectNetworkModel routes messages with zero latency."""
    model = DirectNetworkModel()

    # Create a test event
    event = Event(
        time_us=1000,
        type="test_message",
        src="sensor1",
        dst="gateway",
        payload={"temp": 25.0},
        size_bytes=100
    )

    # Route the message
    result = model.route_message(event)

    # Should return the event immediately
    if not isinstance(result, list):
        print(f"✗ test_direct_routing_returns_event_immediately FAILED: Expected list, got {type(result)}")
        return False

    if len(result) != 1:
        print(f"✗ test_direct_routing_returns_event_immediately FAILED: Expected 1 event, got {len(result)}")
        return False

    if result[0] != event:
        print(f"✗ test_direct_routing_returns_event_immediately FAILED: Event was modified")
        return False

    print("✓ test_direct_routing_returns_event_immediately PASSED")
    return True


def test_advance_returns_empty_list():
    """Test that DirectNetworkModel has no delayed events."""
    model = DirectNetworkModel()

    # Advance to various times
    for target_time in [1000, 5000, 10000]:
        result = model.advance_to(target_time)

        if not isinstance(result, list):
            print(f"✗ test_advance_returns_empty_list FAILED: Expected list, got {type(result)}")
            return False

        if len(result) != 0:
            print(f"✗ test_advance_returns_empty_list FAILED: Expected empty list, got {len(result)} events")
            return False

    print("✓ test_advance_returns_empty_list PASSED")
    return True


def test_reset_is_noop():
    """Test that reset() doesn't raise errors (DirectNetworkModel is stateless)."""
    model = DirectNetworkModel()

    try:
        model.reset()
        print("✓ test_reset_is_noop PASSED")
        return True
    except Exception as e:
        print(f"✗ test_reset_is_noop FAILED: reset() raised {e}")
        return False


def test_preserves_event_data():
    """Test that routing preserves all event data."""
    model = DirectNetworkModel()

    # Create event with all fields populated
    original = Event(
        time_us=12345,
        type="sensor_reading",
        src="sensor1",
        dst="gateway",
        payload={"temperature": 25.5, "humidity": 60},
        size_bytes=256
    )

    result = model.route_message(original)

    routed_event = result[0]

    # Verify all fields preserved
    if routed_event.time_us != original.time_us:
        print(f"✗ test_preserves_event_data FAILED: time_us changed")
        return False

    if routed_event.type != original.type:
        print(f"✗ test_preserves_event_data FAILED: type changed")
        return False

    if routed_event.src != original.src:
        print(f"✗ test_preserves_event_data FAILED: src changed")
        return False

    if routed_event.dst != original.dst:
        print(f"✗ test_preserves_event_data FAILED: dst changed")
        return False

    if routed_event.payload != original.payload:
        print(f"✗ test_preserves_event_data FAILED: payload changed")
        return False

    if routed_event.size_bytes != original.size_bytes:
        print(f"✗ test_preserves_event_data FAILED: size_bytes changed")
        return False

    print("✓ test_preserves_event_data PASSED")
    return True


def test_handles_event_without_destination():
    """Test routing of events without destination (local events)."""
    model = DirectNetworkModel()

    # Event with no destination (local event)
    event = Event(
        time_us=1000,
        type="local_event",
        src="sensor1",
        dst=None,
        payload=None,
        size_bytes=0
    )

    result = model.route_message(event)

    # Should still route it (coordinator will filter based on dst)
    if len(result) != 1:
        print(f"✗ test_handles_event_without_destination FAILED: Expected 1 event")
        return False

    if result[0] != event:
        print(f"✗ test_handles_event_without_destination FAILED: Event was modified")
        return False

    print("✓ test_handles_event_without_destination PASSED")
    return True


def test_stateless_behavior():
    """Test that DirectNetworkModel maintains no state between calls."""
    model = DirectNetworkModel()

    # Route multiple events
    event1 = Event(time_us=1000, type="msg1", src="n1", dst="n2")
    event2 = Event(time_us=2000, type="msg2", src="n2", dst="n3")
    event3 = Event(time_us=3000, type="msg3", src="n3", dst="n1")

    result1 = model.route_message(event1)
    result2 = model.route_message(event2)
    result3 = model.route_message(event3)

    # Each call should be independent
    if len(result1) != 1 or result1[0] != event1:
        print(f"✗ test_stateless_behavior FAILED: First call affected")
        return False

    if len(result2) != 1 or result2[0] != event2:
        print(f"✗ test_stateless_behavior FAILED: Second call affected")
        return False

    if len(result3) != 1 or result3[0] != event3:
        print(f"✗ test_stateless_behavior FAILED: Third call affected")
        return False

    print("✓ test_stateless_behavior PASSED")
    return True


def test_multiple_advance_calls():
    """Test that advance_to can be called multiple times safely."""
    model = DirectNetworkModel()

    # Advance to different times
    times = [1000, 2000, 5000, 10000, 1000]  # Including going backwards

    for t in times:
        result = model.advance_to(t)
        if len(result) != 0:
            print(f"✗ test_multiple_advance_calls FAILED: Got events at time {t}")
            return False

    print("✓ test_multiple_advance_calls PASSED")
    return True


def main():
    """Run all DirectNetworkModel tests."""
    print("="*60)
    print("M1c: DirectNetworkModel Tests")
    print("="*60)

    tests = [
        test_direct_routing_returns_event_immediately,
        test_advance_returns_empty_list,
        test_reset_is_noop,
        test_preserves_event_data,
        test_handles_event_without_destination,
        test_stateless_behavior,
        test_multiple_advance_calls,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ {test.__name__} EXCEPTION: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("="*60)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*60)

    return failed == 0


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
