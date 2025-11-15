"""
scenario.py - YAML Scenario Parser (M1b, extended in M1d, M2d)

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

    network:  # M1d: Optional network configuration
      model: latency  # "direct" or "latency"
      default_latency_us: 10000
      default_loss_rate: 0.0
      links:
        - src: sensor1
          dst: gateway
          latency_us: 5000
          loss_rate: 0.01

    nodes:
      - id: sensor1
        type: sensor
        implementation: python_model  # M2d: "python_model" or "docker"
        port: 5001

      - id: gateway1
        type: gateway
        implementation: docker  # M2d: Docker container
        docker:  # M2d: Docker-specific config
          image: xedgesim/gateway:latest
          build_context: containers/gateway
          ports:
            5000: 5000
"""

import yaml
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from pathlib import Path
import os


@dataclass
class NetworkLink:
    """Network link configuration (M1d)."""
    src: str
    dst: str
    latency_us: int
    loss_rate: float = 0.0


@dataclass
class NetworkConfig:
    """
    Network model configuration (M1d).

    Attributes:
        model: Network model type ("direct" or "latency")
        default_latency_us: Default latency for unconfigured links
        default_loss_rate: Default packet loss rate (0.0 = no loss)
        links: List of per-link configurations
    """
    model: str = "direct"
    default_latency_us: int = 10000
    default_loss_rate: float = 0.0
    links: List[NetworkLink] = field(default_factory=list)

    def __post_init__(self):
        """Validate network configuration."""
        if self.model not in ["direct", "latency"]:
            raise ValueError(f"network.model must be 'direct' or 'latency', got '{self.model}'")

        if self.default_latency_us < 0:
            raise ValueError(f"default_latency_us must be non-negative, got {self.default_latency_us}")

        if not (0.0 <= self.default_loss_rate <= 1.0):
            raise ValueError(f"default_loss_rate must be in [0.0, 1.0], got {self.default_loss_rate}")

        for link in self.links:
            if not (0.0 <= link.loss_rate <= 1.0):
                raise ValueError(f"Link {link.src}->{link.dst}: loss_rate must be in [0.0, 1.0], got {link.loss_rate}")


@dataclass
class MLInferenceConfig:
    """
    ML inference configuration (M3c).

    Attributes:
        placement: Inference placement location ("edge" or "cloud")
        edge_config: Configuration for edge ML inference (if placement=edge)
        cloud_config: Configuration for cloud ML inference (if placement=cloud)
    """
    placement: str
    edge_config: Optional[Dict[str, Any]] = None
    cloud_config: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Validate ML inference configuration."""
        # Validate placement value
        if self.placement not in ["edge", "cloud"]:
            raise ValueError(f"ml_inference.placement must be 'edge' or 'cloud', got '{self.placement}'")

        # Validate required config sections
        if self.placement == "edge":
            if self.edge_config is None:
                raise ValueError("ml_inference.placement='edge' requires 'edge_config' section")

            # Validate edge_config has required fields
            if 'model_path' not in self.edge_config:
                raise ValueError("ml_inference.edge_config must specify 'model_path'")

            # Validate model file exists
            model_path = self.edge_config['model_path']
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"Edge ML model not found: {model_path}")

        if self.placement == "cloud":
            if self.cloud_config is None:
                raise ValueError("ml_inference.placement='cloud' requires 'cloud_config' section")

            # Validate cloud_config has required fields
            if 'model_path' not in self.cloud_config:
                raise ValueError("ml_inference.cloud_config must specify 'model_path'")

            # Validate model file exists
            model_path = self.cloud_config['model_path']
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"Cloud ML model not found: {model_path}")


@dataclass
class Scenario:
    """
    Simulation scenario configuration.

    Attributes:
        duration_s: Simulation duration in seconds
        seed: Random seed for deterministic execution
        time_quantum_us: Time step size in microseconds
        nodes: List of node configurations (dicts with id, type, port)
        network: Optional network configuration (M1d)
        ml_inference: Optional ML inference configuration (M3c)
    """
    duration_s: float
    seed: int
    time_quantum_us: int
    nodes: List[Dict[str, Any]]
    network: Optional[NetworkConfig] = None
    ml_inference: Optional[MLInferenceConfig] = None  # M3c

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

        # M2d/M3fc: Parse implementation field (default to python_model)
        implementation = node.get('implementation', 'python_model')
        if implementation not in ['python_model', 'docker', 'renode_inprocess']:  # M3fc
            raise ValueError(
                f"Node {i} (id={node.get('id')}): "
                f"implementation must be 'python_model', 'docker', or 'renode_inprocess', got '{implementation}'"
            )

        # Port is required for socket-based nodes, but not for in-process nodes (M3fc)
        if implementation in ['python_model', 'docker'] and 'port' not in node:
            raise ValueError(f"Node {i} (id={node.get('id')}): Missing required field 'port' for {implementation}")

        # M2d: Parse Docker-specific configuration
        docker_config = None
        if implementation == 'docker':
            if 'docker' in node:
                docker = node['docker']
                if not isinstance(docker, dict):
                    raise ValueError(
                        f"Node {i} (id={node.get('id')}): "
                        f"'docker' section must be a dict"
                    )
                docker_config = docker  # Pass through as-is for now

        # Build validated node config (M3fc: port optional for renode_inprocess)
        validated_node = {
            'id': node['id'],
            'type': node['type'],
            'implementation': implementation,
        }

        if 'port' in node:
            validated_node['port'] = int(node['port'])

        if docker_config:
            validated_node['docker'] = docker_config

        # M3fc: Pass through Renode-specific fields
        if implementation == 'renode_inprocess':
            if 'platform' in node:
                validated_node['platform'] = node['platform']
            if 'firmware' in node:
                validated_node['firmware'] = node['firmware']
            if 'monitor_port' in node:
                validated_node['monitor_port'] = int(node['monitor_port'])
            if 'working_dir' in node:
                validated_node['working_dir'] = node['working_dir']
            if 'seed' in node:
                validated_node['seed'] = int(node['seed'])

        validated_nodes.append(validated_node)

    # Parse network configuration (M1d - optional)
    network_config = None
    if 'network' in data:
        net = data['network']
        if not isinstance(net, dict):
            raise ValueError("'network' section must be a dict")

        # Parse network model type
        model = net.get('model', 'direct')

        # Parse defaults
        default_latency_us = int(net.get('default_latency_us', 10000))
        default_loss_rate = float(net.get('default_loss_rate', 0.0))

        # Parse links
        links = []
        if 'links' in net:
            link_list = net['links']
            if not isinstance(link_list, list):
                raise ValueError("network.links must be a list")

            for i, link in enumerate(link_list):
                if not isinstance(link, dict):
                    raise ValueError(f"Link {i} must be a dict, got {type(link)}")

                if 'src' not in link:
                    raise ValueError(f"Link {i}: Missing required field 'src'")
                if 'dst' not in link:
                    raise ValueError(f"Link {i}: Missing required field 'dst'")

                # latency_us is required for links in latency model
                if model == 'latency' and 'latency_us' not in link:
                    raise ValueError(f"Link {i} ({link['src']}->{link['dst']}): Missing required field 'latency_us' for latency model")

                latency_us = int(link.get('latency_us', default_latency_us))
                loss_rate = float(link.get('loss_rate', default_loss_rate))

                links.append(NetworkLink(
                    src=link['src'],
                    dst=link['dst'],
                    latency_us=latency_us,
                    loss_rate=loss_rate
                ))

        network_config = NetworkConfig(
            model=model,
            default_latency_us=default_latency_us,
            default_loss_rate=default_loss_rate,
            links=links
        )

    # Parse ML inference configuration (M3c - optional)
    ml_inference_config = None
    if 'ml_inference' in data:
        ml = data['ml_inference']
        if not isinstance(ml, dict):
            raise ValueError("'ml_inference' section must be a dict")

        # Parse placement
        if 'placement' not in ml:
            raise ValueError("ml_inference section must specify 'placement'")

        placement = ml['placement']

        # Parse configs
        edge_config = ml.get('edge_config')
        cloud_config = ml.get('cloud_config')

        # MLInferenceConfig.__post_init__ will validate required fields
        ml_inference_config = MLInferenceConfig(
            placement=placement,
            edge_config=edge_config,
            cloud_config=cloud_config
        )

    # Create and return scenario
    return Scenario(
        duration_s=float(duration_s),
        seed=int(seed),
        time_quantum_us=int(time_quantum_us),
        nodes=validated_nodes,
        network=network_config,
        ml_inference=ml_inference_config  # M3c
    )
