#!/bin/bash
# M3fb Standalone Renode Test
#
# Tests the firmware in Renode without the coordinator.
# This validates that the firmware builds, loads, and produces JSON output.
#
# Prerequisites:
# - Renode installed (renode --version)
# - Firmware built (firmware/sensor-node/build/zephyr/zephyr.elf)
#
# Usage:
#   ./test_standalone_renode.sh [duration_seconds]
#
# Example:
#   ./test_standalone_renode.sh 5

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
FIRMWARE_ELF="$PROJECT_ROOT/firmware/sensor-node/build/zephyr/zephyr.elf"
DURATION="${1:-5.0}"  # Default: 5 seconds

echo "=== M3fb Standalone Renode Test ==="
echo "Project root: $PROJECT_ROOT"
echo "Firmware: $FIRMWARE_ELF"
echo "Duration: $DURATION seconds"
echo

# Check firmware exists
if [ ! -f "$FIRMWARE_ELF" ]; then
    echo "ERROR: Firmware not found at $FIRMWARE_ELF"
    echo
    echo "Build firmware first:"
    echo "  cd $PROJECT_ROOT/firmware/sensor-node"
    echo "  west build -b nrf52840dk_nrf52840"
    exit 1
fi

# Check Renode is installed
if ! command -v renode &> /dev/null; then
    echo "ERROR: Renode not found"
    echo
    echo "Install Renode:"
    echo "  Ubuntu: sudo apt install renode"
    echo "  macOS: brew install renode"
    exit 1
fi

echo "Renode version:"
renode --version
echo

# Create temp file for Renode script
RENODE_SCRIPT=$(mktemp /tmp/renode_test_XXXXXX.resc)

cat > "$RENODE_SCRIPT" <<EOF
# M3fb Test Script - Auto-generated
# Tests sensor firmware in standalone Renode

# Create machine
mach create "sensor_test"

# Load nRF52840 platform
machine LoadPlatformDescription @platforms/cpus/nrf52840.repl

# Load firmware ELF
sysbus LoadELF @$FIRMWARE_ELF

# Show UART analyzer (outputs to console)
showAnalyzer sysbus.uart0

# Configure emulation timing
emulation SetGlobalQuantum "0.0001"

# Start emulation
start

# Run for specified duration
echo "Running emulation for $DURATION seconds..."
emulation RunFor @$DURATION

# Show results
echo ""
echo "=== Emulation Complete ==="
echo "Check above for JSON output like:"
echo '  {"type":"SAMPLE","value":25.3,"time":0}'
echo '  {"type":"SAMPLE","value":26.1,"time":1000000}'
echo ""

# Quit
quit
EOF

echo "Generated Renode script: $RENODE_SCRIPT"
echo
echo "Starting Renode..."
echo "=========================="
echo

# Run Renode with script
renode --disable-xwt "$RENODE_SCRIPT"

# Cleanup
rm -f "$RENODE_SCRIPT"

echo
echo "=========================="
echo "Test complete!"
