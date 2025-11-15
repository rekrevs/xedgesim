#!/bin/bash
# M3fc End-to-End Integration Test
# Tests coordinator with actual Renode process and firmware

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
SCENARIO="$PROJECT_ROOT/examples/scenarios/device_emulation_simple.yaml"

echo "=== M3fc E2E Integration Test ==="
echo "Project root: $PROJECT_ROOT"
echo "Scenario: $SCENARIO"
echo

# Check prerequisites
if ! command -v renode &> /dev/null; then
    echo "ERROR: Renode not found"
    exit 1
fi

if [ ! -f "$PROJECT_ROOT/firmware/sensor-node/build/zephyr/zephyr.elf" ]; then
    echo "ERROR: Firmware not built"
    exit 1
fi

echo "Prerequisites OK"
echo

# Run coordinator with scenario
cd "$PROJECT_ROOT"
echo "Running coordinator with Renode scenario..."
PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH" python3 sim/harness/coordinator.py "$SCENARIO"

echo
echo "=== Test Complete ==="
echo "Check output above for:"
echo "  - [Coordinator] Registered in-process Renode node"
echo "  - [Coordinator] Starting in-process node"
echo "  - [RenodeNode] Starting Renode"
echo "  - [RenodeNode] Executing: renode ..."
echo "  - [Coordinator] Simulation complete"
echo "  - No errors or exceptions"
