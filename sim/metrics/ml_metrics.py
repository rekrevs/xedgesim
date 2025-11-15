"""
ml_metrics.py - M3d ML Metrics Collection

Collects and exports ML-specific metrics for placement comparison analysis.

DESIGN PHILOSOPHY:
- Simple data collection (list of dicts)
- CSV export for post-simulation analysis
- Integration with M3a/M3b ML services
- Placement comparison (edge vs cloud)
"""

import csv
import time
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from pathlib import Path


@dataclass
class MLInferenceSample:
    """
    Single ML inference measurement.

    Attributes:
        timestamp_us: Simulation time when inference completed (microseconds)
        device_id: ID of device that requested inference
        placement: Where inference ran ('edge' or 'cloud')
        inference_time_ms: Actual inference computation time
        cloud_latency_ms: Network latency for cloud (0 for edge)
        total_latency_ms: Total time (inference + network)
    """
    timestamp_us: int
    device_id: str
    placement: str  # 'edge' or 'cloud'
    inference_time_ms: float
    cloud_latency_ms: float
    total_latency_ms: float


@dataclass
class CommunicationSample:
    """
    Communication overhead measurement.

    Attributes:
        timestamp_us: Simulation time when message sent
        message_type: Type of message ('inference_request', 'inference_result')
        payload_bytes: Size of message payload
        features_count: Number of features (for normalization)
    """
    timestamp_us: int
    message_type: str
    payload_bytes: int
    features_count: int = 0


class MLMetricsCollector:
    """
    Collects ML-specific metrics for placement comparison.

    Usage:
        # Initialize collector
        metrics = MLMetricsCollector()

        # Record inference
        metrics.record_inference(
            timestamp_us=1000000,
            device_id="sensor1",
            placement="edge",
            inference_time_ms=5.2,
            cloud_latency_ms=0,
            total_latency_ms=5.2
        )

        # Export to CSV
        metrics.export_csv("ml_metrics.csv")
    """

    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize metrics collector.

        Args:
            output_dir: Directory for CSV output (default: "metrics")
        """
        self.output_dir = Path(output_dir or "metrics")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.inference_samples: List[MLInferenceSample] = []
        self.communication_samples: List[CommunicationSample] = []

    def record_inference(
        self,
        timestamp_us: int,
        device_id: str,
        placement: str,
        inference_time_ms: float,
        cloud_latency_ms: float = 0.0,
        total_latency_ms: Optional[float] = None
    ):
        """
        Record an ML inference event.

        Args:
            timestamp_us: Simulation time (microseconds)
            device_id: Device that requested inference
            placement: 'edge' or 'cloud'
            inference_time_ms: Actual inference computation time
            cloud_latency_ms: Network latency (0 for edge)
            total_latency_ms: Total latency (defaults to inference + cloud)
        """
        if total_latency_ms is None:
            total_latency_ms = inference_time_ms + cloud_latency_ms

        sample = MLInferenceSample(
            timestamp_us=timestamp_us,
            device_id=device_id,
            placement=placement,
            inference_time_ms=inference_time_ms,
            cloud_latency_ms=cloud_latency_ms,
            total_latency_ms=total_latency_ms
        )

        self.inference_samples.append(sample)

    def record_communication(
        self,
        timestamp_us: int,
        message_type: str,
        payload_bytes: int,
        features_count: int = 0
    ):
        """
        Record a communication event.

        Args:
            timestamp_us: Simulation time (microseconds)
            message_type: 'inference_request' or 'inference_result'
            payload_bytes: Message size in bytes
            features_count: Number of features (for normalization)
        """
        sample = CommunicationSample(
            timestamp_us=timestamp_us,
            message_type=message_type,
            payload_bytes=payload_bytes,
            features_count=features_count
        )

        self.communication_samples.append(sample)

    def get_inference_stats(self, placement: Optional[str] = None) -> Dict[str, Any]:
        """
        Compute inference statistics.

        Args:
            placement: Filter by placement ('edge' or 'cloud'), or None for all

        Returns:
            Dictionary with mean, min, max, p50, p95, p99 latencies
        """
        samples = self.inference_samples
        if placement:
            samples = [s for s in samples if s.placement == placement]

        if not samples:
            return {
                'count': 0,
                'mean_inference_ms': 0.0,
                'mean_total_ms': 0.0,
                'min_total_ms': 0.0,
                'max_total_ms': 0.0
            }

        total_latencies = sorted([s.total_latency_ms for s in samples])
        n = len(total_latencies)

        return {
            'count': n,
            'mean_inference_ms': sum(s.inference_time_ms for s in samples) / n,
            'mean_cloud_ms': sum(s.cloud_latency_ms for s in samples) / n,
            'mean_total_ms': sum(s.total_latency_ms for s in samples) / n,
            'min_total_ms': min(total_latencies),
            'max_total_ms': max(total_latencies),
            'p50_total_ms': total_latencies[n // 2],
            'p95_total_ms': total_latencies[int(n * 0.95)] if n > 20 else total_latencies[-1],
            'p99_total_ms': total_latencies[int(n * 0.99)] if n > 100 else total_latencies[-1]
        }

    def get_communication_stats(self) -> Dict[str, Any]:
        """
        Compute communication overhead statistics.

        Returns:
            Dictionary with total bytes, message counts
        """
        if not self.communication_samples:
            return {
                'total_bytes': 0,
                'total_messages': 0,
                'avg_message_bytes': 0.0
            }

        total_bytes = sum(s.payload_bytes for s in self.communication_samples)
        total_messages = len(self.communication_samples)

        return {
            'total_bytes': total_bytes,
            'total_messages': total_messages,
            'avg_message_bytes': total_bytes / total_messages if total_messages > 0 else 0.0
        }

    def export_csv(self, filename: Optional[str] = None) -> str:
        """
        Export metrics to CSV file.

        Args:
            filename: Output filename (default: ml_metrics_{timestamp}.csv)

        Returns:
            Path to created CSV file
        """
        if filename is None:
            timestamp = int(time.time())
            filename = f"ml_metrics_{timestamp}.csv"

        output_path = self.output_dir / filename

        # Write inference samples to CSV
        with open(output_path, 'w', newline='') as f:
            if self.inference_samples:
                # Get field names from dataclass
                fieldnames = list(asdict(self.inference_samples[0]).keys())
                writer = csv.DictWriter(f, fieldnames=fieldnames)

                writer.writeheader()
                for sample in self.inference_samples:
                    writer.writerow(asdict(sample))

        # Also create communication CSV if we have samples
        if self.communication_samples:
            comm_filename = filename.replace('.csv', '_communication.csv')
            comm_path = self.output_dir / comm_filename

            with open(comm_path, 'w', newline='') as f:
                fieldnames = list(asdict(self.communication_samples[0]).keys())
                writer = csv.DictWriter(f, fieldnames=fieldnames)

                writer.writeheader()
                for sample in self.communication_samples:
                    writer.writerow(asdict(sample))

        return str(output_path)

    def print_summary(self):
        """Print summary statistics to console."""
        print("\n" + "=" * 60)
        print("ML Metrics Summary")
        print("=" * 60)

        # Edge stats
        edge_stats = self.get_inference_stats('edge')
        if edge_stats['count'] > 0:
            print("\nEdge Placement:")
            print(f"  Samples: {edge_stats['count']}")
            print(f"  Mean inference time: {edge_stats['mean_inference_ms']:.2f}ms")
            print(f"  Mean total latency: {edge_stats['mean_total_ms']:.2f}ms")
            print(f"  P50: {edge_stats['p50_total_ms']:.2f}ms")
            print(f"  P95: {edge_stats['p95_total_ms']:.2f}ms")

        # Cloud stats
        cloud_stats = self.get_inference_stats('cloud')
        if cloud_stats['count'] > 0:
            print("\nCloud Placement:")
            print(f"  Samples: {cloud_stats['count']}")
            print(f"  Mean inference time: {cloud_stats['mean_inference_ms']:.2f}ms")
            print(f"  Mean cloud latency: {cloud_stats['mean_cloud_ms']:.2f}ms")
            print(f"  Mean total latency: {cloud_stats['mean_total_ms']:.2f}ms")
            print(f"  P50: {cloud_stats['p50_total_ms']:.2f}ms")
            print(f"  P95: {cloud_stats['p95_total_ms']:.2f}ms")

        # Comparison
        if edge_stats['count'] > 0 and cloud_stats['count'] > 0:
            speedup = cloud_stats['mean_total_ms'] / edge_stats['mean_total_ms']
            print(f"\nComparison:")
            print(f"  Edge is {speedup:.1f}x faster than cloud")

        # Communication
        comm_stats = self.get_communication_stats()
        if comm_stats['total_messages'] > 0:
            print(f"\nCommunication Overhead:")
            print(f"  Total messages: {comm_stats['total_messages']}")
            print(f"  Total bytes: {comm_stats['total_bytes']}")
            print(f"  Avg message size: {comm_stats['avg_message_bytes']:.1f} bytes")

        print("=" * 60 + "\n")

    def reset(self):
        """Clear all collected metrics."""
        self.inference_samples.clear()
        self.communication_samples.clear()
