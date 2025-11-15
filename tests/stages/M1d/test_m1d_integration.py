#!/usr/bin/env python3
"""
test_m1d_integration.py - M1d Integration Test

Simple integration test to verify LatencyNetworkModel works with coordinator.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from sim.config.scenario import load_scenario, NetworkConfig, NetworkLink
from sim.network.latency_model import LatencyNetworkModel


def test_load_latency_scenario():
    """Test loading scenario with latency network configuration."""
    print("\nTest: Load M1d latency scenario")

    scenario_path = project_root / "scenarios" / "m1d_latency_test.yaml"
    scenario = load_scenario(str(scenario_path))

    # Verify network config loaded
    assert scenario.network is not None, "Network config not loaded"
    assert scenario.network.model == "latency", f"Wrong model: {scenario.network.model}"
    assert scenario.network.default_latency_us == 10000
    assert len(scenario.network.links) == 1
    assert scenario.network.links[0].latency_us == 5000

    print("✓ Latency scenario loads correctly")
    return True


def test_latency_model_with_scenario():
    """Test creating LatencyNetworkModel from scenario config."""
    print("\nTest: Create LatencyNetworkModel from scenario")

    scenario_path = project_root / "scenarios" / "m1d_latency_test.yaml"
    scenario = load_scenario(str(scenario_path))

    model = LatencyNetworkModel(scenario.network, scenario.seed)

    # Verify model created successfully
    assert model is not None
    print("✓ LatencyNetworkModel created from scenario config")
    return True


def main():
    print("="*60)
    print("M1d Integration Tests")
    print("="*60)

    tests = [
        test_load_latency_scenario,
        test_latency_model_with_scenario,
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

    print("\n" + "="*60)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*60)

    return failed == 0


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
