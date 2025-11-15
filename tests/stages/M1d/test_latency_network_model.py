#!/usr/bin/env python3
"""
test_latency_network_model.py - M1d Unit Tests for LatencyNetworkModel

Tests the latency-based network model with configurable delays and packet loss.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from sim.network.latency_model import LatencyNetworkModel
from sim.config.scenario import NetworkConfig, NetworkLink
from sim.harness.coordinator import Event


def test_route_with_latency():
    """Test that messages are delayed by configured latency."""
    config = NetworkConfig(
        model="latency",
        default_latency_us=10000,
        links=[
            NetworkLink(src="sensor1", dst="gateway", latency_us=5000)
        ]
    )

    model = LatencyNetworkModel(config, seed=42)

    # Create event at time 1000us
    event = Event(
        time_us=1000,
        type="test_message",
        src="sensor1",
        dst="gateway",
        payload={"value": 42}
    )

    # Route the message - should not deliver immediately
    result = model.route_message(event)

    if len(result) != 0:
        print(f"✗ test_route_with_latency FAILED: Expected no immediate delivery, got {len(result)} events")
        return False

    # Advance to before delivery time (1000 + 5000 = 6000us)
    ready = model.advance_to(5999)
    if len(ready) != 0:
        print(f"✗ test_route_with_latency FAILED: Event delivered too early")
        return False

    # Advance to delivery time
    ready = model.advance_to(6000)
    if len(ready) != 1:
        print(f"✗ test_route_with_latency FAILED: Expected 1 event at t=6000, got {len(ready)}")
        return False

    delivered = ready[0]
    if delivered.time_us != 6000:
        print(f"✗ test_route_with_latency FAILED: Expected delivery at 6000us, got {delivered.time_us}us")
        return False

    if delivered.payload != {"value": 42}:
        print(f"✗ test_route_with_latency FAILED: Payload was modified")
        return False

    print("✓ test_route_with_latency PASSED")
    return True


def test_default_latency():
    """Test that unconfigured links use default latency."""
    config = NetworkConfig(
        model="latency",
        default_latency_us=10000  # 10ms default
    )

    model = LatencyNetworkModel(config, seed=42)

    event = Event(
        time_us=1000,
        type="test",
        src="sensor_unknown",
        dst="gateway_unknown"
    )

    model.route_message(event)

    # Should be delivered at 1000 + 10000 = 11000us
    ready = model.advance_to(10999)
    if len(ready) != 0:
        print(f"✗ test_default_latency FAILED: Event delivered too early")
        return False

    ready = model.advance_to(11000)
    if len(ready) != 1:
        print(f"✗ test_default_latency FAILED: Expected 1 event, got {len(ready)}")
        return False

    if ready[0].time_us != 11000:
        print(f"✗ test_default_latency FAILED: Wrong delivery time")
        return False

    print("✓ test_default_latency PASSED")
    return True


def test_multiple_events_delivered_in_time_order():
    """Test that events are delivered in correct time order."""
    config = NetworkConfig(
        model="latency",
        default_latency_us=1000,
        links=[
            NetworkLink(src="s1", dst="g", latency_us=5000),
            NetworkLink(src="s2", dst="g", latency_us=3000),
            NetworkLink(src="s3", dst="g", latency_us=7000),
        ]
    )

    model = LatencyNetworkModel(config, seed=42)

    # Send three events at t=1000
    model.route_message(Event(time_us=1000, type="m1", src="s1", dst="g"))
    model.route_message(Event(time_us=1000, type="m2", src="s2", dst="g"))
    model.route_message(Event(time_us=1000, type="m3", src="s3", dst="g"))

    # s2->g: 1000 + 3000 = 4000
    # s1->g: 1000 + 5000 = 6000
    # s3->g: 1000 + 7000 = 8000

    ready = model.advance_to(4000)
    if len(ready) != 1 or ready[0].type != "m2":
        print(f"✗ test_multiple_events_delivered_in_time_order FAILED: Expected m2 first")
        return False

    ready = model.advance_to(6000)
    if len(ready) != 1 or ready[0].type != "m1":
        print(f"✗ test_multiple_events_delivered_in_time_order FAILED: Expected m1 second")
        return False

    ready = model.advance_to(8000)
    if len(ready) != 1 or ready[0].type != "m3":
        print(f"✗ test_multiple_events_delivered_in_time_order FAILED: Expected m3 third")
        return False

    print("✓ test_multiple_events_delivered_in_time_order PASSED")
    return True


def test_packet_loss_deterministic():
    """Test that packet loss is deterministic (same seed → same drops)."""
    config = NetworkConfig(
        model="latency",
        default_latency_us=1000,
        links=[
            NetworkLink(src="s1", dst="g", latency_us=1000, loss_rate=0.5)  # 50% loss
        ]
    )

    # Run twice with same seed
    results1 = []
    model1 = LatencyNetworkModel(config, seed=42)
    for i in range(100):
        event = Event(time_us=i * 100, type=f"msg{i}", src="s1", dst="g")
        model1.route_message(event)

    for i in range(100):
        ready = model1.advance_to((i+1) * 100 + 1000)
        results1.extend([e.type for e in ready])

    results2 = []
    model2 = LatencyNetworkModel(config, seed=42)
    for i in range(100):
        event = Event(time_us=i * 100, type=f"msg{i}", src="s1", dst="g")
        model2.route_message(event)

    for i in range(100):
        ready = model2.advance_to((i+1) * 100 + 1000)
        results2.extend([e.type for e in ready])

    if results1 != results2:
        print(f"✗ test_packet_loss_deterministic FAILED: Different results with same seed")
        print(f"  Run 1: {len(results1)} delivered")
        print(f"  Run 2: {len(results2)} delivered")
        return False

    # With 50% loss, should drop roughly half (but deterministically)
    if not (30 <= len(results1) <= 70):
        print(f"✗ test_packet_loss_deterministic FAILED: Unexpected delivery count: {len(results1)}")
        return False

    print(f"✓ test_packet_loss_deterministic PASSED (delivered {len(results1)}/100, deterministic)")
    return True


def test_no_packet_loss_with_zero_loss_rate():
    """Test that loss_rate=0.0 means no packet loss."""
    config = NetworkConfig(
        model="latency",
        default_latency_us=1000,
        links=[
            NetworkLink(src="s1", dst="g", latency_us=1000, loss_rate=0.0)
        ]
    )

    model = LatencyNetworkModel(config, seed=42)

    # Send 100 messages
    for i in range(100):
        event = Event(time_us=i * 10, type=f"msg{i}", src="s1", dst="g")
        model.route_message(event)

    # Collect all delivered events
    delivered = []
    for i in range(100):
        ready = model.advance_to((i+1) * 10 + 1000)
        delivered.extend(ready)

    if len(delivered) != 100:
        print(f"✗ test_no_packet_loss_with_zero_loss_rate FAILED: Expected 100 deliveries, got {len(delivered)}")
        return False

    print("✓ test_no_packet_loss_with_zero_loss_rate PASSED")
    return True


def test_reset_clears_event_queue():
    """Test that reset() clears all pending events."""
    config = NetworkConfig(
        model="latency",
        default_latency_us=10000
    )

    model = LatencyNetworkModel(config, seed=42)

    # Add some events
    model.route_message(Event(time_us=1000, type="m1", src="s1", dst="g"))
    model.route_message(Event(time_us=2000, type="m2", src="s1", dst="g"))

    # Reset
    model.reset()

    # Advance - should deliver nothing
    ready = model.advance_to(20000)

    if len(ready) != 0:
        print(f"✗ test_reset_clears_event_queue FAILED: Expected empty after reset, got {len(ready)} events")
        return False

    print("✓ test_reset_clears_event_queue PASSED")
    return True


def test_advance_to_same_time_is_idempotent():
    """Test that calling advance_to() multiple times with same time doesn't re-deliver events."""
    config = NetworkConfig(
        model="latency",
        default_latency_us=1000
    )

    model = LatencyNetworkModel(config, seed=42)

    model.route_message(Event(time_us=1000, type="msg", src="s1", dst="g"))

    # Advance to delivery time
    ready1 = model.advance_to(2000)
    if len(ready1) != 1:
        print(f"✗ test_advance_to_same_time_is_idempotent FAILED: Expected 1 event first time")
        return False

    # Advance again to same time - should be empty
    ready2 = model.advance_to(2000)
    if len(ready2) != 0:
        print(f"✗ test_advance_to_same_time_is_idempotent FAILED: Event re-delivered")
        return False

    print("✓ test_advance_to_same_time_is_idempotent PASSED")
    return True


def test_advance_backwards_is_safe():
    """Test that advancing backwards doesn't cause issues."""
    config = NetworkConfig(
        model="latency",
        default_latency_us=1000
    )

    model = LatencyNetworkModel(config, seed=42)

    model.route_message(Event(time_us=1000, type="msg", src="s1", dst="g"))

    # Advance forward
    model.advance_to(3000)

    # Advance backward (should be safe, just returns empty)
    ready = model.advance_to(2000)

    if len(ready) != 0:
        print(f"✗ test_advance_backwards_is_safe FAILED: Got events when going backward")
        return False

    print("✓ test_advance_backwards_is_safe PASSED")
    return True


def main():
    """Run all LatencyNetworkModel tests."""
    print("="*60)
    print("M1d: LatencyNetworkModel Tests")
    print("="*60)

    tests = [
        test_route_with_latency,
        test_default_latency,
        test_multiple_events_delivered_in_time_order,
        test_packet_loss_deterministic,
        test_no_packet_loss_with_zero_loss_rate,
        test_reset_clears_event_queue,
        test_advance_to_same_time_is_idempotent,
        test_advance_backwards_is_safe,
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
