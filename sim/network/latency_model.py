"""
latency_model.py - M1d Latency Network Model (extended in M1e)

Implements a deterministic network model with configurable latency and packet loss.

DESIGN PHILOSOPHY:
- Deterministic: same seed → same packet drops
- Configurable: per-link latency and loss rates
- Simple: just latency and loss, no bandwidth/reordering yet
- Event queue maintains in-flight packets
- M1e: Tracks network metrics for performance analysis
"""

import heapq
import random
import hashlib
from typing import List, Dict, TYPE_CHECKING
from sim.network.network_model import NetworkModel
from sim.network.metrics import NetworkMetrics

# Avoid circular import
if TYPE_CHECKING:
    from sim.harness.coordinator import Event
    from sim.config.scenario import NetworkConfig


class LatencyNetworkModel(NetworkModel):
    """
    Latency-based network model with configurable delays and packet loss.

    Features:
    - Configurable per-link latency (microseconds)
    - Deterministic packet loss (percentage-based, seeded RNG)
    - Event queue for in-flight packets
    - FIFO delivery (no reordering)

    Configuration:
        - Link-specific latency and loss rates via NetworkConfig
        - Default latency/loss for unconfigured links
        - Deterministic RNG seeding for reproducibility

    Limitations (deferred to later stages):
        - No bandwidth constraints
        - No packet reordering
        - No congestion simulation
        - Simple point-to-point links only
    """

    def __init__(self, config: 'NetworkConfig', seed: int = 42):
        """
        Initialize LatencyNetworkModel.

        Args:
            config: Network configuration with latency and loss parameters
            seed: Random seed for deterministic packet loss
        """
        self.config = config
        self.seed = seed

        # Event queue: min-heap sorted by delivery time
        # Each item: (delivery_time_us, event)
        self.event_queue: List[tuple] = []

        # Build link configuration lookup
        # Key: (src, dst) -> (latency_us, loss_rate)
        self.links: Dict[tuple, tuple] = {}
        for link in config.links:
            self.links[(link.src, link.dst)] = (link.latency_us, link.loss_rate)

        # Create deterministic RNG for each link
        # This ensures same seed → same packet drop pattern
        self.link_rngs: Dict[tuple, random.Random] = {}
        for link in config.links:
            link_key = (link.src, link.dst)
            link_id = f"{link.src}_{link.dst}"
            hash_input = f"{link_id}_{seed}".encode('utf-8')
            hash_digest = hashlib.sha256(hash_input).digest()
            link_seed = int.from_bytes(hash_digest[:8], 'big')
            self.link_rngs[link_key] = random.Random(link_seed)

        # Default RNG for unconfigured links
        hash_input = f"default_{seed}".encode('utf-8')
        hash_digest = hashlib.sha256(hash_input).digest()
        default_seed = int.from_bytes(hash_digest[:8], 'big')
        self.default_rng = random.Random(default_seed)

        # Track current simulation time (for advance_to logic)
        self.current_time_us = 0

        # M1e: Network metrics tracking
        self.metrics = NetworkMetrics()

    def route_message(self, event: 'Event') -> List['Event']:
        """
        Route message with latency and possible packet loss.

        Args:
            event: Event to route

        Returns:
            Empty list (event is queued for delayed delivery)
            or empty list if packet is dropped
        """
        # M1e: Record packet sent
        self.metrics.record_sent()

        # Look up link configuration
        link_key = (event.src, event.dst) if event.dst else (event.src, None)

        if link_key in self.links:
            latency_us, loss_rate = self.links[link_key]
            rng = self.link_rngs[link_key]
        else:
            # Use defaults for unconfigured links
            latency_us = self.config.default_latency_us
            loss_rate = self.config.default_loss_rate
            rng = self.default_rng

        # Determine if packet is dropped (deterministic)
        if rng.random() < loss_rate:
            # M1e: Record packet dropped
            self.metrics.record_dropped()
            return []

        # Calculate delivery time
        delivery_time_us = event.time_us + latency_us

        # Create delayed event (preserve all fields)
        from sim.harness.coordinator import Event as EventClass
        delayed_event = EventClass(
            time_us=delivery_time_us,  # Updated delivery time
            type=event.type,
            src=event.src,
            dst=event.dst,
            payload=event.payload,
            size_bytes=event.size_bytes,
            network_metadata={
                'latency_us': latency_us,
                'sent_time_us': event.time_us,
                'delivery_time_us': delivery_time_us,
                'loss_rate': loss_rate
            }
        )

        # Store latency with event for metrics tracking
        # We'll record delivery when the event is actually delivered in advance_to()
        delayed_event._latency_us = latency_us  # Store for metrics

        # Add to priority queue
        heapq.heappush(self.event_queue, (delivery_time_us, delayed_event))

        # No immediate delivery
        return []

    def advance_to(self, target_time_us: int) -> List['Event']:
        """
        Advance network simulation to target time, delivering ready events.

        Args:
            target_time_us: Target simulation time

        Returns:
            List of events ready for delivery at this time
        """
        self.current_time_us = target_time_us

        # Deliver all events with delivery_time <= target_time
        ready_events = []

        while self.event_queue:
            # Peek at next event
            delivery_time, event = self.event_queue[0]

            if delivery_time <= target_time_us:
                # Event is ready - pop it
                heapq.heappop(self.event_queue)
                ready_events.append(event)

                # M1e: Record delivery with latency
                latency_us = getattr(event, '_latency_us', 0)
                self.metrics.record_delivered(latency_us)
            else:
                # Next event is in the future
                break

        return ready_events

    def reset(self):
        """Reset network state (clear event queue and metrics)."""
        self.event_queue = []
        self.current_time_us = 0

        # M1e: Reset metrics
        self.metrics.reset()

        # Re-initialize RNGs to original seed state
        for link in self.config.links:
            link_key = (link.src, link.dst)
            link_id = f"{link.src}_{link.dst}"
            hash_input = f"{link_id}_{self.seed}".encode('utf-8')
            hash_digest = hashlib.sha256(hash_input).digest()
            link_seed = int.from_bytes(hash_digest[:8], 'big')
            self.link_rngs[link_key] = random.Random(link_seed)

        hash_input = f"default_{self.seed}".encode('utf-8')
        hash_digest = hashlib.sha256(hash_input).digest()
        default_seed = int.from_bytes(hash_digest[:8], 'big')
        self.default_rng = random.Random(default_seed)

    def get_metrics(self) -> NetworkMetrics:
        """
        Get current network metrics (M1e).

        Returns:
            NetworkMetrics with current performance statistics
        """
        return self.metrics
