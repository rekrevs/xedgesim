"""
Metrics collection for xEdgeSim.

M1e: Network metrics (packet latency, delivery, drops)
M3d: ML metrics (inference latency, placement comparison)
"""

from sim.metrics.ml_metrics import MLMetricsCollector

__all__ = ['MLMetricsCollector']
