#!/usr/bin/env python3
"""
coordinator.py - M0 Minimal Coordinator

DESIGN PHILOSOPHY (from critical analysis):
- "Dumb and simple" - ONLY coordinates time
- Conservative synchronous lockstep
- ~200 lines total
- No metrics aggregation (nodes write their own CSV files)
- No complex error handling (fail fast)
- Hardcoded configuration for M0

This coordinator implements the core federated co-simulation algorithm:
1. Send ADVANCE <time_us> to all nodes
2. Wait for all nodes to reply DONE
3. Collect events from all nodes
4. Route cross-node messages
5. Advance global time
6. Repeat
"""

import socket
import json
import time
import sys
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod

# Add project root to path for imports (M1b: needed for sim.config)
_project_root = Path(__file__).parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


@dataclass
class Event:
    """Simulation event."""
    time_us: int
    type: str
    src: str
    dst: str = None
    payload: Any = None
    size_bytes: int = 0


class NodeAdapter(ABC):
    """
    Abstract base class for node adapters (M3fc).

    Supports both socket-based nodes (python_model, docker) and
    in-process nodes (renode_inprocess).
    """

    def __init__(self, node_id: str):
        self.node_id = node_id

    @abstractmethod
    def connect(self):
        """Connect/initialize the node."""
        pass

    @abstractmethod
    def send_init(self, config: Dict[str, Any]):
        """Send initialization configuration to node."""
        pass

    @abstractmethod
    def send_advance(self, target_time_us: int, pending_events: List[Event]):
        """Advance node to target time with pending events."""
        pass

    @abstractmethod
    def wait_done(self) -> List[Event]:
        """Wait for node to finish advancing and return events."""
        pass

    @abstractmethod
    def send_shutdown(self):
        """Shutdown the node."""
        pass


class NodeConnection(NodeAdapter):
    """Represents a socket-based connection to a simulated node (python_model, docker)."""

    def __init__(self, node_id: str, host: str, port: int):
        super().__init__(node_id)
        self.host = host
        self.port = port
        self.sock = None
        self.sock_file = None

    def connect(self, max_retries=10, retry_delay=0.5):
        """Connect to node with retries."""
        for attempt in range(max_retries):
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.connect((self.host, self.port))
                self.sock_file = self.sock.makefile('rw')
                print(f"[Coordinator] Connected to {self.node_id} at {self.host}:{self.port}")
                return
            except ConnectionRefusedError:
                if attempt < max_retries - 1:
                    print(f"[Coordinator] Connection to {self.node_id} failed, retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                else:
                    raise

    def send_init(self, config: Dict[str, Any]):
        """Send INIT message to node."""
        config_json = json.dumps(config)
        self.sock_file.write(f"INIT {self.node_id} {config_json}\n")
        self.sock_file.flush()

        # Wait for READY
        response = self.sock_file.readline().strip()
        if response != "READY":
            raise RuntimeError(f"Expected READY from {self.node_id}, got: {response}")

    def send_advance(self, target_time_us: int, pending_events: List[Event]):
        """Send ADVANCE message with pending events."""
        events_json = json.dumps([asdict(e) for e in pending_events])
        self.sock_file.write(f"ADVANCE {target_time_us}\n")
        self.sock_file.write(f"{events_json}\n")
        self.sock_file.flush()

    def wait_done(self) -> List[Event]:
        """Wait for DONE response and collect events."""
        response = self.sock_file.readline().strip()
        if response != "DONE":
            raise RuntimeError(f"Expected DONE from {self.node_id}, got: {response}")

        # Read events JSON
        events_json = self.sock_file.readline().strip()
        events_data = json.loads(events_json)

        # Convert to Event objects
        events = []
        for e in events_data:
            events.append(Event(**e))

        return events

    def send_shutdown(self):
        """Send SHUTDOWN message."""
        self.sock_file.write("SHUTDOWN\n")
        self.sock_file.flush()
        self.sock.close()


class InProcessNodeAdapter(NodeAdapter):
    """
    Adapter for in-process nodes (M3fc: renode_inprocess).

    Wraps nodes that are instantiated directly by the coordinator
    (e.g., RenodeNode) to provide the same interface as socket-based nodes.
    """

    def __init__(self, node_id: str, node_instance):
        """
        Initialize in-process node adapter.

        Args:
            node_id: Node identifier
            node_instance: Instance of node class (e.g., RenodeNode)
                          Must implement: start(), advance(time_us), stop()
        """
        super().__init__(node_id)
        self.node = node_instance
        self.current_time_us = 0

    def connect(self):
        """Start the in-process node."""
        print(f"[Coordinator] Starting in-process node: {self.node_id}")
        self.node.start()

    def send_init(self, config: Dict[str, Any]):
        """
        Initialize the node with configuration.

        For in-process nodes, initialization happens in constructor,
        so this is a no-op. Just log that we're ready.
        """
        print(f"[Coordinator] {self.node_id} initialized and ready (in-process)")

    def send_advance(self, target_time_us: int, pending_events: List[Event]):
        """
        Advance the in-process node to target time.

        Note: pending_events are currently ignored for in-process nodes.
        M3fc focuses on device-tier emulation which doesn't receive events
        from other nodes. Future stages can extend this.
        """
        self.current_time_us = target_time_us
        # Note: pending_events handling can be added if needed in future

    def wait_done(self) -> List[Event]:
        """
        Advance node and collect events.

        For in-process nodes, advance() is synchronous (blocks until complete).
        """
        events = self.node.advance(self.current_time_us)

        # Convert node-specific events to coordinator Event format
        coordinator_events = []
        for event in events:
            coordinator_events.append(Event(
                time_us=event.time_us,
                type=event.type,
                src=self.node_id,
                dst=None,  # Device events broadcast to network
                payload={'value': event.value} if hasattr(event, 'value') else None,
                size_bytes=64  # Assume small JSON payload
            ))

        return coordinator_events

    def send_shutdown(self):
        """Shutdown the in-process node."""
        print(f"[Coordinator] Shutting down in-process node: {self.node_id}")
        self.node.stop()


class Coordinator:
    """
    Minimal M0 Coordinator.

    Implements conservative synchronous lockstep:
    - All nodes advance together in fixed time quanta
    - No node advances ahead of others
    - Simple, deterministic, easy to debug

    M1c: Now uses NetworkModel abstraction for message routing.
    """

    def __init__(self, time_quantum_us: int = 1000, network_model=None):
        """
        Initialize coordinator.

        Args:
            time_quantum_us: Time step size in microseconds (default 1ms)
            network_model: NetworkModel instance for routing (default: DirectNetworkModel)
        """
        self.time_quantum_us = time_quantum_us
        self.current_time_us = 0
        self.nodes: Dict[str, NodeAdapter] = {}  # M3fc: Support both socket and in-process nodes
        self.pending_events: Dict[str, List[Event]] = {}  # node_id -> events

        # M1c: Network model for message routing
        if network_model is None:
            from sim.network.direct_model import DirectNetworkModel
            network_model = DirectNetworkModel()
        self.network_model = network_model

    def add_node(self, node_id: str, host: str, port: int):
        """Register a socket-based node (python_model, docker)."""
        self.nodes[node_id] = NodeConnection(node_id, host, port)
        self.pending_events[node_id] = []

    def add_inprocess_node(self, node_id: str, node_instance):
        """
        Register an in-process node (M3fc: renode_inprocess).

        Args:
            node_id: Node identifier
            node_instance: Instance of node class (e.g., RenodeNode)
        """
        self.nodes[node_id] = InProcessNodeAdapter(node_id, node_instance)
        self.pending_events[node_id] = []

    def add_adapter(self, node_id: str, adapter: NodeAdapter):
        """
        Register a custom node adapter (M3h: protocol-based containers).

        Args:
            node_id: Node identifier
            adapter: Custom NodeAdapter instance (e.g., DockerProtocolAdapter)
        """
        self.nodes[node_id] = adapter
        self.pending_events[node_id] = []

    def connect_all(self):
        """Connect to all registered nodes."""
        print("[Coordinator] Connecting to all nodes...")
        for node_id, conn in self.nodes.items():
            conn.connect()

    def initialize_all(self, seed: int = 42):
        """Send INIT to all nodes."""
        print(f"[Coordinator] Initializing all nodes with seed={seed}...")
        for node_id, conn in self.nodes.items():
            config = {"seed": seed}
            conn.send_init(config)
            print(f"[Coordinator] {node_id} initialized and ready")

    def run(self, duration_us: int):
        """
        Run simulation for specified duration.

        Args:
            duration_us: Simulation duration in microseconds
        """
        print(f"[Coordinator] Starting simulation for {duration_us / 1e6:.1f}s (virtual time)")
        print(f"[Coordinator] Time quantum: {self.time_quantum_us}us")

        start_wall_time = time.time()
        step_count = 0

        while self.current_time_us < duration_us:
            target_time_us = min(self.current_time_us + self.time_quantum_us, duration_us)

            # Phase 1: Send ADVANCE to all nodes
            for node_id, conn in self.nodes.items():
                conn.send_advance(target_time_us, self.pending_events[node_id])
                self.pending_events[node_id] = []

            # Phase 2: Wait for all DONE responses and collect events
            all_events = []
            for node_id, conn in self.nodes.items():
                events = conn.wait_done()
                all_events.extend(events)

            # Phase 3: Route cross-node messages via NetworkModel (M1c)
            for event in all_events:
                # Route event through network model
                routed_events = self.network_model.route_message(event)

                # Deliver routed events to destination nodes
                for routed_event in routed_events:
                    if routed_event.dst and routed_event.dst in self.pending_events:
                        self.pending_events[routed_event.dst].append(routed_event)

            # Phase 3b: Collect any delayed events from network (M1c)
            # (For DirectNetworkModel this returns [], but LatencyNetworkModel will use this)
            delayed_events = self.network_model.advance_to(target_time_us)
            for event in delayed_events:
                if event.dst and event.dst in self.pending_events:
                    self.pending_events[event.dst].append(event)

            # Phase 4: Advance time
            self.current_time_us = target_time_us
            step_count += 1

            # Progress report every 1000 steps
            if step_count % 1000 == 0:
                elapsed = time.time() - start_wall_time
                progress = (self.current_time_us / duration_us) * 100
                print(f"[Coordinator] Step {step_count}: t={self.current_time_us/1e6:.2f}s "
                      f"({progress:.1f}%), wall time: {elapsed:.2f}s")

        # Shutdown all nodes
        print("[Coordinator] Simulation complete, shutting down nodes...")
        for node_id, conn in self.nodes.items():
            conn.send_shutdown()

        elapsed = time.time() - start_wall_time
        print(f"[Coordinator] Simulation finished:")
        print(f"  Virtual time: {duration_us / 1e6:.1f}s")
        print(f"  Wall time: {elapsed:.2f}s")
        print(f"  Steps: {step_count}")
        print(f"  Speedup: {(duration_us / 1e6) / elapsed:.1f}x")


def main():
    """
    Run coordinator with scenario configuration.

    Usage:
        python3 coordinator.py                          # M0 hardcoded scenario
        python3 coordinator.py scenarios/m0_baseline.yaml  # YAML scenario (M1b+)
    """
    import sys

    print("="*60)
    print("xEdgeSim Coordinator")
    print("="*60)

    # Check if YAML scenario provided
    if len(sys.argv) > 1:
        # M1b: Load from YAML
        scenario_path = sys.argv[1]
        print(f"[Coordinator] Loading scenario from: {scenario_path}")

        from sim.config.scenario import load_scenario
        scenario = load_scenario(scenario_path)

        # M1d: Create network model based on scenario configuration
        network_model = None
        if scenario.network:
            if scenario.network.model == "direct":
                from sim.network.direct_model import DirectNetworkModel
                network_model = DirectNetworkModel()
                print(f"[Coordinator] Using DirectNetworkModel (zero-latency)")
            elif scenario.network.model == "latency":
                from sim.network.latency_model import LatencyNetworkModel
                network_model = LatencyNetworkModel(scenario.network, scenario.seed)
                print(f"[Coordinator] Using LatencyNetworkModel")
                print(f"  Default latency: {scenario.network.default_latency_us}us")
                print(f"  Default loss rate: {scenario.network.default_loss_rate * 100:.1f}%")
                if scenario.network.links:
                    print(f"  Configured links: {len(scenario.network.links)}")
            else:
                raise ValueError(f"Unknown network model: {scenario.network.model}")
        # If no network section, network_model stays None (Coordinator defaults to DirectNetworkModel)

        # Create coordinator with scenario parameters and network model
        coordinator = Coordinator(
            time_quantum_us=scenario.time_quantum_us,
            network_model=network_model
        )

        # Register nodes from scenario (M3fc: support both socket and in-process nodes)
        for node in scenario.nodes:
            implementation = node.get('implementation', 'python_model')

            if implementation == 'renode_inprocess':
                # M3fc: Create in-process RenodeNode
                from sim.device.renode_node import RenodeNode

                # Extract Renode configuration from node
                renode_config = {
                    'platform': node.get('platform'),
                    'firmware': node.get('firmware'),
                    'monitor_port': node.get('monitor_port', None),  # Auto-assign if not specified
                    'working_dir': node.get('working_dir', f'/tmp/xedgesim/{node["id"]}'),
                }

                # Validate required fields
                if not renode_config['platform']:
                    raise ValueError(f"Node {node['id']}: 'platform' required for renode_inprocess")
                if not renode_config['firmware']:
                    raise ValueError(f"Node {node['id']}: 'firmware' required for renode_inprocess")

                # Create RenodeNode instance
                renode_node = RenodeNode(node['id'], renode_config)
                coordinator.add_inprocess_node(node['id'], renode_node)

                print(f"[Coordinator] Registered in-process Renode node: {node['id']}")
                print(f"  Platform: {renode_config['platform']}")
                print(f"  Firmware: {renode_config['firmware']}")

            else:
                # Socket-based nodes (python_model, docker)
                if 'port' not in node:
                    raise ValueError(f"Node {node['id']}: 'port' required for {implementation}")
                coordinator.add_node(node['id'], "localhost", node['port'])

        # Connect and initialize
        coordinator.connect_all()
        coordinator.initialize_all(seed=scenario.seed)

        # Run simulation
        duration_us = int(scenario.duration_s * 1_000_000)
        coordinator.run(duration_us=duration_us)

    else:
        # M0: Hardcoded configuration (backward compatibility)
        print("[Coordinator] Using hardcoded M0 configuration")
        print("[Coordinator] (Use 'python3 coordinator.py <scenario.yaml>' for YAML config)")

        coordinator = Coordinator(time_quantum_us=1000)  # 1ms steps

        # Register nodes (must be started externally before running coordinator)
        coordinator.add_node("sensor1", "localhost", 5001)
        coordinator.add_node("sensor2", "localhost", 5002)
        coordinator.add_node("sensor3", "localhost", 5003)
        coordinator.add_node("gateway", "localhost", 5004)

        # Connect and initialize
        coordinator.connect_all()
        coordinator.initialize_all(seed=42)

        # Run for 10 seconds of virtual time
        coordinator.run(duration_us=10_000_000)

    print("\n[Coordinator] Done! Check CSV files for metrics.")


if __name__ == "__main__":
    main()
