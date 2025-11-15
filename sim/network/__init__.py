"""
sim.network - Network simulation models for xEdgeSim

This module provides network abstraction for routing messages between nodes.
Introduced in M1c to decouple network logic from the coordinator.
"""

from sim.network.network_model import NetworkModel
from sim.network.direct_model import DirectNetworkModel

__all__ = ['NetworkModel', 'DirectNetworkModel']
