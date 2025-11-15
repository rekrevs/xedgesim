"""
network_model.py - M1c Network Abstraction

Defines the NetworkModel abstract base class for network simulation.

DESIGN PHILOSOPHY:
- Abstract interface for pluggable network models
- Enables progression from zero-latency (M1c) to realistic ns-3 (M1f)
- Simple, extensible interface
"""

from abc import ABC, abstractmethod
from typing import List, TYPE_CHECKING

# Avoid circular import
if TYPE_CHECKING:
    from sim.harness.coordinator import Event


class NetworkModel(ABC):
    """
    Abstract base class for network simulation models.

    A NetworkModel is responsible for:
    - Routing messages between nodes
    - Simulating network effects (delay, loss, reordering)
    - Maintaining virtual time awareness

    Different implementations provide different levels of realism:
    - DirectNetworkModel (M1c): Zero-latency direct routing
    - LatencyNetworkModel (M1d): Configurable latency
    - Ns3NetworkModel (M1f): Full packet-level simulation with ns-3
    """

    @abstractmethod
    def route_message(self, event: 'Event') -> List['Event']:
        """
        Route a message event through the network.

        This method is called by the coordinator when a node generates
        a message that should be sent to another node.

        Args:
            event: Event to route (must have src and dst fields)

        Returns:
            List of events to deliver. May be:
            - Empty list (packet dropped)
            - Single event (normal delivery)
            - Single delayed event (with updated time_us)
            - Multiple events (packet duplication, broadcast, etc.)

        Notes:
            - For zero-latency models: return [event] immediately
            - For latency models: may return [] and deliver via advance_to()
            - Event data should be preserved (don't modify payload)
        """
        pass

    @abstractmethod
    def advance_to(self, target_time_us: int) -> List['Event']:
        """
        Advance network simulation to target time.

        Called by coordinator during each time step to allow the network
        to deliver delayed messages.

        Args:
            target_time_us: Target simulation time in microseconds

        Returns:
            List of events that should be delivered at this time.
            For stateless models (DirectNetworkModel), returns empty list.
            For stateful models (LatencyNetworkModel), returns delayed events.

        Notes:
            - Only return events with time_us <= target_time_us
            - Events are delivered in time order
            - Multiple calls with same time are valid (idempotent)
        """
        pass

    @abstractmethod
    def reset(self):
        """
        Reset network state (for testing).

        Called between test runs to ensure clean state.
        Stateless models (DirectNetworkModel) can leave this as no-op.
        Stateful models should clear any pending events and reset counters.
        """
        pass
