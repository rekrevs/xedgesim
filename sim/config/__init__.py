"""
sim.config - Scenario and configuration management

Provides YAML-based scenario parsing for xEdgeSim simulations.
"""

from .scenario import Scenario, load_scenario

__all__ = ['Scenario', 'load_scenario']
