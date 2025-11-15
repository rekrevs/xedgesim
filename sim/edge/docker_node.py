"""
docker_node.py - M2a/M2b Docker Node Implementation

Provides DockerNode class for running edge services in Docker containers.
Manages container lifecycle and socket communication.

M2a: Container lifecycle (create, start, stop, remove)
M2b: Socket communication (send/receive events via TCP)
"""

import time
import socket
import json

# Optional docker import (allows module to be imported even without Docker installed)
try:
    import docker
    from docker.errors import NotFound, ImageNotFound, APIError
    DOCKER_AVAILABLE = True
except ImportError:
    docker = None
    NotFound = Exception
    ImageNotFound = Exception
    APIError = Exception
    DOCKER_AVAILABLE = False


class DockerNode:
    """
    Docker-based edge node for simulation.

    Manages Docker container lifecycle (create, start, stop, remove) and
    implements same interface as Python simulation nodes (SensorNode, GatewayNode).

    Design:
    - Container runs in wall-clock time (not virtual time)
    - advance_to() sleeps for equivalent wall-clock duration
    - Non-deterministic (container execution varies)
    - Acceptable per architecture.md Section 5: Statistical reproducibility for edge tier

    M2a scope: Basic lifecycle management only
    M2b will add: Socket communication with container
    """

    def __init__(self, node_id, config, seed):
        """
        Initialize Docker node.

        Args:
            node_id: Unique identifier for this node (used in container name)
            config: Dict with Docker configuration:
                - image: Docker image to use (e.g., "alpine:latest")
                - command: Command to run in container (e.g., "sleep 60")
                - ports: Dict of port mappings (optional, for M2b)
                - environment: Dict of environment variables (optional)
                - volumes: Dict of volume mounts (optional, for M2c)
            seed: Random seed (unused for Docker, kept for interface compatibility)
        """
        self.node_id = node_id
        self.config = config
        self.seed = seed
        self.current_time_us = 0

        self.container = None
        self.client = None
        self.sock = None  # M2b: Socket connection to container

    def start(self):
        """
        Create and start Docker container.

        Raises:
            RuntimeError: If Docker is not available
            docker.errors.ImageNotFound: If image doesn't exist
            docker.errors.APIError: If Docker daemon error
        """
        if not DOCKER_AVAILABLE:
            raise RuntimeError(
                "Docker is not installed. Install Docker to use DockerNode: "
                "https://docs.docker.com/get-docker/"
            )

        self.client = docker.from_env()

        # Pull image if not present (may take time on first run)
        try:
            self.client.images.get(self.config["image"])
        except ImageNotFound:
            print(f"Pulling image {self.config['image']}...")
            self.client.images.pull(self.config["image"])

        # Create container with xedgesim labels
        container_name = f"xedgesim-{self.node_id}"

        self.container = self.client.containers.run(
            image=self.config["image"],
            command=self.config.get("command", None),
            detach=True,
            name=container_name,
            labels={
                "xedgesim": "true",
                "xedgesim_node_id": self.node_id
            },
            environment=self.config.get("environment", {}),
            # Ports and volumes will be added in M2b/M2c
            ports=self.config.get("ports", {}),
            # Auto-remove disabled so we can inspect after shutdown if needed
            auto_remove=False,
        )

    def wait_for_ready(self, timeout_s=10):
        """
        Wait for container to be running.

        Args:
            timeout_s: Maximum time to wait in seconds

        Returns:
            True if container is running

        Raises:
            TimeoutError: If container not running after timeout
        """
        start_time = time.time()

        while time.time() - start_time < timeout_s:
            self.container.reload()

            if self.container.status == 'running':
                return True

            if self.container.status in ['exited', 'dead']:
                raise RuntimeError(
                    f"Container {self.node_id} failed to start: status={self.container.status}"
                )

            time.sleep(0.1)

        raise TimeoutError(
            f"Container {self.node_id} not ready after {timeout_s}s "
            f"(status={self.container.status})"
        )

    def connect_to_socket(self, timeout_s=10):
        """
        Connect to container's TCP socket (M2b).

        Args:
            timeout_s: Maximum time to wait for connection

        Raises:
            RuntimeError: If cannot connect to socket
        """
        if self.sock is not None:
            return  # Already connected

        # Get container IP address
        self.container.reload()
        container_ip = self.container.attrs['NetworkSettings']['IPAddress']
        socket_port = self.config.get('socket_port', 5000)

        # Retry connection (container service may take time to start)
        start_time = time.time()
        last_error = None

        while time.time() - start_time < timeout_s:
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.settimeout(2.0)  # 2s timeout for socket operations
                self.sock.connect((container_ip, socket_port))
                print(f"Connected to container {self.node_id} at {container_ip}:{socket_port}")
                return
            except (ConnectionRefusedError, OSError) as e:
                last_error = e
                if self.sock:
                    self.sock.close()
                    self.sock = None
                time.sleep(0.5)

        raise RuntimeError(
            f"Could not connect to container {self.node_id} socket at "
            f"{container_ip}:{socket_port} after {timeout_s}s: {last_error}"
        )

    def advance_to(self, target_time_us, incoming_events):
        """
        Advance container execution to target virtual time.

        Implementation (M2b):
        - Sleeps for wall-clock time equivalent to virtual time delta
        - Sends incoming_events to container via socket
        - Receives outgoing events from container via socket

        Args:
            target_time_us: Target virtual time in microseconds
            incoming_events: List of events to deliver to this node

        Returns:
            List of outgoing events from container
        """
        # Calculate time delta
        delta_us = target_time_us - self.current_time_us

        if delta_us < 0:
            raise ValueError(
                f"Cannot advance backwards: current={self.current_time_us}, "
                f"target={target_time_us}"
            )

        # Sleep for wall-clock equivalent
        if delta_us > 0:
            time.sleep(delta_us / 1_000_000)

        # Update current time
        self.current_time_us = target_time_us

        # M2b: Send/receive events via socket (if connected)
        if self.sock is not None:
            # Send incoming events to container
            for event in incoming_events:
                self._send_event(event)

            # Receive outgoing events from container
            return self._receive_events()
        else:
            # No socket connection (M2a behavior)
            return []

    def _send_event(self, event):
        """
        Send event to container via socket (M2b).

        Args:
            event: Event dict to send
        """
        try:
            msg = json.dumps(event) + '\n'
            self.sock.sendall(msg.encode('utf-8'))
        except (BrokenPipeError, OSError) as e:
            print(f"Error sending event to container {self.node_id}: {e}")

    def _receive_events(self):
        """
        Receive events from container via socket (M2b).

        Uses non-blocking read to get all available events.

        Returns:
            List of event dicts
        """
        events = []

        try:
            # Set non-blocking mode
            self.sock.setblocking(False)

            buffer = ""
            while True:
                try:
                    data = self.sock.recv(4096).decode('utf-8')
                    if not data:
                        break
                    buffer += data
                except BlockingIOError:
                    # No more data available
                    break

            # Parse line-delimited JSON
            for line in buffer.strip().split('\n'):
                if line:
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError as e:
                        print(f"Invalid JSON from container {self.node_id}: {line}: {e}")

        finally:
            # Restore blocking mode
            self.sock.setblocking(True)

        return events

    def shutdown(self):
        """
        Stop and remove Docker container.

        Idempotent: Safe to call multiple times.
        """
        # M2b: Close socket first
        if self.sock is not None:
            try:
                self.sock.close()
            except:
                pass
            self.sock = None

        if self.container is None:
            return

        try:
            # Stop container (1 second timeout)
            self.container.stop(timeout=1)
        except (NotFound, APIError):
            # Already stopped or removed
            pass

        try:
            # Remove container
            self.container.remove(force=True)
        except (NotFound, APIError):
            # Already removed
            pass

        self.container = None


def cleanup_xedgesim_containers(client=None):
    """
    Remove all xedgesim containers (running or stopped).

    Utility function for cleanup after tests or crashes.

    Args:
        client: Docker client (creates new one if None)
    """
    if client is None:
        client = docker.from_env()

    # Find all containers with xedgesim label
    containers = client.containers.list(
        all=True,  # Include stopped containers
        filters={"label": "xedgesim=true"}
    )

    # Stop and remove each container
    for container in containers:
        try:
            container.stop(timeout=1)
        except (NotFound, APIError):
            pass

        try:
            container.remove(force=True)
        except (NotFound, APIError):
            pass
