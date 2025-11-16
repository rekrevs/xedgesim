"""
sim.harness - Simulation orchestration and execution (M3g)

This module provides the scenario harness for launching and running
complete xEdgeSim simulations.
"""

from .coordinator import Coordinator, Event, NodeAdapter, NodeConnection, InProcessNodeAdapter
from .launcher import SimulationLauncher, SimulationResult, run_scenario

__all__ = [
    'Coordinator',
    'Event',
    'NodeAdapter',
    'NodeConnection',
    'InProcessNodeAdapter',
    'SimulationLauncher',
    'SimulationResult',
    'run_scenario',
]
