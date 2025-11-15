#!/usr/bin/env python3
"""
test_metrics_integration.py - M1e Integration Test

Test that network metrics are properly collected by LatencyNetworkModel.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from sim.network.latency_model import LatencyNetworkModel
from sim.config.scenario import NetworkConfig, NetworkLink
from sim.harness.coordinator import Event


def test_latency_model_metrics_collection():
    """Test that LatencyNetworkModel tracks metrics correctly."""
    print("\nTest: LatencyNetworkModel metrics collection")

    config = NetworkConfig(
        model="latency",
        default_latency_us=1000,
        links=[
            NetworkLink(src="s1", dst="g", latency_us=5000, loss_rate=0.5)  # 50% loss
        ]
    )

    model = LatencyNetworkModel(config, seed=42)

    # Send 100 packets
    for i in range(100):
        event = Event(time_us=i * 100, type=f"msg{i}", src="s1", dst="g")
        model.route_message(event)

    # Check metrics after routing
    metrics = model.get_metrics()
    assert metrics.packets_sent == 100, f"Expected 100 sent, got {metrics.packets_sent}"

    # Deliver all packets
    for i in range(100):
        delivered = model.advance_to((i+1) * 100 + 5000)

    # Check final metrics
    metrics = model.get_metrics()

    # Verify conservation: sent = delivered + dropped
    total_accounted = metrics.packets_delivered + metrics.packets_dropped
    assert total_accounted == 100, f"Conservation failed: {metrics.packets_delivered} + {metrics.packets_dropped} != 100"

    # With 50% loss, should drop roughly half (deterministic)
    assert 30 <= metrics.packets_delivered <= 70, f"Unexpected delivery count: {metrics.packets_delivered}"

    # All delivered packets should have 5000us latency
    if metrics.packets_delivered > 0:
        assert metrics.min_latency_us == 5000
        assert metrics.max_latency_us == 5000
        assert metrics.average_latency_us() == 5000.0

    print(f"  Sent: {metrics.packets_sent}")
    print(f"  Delivered: {metrics.packets_delivered}")
    print(f"  Dropped: {metrics.packets_dropped}")
    print(f"  Avg latency: {metrics.average_latency_us()}us")
    print("✓ LatencyNetworkModel metrics collection PASSED")
    return True


def test_direct_model_metrics():
    """Test that DirectNetworkModel returns empty metrics."""
    print("\nTest: DirectNetworkModel metrics")

    from sim.network.direct_model import DirectNetworkModel

    model = DirectNetworkModel()
    metrics = model.get_metrics()

    assert metrics.packets_sent == 0
    assert metrics.packets_delivered == 0
    assert metrics.packets_dropped == 0

    print("✓ DirectNetworkModel returns empty metrics")
    return True


def test_metrics_reset():
    """Test that metrics reset works."""
    print("\nTest: Metrics reset")

    config = NetworkConfig(
        model="latency",
        default_latency_us=1000
    )

    model = LatencyNetworkModel(config, seed=42)

    # Send and deliver some packets
    for i in range(10):
        model.route_message(Event(time_us=i * 100, type=f"msg{i}", src="s1", dst="g"))

    model.advance_to(100000)  # Deliver all

    # Verify metrics collected
    metrics = model.get_metrics()
    assert metrics.packets_sent > 0

    # Reset
    model.reset()

    # Verify metrics cleared
    metrics = model.get_metrics()
    assert metrics.packets_sent == 0
    assert metrics.packets_delivered == 0
    assert metrics.packets_dropped == 0

    print("✓ Metrics reset works")
    return True


def main():
    print("="*60)
    print("M1e: Metrics Integration Tests")
    print("="*60)

    tests = [
        test_latency_model_metrics_collection,
        test_direct_model_metrics,
        test_metrics_reset,
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
            print(f"✗ {test.__name__} FAILED: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "="*60)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*60)

    return failed == 0


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
