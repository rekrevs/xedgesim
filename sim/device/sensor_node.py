#!/usr/bin/env python3
"""
sensor_node.py - M0 Simulated Sensor Node

Represents a simple IoT sensor device that:
- Periodically samples temperature (every 1 second)
- Transmits readings to gateway
- Uses deterministic random number generation
- Maintains virtual time synchronization

This is a MODEL of a sensor, not actual Renode emulation (that's M1+).
For M0, we just want to prove the coordination protocol works.
"""

import socket
import json
import random
import heapq
import csv
from dataclasses import dataclass, asdict
from typing import Any, List


@dataclass
class Event:
    """Internal event for the node's event queue."""
    time_us: int
    type: str
    src: str
    dst: str = None
    payload: Any = None
    size_bytes: int = 0

    def __lt__(self, other):
        """For heapq ordering."""
        return self.time_us < other.time_us


class SensorNode:
    """
    Simulated sensor node with deterministic behavior.

    Implements the xEdgeSim node protocol:
    - INIT: Initialize with node_id and config
    - ADVANCE: Advance to target time, return events
    - SHUTDOWN: Clean up
    """

    def __init__(self, port: int):
        """
        Initialize sensor node server.

        Args:
            port: Port to listen on for coordinator connection
        """
        self.port = port
        self.node_id = None
        self.config = {}
        self.current_time_us = 0
        self.event_queue = []
        self.rng = None

        # Metrics
        self.samples_taken = 0
        self.messages_sent = 0
        self.metrics_file = None
        self.metrics_writer = None

    def start_server(self):
        """Start server and wait for coordinator connection."""
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind(('localhost', self.port))
        server_sock.listen(1)

        print(f"[SensorNode] Listening on port {self.port}...")
        conn, addr = server_sock.accept()
        print(f"[SensorNode] Coordinator connected from {addr}")

        self.sock_file = conn.makefile('rw')
        self.run_protocol()

        conn.close()
        server_sock.close()

    def run_protocol(self):
        """Run the node protocol loop."""
        while True:
            line = self.sock_file.readline().strip()
            if not line:
                break

            parts = line.split(' ', 2)
            cmd = parts[0]

            if cmd == 'INIT':
                self.handle_init(parts[1], parts[2])
            elif cmd == 'ADVANCE':
                self.handle_advance(int(parts[1]))
            elif cmd == 'SHUTDOWN':
                self.handle_shutdown()
                break
            else:
                raise ValueError(f"Unknown command: {cmd}")

    def handle_init(self, node_id: str, config_json: str):
        """Handle INIT message."""
        self.node_id = node_id
        self.config = json.loads(config_json)

        # Initialize deterministic RNG
        # IMPORTANT: Use deterministic hash (hashlib) not hash() which is randomized
        import hashlib
        seed = self.config.get('seed', 0)
        hash_input = f"{self.node_id}_{seed}".encode('utf-8')
        hash_digest = hashlib.sha256(hash_input).digest()
        rng_seed = int.from_bytes(hash_digest[:8], 'big')
        self.rng = random.Random(rng_seed)

        print(f"[{self.node_id}] Initialized with seed={seed} (rng_seed={rng_seed})")

        # Open metrics CSV file
        self.metrics_file = open(f"{self.node_id}_metrics.csv", 'w', newline='')
        self.metrics_writer = csv.writer(self.metrics_file)
        self.metrics_writer.writerow(['time_us', 'event_type', 'value'])

        # Schedule initial sampling event at t=1s
        self.schedule_event(1_000_000, 'SAMPLE', None, None, {})

        # Send READY
        self.sock_file.write("READY\n")
        self.sock_file.flush()

    def schedule_event(self, time_us: int, event_type: str, dst: str, payload: Any, extra: dict):
        """Schedule an internal event."""
        event = Event(
            time_us=time_us,
            type=event_type,
            src=self.node_id,
            dst=dst,
            payload=payload,
            size_bytes=extra.get('size_bytes', 0)
        )
        heapq.heappush(self.event_queue, event)

    def handle_advance(self, target_time_us: int):
        """Handle ADVANCE message."""
        # Read incoming events from coordinator
        events_json = self.sock_file.readline().strip()
        incoming_events = json.loads(events_json)

        # Add incoming events to queue
        for e in incoming_events:
            heapq.heappush(self.event_queue, Event(**e))

        # Process all events up to target time
        output_events = []
        while self.event_queue and self.event_queue[0].time_us < target_time_us:
            event = heapq.heappop(self.event_queue)
            self.current_time_us = event.time_us

            if event.type == 'SAMPLE':
                output = self.handle_sample_event()
                if output:
                    output_events.extend(output)

        # Advance to target time
        self.current_time_us = target_time_us

        # Send DONE + events
        self.sock_file.write("DONE\n")
        events_out_json = json.dumps([asdict(e) for e in output_events])
        self.sock_file.write(f"{events_out_json}\n")
        self.sock_file.flush()

    def handle_sample_event(self):
        """Handle periodic sampling."""
        # Sample temperature with deterministic randomness
        temperature = self.rng.gauss(20.0, 2.0)  # Mean=20°C, StdDev=2°C
        self.samples_taken += 1

        # Log metric
        self.metrics_writer.writerow([self.current_time_us, 'sample', temperature])

        # Schedule next sample in 1 second
        self.schedule_event(
            self.current_time_us + 1_000_000,  # +1s
            'SAMPLE',
            None,
            None,
            {}
        )

        # Transmit to gateway
        self.messages_sent += 1
        transmit_event = Event(
            time_us=self.current_time_us,
            type='TRANSMIT',
            src=self.node_id,
            dst='gateway',
            payload={
                'temperature': temperature,
                'unit': 'C',
                'sample_id': self.samples_taken
            },
            size_bytes=64  # Simulated packet size
        )

        # Log transmission
        self.metrics_writer.writerow([self.current_time_us, 'transmit', self.messages_sent])

        return [transmit_event]

    def handle_shutdown(self):
        """Handle SHUTDOWN message."""
        print(f"[{self.node_id}] Shutdown received")
        print(f"[{self.node_id}] Final stats:")
        print(f"  Samples taken: {self.samples_taken}")
        print(f"  Messages sent: {self.messages_sent}")

        if self.metrics_file:
            self.metrics_file.close()


def main():
    """Run sensor node server."""
    import sys

    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <port>")
        sys.exit(1)

    port = int(sys.argv[1])
    node = SensorNode(port)
    node.start_server()


if __name__ == "__main__":
    main()
