#!/usr/bin/env python3
"""
test_network_metrics.py - M1e Unit Tests for Network Metrics

Tests the NetworkMetrics dataclass and metrics tracking functionality.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from sim.network.metrics import NetworkMetrics


def test_metrics_initialization():
    """Test that metrics start at zero."""
    metrics = NetworkMetrics()

    assert metrics.packets_sent == 0
    assert metrics.packets_delivered == 0
    assert metrics.packets_dropped == 0
    assert metrics.total_latency_us == 0
    assert metrics.min_latency_us is None
    assert metrics.max_latency_us is None
    assert metrics.average_latency_us() == 0.0

    print("✓ test_metrics_initialization PASSED")
    return True


def test_record_sent():
    """Test recording packets sent."""
    metrics = NetworkMetrics()

    metrics.record_sent()
    assert metrics.packets_sent == 1

    metrics.record_sent()
    assert metrics.packets_sent == 2

    print("✓ test_record_sent PASSED")
    return True


def test_record_delivered():
    """Test recording packets delivered with latency."""
    metrics = NetworkMetrics()

    metrics.record_delivered(1000)
    assert metrics.packets_delivered == 1
    assert metrics.total_latency_us == 1000
    assert metrics.min_latency_us == 1000
    assert metrics.max_latency_us == 1000
    assert metrics.average_latency_us() == 1000.0

    metrics.record_delivered(2000)
    assert metrics.packets_delivered == 2
    assert metrics.total_latency_us == 3000
    assert metrics.min_latency_us == 1000  # Still min
    assert metrics.max_latency_us == 2000  # New max
    assert metrics.average_latency_us() == 1500.0

    print("✓ test_record_delivered PASSED")
    return True


def test_record_dropped():
    """Test recording packets dropped."""
    metrics = NetworkMetrics()

    metrics.record_dropped()
    assert metrics.packets_dropped == 1

    metrics.record_dropped()
    assert metrics.packets_dropped == 2

    print("✓ test_record_dropped PASSED")
    return True


def test_latency_min_max():
    """Test min/max latency tracking."""
    metrics = NetworkMetrics()

    latencies = [5000, 2000, 10000, 3000, 8000]
    for lat in latencies:
        metrics.record_delivered(lat)

    assert metrics.min_latency_us == 2000
    assert metrics.max_latency_us == 10000
    assert metrics.average_latency_us() == (5000 + 2000 + 10000 + 3000 + 8000) / 5

    print("✓ test_latency_min_max PASSED")
    return True


def test_average_with_no_deliveries():
    """Test average latency when no packets delivered."""
    metrics = NetworkMetrics()

    metrics.record_sent()
    metrics.record_dropped()

    # No deliveries, so average should be 0
    assert metrics.average_latency_us() == 0.0

    print("✓ test_average_with_no_deliveries PASSED")
    return True


def test_metrics_reset():
    """Test resetting metrics to initial state."""
    metrics = NetworkMetrics()

    # Record some activity
    metrics.record_sent()
    metrics.record_delivered(1000)
    metrics.record_dropped()

    # Reset
    metrics.reset()

    # Should be back to initial state
    assert metrics.packets_sent == 0
    assert metrics.packets_delivered == 0
    assert metrics.packets_dropped == 0
    assert metrics.total_latency_us == 0
    assert metrics.min_latency_us is None
    assert metrics.max_latency_us is None
    assert metrics.average_latency_us() == 0.0

    print("✓ test_metrics_reset PASSED")
    return True


def test_conservation():
    """Test packet conservation: sent = delivered + dropped."""
    metrics = NetworkMetrics()

    # Send 100 packets
    for i in range(100):
        metrics.record_sent()

    # 70 delivered
    for i in range(70):
        metrics.record_delivered(1000)

    # 30 dropped
    for i in range(30):
        metrics.record_dropped()

    # Conservation check
    assert metrics.packets_sent == metrics.packets_delivered + metrics.packets_dropped
    assert metrics.packets_sent == 100
    assert metrics.packets_delivered == 70
    assert metrics.packets_dropped == 30

    print("✓ test_conservation PASSED")
    return True


def main():
    """Run all network metrics tests."""
    print("="*60)
    print("M1e: Network Metrics Tests")
    print("="*60)

    tests = [
        test_metrics_initialization,
        test_record_sent,
        test_record_delivered,
        test_record_dropped,
        test_latency_min_max,
        test_average_with_no_deliveries,
        test_metrics_reset,
        test_conservation,
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
