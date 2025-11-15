"""
Device tier simulation nodes.

This module provides different implementations of device-tier nodes:
- SensorNode: Python-based sensor model (abstract, fast)
- RenodeNode: ARM/RISC-V emulator integration (realistic, slower)

Author: xEdgeSim Project
"""

from sim.device.sensor_node import SensorNode
from sim.device.renode_node import RenodeNode, Event, RenodeConnectionError, RenodeTimeoutError

__all__ = [
    'SensorNode',
    'RenodeNode',
    'Event',
    'RenodeConnectionError',
    'RenodeTimeoutError',
]
