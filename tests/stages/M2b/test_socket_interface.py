#!/usr/bin/env python3
"""
test_socket_interface.py - M2b Tests for Socket Communication Interface

Tests socket communication methods (without requiring actual Docker).
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from sim.edge.docker_node import DockerNode


def test_docker_node_has_socket_methods():
    """Test DockerNode has socket communication methods."""
    config = {"image": "alpine:latest"}
    node = DockerNode("test1", config, seed=42)

    # M2b methods should exist
    assert hasattr(node, "connect_to_socket")
    assert hasattr(node, "_send_event")
    assert hasattr(node, "_receive_events")

    # Socket attribute should be initialized to None
    assert node.sock is None

    print("✓ test_docker_node_has_socket_methods PASSED")
    return True


def test_advance_to_with_no_socket():
    """Test advance_to() works without socket connection (M2a behavior)."""
    config = {"image": "alpine:latest"}
    node = DockerNode("test1", config, seed=42)

    # advance_to() should work even without socket
    events = node.advance_to(1000, incoming_events=[])

    assert events == []  # No socket, no events
    assert node.current_time_us == 1000

    print("✓ test_advance_to_with_no_socket PASSED")
    return True


def test_advance_to_updates_time():
    """Test advance_to() updates current_time_us correctly."""
    config = {"image": "alpine:latest"}
    node = DockerNode("test1", config, seed=42)

    # Multiple advances
    node.advance_to(1000, [])
    assert node.current_time_us == 1000

    node.advance_to(5000, [])
    assert node.current_time_us == 5000

    node.advance_to(10000, [])
    assert node.current_time_us == 10000

    print("✓ test_advance_to_updates_time PASSED")
    return True


def test_shutdown_with_no_socket():
    """Test shutdown() works safely without socket."""
    config = {"image": "alpine:latest"}
    node = DockerNode("test1", config, seed=42)

    # Should not raise error
    node.shutdown()

    assert node.sock is None
    assert node.container is None

    print("✓ test_shutdown_with_no_socket PASSED")
    return True


def test_socket_config_parameter():
    """Test socket_port config parameter is recognized."""
    config1 = {"image": "alpine:latest"}
    node1 = DockerNode("test1", config1, seed=42)
    # Default port should be 5000 (will be used in connect_to_socket)

    config2 = {"image": "alpine:latest", "socket_port": 8080}
    node2 = DockerNode("test2", config2, seed=42)
    assert node2.config["socket_port"] == 8080

    print("✓ test_socket_config_parameter PASSED")
    return True


def main():
    """Run all socket interface tests."""
    print("=" * 60)
    print("M2b: Socket Interface Tests")
    print("=" * 60)
    print("\nThese tests do NOT require Docker daemon.")
    print("For full socket lifecycle tests, see test_socket_integration.py\n")

    tests = [
        test_docker_node_has_socket_methods,
        test_advance_to_with_no_socket,
        test_advance_to_updates_time,
        test_shutdown_with_no_socket,
        test_socket_config_parameter,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ {test.__name__} FAILED: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
