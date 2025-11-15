"""
sim.network - Network simulation models for xEdgeSim

This module provides network abstraction for routing messages between nodes.
Introduced in M1c to decouple network logic from the coordinator.

M1d adds LatencyNetworkModel with configurable latency and packet loss.
"""

from sim.network.network_model import NetworkModel
from sim.network.direct_model import DirectNetworkModel
from sim.network.latency_model import LatencyNetworkModel

__all__ = ['NetworkModel', 'DirectNetworkModel', 'LatencyNetworkModel']
