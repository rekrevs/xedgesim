#!/usr/bin/env python3
"""
docker_protocol_adapter.py - M3h Docker Protocol Adapter

Coordinator-side adapter for communicating with Docker containers via stdin/stdout protocol.

Design:
- Implements NodeAdapter interface for coordinator integration
- Uses subprocess pipes for stdin/stdout communication
- Sends INIT/ADVANCE/SHUTDOWN protocol messages
- Receives READY/DONE responses with events

This is the coordinator-side counterpart to containers/protocol_adapter.py (container-side).
"""

import subprocess
import json
import time
import sys
import threading
import queue
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add project root to path
_project_root = Path(__file__).parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from sim.harness.coordinator import NodeAdapter, Event


class DockerProtocolAdapter(NodeAdapter):
    """
    Coordinator-side adapter for Docker containers using stdin/stdout protocol.

    This adapter manages communication with a Docker container that implements
    the protocol defined in containers/protocol_adapter.py.

    Protocol:
        Coordinator -> Container:
            INIT <config_json>
            ADVANCE <target_time_us>
            <events_json>
            SHUTDOWN

        Container -> Coordinator:
            READY
            DONE
            <events_json>
    """

    def __init__(self, node_id: str, container_id: str):
        """
        Initialize Docker protocol adapter.

        Args:
            node_id: Logical node ID in simulation
            container_id: Docker container ID
        """
        super().__init__(node_id)
        self.container_id = container_id
        self.process: Optional[subprocess.Popen] = None
        self.connected = False
        self.stdout_queue: queue.Queue = queue.Queue()
        self.stderr_queue: queue.Queue = queue.Queue()
        self.stdout_thread: Optional[threading.Thread] = None
        self.stderr_thread: Optional[threading.Thread] = None

    def connect(self):
        """
        Connect to Docker container via exec with stdin/stdout pipes.

        Uses 'docker exec -i' to attach to running container with stdin pipe.

        Raises:
            RuntimeError: If cannot attach to container
        """
        if self.connected:
            return

        # Start docker exec with stdin/stdout pipes
        # Note: Container must already be running (started by launcher)
        try:
            # Check container is running
            result = subprocess.run(
                ['docker', 'inspect', '-f', '{{.State.Running}}', self.container_id],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0 or result.stdout.strip() != 'true':
                raise RuntimeError(
                    f"Container {self.container_id} is not running"
                )

            # Attach to container with stdin/stdout
            # -i: Keep stdin open
            # -u: Run Python in unbuffered mode (critical for stdin/stdout protocol)
            # Container entrypoint should be running the service with protocol adapter
            #
            # IMPORTANT: We capture stderr separately but read it in a background thread
            # to prevent the stderr buffer from filling (65KB limit) and blocking the process
            self.process = subprocess.Popen(
                ['docker', 'exec', '-i', self.container_id, 'python', '-u', '-m', 'service'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,  # Capture stderr separately
                text=True,
                bufsize=0  # Unbuffered for real-time communication
            )

            # Start background threads to continuously read stdout and stderr
            # This prevents buffers from filling and blocking the process
            # Also solves the select() vs TextIOWrapper buffering issue
            self.stdout_thread = threading.Thread(
                target=self._stdout_reader,
                daemon=True
            )
            self.stdout_thread.start()

            self.stderr_thread = threading.Thread(
                target=self._stderr_reader,
                daemon=True
            )
            self.stderr_thread.start()

            self.connected = True
            print(f"[DockerProtocolAdapter] Connected to container {self.container_id} for node {self.node_id}")

        except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
            raise RuntimeError(
                f"Failed to connect to container {self.container_id}: {e}"
            )

    def send_init(self, config: Dict[str, Any]):
        """
        Send INIT message to container.

        Protocol:
            -> INIT <config_json>
            <- READY

        Args:
            config: Initialization configuration including seed

        Raises:
            RuntimeError: If not connected or container doesn't respond READY
        """
        if not self.connected:
            raise RuntimeError(f"Not connected to container {self.container_id}")

        # Send INIT with config
        config_json = json.dumps(config)
        self._write_line(f"INIT {config_json}")

        # Wait for READY response
        response = self._read_line()
        if response != "READY":
            stderr_output = self._get_stderr()
            raise RuntimeError(
                f"Expected READY from container {self.node_id}, got: {response}\n"
                f"Container stderr: {stderr_output}"
            )

        print(f"[DockerProtocolAdapter] {self.node_id} initialized (READY)")

    def send_advance(self, target_time_us: int, pending_events: List[Event]):
        """
        Send ADVANCE message to container.

        Protocol:
            -> ADVANCE <target_time_us>
            -> <events_json>

        Args:
            target_time_us: Target virtual time in microseconds
            pending_events: Events to deliver to this node
        """
        if not self.connected:
            raise RuntimeError(f"Not connected to container {self.container_id}")

        # Send ADVANCE with target time
        advance_cmd = f"ADVANCE {target_time_us}"
        print(f"[DockerProtocolAdapter] Sending: {advance_cmd}")
        self._write_line(advance_cmd)

        # Send events JSON
        # Convert Event dataclass to dict
        events_data = []
        for event in pending_events:
            events_data.append({
                'timestamp_us': event.time_us,
                'event_type': event.type,
                'source': event.src,
                'destination': event.dst,
                'payload': event.payload
            })

        events_json = json.dumps(events_data)
        print(f"[DockerProtocolAdapter] Sending events: {events_json[:100]}{'...' if len(events_json) > 100 else ''}")
        self._write_line(events_json)

    def wait_done(self) -> List[Event]:
        """
        Wait for DONE response and collect output events.

        Protocol:
            <- DONE
            <- <events_json>

        Returns:
            List of events generated by container

        Raises:
            RuntimeError: If container doesn't respond DONE
        """
        if not self.connected:
            raise RuntimeError(f"Not connected to container {self.container_id}")

        # Wait for DONE response
        print(f"[DockerProtocolAdapter] Waiting for DONE response...")
        response = self._read_line(timeout=30.0)  # 30s timeout for container processing
        print(f"[DockerProtocolAdapter] Received: {response}")

        if response != "DONE":
            stderr_output = self._get_stderr()
            raise RuntimeError(
                f"Expected DONE from container {self.node_id}, got: {response}\n"
                f"Container stderr: {stderr_output}"
            )

        # Read events JSON
        print(f"[DockerProtocolAdapter] Waiting for events JSON...")
        events_json = self._read_line()
        print(f"[DockerProtocolAdapter] Received events: {events_json[:100]}{'...' if len(events_json) > 100 else ''}")
        events_data = json.loads(events_json)

        # Convert to Event objects
        events = []
        for e in events_data:
            # Map protocol event format to coordinator Event format
            events.append(Event(
                time_us=e.get('timestamp_us', 0),
                type=e.get('event_type', 'unknown'),
                src=e.get('source', self.node_id),
                dst=e.get('destination'),
                payload=e.get('payload')
            ))

        print(f"[DockerProtocolAdapter] Received {len(events)} events from container")
        return events

    def send_shutdown(self):
        """
        Send SHUTDOWN message to container.

        Protocol:
            -> SHUTDOWN

        Container process will exit after processing shutdown.
        """
        if not self.connected:
            return

        try:
            self._write_line("SHUTDOWN")

            # Wait for process to exit (with timeout)
            self.process.wait(timeout=5)

        except subprocess.TimeoutExpired:
            print(f"[DockerProtocolAdapter] WARNING: Container {self.node_id} did not exit cleanly, terminating...")
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()

        finally:
            self.connected = False
            print(f"[DockerProtocolAdapter] {self.node_id} shutdown complete")

    def _write_line(self, line: str):
        """
        Write a line to container stdin.

        Args:
            line: Line to write (newline will be added)
        """
        try:
            self.process.stdin.write(line + '\n')
            self.process.stdin.flush()
        except BrokenPipeError:
            raise RuntimeError(
                f"Container {self.node_id} stdin closed unexpectedly"
            )

    def _stdout_reader(self):
        """
        Background thread to continuously read stdout.

        This solves the select() vs TextIOWrapper buffering issue where
        readline() pre-buffers multiple lines into Python's internal buffer,
        making them invisible to select().
        """
        try:
            while self.process and self.process.poll() is None:
                line = self.process.stdout.readline()
                if not line:
                    break
                # Store stdout lines in queue
                self.stdout_queue.put(line.rstrip('\n'))
        except:
            pass  # Thread will exit when process dies

    def _stderr_reader(self):
        """
        Background thread to continuously read stderr.

        This prevents the stderr buffer from filling (65KB limit) which would
        block the child process when it tries to write to stderr.
        """
        try:
            while self.process and self.process.poll() is None:
                line = self.process.stderr.readline()
                if not line:
                    break
                # Store stderr lines in queue for debugging
                self.stderr_queue.put(line.rstrip('\n'))
        except:
            pass  # Thread will exit when process dies

    def _read_line(self, timeout: float = 10.0) -> str:
        """
        Read a line from container stdout via queue.

        The stdout is read by a background thread to avoid the select() vs
        TextIOWrapper buffering issue where readline() pre-buffers multiple
        lines making them invisible to select().

        Args:
            timeout: Maximum time to wait for line

        Returns:
            Line from stdout (already stripped)

        Raises:
            RuntimeError: If timeout or read error
        """
        try:
            line = self.stdout_queue.get(timeout=timeout)
            return line
        except queue.Empty:
            # Check if process died
            if self.process.poll() is not None:
                stderr_output = self._get_stderr()
                raise RuntimeError(
                    f"Container {self.node_id} process exited unexpectedly "
                    f"(exit code {self.process.returncode})\n"
                    f"Container stderr: {stderr_output}"
                )

            # Timeout
            stderr_output = self._get_stderr()
            raise RuntimeError(
                f"Timeout waiting for response from container {self.node_id} after {timeout:.1f}s\n"
                f"Container stderr: {stderr_output}"
            )

    def _get_stderr(self) -> str:
        """
        Get all stderr output collected so far.

        Returns:
            Stderr output as string
        """
        lines = []
        while not self.stderr_queue.empty():
            try:
                lines.append(self.stderr_queue.get_nowait())
            except queue.Empty:
                break
        return '\n'.join(lines) if lines else "(no stderr output)"

