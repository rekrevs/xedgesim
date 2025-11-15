#!/usr/bin/env python3
"""
Manual M3c schema validation (no pytest required).
Tests ML inference schema parsing.
"""

import tempfile
import os
from pathlib import Path
import sys

# Add repo root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from sim.config.scenario import load_scenario, MLInferenceConfig


def test_edge_placement():
    """Test edge placement configuration."""
    print("Test 1: Edge placement config...", end=" ")

    # Create temp model file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.onnx', delete=False) as model_f:
        model_path = model_f.name

    # Create temp YAML
    yaml_content = f"""
simulation:
  duration_s: 10
  seed: 42

nodes:
  - id: sensor1
    type: sensor
    port: 5001

ml_inference:
  placement: edge
  edge_config:
    model_path: {model_path}
    broker_host: localhost
    broker_port: 1883
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as yaml_f:
        yaml_f.write(yaml_content)
        yaml_path = yaml_f.name

    try:
        scenario = load_scenario(yaml_path)
        assert scenario.ml_inference is not None, "ml_inference should be set"
        assert scenario.ml_inference.placement == 'edge', f"Expected 'edge', got {scenario.ml_inference.placement}"
        assert scenario.ml_inference.edge_config is not None, "edge_config should be set"
        assert scenario.ml_inference.edge_config['model_path'] == model_path
        print("✓ PASS")
        return True
    except Exception as e:
        print(f"✗ FAIL: {e}")
        return False
    finally:
        os.unlink(yaml_path)
        os.unlink(model_path)


def test_cloud_placement():
    """Test cloud placement configuration."""
    print("Test 2: Cloud placement config...", end=" ")

    with tempfile.NamedTemporaryFile(mode='w', suffix='.pt', delete=False) as model_f:
        model_path = model_f.name

    yaml_content = f"""
simulation:
  duration_s: 10
  seed: 42

nodes:
  - id: sensor1
    type: sensor
    port: 5001

ml_inference:
  placement: cloud
  cloud_config:
    model_path: {model_path}
    broker_host: localhost
    broker_port: 1883
    latency_ms: 50
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as yaml_f:
        yaml_f.write(yaml_content)
        yaml_path = yaml_f.name

    try:
        scenario = load_scenario(yaml_path)
        assert scenario.ml_inference is not None
        assert scenario.ml_inference.placement == 'cloud'
        assert scenario.ml_inference.cloud_config is not None
        assert scenario.ml_inference.cloud_config['latency_ms'] == 50
        print("✓ PASS")
        return True
    except Exception as e:
        print(f"✗ FAIL: {e}")
        return False
    finally:
        os.unlink(yaml_path)
        os.unlink(model_path)


def test_no_ml_config():
    """Test scenario without ML config (optional)."""
    print("Test 3: No ML config (backward compat)...", end=" ")

    yaml_content = """
simulation:
  duration_s: 10
  seed: 42

nodes:
  - id: sensor1
    type: sensor
    port: 5001
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as yaml_f:
        yaml_f.write(yaml_content)
        yaml_path = yaml_f.name

    try:
        scenario = load_scenario(yaml_path)
        assert scenario.ml_inference is None, "ml_inference should be None"
        print("✓ PASS")
        return True
    except Exception as e:
        print(f"✗ FAIL: {e}")
        return False
    finally:
        os.unlink(yaml_path)


def test_invalid_placement():
    """Test invalid placement value."""
    print("Test 4: Invalid placement value...", end=" ")

    with tempfile.NamedTemporaryFile(mode='w', suffix='.onnx', delete=False) as model_f:
        model_path = model_f.name

    yaml_content = f"""
simulation:
  duration_s: 10
  seed: 42

nodes:
  - id: sensor1
    type: sensor
    port: 5001

ml_inference:
  placement: invalid
  edge_config:
    model_path: {model_path}
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as yaml_f:
        yaml_f.write(yaml_content)
        yaml_path = yaml_f.name

    try:
        scenario = load_scenario(yaml_path)
        print("✗ FAIL: Should have raised ValueError")
        return False
    except ValueError as e:
        if "must be 'edge' or 'cloud'" in str(e):
            print("✓ PASS")
            return True
        else:
            print(f"✗ FAIL: Wrong error message: {e}")
            return False
    except Exception as e:
        print(f"✗ FAIL: Wrong exception type: {e}")
        return False
    finally:
        os.unlink(yaml_path)
        os.unlink(model_path)


def test_missing_edge_config():
    """Test edge placement without edge_config."""
    print("Test 5: Missing edge_config...", end=" ")

    yaml_content = """
simulation:
  duration_s: 10
  seed: 42

nodes:
  - id: sensor1
    type: sensor
    port: 5001

ml_inference:
  placement: edge
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as yaml_f:
        yaml_f.write(yaml_content)
        yaml_path = yaml_f.name

    try:
        scenario = load_scenario(yaml_path)
        print("✗ FAIL: Should have raised ValueError")
        return False
    except ValueError as e:
        if "requires 'edge_config'" in str(e):
            print("✓ PASS")
            return True
        else:
            print(f"✗ FAIL: Wrong error: {e}")
            return False
    finally:
        os.unlink(yaml_path)


def test_model_not_found():
    """Test model file validation."""
    print("Test 6: Model file not found...", end=" ")

    yaml_content = """
simulation:
  duration_s: 10
  seed: 42

nodes:
  - id: sensor1
    type: sensor
    port: 5001

ml_inference:
  placement: edge
  edge_config:
    model_path: /nonexistent/model.onnx
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as yaml_f:
        yaml_f.write(yaml_content)
        yaml_path = yaml_f.name

    try:
        scenario = load_scenario(yaml_path)
        print("✗ FAIL: Should have raised FileNotFoundError")
        return False
    except FileNotFoundError as e:
        if "Edge ML model not found" in str(e):
            print("✓ PASS")
            return True
        else:
            print(f"✗ FAIL: Wrong error: {e}")
            return False
    finally:
        os.unlink(yaml_path)


def main():
    """Run all tests."""
    print("=" * 60)
    print("M3c Schema Validation Tests")
    print("=" * 60)

    tests = [
        test_edge_placement,
        test_cloud_placement,
        test_no_ml_config,
        test_invalid_placement,
        test_missing_edge_config,
        test_model_not_found
    ]

    results = [test() for test in tests]
    passed = sum(results)
    total = len(results)

    print("=" * 60)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 60)

    if passed == total:
        print("✓ All tests passed!")
        return 0
    else:
        print(f"✗ {total - passed} test(s) failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
