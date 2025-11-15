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
            # Container entrypoint should be running the service with protocol adapter
            self.process = subprocess.Popen(
                ['docker', 'exec', '-i', self.container_id, 'python', '-m', 'service'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1  # Line buffered
            )

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
            stderr_output = self._read_stderr()
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
        self._write_line(f"ADVANCE {target_time_us}")

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
        response = self._read_line(timeout=30.0)  # 30s timeout for container processing
        if response != "DONE":
            stderr_output = self._read_stderr()
            raise RuntimeError(
                f"Expected DONE from container {self.node_id}, got: {response}\n"
                f"Container stderr: {stderr_output}"
            )

        # Read events JSON
        events_json = self._read_line()
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
            stderr_output = self._read_stderr()
            raise RuntimeError(
                f"Container {self.node_id} stdin closed unexpectedly\n"
                f"Container stderr: {stderr_output}"
            )

    def _read_line(self, timeout: float = 10.0) -> str:
        """
        Read a line from container stdout.

        Args:
            timeout: Maximum time to wait for line

        Returns:
            Line from stdout (stripped)

        Raises:
            RuntimeError: If timeout or read error
        """
        import select

        start_time = time.time()

        while time.time() - start_time < timeout:
            # Check if data available (non-blocking)
            ready, _, _ = select.select([self.process.stdout], [], [], 0.1)

            if ready:
                line = self.process.stdout.readline()
                if not line:
                    # EOF
                    stderr_output = self._read_stderr()
                    raise RuntimeError(
                        f"Container {self.node_id} stdout closed unexpectedly\n"
                        f"Container stderr: {stderr_output}"
                    )
                return line.strip()

            # Check if process died
            if self.process.poll() is not None:
                stderr_output = self._read_stderr()
                raise RuntimeError(
                    f"Container {self.node_id} process exited unexpectedly "
                    f"(exit code {self.process.returncode})\n"
                    f"Container stderr: {stderr_output}"
                )

        # Timeout
        stderr_output = self._read_stderr()
        raise RuntimeError(
            f"Timeout waiting for response from container {self.node_id}\n"
            f"Container stderr: {stderr_output}"
        )

    def _read_stderr(self) -> str:
        """
        Read available stderr output from container (non-blocking).

        Returns:
            Stderr output if available, else empty string
        """
        import select

        stderr_lines = []

        try:
            # Non-blocking check for stderr
            while True:
                ready, _, _ = select.select([self.process.stderr], [], [], 0)
                if not ready:
                    break

                line = self.process.stderr.readline()
                if not line:
                    break

                stderr_lines.append(line.strip())
        except:
            pass

        return '\n'.join(stderr_lines) if stderr_lines else "(no stderr output)"
