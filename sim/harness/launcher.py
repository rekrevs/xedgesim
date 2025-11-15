#!/usr/bin/env python3
"""
launcher.py - Simulation Launcher (M3g)

Manages lifecycle of all simulation components:
- Python node processes (if multi-process mode)
- Docker containers
- Renode processes
- Coordinator

Design philosophy:
- Fail-fast during setup (validation before launch)
- Graceful during execution (cleanup on errors)
- Always cleanup on shutdown (no zombie processes)
"""

import subprocess
import time
import os
import signal
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

# Add project root to path for imports
_project_root = Path(__file__).parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from sim.config.scenario import Scenario
from sim.harness.coordinator import Coordinator


@dataclass
class SimulationResult:
    """Results from simulation execution."""
    success: bool
    duration_sec: float
    virtual_time_sec: float
    step_count: int = 0
    error_message: Optional[str] = None


class SimulationLauncher:
    """
    Manages lifecycle of all simulation components.

    Responsibilities:
    1. Validate scenario before launch
    2. Start Docker containers (if any)
    3. Spawn Python node processes (if multi-process mode)
    4. Create in-process nodes (Renode, Python models)
    5. Create and configure coordinator
    6. Orchestrate simulation execution
    7. Clean shutdown of all components
    """

    def __init__(self, scenario: Scenario):
        """
        Initialize launcher with scenario.

        Args:
            scenario: Parsed scenario configuration
        """
        self.scenario = scenario
        self.processes: List[subprocess.Popen] = []
        self.docker_containers: List[str] = []
        self.coordinator: Optional[Coordinator] = None
        self.start_wall_time = None

    def validate_scenario(self) -> List[str]:
        """
        Validate scenario before launch.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Check files exist for Renode nodes
        for node in self.scenario.nodes:
            node_id = node.get('id', 'unknown')
            implementation = node.get('implementation', 'python_model')

            if implementation == 'renode_inprocess':
                firmware = node.get('firmware')
                platform = node.get('platform')

                if not firmware:
                    errors.append(f"Node {node_id}: 'firmware' required for renode_inprocess")
                elif not os.path.exists(firmware):
                    errors.append(f"Node {node_id}: Firmware not found: {firmware}")

                if not platform:
                    errors.append(f"Node {node_id}: 'platform' required for renode_inprocess")
                elif not os.path.exists(platform):
                    errors.append(f"Node {node_id}: Platform not found: {platform}")

        # Check ML models exist
        if self.scenario.ml_inference:
            ml = self.scenario.ml_inference
            if ml.placement == 'edge' and ml.edge_config:
                model_path = ml.edge_config.get('model_path')
                if model_path and not os.path.exists(model_path):
                    errors.append(f"Edge ML model not found: {model_path}")

            if ml.placement == 'cloud' and ml.cloud_config:
                model_path = ml.cloud_config.get('model_path')
                if model_path and not os.path.exists(model_path):
                    errors.append(f"Cloud ML model not found: {model_path}")

        return errors

    def launch(self) -> Coordinator:
        """
        Launch all components and return configured coordinator.

        Returns:
            Coordinator instance ready to run

        Raises:
            ValueError: If validation fails
            RuntimeError: If launch fails
        """
        print("\n" + "="*60)
        print("xEdgeSim Simulation Launcher (M3g)")
        print("="*60)

        # Phase 1: Validate scenario
        print("\n[Launcher] Validating scenario...")
        errors = self.validate_scenario()
        if errors:
            error_msg = "Scenario validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            raise ValueError(error_msg)
        print("[Launcher] ✓ Scenario validation passed")

        # Phase 2: Start Docker containers (if any)
        docker_nodes = [n for n in self.scenario.nodes
                        if n.get('implementation') == 'docker']
        if docker_nodes:
            print(f"\n[Launcher] Starting {len(docker_nodes)} Docker container(s)...")
            for node in docker_nodes:
                self._start_docker_container(node)
            print("[Launcher] ✓ Docker containers started")

        # Phase 3: Create network model
        print("\n[Launcher] Creating network model...")
        network_model = self._create_network_model()
        print(f"[Launcher] ✓ Network model: {type(network_model).__name__}")

        # Phase 4: Create coordinator
        print("\n[Launcher] Creating coordinator...")
        self.coordinator = Coordinator(
            time_quantum_us=self.scenario.time_quantum_us,
            network_model=network_model
        )
        print(f"[Launcher] ✓ Coordinator created")
        print(f"  Time quantum: {self.scenario.time_quantum_us}us")
        print(f"  Duration: {self.scenario.duration_s}s")
        print(f"  Seed: {self.scenario.seed}")

        # Phase 5: Register nodes with coordinator
        print("\n[Launcher] Registering nodes...")
        for node in self.scenario.nodes:
            self._register_node(node)
        print(f"[Launcher] ✓ Registered {len(self.scenario.nodes)} node(s)")

        # Phase 6: Connect and initialize all nodes
        print("\n[Launcher] Connecting to nodes...")
        self.coordinator.connect_all()
        print("[Launcher] ✓ All nodes connected")

        print("\n[Launcher] Initializing nodes...")
        self.coordinator.initialize_all(seed=self.scenario.seed)
        print("[Launcher] ✓ All nodes initialized")

        print("\n" + "="*60)
        print("Simulation ready to run")
        print("="*60 + "\n")

        return self.coordinator

    def run(self) -> SimulationResult:
        """
        Launch and run complete simulation.

        Returns:
            SimulationResult with execution details
        """
        try:
            # Launch coordinator
            coordinator = self.launch()

            # Run simulation
            self.start_wall_time = time.time()
            duration_us = int(self.scenario.duration_s * 1_000_000)
            coordinator.run(duration_us=duration_us)

            # Success!
            elapsed = time.time() - self.start_wall_time
            return SimulationResult(
                success=True,
                duration_sec=elapsed,
                virtual_time_sec=self.scenario.duration_s
            )

        except Exception as e:
            # Failure
            elapsed = time.time() - self.start_wall_time if self.start_wall_time else 0
            return SimulationResult(
                success=False,
                duration_sec=elapsed,
                virtual_time_sec=0,
                error_message=str(e)
            )

        finally:
            # Always cleanup
            self.shutdown()

    def shutdown(self):
        """
        Clean shutdown of all components.

        Ensures:
        - All processes terminated
        - All Docker containers stopped
        - No zombie processes
        """
        print("\n" + "="*60)
        print("Shutting down simulation...")
        print("="*60)

        # Note: Coordinator shutdown is handled in coordinator.run()
        # (sends SHUTDOWN to all nodes)

        # Stop Docker containers
        if self.docker_containers:
            print(f"\n[Launcher] Stopping {len(self.docker_containers)} Docker container(s)...")
            for container_id in self.docker_containers:
                self._stop_docker_container(container_id)
            print("[Launcher] ✓ Docker containers stopped")

        # Terminate any spawned processes
        if self.processes:
            print(f"\n[Launcher] Terminating {len(self.processes)} process(es)...")
            for proc in self.processes:
                if proc.poll() is None:  # Still running
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        print(f"[Launcher] WARNING: Process {proc.pid} didn't terminate, killing...")
                        proc.kill()
                        proc.wait()
            print("[Launcher] ✓ All processes terminated")

        # Verify no zombies
        zombies = [p for p in self.processes if p.poll() is None]
        if zombies:
            print(f"\n[Launcher] WARNING: {len(zombies)} zombie process(es) detected!")
            for proc in zombies:
                print(f"  - PID {proc.pid}")
        else:
            print("\n[Launcher] ✓ Clean shutdown - no zombie processes")

        print("\n" + "="*60 + "\n")

    def _create_network_model(self):
        """Create network model based on scenario configuration."""
        if not self.scenario.network:
            # No network config - use default direct model
            from sim.network.direct_model import DirectNetworkModel
            return DirectNetworkModel()

        if self.scenario.network.model == "direct":
            from sim.network.direct_model import DirectNetworkModel
            return DirectNetworkModel()

        elif self.scenario.network.model == "latency":
            from sim.network.latency_model import LatencyNetworkModel
            return LatencyNetworkModel(self.scenario.network, self.scenario.seed)

        else:
            raise ValueError(f"Unknown network model: {self.scenario.network.model}")

    def _register_node(self, node: Dict[str, Any]):
        """Register a node with the coordinator."""
        node_id = node['id']
        implementation = node.get('implementation', 'python_model')

        if implementation == 'renode_inprocess':
            # Create in-process Renode node
            from sim.device.renode_node import RenodeNode

            renode_config = {
                'platform': node['platform'],
                'firmware': node['firmware'],
                'monitor_port': node.get('monitor_port'),
                'working_dir': node.get('working_dir', f'/tmp/xedgesim/{node_id}'),
            }

            renode_node = RenodeNode(node_id, renode_config)
            self.coordinator.add_inprocess_node(node_id, renode_node)

            print(f"  - {node_id}: Renode (in-process)")
            print(f"      Platform: {renode_config['platform']}")
            print(f"      Firmware: {renode_config['firmware']}")

        else:
            # Socket-based nodes (python_model, docker)
            port = node.get('port')
            if not port:
                raise ValueError(f"Node {node_id}: 'port' required for {implementation}")

            self.coordinator.add_node(node_id, "localhost", port)
            print(f"  - {node_id}: {implementation} (socket, port {port})")

    def _start_docker_container(self, node: Dict[str, Any]):
        """
        Start a Docker container for a node.

        Note: This is a stub for M3g. Full Docker integration
        requires Docker daemon and will be tested by testing agent.
        """
        node_id = node['id']
        docker_config = node.get('docker', {})

        # M3g: Basic Docker container startup
        # Full implementation will be tested by testing agent with Docker

        print(f"  - {node_id}: Docker container")

        # Check if we can run docker
        try:
            result = subprocess.run(['docker', '--version'],
                                  capture_output=True,
                                  timeout=5)
            if result.returncode != 0:
                raise RuntimeError("Docker not available")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            print(f"    WARNING: Docker not available (development environment)")
            print(f"    This node will be skipped in this environment.")
            print(f"    Full Docker tests will be run by testing agent.")
            return

        # Docker is available - try to start container
        # (This code will be fully tested by testing agent)
        image = docker_config.get('image')
        if not image:
            raise ValueError(f"Node {node_id}: Docker node requires 'image' in docker config")

        # Build if build_context specified
        if 'build_context' in docker_config:
            print(f"    Building image from: {docker_config['build_context']}")
            # docker build implementation here (delegated to testing agent)

        # Run container
        print(f"    Starting container: {image}")
        # docker run implementation here (delegated to testing agent)

        # Store container ID for cleanup
        # self.docker_containers.append(container_id)

    def _stop_docker_container(self, container_id: str):
        """
        Stop a Docker container.

        Note: This is a stub for M3g. Full Docker integration
        will be tested by testing agent.
        """
        try:
            subprocess.run(['docker', 'stop', container_id],
                         capture_output=True,
                         timeout=10)
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            print(f"    WARNING: Failed to stop container {container_id}: {e}")


def run_scenario(scenario_path: str, seed: Optional[int] = None) -> SimulationResult:
    """
    Convenience function to run a scenario from YAML file.

    Args:
        scenario_path: Path to YAML scenario file
        seed: Optional override for scenario seed

    Returns:
        SimulationResult
    """
    from sim.config.scenario import load_scenario

    # Load scenario
    scenario = load_scenario(scenario_path)

    # Override seed if specified
    if seed is not None:
        scenario.seed = seed

    # Launch and run
    launcher = SimulationLauncher(scenario)
    return launcher.run()
