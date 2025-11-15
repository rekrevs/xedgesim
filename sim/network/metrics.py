"""
metrics.py - M1e Network Metrics

Defines network-level metrics for performance analysis.

DESIGN PHILOSOPHY:
- Simple counters and statistics
- Network-wide totals (not per-link for M1e)
- Easy to serialize to CSV
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class NetworkMetrics:
    """
    Network performance metrics.

    Tracks packet-level statistics for the entire network:
    - Packet counts (sent, delivered, dropped)
    - Latency statistics (min, max, average)

    Used by NetworkModel implementations to report performance data.
    """

    packets_sent: int = 0
    packets_delivered: int = 0
    packets_dropped: int = 0
    total_latency_us: int = 0  # Sum of all latencies (for average calculation)
    min_latency_us: Optional[int] = None
    max_latency_us: Optional[int] = None

    def average_latency_us(self) -> float:
        """
        Calculate average latency across all delivered packets.

        Returns:
            Average latency in microseconds, or 0.0 if no packets delivered
        """
        if self.packets_delivered == 0:
            return 0.0
        return self.total_latency_us / self.packets_delivered

    def record_sent(self):
        """Record a packet being sent."""
        self.packets_sent += 1

    def record_delivered(self, latency_us: int):
        """
        Record a packet being delivered.

        Args:
            latency_us: Latency for this packet in microseconds
        """
        self.packets_delivered += 1
        self.total_latency_us += latency_us

        # Update min/max
        if self.min_latency_us is None or latency_us < self.min_latency_us:
            self.min_latency_us = latency_us

        if self.max_latency_us is None or latency_us > self.max_latency_us:
            self.max_latency_us = latency_us

    def record_dropped(self):
        """Record a packet being dropped."""
        self.packets_dropped += 1

    def reset(self):
        """Reset all metrics to initial state."""
        self.packets_sent = 0
        self.packets_delivered = 0
        self.packets_dropped = 0
        self.total_latency_us = 0
        self.min_latency_us = None
        self.max_latency_us = None
