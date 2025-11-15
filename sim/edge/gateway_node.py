#!/usr/bin/env python3
"""
gateway_node.py - M0 Edge Gateway Model

Represents an edge gateway that:
- Receives sensor data from devices
- Performs simple aggregation
- Writes metrics to CSV

This is a DETERMINISTIC MODEL (not Docker) for M0.
Uses event-driven processing with fixed latencies.
"""

import socket
import json
import heapq
import csv
from dataclasses import dataclass, asdict
from typing import Any, List, Dict


@dataclass
class Event:
    """Internal event."""
    time_us: int
    type: str
    src: str
    dst: str = None
    payload: Any = None
    size_bytes: int = 0

    def __lt__(self, other):
        return self.time_us < other.time_us


class GatewayNode:
    """
    Edge gateway model with deterministic processing.

    Processing model:
    - Receive message: queue for processing
    - Processing latency: 100us (deterministic)
    - Log all received data
    """

    def __init__(self, node_id_or_port, config=None, seed=None):
        """
        Initialize gateway node.

        Supports two modes:
        1. Server mode (M0): GatewayNode(port) - runs as standalone process
        2. Direct mode (M2+): GatewayNode(node_id, config, seed) - Python object

        Args:
            node_id_or_port: Port (int) for server mode, or node_id (str) for direct mode
            config: Configuration dict (direct mode only)
            seed: Random seed (direct mode only)
        """
        # Detect mode based on first argument type
        if isinstance(node_id_or_port, int):
            # Server mode (M0)
            self.port = node_id_or_port
            self.node_id = None
            self.config = {}
            self.seed = None
            self.direct_mode = False
        else:
            # Direct mode (M2+)
            self.port = None
            self.node_id = node_id_or_port
            self.config = config or {}
            self.seed = seed
            self.direct_mode = True

        self.current_time_us = 0
        self.event_queue = []

        # Gateway state
        self.messages_received = 0
        self.messages_processed = 0
        self.sensor_readings: Dict[str, List[float]] = {}  # sensor_id -> readings

        # Metrics
        self.metrics_file = None
        self.metrics_writer = None

        # MQTT support (M2c)
        self.mqtt_client = None
        self.mqtt_messages = []  # Store received MQTT messages

    def start_server(self):
        """Start server and wait for coordinator."""
        if self.direct_mode:
            raise RuntimeError("Cannot start server in direct mode")

        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind(('localhost', self.port))
        server_sock.listen(1)

        print(f"[Gateway] Listening on port {self.port}...")
        conn, addr = server_sock.accept()
        print(f"[Gateway] Coordinator connected from {addr}")

        self.sock_file = conn.makefile('rw')
        self.run_protocol()

        conn.close()
        server_sock.close()

    def run_protocol(self):
        """Run protocol loop."""
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

    def handle_init(self, node_id: str, config_json: str):
        """Handle INIT."""
        self.node_id = node_id
        self.config = json.loads(config_json)

        print(f"[{self.node_id}] Initialized")

        # Open metrics file
        self.metrics_file = open(f"{self.node_id}_metrics.csv", 'w', newline='')
        self.metrics_writer = csv.writer(self.metrics_file)
        self.metrics_writer.writerow(['time_us', 'event_type', 'value', 'details'])

        # Schedule periodic aggregation every 5 seconds
        self.schedule_internal_event(5_000_000, 'AGGREGATE', {})

        self.sock_file.write("READY\n")
        self.sock_file.flush()

    def schedule_internal_event(self, time_us: int, event_type: str, payload: Any):
        """Schedule internal event."""
        event = Event(
            time_us=time_us,
            type=event_type,
            src=self.node_id,
            payload=payload
        )
        heapq.heappush(self.event_queue, event)

    def handle_advance(self, target_time_us: int):
        """Handle ADVANCE."""
        # Read incoming events
        events_json = self.sock_file.readline().strip()
        incoming_events = json.loads(events_json)

        # Add incoming events to queue
        for e in incoming_events:
            event = Event(**e)
            if event.type == 'TRANSMIT':
                # Schedule processing after 100us delay (deterministic)
                heapq.heappush(self.event_queue, Event(
                    time_us=event.time_us + 100,
                    type='PROCESS',
                    src=self.node_id,
                    payload=event.payload
                ))
                self.messages_received += 1

        # Process all events up to target time
        output_events = []
        while self.event_queue and self.event_queue[0].time_us < target_time_us:
            event = heapq.heappop(self.event_queue)
            self.current_time_us = event.time_us

            if event.type == 'PROCESS':
                self.handle_process_event(event)
            elif event.type == 'AGGREGATE':
                self.handle_aggregate_event()
                # Schedule next aggregation
                self.schedule_internal_event(
                    self.current_time_us + 5_000_000,
                    'AGGREGATE',
                    {}
                )

        # Advance to target
        self.current_time_us = target_time_us

        # Send DONE
        self.sock_file.write("DONE\n")
        events_out_json = json.dumps([asdict(e) for e in output_events])
        self.sock_file.write(f"{events_out_json}\n")
        self.sock_file.flush()

    def handle_process_event(self, event: Event):
        """Process received sensor data."""
        payload = event.payload
        sensor_id = payload.get('sample_id', 0)  # Using sample_id as identifier
        temperature = payload.get('temperature', 0)

        # Store reading
        if sensor_id not in self.sensor_readings:
            self.sensor_readings[sensor_id] = []
        self.sensor_readings[sensor_id].append(temperature)

        self.messages_processed += 1

        # Log
        self.metrics_writer.writerow([
            self.current_time_us,
            'process',
            temperature,
            f'sample_{sensor_id}'
        ])

    def handle_aggregate_event(self):
        """Perform periodic aggregation."""
        total_readings = sum(len(readings) for readings in self.sensor_readings.values())

        if total_readings > 0:
            all_temps = [temp for readings in self.sensor_readings.values() for temp in readings]
            avg_temp = sum(all_temps) / len(all_temps)
            min_temp = min(all_temps)
            max_temp = max(all_temps)

            print(f"[{self.node_id}] Aggregation at t={self.current_time_us/1e6:.2f}s: "
                  f"readings={total_readings}, avg={avg_temp:.2f}°C, "
                  f"min={min_temp:.2f}°C, max={max_temp:.2f}°C")

            # Log aggregation
            self.metrics_writer.writerow([
                self.current_time_us,
                'aggregate',
                avg_temp,
                f'count={total_readings},min={min_temp:.2f},max={max_temp:.2f}'
            ])

    def handle_shutdown(self):
        """Handle SHUTDOWN."""
        print(f"[{self.node_id}] Shutdown received")
        print(f"[{self.node_id}] Final stats:")
        print(f"  Messages received: {self.messages_received}")
        print(f"  Messages processed: {self.messages_processed}")

        if self.metrics_file:
            self.metrics_file.close()

    # MQTT methods (M2c)
    def connect_mqtt(self, broker_host, broker_port=1883, topics=None):
        """
        Connect to MQTT broker and subscribe to topics (M2c).

        Args:
            broker_host: MQTT broker hostname/IP
            broker_port: MQTT broker port (default 1883)
            topics: List of topics to subscribe to (default ['sensor/#'])
        """
        try:
            import paho.mqtt.client as mqtt
        except ImportError:
            raise ImportError("paho-mqtt not installed. Install with: pip install paho-mqtt")

        if topics is None:
            topics = ['sensor/#']

        # Create MQTT client
        self.mqtt_client = mqtt.Client(client_id=f"gateway_{self.node_id}")

        # Set message callback
        self.mqtt_client.on_message = self._on_mqtt_message

        # Connect to broker
        self.mqtt_client.connect(broker_host, broker_port, keepalive=60)

        # Subscribe to topics
        for topic in topics:
            self.mqtt_client.subscribe(topic, qos=0)

        # Start background network loop
        self.mqtt_client.loop_start()

    def _on_mqtt_message(self, client, userdata, msg):
        """
        Callback for incoming MQTT messages (M2c).

        Args:
            client: MQTT client instance
            userdata: User data (unused)
            msg: MQTT message
        """
        try:
            # Parse JSON payload
            payload = json.loads(msg.payload.decode('utf-8'))

            # Store message
            self.mqtt_messages.append({
                'topic': msg.topic,
                'payload': payload
            })

        except json.JSONDecodeError as e:
            print(f"[{self.node_id}] Invalid JSON in MQTT message: {e}")

    def disconnect_mqtt(self):
        """Disconnect from MQTT broker (M2c)."""
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            self.mqtt_client = None


def main():
    """Run gateway node."""
    import sys

    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <port>")
        sys.exit(1)

    port = int(sys.argv[1])
    node = GatewayNode(port)
    node.start_server()


if __name__ == "__main__":
    main()
