#!/usr/bin/env python3
"""
test_coordinator_with_yaml.py - M1b Integration Test

Tests that coordinator can load and run YAML scenarios.
Verifies backward compatibility with M0 determinism.
"""

import subprocess
import sys
import time
from pathlib import Path
import hashlib

# Find project root
project_root = Path(__file__).parent.parent.parent.parent


def start_node(script_path, port, name, output_dir):
    """Start a simulation node in background."""
    log_file = open(output_dir / f"{name}.log", 'w')
    proc = subprocess.Popen(
        [sys.executable, str(script_path), str(port)],
        stdout=log_file,
        stderr=subprocess.STDOUT
    )
    return proc, log_file


def test_coordinator_with_yaml_scenario():
    """Test coordinator loading and running with YAML scenario."""
    print("\n" + "="*60)
    print("M1b Integration Test: Coordinator with YAML")
    print("="*60)

    # Create output directory
    output_dir = project_root / "test_output_m1b"
    output_dir.mkdir(exist_ok=True)

    # Start nodes for m1b_minimal scenario (2 nodes)
    nodes_dir = project_root / "sim"
    sensor_script = nodes_dir / "device" / "sensor_node.py"
    gateway_script = nodes_dir / "edge" / "gateway_node.py"

    print("\n[Test] Starting nodes...")
    processes = []

    # Start sensor1 (port 5001)
    proc1, log1 = start_node(sensor_script, 5001, "sensor1", output_dir)
    processes.append((proc1, log1, "sensor1"))

    # Start gateway (port 5004)
    proc2, log2 = start_node(gateway_script, 5004, "gateway", output_dir)
    processes.append((proc2, log2, "gateway"))

    time.sleep(2)  # Wait for nodes to start

    # Run coordinator with YAML scenario
    scenario_path = project_root / "scenarios" / "m1b_minimal.yaml"
    coordinator_script = project_root / "sim" / "harness" / "coordinator.py"

    print(f"[Test] Running coordinator with {scenario_path}...")

    result = subprocess.run(
        [sys.executable, str(coordinator_script), str(scenario_path)],
        capture_output=True,
        text=True,
        cwd=output_dir
    )

    # Save coordinator output
    with open(output_dir / "coordinator.log", 'w') as f:
        f.write(result.stdout)
        if result.stderr:
            f.write("\n=== STDERR ===\n")
            f.write(result.stderr)

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

    # Verify results
    print("\n[Test] Verifying results...")

    # Check coordinator ran successfully
    if result.returncode != 0:
        print(f"✗ Coordinator failed with return code {result.returncode}")
        print("Coordinator output:")
        print(result.stdout)
        print(result.stderr)
        return False

    # Check output files exist
    # Note: Nodes write CSV files to their working directory (repo root for now)
    expected_files = [
        "sensor1_metrics.csv",
        "gateway_metrics.csv"
    ]

    all_exist = True
    for fname in expected_files:
        # Check in repo root (where nodes run from)
        fpath = project_root / fname
        if not fpath.exists():
            print(f"✗ Missing file: {fname}")
            all_exist = False
        else:
            size = fpath.stat().st_size
            print(f"✓ {fname} ({size} bytes)")

    if not all_exist:
        return False

    # Verify simulation parameters from output
    if "2.0s" not in result.stdout:
        print("✗ Expected 2.0s simulation duration (from YAML)")
        return False

    print("\n✓ Coordinator with YAML scenario: PASSED")
    return True


def test_yaml_determinism():
    """Test that YAML-based scenarios are deterministic."""
    print("\n" + "="*60)
    print("M1b Determinism Test: YAML Scenarios")
    print("="*60)

    def run_with_yaml(test_name):
        """Run one simulation with YAML config."""
        output_dir = project_root / f"test_output_m1b_{test_name}"
        output_dir.mkdir(exist_ok=True)

        # Start nodes
        nodes_dir = project_root / "sim"
        sensor_script = nodes_dir / "device" / "sensor_node.py"
        gateway_script = nodes_dir / "edge" / "gateway_node.py"

        processes = []

        proc1, log1 = start_node(sensor_script, 5001, "sensor1", output_dir)
        processes.append((proc1, log1))

        proc2, log2 = start_node(gateway_script, 5004, "gateway", output_dir)
        processes.append((proc2, log2))

        time.sleep(2)

        # Run coordinator
        scenario_path = project_root / "scenarios" / "m1b_minimal.yaml"
        coordinator_script = project_root / "sim" / "harness" / "coordinator.py"

        result = subprocess.run(
            [sys.executable, str(coordinator_script), str(scenario_path)],
            capture_output=True,
            text=True,
            cwd=output_dir
        )

        # Clean up
        for proc, log in processes:
            if proc.poll() is None:
                proc.terminate()
                proc.wait(timeout=2)
            log.close()

        if result.returncode != 0:
            return None

        # Compute hash of CSV files
        # Note: Nodes write CSV files to repo root for now
        csv_files = sorted(project_root.glob("*_metrics.csv"))
        if not csv_files:
            return None

        hasher = hashlib.sha256()
        for csv_file in csv_files:
            with open(csv_file, 'rb') as f:
                hasher.update(f.read())

        return hasher.hexdigest()

    # Run twice with same seed
    print("[Test] Run 1...")
    hash1 = run_with_yaml("run1")

    print("[Test] Run 2...")
    hash2 = run_with_yaml("run2")

    if hash1 is None or hash2 is None:
        print("✗ One or both runs failed")
        return False

    print(f"\nHash 1: {hash1}")
    print(f"Hash 2: {hash2}")

    if hash1 == hash2:
        print("\n✓ YAML determinism: PASSED (identical results)")
        return True
    else:
        print("\n✗ YAML determinism: FAILED (different results)")
        return False


def main():
    """Run M1b integration tests."""
    print("""
╔══════════════════════════════════════════════════════════════╗
║             M1b Integration Tests                            ║
║                                                              ║
║  Tests:                                                      ║
║  1. Coordinator loads and runs YAML scenarios                ║
║  2. YAML scenarios maintain determinism                      ║
╚══════════════════════════════════════════════════════════════╝
    """)

    passed = 0
    failed = 0

    # Test 1: Coordinator with YAML
    try:
        if test_coordinator_with_yaml_scenario():
            passed += 1
        else:
            failed += 1
    except Exception as e:
        print(f"✗ test_coordinator_with_yaml_scenario EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        failed += 1

    # Test 2: YAML determinism
    try:
        if test_yaml_determinism():
            passed += 1
        else:
            failed += 1
    except Exception as e:
        print(f"✗ test_yaml_determinism EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        failed += 1

    # Final summary
    print("\n" + "="*60)
    print("M1b Integration Test Summary")
    print("="*60)
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print("="*60)

    if failed == 0:
        print("\n✓ ALL M1b INTEGRATION TESTS PASSED")
        return True
    else:
        print("\n✗ SOME M1b TESTS FAILED")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
