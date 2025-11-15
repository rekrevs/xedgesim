#!/usr/bin/env python3
"""
Manual M3d ML metrics tests (no pytest required).
Tests ML metrics collection and CSV export.
"""

import tempfile
import os
import csv
from pathlib import Path
import sys

# Add repo root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from sim.metrics.ml_metrics import MLMetricsCollector


def test_collector_initialization():
    """Test metrics collector initializes correctly."""
    print("Test 1: Collector initialization...", end=" ")

    with tempfile.TemporaryDirectory() as tmpdir:
        collector = MLMetricsCollector(output_dir=tmpdir)

        assert len(collector.inference_samples) == 0
        assert len(collector.communication_samples) == 0
        assert collector.output_dir == Path(tmpdir)

    print("✓ PASS")
    return True


def test_record_edge_inference():
    """Test recording edge inference."""
    print("Test 2: Record edge inference...", end=" ")

    collector = MLMetricsCollector()

    collector.record_inference(
        timestamp_us=1000000,
        device_id="sensor1",
        placement="edge",
        inference_time_ms=5.2,
        cloud_latency_ms=0,
        total_latency_ms=5.2
    )

    assert len(collector.inference_samples) == 1
    sample = collector.inference_samples[0]
    assert sample.device_id == "sensor1"
    assert sample.placement == "edge"
    assert sample.inference_time_ms == 5.2
    assert sample.cloud_latency_ms == 0
    assert sample.total_latency_ms == 5.2

    print("✓ PASS")
    return True


def test_record_cloud_inference():
    """Test recording cloud inference."""
    print("Test 3: Record cloud inference...", end=" ")

    collector = MLMetricsCollector()

    collector.record_inference(
        timestamp_us=2000000,
        device_id="sensor2",
        placement="cloud",
        inference_time_ms=4.8,
        cloud_latency_ms=100,
        total_latency_ms=104.8
    )

    assert len(collector.inference_samples) == 1
    sample = collector.inference_samples[0]
    assert sample.device_id == "sensor2"
    assert sample.placement == "cloud"
    assert sample.inference_time_ms == 4.8
    assert sample.cloud_latency_ms == 100
    assert sample.total_latency_ms == 104.8

    print("✓ PASS")
    return True


def test_record_communication():
    """Test recording communication overhead."""
    print("Test 4: Record communication...", end=" ")

    collector = MLMetricsCollector()

    collector.record_communication(
        timestamp_us=1000000,
        message_type="inference_request",
        payload_bytes=128,
        features_count=32
    )

    assert len(collector.communication_samples) == 1
    sample = collector.communication_samples[0]
    assert sample.message_type == "inference_request"
    assert sample.payload_bytes == 128
    assert sample.features_count == 32

    print("✓ PASS")
    return True


def test_edge_stats():
    """Test edge inference statistics."""
    print("Test 5: Edge stats computation...", end=" ")

    collector = MLMetricsCollector()

    # Record multiple edge inferences
    for i in range(10):
        collector.record_inference(
            timestamp_us=i * 1000000,
            device_id=f"sensor{i}",
            placement="edge",
            inference_time_ms=5.0 + i * 0.1,
            cloud_latency_ms=0,
            total_latency_ms=5.0 + i * 0.1
        )

    stats = collector.get_inference_stats('edge')

    assert stats['count'] == 10
    assert stats['mean_cloud_ms'] == 0.0  # Edge has no cloud latency
    assert 5.0 <= stats['mean_inference_ms'] <= 6.0
    assert stats['min_total_ms'] == 5.0
    assert stats['max_total_ms'] == 5.9

    print("✓ PASS")
    return True


def test_cloud_stats():
    """Test cloud inference statistics."""
    print("Test 6: Cloud stats computation...", end=" ")

    collector = MLMetricsCollector()

    # Record multiple cloud inferences
    for i in range(10):
        collector.record_inference(
            timestamp_us=i * 1000000,
            device_id=f"sensor{i}",
            placement="cloud",
            inference_time_ms=5.0,
            cloud_latency_ms=100,
            total_latency_ms=105.0
        )

    stats = collector.get_inference_stats('cloud')

    assert stats['count'] == 10
    assert stats['mean_inference_ms'] == 5.0
    assert stats['mean_cloud_ms'] == 100.0
    assert stats['mean_total_ms'] == 105.0

    print("✓ PASS")
    return True


def test_csv_export():
    """Test CSV export functionality."""
    print("Test 7: CSV export...", end=" ")

    with tempfile.TemporaryDirectory() as tmpdir:
        collector = MLMetricsCollector(output_dir=tmpdir)

        # Record some samples
        collector.record_inference(
            timestamp_us=1000000,
            device_id="sensor1",
            placement="edge",
            inference_time_ms=5.2,
            cloud_latency_ms=0,
            total_latency_ms=5.2
        )

        collector.record_inference(
            timestamp_us=2000000,
            device_id="sensor2",
            placement="cloud",
            inference_time_ms=4.8,
            cloud_latency_ms=100,
            total_latency_ms=104.8
        )

        # Export to CSV
        csv_path = collector.export_csv("test_metrics.csv")

        # Verify file exists
        assert os.path.exists(csv_path)

        # Verify CSV content
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

            assert len(rows) == 2

            # Check first row (edge)
            assert rows[0]['device_id'] == 'sensor1'
            assert rows[0]['placement'] == 'edge'
            assert float(rows[0]['inference_time_ms']) == 5.2

            # Check second row (cloud)
            assert rows[1]['device_id'] == 'sensor2'
            assert rows[1]['placement'] == 'cloud'
            assert float(rows[1]['cloud_latency_ms']) == 100.0

    print("✓ PASS")
    return True


def test_mixed_placement_stats():
    """Test stats with both edge and cloud."""
    print("Test 8: Mixed placement stats...", end=" ")

    collector = MLMetricsCollector()

    # Record edge inferences
    for i in range(5):
        collector.record_inference(
            timestamp_us=i * 1000000,
            device_id=f"edge_sensor{i}",
            placement="edge",
            inference_time_ms=5.0,
            cloud_latency_ms=0,
            total_latency_ms=5.0
        )

    # Record cloud inferences
    for i in range(5):
        collector.record_inference(
            timestamp_us=(i + 5) * 1000000,
            device_id=f"cloud_sensor{i}",
            placement="cloud",
            inference_time_ms=5.0,
            cloud_latency_ms=100,
            total_latency_ms=105.0
        )

    edge_stats = collector.get_inference_stats('edge')
    cloud_stats = collector.get_inference_stats('cloud')

    assert edge_stats['count'] == 5
    assert cloud_stats['count'] == 5
    assert edge_stats['mean_total_ms'] == 5.0
    assert cloud_stats['mean_total_ms'] == 105.0

    # Cloud should be 21x slower (105 / 5)
    speedup = cloud_stats['mean_total_ms'] / edge_stats['mean_total_ms']
    assert speedup == 21.0

    print("✓ PASS")
    return True


def test_communication_stats():
    """Test communication overhead statistics."""
    print("Test 9: Communication stats...", end=" ")

    collector = MLMetricsCollector()

    # Record multiple messages
    for i in range(10):
        collector.record_communication(
            timestamp_us=i * 1000000,
            message_type="inference_request",
            payload_bytes=128,
            features_count=32
        )

    stats = collector.get_communication_stats()

    assert stats['total_messages'] == 10
    assert stats['total_bytes'] == 1280  # 10 * 128
    assert stats['avg_message_bytes'] == 128.0

    print("✓ PASS")
    return True


def test_reset():
    """Test metrics reset."""
    print("Test 10: Metrics reset...", end=" ")

    collector = MLMetricsCollector()

    # Add some samples
    collector.record_inference(
        timestamp_us=1000000,
        device_id="sensor1",
        placement="edge",
        inference_time_ms=5.0,
        cloud_latency_ms=0,
        total_latency_ms=5.0
    )

    collector.record_communication(
        timestamp_us=1000000,
        message_type="inference_request",
        payload_bytes=128
    )

    assert len(collector.inference_samples) == 1
    assert len(collector.communication_samples) == 1

    # Reset
    collector.reset()

    assert len(collector.inference_samples) == 0
    assert len(collector.communication_samples) == 0

    print("✓ PASS")
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("M3d ML Metrics Tests")
    print("=" * 60)

    tests = [
        test_collector_initialization,
        test_record_edge_inference,
        test_record_cloud_inference,
        test_record_communication,
        test_edge_stats,
        test_cloud_stats,
        test_csv_export,
        test_mixed_placement_stats,
        test_communication_stats,
        test_reset
    ]

    results = [test() for test in tests]
    passed = sum(results)
    total = len(results)

    print("=" * 60)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 60)

    if passed == total:
        print("✓ All tests passed!")
        return 0
    else:
        print(f"✗ {total - passed} test(s) failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
