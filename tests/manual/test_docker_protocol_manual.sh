#!/bin/bash
#
# Manual Docker Protocol Test Script
#
# This script manually tests the protocol adapter by sending commands to a
# Docker container running the echo service via stdin and reading responses
# from stdout.
#
# Usage:
#   1. Build the echo service image:
#      docker build -t xedgesim/echo-service -f containers/examples/Dockerfile.echo .
#
#   2. Run this script:
#      bash tests/manual/test_docker_protocol_manual.sh
#

set -e  # Exit on error

echo "=== Docker Protocol Manual Test ==="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if image exists
if ! docker images | grep -q "xedgesim/echo-service"; then
    echo -e "${RED}ERROR: xedgesim/echo-service image not found${NC}"
    echo "Build it with:"
    echo "  docker build -t xedgesim/echo-service -f containers/examples/Dockerfile.echo ."
    exit 1
fi

echo -e "${GREEN}✓ Found xedgesim/echo-service image${NC}"
echo ""

# Start container
echo "Starting container..."
CONTAINER_ID=$(docker run -d --name test-echo-manual xedgesim/echo-service)
echo -e "${GREEN}✓ Container started: ${CONTAINER_ID:0:12}${NC}"
echo ""

# Cleanup function
cleanup() {
    echo ""
    echo "Cleaning up..."
    docker stop test-echo-manual > /dev/null 2>&1 || true
    docker rm test-echo-manual > /dev/null 2>&1 || true
    echo -e "${GREEN}✓ Cleanup complete${NC}"
}
trap cleanup EXIT

# Wait for container to be ready
sleep 1

echo "=== Test 1: INIT command ==="
echo ""
echo "Sending INIT command..."
echo 'INIT {"seed": 42}' | docker exec -i test-echo-manual python -u -m service &
EXEC_PID=$!

# Give it time to process
sleep 2

# Check if we got READY
echo ""
echo -e "${YELLOW}Expected output: READY${NC}"
echo ""

wait $EXEC_PID 2>/dev/null || true

echo ""
echo "=== Test 2: INIT + ADVANCE (no events) ==="
echo ""

echo "Sending full protocol sequence..."
(
cat <<'PROTOCOL'
INIT {"seed": 42}
ADVANCE 1000000
[]
SHUTDOWN
PROTOCOL
) | docker exec -i test-echo-manual python -u -m service

echo ""
echo -e "${YELLOW}Expected output:${NC}"
echo -e "${YELLOW}  READY${NC}"
echo -e "${YELLOW}  DONE${NC}"
echo -e "${YELLOW}  []${NC}"
echo ""

echo "=== Test 3: INIT + ADVANCE (with events) ==="
echo ""

# Start new container for this test
docker stop test-echo-manual > /dev/null 2>&1
docker rm test-echo-manual > /dev/null 2>&1
CONTAINER_ID=$(docker run -d --name test-echo-manual xedgesim/echo-service)
sleep 1

echo "Sending protocol with events..."
(
cat <<'PROTOCOL'
INIT {"seed": 42}
ADVANCE 1000000
[{"timestamp_us": 1000000, "event_type": "test_event", "source": "test", "destination": "echo_service", "payload": {"value": 123}}]
SHUTDOWN
PROTOCOL
) | docker exec -i test-echo-manual python -u -m service

echo ""
echo -e "${YELLOW}Expected output:${NC}"
echo -e "${YELLOW}  READY${NC}"
echo -e "${YELLOW}  DONE${NC}"
echo -e "${YELLOW}  [{\"timestamp_us\": ..., \"event_type\": \"echo_test_event\", ...}]${NC}"
echo ""

echo "=== Test 4: Interactive test ==="
echo ""
echo "Testing with Python subprocess directly..."

python3 << 'PYTHON_TEST'
import subprocess
import time

# Start container
proc = subprocess.Popen(
    ['docker', 'exec', '-i', 'test-echo-manual', 'python', '-u', '-m', 'service'],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    bufsize=0
)

print("Sending INIT...")
proc.stdin.write("INIT {\"seed\": 42}\n")
proc.stdin.flush()

print("Reading response...")
response = proc.stdout.readline().strip()
print(f"  Response: {response}")

if response == "READY":
    print("✓ INIT successful")

    print("\nSending ADVANCE...")
    proc.stdin.write("ADVANCE 1000000\n")
    proc.stdin.flush()

    print("Sending events...")
    proc.stdin.write("[]\n")
    proc.stdin.flush()

    print("Reading DONE response...")
    # Try to read with timeout
    import select
    ready, _, _ = select.select([proc.stdout], [], [], 5.0)
    if ready:
        response = proc.stdout.readline().strip()
        print(f"  Response: {response}")

        if response == "DONE":
            print("✓ ADVANCE successful")
            events = proc.stdout.readline().strip()
            print(f"  Events: {events}")
        else:
            print(f"✗ Expected DONE, got: {response}")
    else:
        print("✗ Timeout waiting for DONE")
        # Read stderr
        import fcntl, os
        flags = fcntl.fcntl(proc.stderr, fcntl.F_GETFL)
        fcntl.fcntl(proc.stderr, fcntl.F_SETFL, flags | os.O_NONBLOCK)
        try:
            stderr = proc.stderr.read()
            if stderr:
                print(f"  Container stderr: {stderr}")
        except:
            pass
else:
    print(f"✗ Expected READY, got: {response}")

print("\nSending SHUTDOWN...")
proc.stdin.write("SHUTDOWN\n")
proc.stdin.flush()

proc.wait(timeout=2)
print("✓ Process exited")
PYTHON_TEST

echo ""
echo "=== All tests complete ==="
echo ""
echo "If Test 4 shows a timeout, the issue is confirmed."
echo "Check the verbose logging output when running the actual tests."
