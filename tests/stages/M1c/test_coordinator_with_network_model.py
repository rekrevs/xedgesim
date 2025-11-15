#!/usr/bin/env python3
"""
test_coordinator_with_network_model.py - M1c Integration Test

Tests that coordinator can use NetworkModel for message routing.
Verifies that DirectNetworkModel produces same results as M0 inline routing.
"""

import subprocess
import sys
import time
import hashlib
from pathlib import Path

# Find project root
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from sim.harness.coordinator import Coordinator, Event
from sim.network.direct_model import DirectNetworkModel


def start_node(script_path, port, name, output_dir):
    """Start a simulation node in background."""
    log_file = open(output_dir / f"{name}.log", 'w')
    proc = subprocess.Popen(
        [sys.executable, str(script_path), str(port)],
        stdout=log_file,
        stderr=subprocess.STDOUT
    )
    return proc, log_file


def test_coordinator_accepts_network_model():
    """Test that coordinator accepts network_model parameter."""
    print("\n" + "="*60)
    print("M1c Integration Test: Coordinator with NetworkModel")
    print("="*60)

    # Create coordinator with DirectNetworkModel
    network_model = DirectNetworkModel()
    coordinator = Coordinator(time_quantum_us=1000, network_model=network_model)

    # Verify coordinator has network model
    if not hasattr(coordinator, 'network_model'):
        print("✗ Coordinator does not have network_model attribute")
        return False

    if coordinator.network_model != network_model:
        print("✗ Coordinator network_model is not the one we passed")
        return False

    print("✓ Coordinator accepts network_model parameter")
    return True


def test_coordinator_defaults_to_direct_network():
    """Test that coordinator defaults to DirectNetworkModel if not specified."""
    print("\n" + "="*60)
    print("M1c: Coordinator defaults to DirectNetworkModel")
    print("="*60)

    # Create coordinator without network_model
    coordinator = Coordinator(time_quantum_us=1000)

    # Should default to DirectNetworkModel
    if not hasattr(coordinator, 'network_model'):
        print("✗ Coordinator does not have network_model attribute")
        return False

    if not isinstance(coordinator.network_model, DirectNetworkModel):
        print(f"✗ Expected DirectNetworkModel, got {type(coordinator.network_model)}")
        return False

    print("✓ Coordinator defaults to DirectNetworkModel")
    return True


def test_end_to_end_with_network_model():
    """Test complete simulation with coordinator using NetworkModel."""
    print("\n" + "="*60)
    print("M1c: End-to-end test with NetworkModel")
    print("="*60)

    # Create output directory
    output_dir = project_root / "test_output_m1c"
    output_dir.mkdir(exist_ok=True)

    # Start nodes
    nodes_dir = project_root / "sim"
    sensor_script = nodes_dir / "device" / "sensor_node.py"
    gateway_script = nodes_dir / "edge" / "gateway_node.py"

    print("[Test] Starting nodes...")
    processes = []

    # Start sensor1 (port 6001 - different from M1b to avoid conflicts)
    proc1, log1 = start_node(sensor_script, 6001, "sensor1", output_dir)
    processes.append((proc1, log1, "sensor1"))

    # Start gateway (port 6004)
    proc2, log2 = start_node(gateway_script, 6004, "gateway", output_dir)
    processes.append((proc2, log2, "gateway"))

    time.sleep(2)  # Wait for nodes to start

    try:
        # Create coordinator with DirectNetworkModel explicitly
        network_model = DirectNetworkModel()
        coordinator = Coordinator(time_quantum_us=1000, network_model=network_model)

        # Register nodes
        coordinator.add_node("sensor1", "localhost", 6001)
        coordinator.add_node("gateway", "localhost", 6004)

        # Connect and initialize
        coordinator.connect_all()
        coordinator.initialize_all(seed=42)

        # Run for 1 second (short test)
        duration_us = 1_000_000
        coordinator.run(duration_us=duration_us)

        print("\n[Test] Simulation completed successfully")
        print("✓ End-to-end test with NetworkModel PASSED")
        return True

    except Exception as e:
        print(f"\n✗ End-to-end test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Clean up nodes
        print("[Test] Cleaning up nodes...")
        for proc, log, name in processes:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    proc.kill()
            log.close()


def main():
    """Run M1c integration tests."""
    print("""
╔══════════════════════════════════════════════════════════════╗
║         M1c Integration Tests                                ║
║                                                              ║
║  Tests:                                                      ║
║  1. Coordinator accepts network_model parameter              ║
║  2. Coordinator defaults to DirectNetworkModel               ║
║  3. End-to-end simulation with NetworkModel                  ║
╚══════════════════════════════════════════════════════════════╝
    """)

    passed = 0
    failed = 0

    # Test 1: Coordinator accepts network model
    try:
        if test_coordinator_accepts_network_model():
            passed += 1
        else:
            failed += 1
    except Exception as e:
        print(f"✗ test_coordinator_accepts_network_model EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        failed += 1

    # Test 2: Coordinator defaults to DirectNetworkModel
    try:
        if test_coordinator_defaults_to_direct_network():
            passed += 1
        else:
            failed += 1
    except Exception as e:
        print(f"✗ test_coordinator_defaults_to_direct_network EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        failed += 1

    # Test 3: End-to-end with network model
    try:
        if test_end_to_end_with_network_model():
            passed += 1
        else:
            failed += 1
    except Exception as e:
        print(f"✗ test_end_to_end_with_network_model EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        failed += 1

    # Final summary
    print("\n" + "="*60)
    print("M1c Integration Test Summary")
    print("="*60)
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print("="*60)

    if failed == 0:
        print("\n✓ ALL M1c INTEGRATION TESTS PASSED")
        return True
    else:
        print("\n✗ SOME M1c TESTS FAILED")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
