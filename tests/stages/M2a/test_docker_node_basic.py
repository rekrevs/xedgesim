#!/usr/bin/env python3
"""
test_docker_node_basic.py - M2a Basic Tests for Docker Node

Tests Docker node can be instantiated and interface matches expectations.
Does NOT require Docker daemon (basic interface tests only).
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from sim.edge.docker_node import DockerNode


def test_docker_node_instantiation():
    """Test DockerNode can be created."""
    config = {
        "image": "alpine:latest",
        "command": "sleep 60"
    }
    node = DockerNode("test1", config, seed=42)

    assert node.node_id == "test1"
    assert node.current_time_us == 0
    assert node.container is None
    assert node.config == config
    assert node.seed == 42

    print("✓ test_docker_node_instantiation PASSED")
    return True


def test_docker_node_config_structure():
    """Test DockerNode accepts various config structures."""
    # Minimal config
    config1 = {"image": "alpine:latest"}
    node1 = DockerNode("test1", config1, seed=42)
    assert node1.config["image"] == "alpine:latest"

    # Full config
    config2 = {
        "image": "nginx:latest",
        "command": "nginx -g 'daemon off;'",
        "ports": {"80/tcp": 8080},
        "environment": {"ENV_VAR": "value"},
        "volumes": {"/host/path": {"bind": "/container/path", "mode": "ro"}}
    }
    node2 = DockerNode("test2", config2, seed=42)
    assert node2.config["image"] == "nginx:latest"
    assert node2.config["ports"] == {"80/tcp": 8080}

    print("✓ test_docker_node_config_structure PASSED")
    return True


def test_docker_node_interface_compatibility():
    """Test DockerNode has same interface as Python nodes."""
    config = {"image": "alpine:latest"}
    node = DockerNode("test1", config, seed=42)

    # Should have these methods (same as SensorNode, GatewayNode)
    assert hasattr(node, "advance_to")
    assert hasattr(node, "shutdown")
    assert hasattr(node, "start")  # DockerNode-specific
    assert hasattr(node, "wait_for_ready")  # DockerNode-specific

    # Should have these attributes
    assert hasattr(node, "node_id")
    assert hasattr(node, "config")
    assert hasattr(node, "current_time_us")

    print("✓ test_docker_node_interface_compatibility PASSED")
    return True


def main():
    """Run all basic Docker node tests."""
    print("=" * 60)
    print("M2a: Docker Node Basic Tests")
    print("=" * 60)
    print("\nThese tests do NOT require Docker daemon.")
    print("For full Docker lifecycle tests, see test_docker_node_lifecycle.py\n")

    tests = [
        test_docker_node_instantiation,
        test_docker_node_config_structure,
        test_docker_node_interface_compatibility,
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
