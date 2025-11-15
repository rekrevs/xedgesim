#!/usr/bin/env python3
"""
echo_service.py - Simple Echo Service for Testing Protocol Adapter

This service demonstrates the container protocol adapter by echoing input
events back to the coordinator with a prefix.

Protocol:
    - Receives events via ADVANCE messages
    - Echoes each event back with "echo_" prefix on event type
    - Demonstrates event-driven virtual time (no wall-clock sleep)

Usage:
    # Run standalone (for testing):
    python3 -m containers.examples.echo_service

    # In Docker container:
    python3 -m containers.examples.echo_service

Example:
    Input event:  {type: "SAMPLE", timestamp_us: 1000000, source: "sensor1"}
    Output event: {type: "echo_SAMPLE", timestamp_us: 1000000, source: "echo_service"}
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from containers.protocol_adapter import CoordinatorProtocolAdapter, Event
from typing import List


def echo_service(current_time_us: int, target_time_us: int, events: List[Event]) -> List[Event]:
    """
    Echo service callback.

    Args:
        current_time_us: Current virtual time in microseconds
        target_time_us: Target virtual time to advance to
        events: Input events to process

    Returns:
        List of output events (echoed input events)
    """
    output_events = []

    for event in events:
        # Echo the event back with modified type
        echo_event = Event(
            timestamp_us=target_time_us,  # Echo at current time
            event_type=f"echo_{event.event_type}",
            source="echo_service",
            destination=event.source,  # Send back to original source
            payload={
                "original_type": event.event_type,
                "original_source": event.source,
                "original_payload": event.payload,
                "echo_time": target_time_us
            }
        )
        output_events.append(echo_event)

    return output_events


def main():
    """Main entry point for echo service."""
    # Create adapter with echo service callback
    adapter = CoordinatorProtocolAdapter(
        service_callback=echo_service,
        node_id="echo_service"
    )

    # Run protocol loop (blocks until SHUTDOWN)
    adapter.run()


if __name__ == "__main__":
    main()
