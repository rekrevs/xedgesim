"""
direct_model.py - M1c DirectNetworkModel (extended in M1e)

Zero-latency direct routing implementation.
Behaves identically to M0 inline routing logic in coordinator.

DESIGN PHILOSOPHY:
- Simplest possible network model
- Zero latency, no packet loss, no reordering
- Stateless (no buffering, no pending events)
- Used to validate network abstraction layer works
- Maintains M0 determinism
- M1e: Returns empty metrics (stateless model)
"""

from typing import List, TYPE_CHECKING
from sim.network.network_model import NetworkModel
from sim.network.metrics import NetworkMetrics

# Avoid circular import
if TYPE_CHECKING:
    from sim.harness.coordinator import Event


class DirectNetworkModel(NetworkModel):
    """
    Zero-latency direct routing (M0 behavior).

    This is the simplest possible NetworkModel implementation:
    - Messages are delivered immediately (zero latency)
    - No packet loss
    - No reordering
    - No state (completely stateless)

    Behavior is identical to M0 coordinator's inline routing:
        for event in all_events:
            if event.dst and event.dst in self.pending_events:
                self.pending_events[event.dst].append(event)

    This model serves as:
    1. Reference implementation for testing
    2. Baseline for comparing more complex models
    3. Validation that network abstraction doesn't change M0 behavior
    """

    def route_message(self, event: 'Event') -> List['Event']:
        """
        Route message with zero latency.

        Args:
            event: Event to route

        Returns:
            List containing the original event (immediate delivery)
        """
        # Direct routing: return event immediately for delivery
        return [event]

    def advance_to(self, target_time_us: int) -> List['Event']:
        """
        Advance network time (no-op for DirectNetworkModel).

        Args:
            target_time_us: Target simulation time

        Returns:
            Empty list (no delayed events in zero-latency model)
        """
        # No delayed events in direct model
        return []

    def reset(self):
        """
        Reset network state (no-op for stateless model).
        """
        # No state to reset
        pass

    def get_metrics(self) -> NetworkMetrics:
        """
        Get network metrics (M1e).

        Returns:
            Empty NetworkMetrics (DirectNetworkModel is stateless, doesn't track metrics)
        """
        # Direct model doesn't track metrics (stateless)
        return NetworkMetrics()
