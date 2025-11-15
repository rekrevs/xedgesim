"""
docker_node.py - M2a Docker Node Implementation

Provides DockerNode class for running edge services in Docker containers.
Manages container lifecycle and provides same interface as Python nodes.
"""

import time

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

    def advance_to(self, target_time_us, incoming_events):
        """
        Advance container execution to target virtual time.

        Implementation (M2a):
        - Sleeps for wall-clock time equivalent to virtual time delta
        - Returns empty events list (no communication yet)

        Future (M2b):
        - Send incoming_events to container via socket
        - Receive outgoing events from container

        Args:
            target_time_us: Target virtual time in microseconds
            incoming_events: List of events to deliver to this node (unused in M2a)

        Returns:
            List of outgoing events (empty in M2a)
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

        # M2a: No events yet (M2b will add socket communication)
        return []

    def shutdown(self):
        """
        Stop and remove Docker container.

        Idempotent: Safe to call multiple times.
        """
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
