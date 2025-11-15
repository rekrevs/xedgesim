#!/usr/bin/env python3
"""
test_network_model_interface.py - M1c Unit Tests for NetworkModel Interface

Tests that NetworkModel is properly defined as an abstract base class
with the required methods.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from abc import ABC
from sim.network.network_model import NetworkModel
from sim.harness.coordinator import Event


def test_network_model_is_abstract():
    """Test that NetworkModel cannot be instantiated directly."""
    try:
        # This should fail because NetworkModel is abstract
        model = NetworkModel()
        print("✗ test_network_model_is_abstract FAILED: Should not be able to instantiate NetworkModel")
        return False
    except TypeError as e:
        # Expected: Can't instantiate abstract class
        if "abstract" in str(e).lower():
            print("✓ test_network_model_is_abstract PASSED")
            return True
        else:
            print(f"✗ test_network_model_is_abstract FAILED: Wrong error: {e}")
            return False


def test_network_model_has_route_message():
    """Test that NetworkModel defines route_message abstract method."""
    # Check that the method exists in the abstract interface
    if not hasattr(NetworkModel, 'route_message'):
        print("✗ test_network_model_has_route_message FAILED: route_message method not defined")
        return False

    # Check that it's marked as abstract
    method = getattr(NetworkModel, 'route_message')
    if not hasattr(method, '__isabstractmethod__') or not method.__isabstractmethod__:
        print("✗ test_network_model_has_route_message FAILED: route_message is not abstract")
        return False

    print("✓ test_network_model_has_route_message PASSED")
    return True


def test_network_model_has_advance_to():
    """Test that NetworkModel defines advance_to abstract method."""
    if not hasattr(NetworkModel, 'advance_to'):
        print("✗ test_network_model_has_advance_to FAILED: advance_to method not defined")
        return False

    method = getattr(NetworkModel, 'advance_to')
    if not hasattr(method, '__isabstractmethod__') or not method.__isabstractmethod__:
        print("✗ test_network_model_has_advance_to FAILED: advance_to is not abstract")
        return False

    print("✓ test_network_model_has_advance_to PASSED")
    return True


def test_network_model_has_reset():
    """Test that NetworkModel defines reset abstract method."""
    if not hasattr(NetworkModel, 'reset'):
        print("✗ test_network_model_has_reset FAILED: reset method not defined")
        return False

    method = getattr(NetworkModel, 'reset')
    if not hasattr(method, '__isabstractmethod__') or not method.__isabstractmethod__:
        print("✗ test_network_model_has_reset FAILED: reset is not abstract")
        return False

    print("✓ test_network_model_has_reset PASSED")
    return True


def test_network_model_inherits_from_abc():
    """Test that NetworkModel inherits from ABC."""
    if not issubclass(NetworkModel, ABC):
        print("✗ test_network_model_inherits_from_abc FAILED: NetworkModel does not inherit from ABC")
        return False

    print("✓ test_network_model_inherits_from_abc PASSED")
    return True


def test_subclass_must_implement_all_methods():
    """Test that a subclass must implement all abstract methods."""

    # Try to create an incomplete subclass
    class IncompleteNetwork(NetworkModel):
        # Missing route_message, advance_to, reset
        pass

    try:
        model = IncompleteNetwork()
        print("✗ test_subclass_must_implement_all_methods FAILED: Should not instantiate incomplete subclass")
        return False
    except TypeError as e:
        if "abstract" in str(e).lower():
            print("✓ test_subclass_must_implement_all_methods PASSED")
            return True
        else:
            print(f"✗ test_subclass_must_implement_all_methods FAILED: Wrong error: {e}")
            return False


def test_complete_subclass_can_be_instantiated():
    """Test that a complete subclass can be instantiated."""

    class CompleteNetwork(NetworkModel):
        def route_message(self, event):
            return [event]

        def advance_to(self, target_time_us):
            return []

        def reset(self):
            pass

    try:
        model = CompleteNetwork()
        print("✓ test_complete_subclass_can_be_instantiated PASSED")
        return True
    except Exception as e:
        print(f"✗ test_complete_subclass_can_be_instantiated FAILED: {e}")
        return False


def main():
    """Run all NetworkModel interface tests."""
    print("="*60)
    print("M1c: NetworkModel Interface Tests")
    print("="*60)

    tests = [
        test_network_model_is_abstract,
        test_network_model_has_route_message,
        test_network_model_has_advance_to,
        test_network_model_has_reset,
        test_network_model_inherits_from_abc,
        test_subclass_must_implement_all_methods,
        test_complete_subclass_can_be_instantiated,
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
            print(f"✗ {test.__name__} EXCEPTION: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("="*60)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*60)

    return failed == 0


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
