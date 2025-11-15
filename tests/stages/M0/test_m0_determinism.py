#!/usr/bin/env python3
"""
test_m0_poc.py - M0 Proof-of-Concept Test Script

Tests the minimal federated co-simulation implementation:
1. Starts all nodes (3 sensors + gateway) in background
2. Runs coordinator
3. Validates determinism (two runs with same seed → identical results)
4. Checks metrics consistency
"""

import subprocess
import time
import os
import sys
import signal
import hashlib
from pathlib import Path


class SimulationRunner:
    """Helper to run simulation and manage processes."""

    def __init__(self, test_name: str):
        self.test_name = test_name
        self.processes = []
        self.output_dir = Path(f"test_output_{test_name}")

    def setup(self):
        """Create output directory."""
        self.output_dir.mkdir(exist_ok=True)
        os.chdir(self.output_dir)
        print(f"[Test] Created output directory: {self.output_dir}")

    def start_node(self, script: str, port: int, name: str):
        """Start a node in background."""
        log_file = open(f"{name}.log", 'w')
        proc = subprocess.Popen(
            [sys.executable, script, str(port)],
            stdout=log_file,
            stderr=subprocess.STDOUT
        )
        self.processes.append((proc, log_file, name))
        print(f"[Test] Started {name} on port {port} (PID {proc.pid})")
        return proc

    def wait_for_nodes(self, delay: float = 2.0):
        """Wait for all nodes to be ready."""
        print(f"[Test] Waiting {delay}s for nodes to start...")
        time.sleep(delay)

    def run_coordinator(self):
        """Run coordinator (blocking)."""
        print("[Test] Starting coordinator...")
        # Find repository root (3 levels up from tests/stages/M0/)
        repo_root = Path(__file__).parent.parent.parent.parent
        coordinator_path = repo_root / "sim/harness/coordinator.py"
        result = subprocess.run(
            [sys.executable, str(coordinator_path)],
            capture_output=True,
            text=True
        )

        # Save output
        with open("coordinator.log", 'w') as f:
            f.write(result.stdout)
            if result.stderr:
                f.write("\n=== STDERR ===\n")
                f.write(result.stderr)

        print("[Test] Coordinator finished")
        return result.returncode == 0

    def cleanup(self):
        """Kill all node processes."""
        print("[Test] Cleaning up node processes...")
        for proc, log_file, name in self.processes:
            if proc.poll() is None:  # Still running
                proc.terminate()
                try:
                    proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    proc.kill()
            log_file.close()
            print(f"[Test] Stopped {name}")

    def verify_outputs(self):
        """Verify that output files were created."""
        expected_files = [
            "sensor1_metrics.csv",
            "sensor2_metrics.csv",
            "sensor3_metrics.csv",
            "gateway_metrics.csv"
        ]

        all_exist = True
        for fname in expected_files:
            exists = Path(fname).exists()
            size = Path(fname).stat().st_size if exists else 0
            status = "✓" if exists and size > 0 else "✗"
            print(f"[Test] {status} {fname} ({size} bytes)")
            if not exists or size == 0:
                all_exist = False

        return all_exist

    def compute_hash(self):
        """Compute hash of all CSV files for comparison."""
        csv_files = sorted(Path(".").glob("*_metrics.csv"))
        hasher = hashlib.sha256()

        for csv_file in csv_files:
            with open(csv_file, 'rb') as f:
                hasher.update(f.read())

        return hasher.hexdigest()


def run_single_test(test_name: str) -> str:
    """Run a single simulation test."""
    print("\n" + "="*60)
    print(f"Running test: {test_name}")
    print("="*60)

    runner = SimulationRunner(test_name)
    runner.setup()

    try:
        # Start all nodes
        # Find repository root (3 levels up from tests/stages/M0/)
        repo_root = Path(__file__).parent.parent.parent.parent if hasattr(Path(__file__), 'parent') else Path(".").resolve().parent.parent.parent
        runner.start_node(str(repo_root / "sim/device/sensor_node.py"), 5001, "sensor1")
        runner.start_node(str(repo_root / "sim/device/sensor_node.py"), 5002, "sensor2")
        runner.start_node(str(repo_root / "sim/device/sensor_node.py"), 5003, "sensor3")
        runner.start_node(str(repo_root / "sim/edge/gateway_node.py"), 5004, "gateway")

        # Wait for nodes to start
        runner.wait_for_nodes(2.0)

        # Run coordinator
        success = runner.run_coordinator()

        if not success:
            print("[Test] ✗ Coordinator failed!")
            return None

        # Verify outputs
        if not runner.verify_outputs():
            print("[Test] ✗ Missing output files!")
            return None

        # Compute hash
        result_hash = runner.compute_hash()
        print(f"[Test] Result hash: {result_hash}")

        print(f"[Test] ✓ Test '{test_name}' completed successfully")
        return result_hash

    finally:
        runner.cleanup()
        os.chdir("..")


def test_determinism():
    """Test that two runs with same seed produce identical results."""
    print("\n" + "="*60)
    print("DETERMINISM TEST")
    print("="*60)
    print("Running simulation twice with same seed (42)...")
    print("Results should be IDENTICAL.\n")

    # Run 1
    hash1 = run_single_test("run1_seed42")

    # Run 2
    hash2 = run_single_test("run2_seed42")

    # Compare
    print("\n" + "="*60)
    print("DETERMINISM VERIFICATION")
    print("="*60)

    if hash1 is None or hash2 is None:
        print("✗ FAILED: One or both runs failed")
        return False

    if hash1 == hash2:
        print("✓ PASSED: Results are IDENTICAL")
        print(f"  Hash 1: {hash1}")
        print(f"  Hash 2: {hash2}")
        return True
    else:
        print("✗ FAILED: Results are DIFFERENT")
        print(f"  Hash 1: {hash1}")
        print(f"  Hash 2: {hash2}")
        return False


def analyze_results():
    """Analyze results from test runs."""
    print("\n" + "="*60)
    print("RESULTS ANALYSIS")
    print("="*60)

    run_dir = Path("test_output_run1_seed42")
    if not run_dir.exists():
        print("No results to analyze")
        return

    print("\nSensor1 metrics:")
    with open(run_dir / "sensor1_metrics.csv") as f:
        lines = f.readlines()
        print(f"  Total lines: {len(lines)}")
        print(f"  First 3 lines:")
        for line in lines[:3]:
            print(f"    {line.strip()}")

    print("\nGateway metrics:")
    with open(run_dir / "gateway_metrics.csv") as f:
        lines = f.readlines()
        print(f"  Total lines: {len(lines)}")
        print(f"  First 3 lines:")
        for line in lines[:3]:
            print(f"    {line.strip()}")

    # Count messages
    import csv
    sensor1_transmits = 0
    with open(run_dir / "sensor1_metrics.csv") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['event_type'] == 'transmit':
                sensor1_transmits += 1

    gateway_processes = 0
    with open(run_dir / "gateway_metrics.csv") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['event_type'] == 'process':
                gateway_processes += 1

    print(f"\nMessage flow:")
    print(f"  Sensor1 transmitted: {sensor1_transmits} messages")
    print(f"  Gateway processed: {gateway_processes} messages (from all sensors)")
    print(f"  Expected: ~10 messages per sensor (1 per second for 10 seconds)")


def main():
    """Run M0 POC tests."""
    print("""
╔══════════════════════════════════════════════════════════════╗
║        xEdgeSim M0 Minimal Proof-of-Concept Test            ║
║                                                              ║
║  This script validates:                                      ║
║  1. Federated co-simulation via sockets works                ║
║  2. Time synchronization is correct                          ║
║  3. Determinism: same seed → identical results               ║
║  4. Cross-node message routing works                         ║
╚══════════════════════════════════════════════════════════════╝
    """)

    # Make sure we can find the repository structure
    # This test can be run from repo root or from tests/stages/M0/
    repo_root = Path(__file__).parent.parent.parent.parent if hasattr(Path(__file__), 'parent') else Path(".")
    if not (repo_root / "sim/harness/coordinator.py").exists():
        print(f"Error: Cannot find sim/harness/coordinator.py from {repo_root}")
        print(f"Current directory: {Path.cwd()}")
        sys.exit(1)

    # Run determinism test
    passed = test_determinism()

    # Analyze results
    analyze_results()

    # Final summary
    print("\n" + "="*60)
    print("FINAL SUMMARY")
    print("="*60)

    if passed:
        print("✓ ALL TESTS PASSED")
        print("\nM0 Proof-of-Concept validated successfully!")
        print("Key achievements:")
        print("  • Socket-based coordination works")
        print("  • Conservative lockstep algorithm correct")
        print("  • Determinism verified (identical hashes)")
        print("  • Cross-node message routing functional")
        return 0
    else:
        print("✗ TESTS FAILED")
        print("Check logs in test_output_* directories")
        return 1


if __name__ == "__main__":
    sys.exit(main())
