#!/usr/bin/env python3
"""
protocol_adapter.py - Coordinator Protocol Adapter for Containers (M3h)

This module provides a reusable adapter for Docker containers to communicate
with the xEdgeSim coordinator using virtual time instead of wall-clock time.

Protocol:
    Coordinator → Container:
        INIT <config_json>          - Initialize with configuration
        ADVANCE <target_time_us> <events_json>  - Advance to target time, process events
        SHUTDOWN                     - Clean shutdown

    Container → Coordinator:
        READY                        - Ready after initialization
        DONE <events_json>          - Completed advancement, return events

Design:
    - Reads from stdin (JSON messages from coordinator)
    - Writes to stdout (responses to coordinator)
    - Service callback processes events in virtual time
    - No wall-clock dependencies (no time.sleep!)
"""

import sys
import json
import logging
from typing import Dict, List, Any, Callable
from dataclasses import dataclass, field

# Configure logging to stderr (stdout is for protocol)
logging.basicConfig(
    level=logging.INFO,
    format='[%(name)s] %(levelname)s: %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger('protocol_adapter')


@dataclass
class Event:
    """Event in virtual time."""
    timestamp_us: int
    event_type: str
    source: str = ""
    destination: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'timestamp_us': self.timestamp_us,
            'event_type': self.event_type,
            'source': self.source,
            'destination': self.destination,
            'payload': self.payload
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Event':
        """Create Event from dictionary."""
        return Event(
            timestamp_us=data['timestamp_us'],
            event_type=data['event_type'],
            source=data.get('source', ''),
            destination=data.get('destination', ''),
            payload=data.get('payload', {})
        )


# Type alias for service callback
ServiceCallback = Callable[[int, int, List[Event]], List[Event]]


class CoordinatorProtocolAdapter:
    """
    Adapter for containers to communicate with coordinator via stdin/stdout.

    The service provides a callback that processes events:
        callback(current_time_us, target_time_us, input_events) -> output_events

    The adapter handles all protocol details, so services can focus on
    processing events in virtual time.

    Usage:
        def my_service(current_time, target_time, events):
            # Process events
            output_events = []
            for event in events:
                # Handle event
                result = process(event)
                output_events.append(Event(...))
            return output_events

        adapter = CoordinatorProtocolAdapter(my_service)
        adapter.run()  # Blocks until SHUTDOWN
    """

    def __init__(self, service_callback: ServiceCallback, node_id: str = "container"):
        """
        Initialize protocol adapter.

        Args:
            service_callback: Function to process events in virtual time
            node_id: Node identifier for logging
        """
        self.service_callback = service_callback
        self.node_id = node_id
        self.current_time_us = 0
        self.running = False
        self.config: Dict[str, Any] = {}

        logger.info(f"Protocol adapter initialized for {node_id}")

    def run(self):
        """
        Main event loop - reads from stdin, processes, writes to stdout.

        Blocks until SHUTDOWN message received.
        """
        self.running = True
        logger.info("Starting protocol event loop")

        try:
            while self.running:
                # Read command from stdin
                line = sys.stdin.readline()
                if not line:
                    # EOF - coordinator closed connection
                    logger.info("EOF received, shutting down")
                    break

                line = line.strip()
                if not line:
                    continue

                # Parse and process command
                try:
                    self._process_command(line)
                except Exception as e:
                    logger.error(f"Error processing command: {e}")
                    # Send error response
                    self._write_line(f"ERROR {str(e)}")
                    break

        except KeyboardInterrupt:
            logger.info("Interrupted, shutting down")
        except Exception as e:
            logger.error(f"Fatal error in event loop: {e}")
            raise
        finally:
            logger.info("Protocol event loop terminated")

    def _process_command(self, line: str):
        """
        Process a command from coordinator.

        Args:
            line: Command line from stdin
        """
        parts = line.split(maxsplit=1)
        if not parts:
            return

        command = parts[0]

        if command == "INIT":
            # INIT <config_json>
            config_json = parts[1] if len(parts) > 1 else "{}"
            self._handle_init(config_json)

        elif command == "ADVANCE":
            # ADVANCE <target_time_us> <events_json>
            if len(parts) < 2:
                raise ValueError("ADVANCE requires target_time_us")

            # Parse: ADVANCE 1000 [events...]
            # Or: ADVANCE 1000\n[events...]
            advance_parts = parts[1].split(maxsplit=1)
            target_time_us = int(advance_parts[0])

            # Events might be on same line or next line
            if len(advance_parts) > 1:
                events_json = advance_parts[1]
            else:
                # Read next line for events
                events_line = sys.stdin.readline().strip()
                events_json = events_line if events_line else "[]"

            self._handle_advance(target_time_us, events_json)

        elif command == "SHUTDOWN":
            self._handle_shutdown()

        else:
            raise ValueError(f"Unknown command: {command}")

    def _handle_init(self, config_json: str):
        """
        Handle INIT command.

        Args:
            config_json: Configuration as JSON string
        """
        logger.info(f"Received INIT")

        # Parse config
        self.config = json.loads(config_json)
        logger.debug(f"Configuration: {self.config}")

        # Reset state
        self.current_time_us = 0

        # Service-specific initialization can be done via config
        # (e.g., load model path from config)

        # Send READY response
        self._write_line("READY")
        logger.info("Initialization complete, sent READY")

    def _handle_advance(self, target_time_us: int, events_json: str):
        """
        Handle ADVANCE command.

        Args:
            target_time_us: Target virtual time in microseconds
            events_json: Input events as JSON string
        """
        logger.debug(f"Received ADVANCE to {target_time_us}us")

        # Parse events
        try:
            events_data = json.loads(events_json)
            input_events = [Event.from_dict(e) for e in events_data]
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse events JSON: {e}")
            logger.error(f"Events JSON: {events_json}")
            input_events = []

        logger.debug(f"Processing {len(input_events)} input events")

        # Call service callback with virtual time
        try:
            output_events = self.service_callback(
                self.current_time_us,
                target_time_us,
                input_events
            )
        except Exception as e:
            logger.error(f"Service callback failed: {e}")
            output_events = []

        # Update current time
        self.current_time_us = target_time_us

        # Send DONE response with output events
        events_dict = [e.to_dict() for e in output_events]
        self._write_line("DONE")
        self._write_line(json.dumps(events_dict))

        logger.debug(f"Sent DONE with {len(output_events)} output events")

    def _handle_shutdown(self):
        """Handle SHUTDOWN command."""
        logger.info("Received SHUTDOWN")
        self.running = False
        # No response needed for SHUTDOWN

    def _write_line(self, line: str):
        """
        Write a line to stdout and flush.

        Args:
            line: Line to write
        """
        sys.stdout.write(line + '\n')
        sys.stdout.flush()


def run_service(service_callback: ServiceCallback, node_id: str = "container"):
    """
    Convenience function to run a service with the protocol adapter.

    Args:
        service_callback: Function to process events
        node_id: Node identifier for logging

    Example:
        def my_service(current_time, target_time, events):
            # Process events
            return output_events

        if __name__ == '__main__':
            run_service(my_service, node_id="my-container")
    """
    adapter = CoordinatorProtocolAdapter(service_callback, node_id)
    adapter.run()
