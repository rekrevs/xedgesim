"""
containers - Docker container support and protocol adapters (M3h)

This module provides infrastructure for Docker containers to integrate
with the xEdgeSim coordinator using virtual time.
"""

from .protocol_adapter import (
    CoordinatorProtocolAdapter,
    Event,
    ServiceCallback,
    run_service
)

__all__ = [
    'CoordinatorProtocolAdapter',
    'Event',
    'ServiceCallback',
    'run_service',
]
