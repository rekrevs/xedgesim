"""
scenario.py - YAML Scenario Parser (M1b)

Parses simulation scenarios from YAML configuration files.

Design philosophy (per critical analysis):
- Keep it simple: minimal validation, no schema framework
- Fail fast: raise clear exceptions on errors
- No magic: explicit field names, no dynamic configuration

Example YAML:
    simulation:
      duration_s: 10
      seed: 42
      time_quantum_us: 1000

    nodes:
      - id: sensor1
        type: sensor_model
        port: 5001
"""

import yaml
from dataclasses import dataclass
from typing import List, Dict, Any
from pathlib import Path


@dataclass
class Scenario:
    """
    Simulation scenario configuration.

    Attributes:
        duration_s: Simulation duration in seconds
        seed: Random seed for deterministic execution
        time_quantum_us: Time step size in microseconds
        nodes: List of node configurations (dicts with id, type, port)
    """
    duration_s: float
    seed: int
    time_quantum_us: int
    nodes: List[Dict[str, Any]]

    def __post_init__(self):
        """Validate scenario after initialization."""
        if self.duration_s <= 0:
            raise ValueError(f"duration_s must be positive, got {self.duration_s}")

        if self.time_quantum_us <= 0:
            raise ValueError(f"time_quantum_us must be positive, got {self.time_quantum_us}")

        if not self.nodes:
            raise ValueError("No nodes defined in scenario")


def load_scenario(yaml_path: str) -> Scenario:
    """
    Load scenario from YAML file.

    Args:
        yaml_path: Path to YAML scenario file

    Returns:
        Scenario object with parsed configuration

    Raises:
        FileNotFoundError: If YAML file doesn't exist
        ValueError: If required fields are missing or invalid
        yaml.YAMLError: If YAML syntax is invalid
    """
    # Check file exists
    path = Path(yaml_path)
    if not path.exists():
        raise FileNotFoundError(f"Scenario file not found: {yaml_path}")

    # Load YAML
    with open(path, 'r') as f:
        try:
            data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Invalid YAML syntax in {yaml_path}: {e}")

    # Validate top-level structure
    if not isinstance(data, dict):
        raise ValueError(f"Scenario file must contain a YAML dict, got {type(data)}")

    # Extract simulation section
    if 'simulation' not in data:
        raise ValueError("Missing required section: 'simulation'")

    sim = data['simulation']
    if not isinstance(sim, dict):
        raise ValueError("'simulation' section must be a dict")

    # Extract nodes section
    if 'nodes' not in data:
        raise ValueError("Missing required section: 'nodes'")

    nodes = data['nodes']
    if not isinstance(nodes, list):
        raise ValueError("'nodes' section must be a list")

    if len(nodes) == 0:
        raise ValueError("No nodes defined in scenario")

    # Parse simulation parameters with defaults
    duration_s = sim.get('duration_s')
    if duration_s is None:
        raise ValueError("Missing required field: simulation.duration_s")

    seed = sim.get('seed')
    if seed is None:
        raise ValueError("Missing required field: simulation.seed")

    # Default time quantum to 1ms if not specified
    time_quantum_us = sim.get('time_quantum_us', 1000)

    # Validate node configurations
    validated_nodes = []
    for i, node in enumerate(nodes):
        if not isinstance(node, dict):
            raise ValueError(f"Node {i} must be a dict, got {type(node)}")

        # Check required fields
        if 'id' not in node:
            raise ValueError(f"Node {i}: Missing required field 'id'")
        if 'type' not in node:
            raise ValueError(f"Node {i}: Missing required field 'type'")
        if 'port' not in node:
            raise ValueError(f"Node {i} (id={node.get('id')}): Missing required field 'port'")

        validated_nodes.append({
            'id': node['id'],
            'type': node['type'],
            'port': int(node['port'])
        })

    # Create and return scenario
    return Scenario(
        duration_s=float(duration_s),
        seed=int(seed),
        time_quantum_us=int(time_quantum_us),
        nodes=validated_nodes
    )
