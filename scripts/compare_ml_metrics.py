#!/usr/bin/env python3
"""
compare_ml_metrics.py - ML Placement Metrics Comparison Utility

Compares edge vs cloud ML placement performance from CSV metrics files.

Usage:
    python scripts/compare_ml_metrics.py --edge metrics/edge.csv --cloud metrics/cloud.csv
    python scripts/compare_ml_metrics.py metrics/combined.csv  # Auto-detect placement
"""

import csv
import argparse
import sys
from pathlib import Path
from typing import List, Dict, Any


def load_metrics(csv_path: str) -> List[Dict[str, Any]]:
    """
    Load metrics from CSV file.

    Args:
        csv_path: Path to CSV file

    Returns:
        List of metric dictionaries
    """
    metrics = []

    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Convert numeric fields
            metrics.append({
                'timestamp_us': int(row['timestamp_us']),
                'device_id': row['device_id'],
                'placement': row['placement'],
                'inference_time_ms': float(row['inference_time_ms']),
                'cloud_latency_ms': float(row['cloud_latency_ms']),
                'total_latency_ms': float(row['total_latency_ms'])
            })

    return metrics


def compute_stats(metrics: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Compute statistics from metrics.

    Args:
        metrics: List of metric dictionaries

    Returns:
        Dictionary with computed statistics
    """
    if not metrics:
        return {
            'count': 0,
            'mean_inference_ms': 0.0,
            'mean_cloud_ms': 0.0,
            'mean_total_ms': 0.0,
            'min_total_ms': 0.0,
            'max_total_ms': 0.0,
            'p50_total_ms': 0.0,
            'p95_total_ms': 0.0,
            'p99_total_ms': 0.0
        }

    n = len(metrics)
    total_latencies = sorted([m['total_latency_ms'] for m in metrics])

    return {
        'count': n,
        'mean_inference_ms': sum(m['inference_time_ms'] for m in metrics) / n,
        'mean_cloud_ms': sum(m['cloud_latency_ms'] for m in metrics) / n,
        'mean_total_ms': sum(m['total_latency_ms'] for m in metrics) / n,
        'min_total_ms': min(total_latencies),
        'max_total_ms': max(total_latencies),
        'p50_total_ms': total_latencies[n // 2],
        'p95_total_ms': total_latencies[int(n * 0.95)] if n > 20 else total_latencies[-1],
        'p99_total_ms': total_latencies[int(n * 0.99)] if n > 100 else total_latencies[-1]
    }


def print_stats(placement: str, stats: Dict[str, float]):
    """
    Print statistics for a placement strategy.

    Args:
        placement: 'edge' or 'cloud'
        stats: Statistics dictionary
    """
    print(f"\n{placement.capitalize()} Placement:")
    print(f"  Samples: {stats['count']}")
    print(f"  Mean inference time: {stats['mean_inference_ms']:.2f}ms")

    if stats['mean_cloud_ms'] > 0:
        print(f"  Mean cloud latency: {stats['mean_cloud_ms']:.2f}ms")

    print(f"  Mean total latency: {stats['mean_total_ms']:.2f}ms")
    print(f"  Min total latency: {stats['min_total_ms']:.2f}ms")
    print(f"  Max total latency: {stats['max_total_ms']:.2f}ms")
    print(f"  P50 total latency: {stats['p50_total_ms']:.2f}ms")
    print(f"  P95 total latency: {stats['p95_total_ms']:.2f}ms")

    if stats['count'] > 100:
        print(f"  P99 total latency: {stats['p99_total_ms']:.2f}ms")


def main():
    """Main comparison function."""
    parser = argparse.ArgumentParser(
        description='Compare ML placement metrics (edge vs cloud)'
    )
    parser.add_argument(
        'metrics_file',
        nargs='?',
        help='Combined metrics CSV file (auto-detects edge/cloud)'
    )
    parser.add_argument(
        '--edge',
        help='Edge placement metrics CSV file'
    )
    parser.add_argument(
        '--cloud',
        help='Cloud placement metrics CSV file'
    )

    args = parser.parse_args()

    # Determine input mode
    if args.metrics_file:
        # Single file mode - load and separate by placement
        print(f"Loading metrics from: {args.metrics_file}")
        all_metrics = load_metrics(args.metrics_file)

        edge_metrics = [m for m in all_metrics if m['placement'] == 'edge']
        cloud_metrics = [m for m in all_metrics if m['placement'] == 'cloud']

    elif args.edge or args.cloud:
        # Two-file mode
        edge_metrics = load_metrics(args.edge) if args.edge else []
        cloud_metrics = load_metrics(args.cloud) if args.cloud else []

    else:
        parser.print_help()
        return 1

    # Compute statistics
    edge_stats = compute_stats(edge_metrics)
    cloud_stats = compute_stats(cloud_metrics)

    # Print results
    print("\n" + "=" * 70)
    print("ML Placement Comparison")
    print("=" * 70)

    if edge_stats['count'] > 0:
        print_stats('edge', edge_stats)

    if cloud_stats['count'] > 0:
        print_stats('cloud', cloud_stats)

    # Comparison
    if edge_stats['count'] > 0 and cloud_stats['count'] > 0:
        print(f"\nComparison:")

        speedup = cloud_stats['mean_total_ms'] / edge_stats['mean_total_ms']
        print(f"  Edge is {speedup:.1f}x faster than cloud (mean latency)")

        # Breakdown
        if cloud_stats['mean_cloud_ms'] > 0:
            cloud_network_pct = (cloud_stats['mean_cloud_ms'] / cloud_stats['mean_total_ms']) * 100
            print(f"  Cloud latency breakdown:")
            print(f"    Network: {cloud_stats['mean_cloud_ms']:.2f}ms ({cloud_network_pct:.1f}%)")
            print(f"    Inference: {cloud_stats['mean_inference_ms']:.2f}ms ({100-cloud_network_pct:.1f}%)")

    print("=" * 70 + "\n")

    return 0


if __name__ == '__main__':
    sys.exit(main())
