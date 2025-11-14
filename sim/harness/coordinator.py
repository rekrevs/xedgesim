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
from typing import Dict, List, Any
from dataclasses import dataclass, asdict


@dataclass
class Event:
    """Simulation event."""
    time_us: int
    type: str
    src: str
    dst: str = None
    payload: Any = None
    size_bytes: int = 0


class NodeConnection:
    """Represents a connection to a simulated node."""

    def __init__(self, node_id: str, host: str, port: int):
        self.node_id = node_id
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


class Coordinator:
    """
    Minimal M0 Coordinator.

    Implements conservative synchronous lockstep:
    - All nodes advance together in fixed time quanta
    - No node advances ahead of others
    - Simple, deterministic, easy to debug
    """

    def __init__(self, time_quantum_us: int = 1000):
        """
        Initialize coordinator.

        Args:
            time_quantum_us: Time step size in microseconds (default 1ms)
        """
        self.time_quantum_us = time_quantum_us
        self.current_time_us = 0
        self.nodes: Dict[str, NodeConnection] = {}
        self.pending_events: Dict[str, List[Event]] = {}  # node_id -> events

    def add_node(self, node_id: str, host: str, port: int):
        """Register a node."""
        self.nodes[node_id] = NodeConnection(node_id, host, port)
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

            # Phase 3: Route cross-node messages
            for event in all_events:
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
    """M0 hardcoded scenario: 3 sensors + 1 gateway."""

    print("="*60)
    print("xEdgeSim M0 Minimal Proof-of-Concept")
    print("="*60)

    # Hardcoded configuration (no YAML parsing for M0)
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
