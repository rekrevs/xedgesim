#!/bin/bash
# Test script for Docker integration on macOS
# Tests M2a (Docker lifecycle) and M2b (socket communication)

set -e  # Exit on error

echo "======================================================================"
echo "xEdgeSim Docker Integration Tests (macOS)"
echo "======================================================================"
echo ""

# Check Docker is running
echo "1. Checking Docker daemon..."
if ! docker info > /dev/null 2>&1; then
    echo "ERROR: Docker daemon not running. Please start Docker Desktop."
    exit 1
fi
echo "✓ Docker daemon is running"
echo ""

# Build echo service image
echo "2. Building echo service container..."
cd containers/echo-service
docker build -t xedgesim/echo:latest .
cd ../..
echo "✓ Echo service image built"
echo ""

# Run M2a tests (Docker lifecycle)
echo "3. Running M2a tests (Docker lifecycle)..."
pytest tests/stages/M2a/test_docker_node_lifecycle.py -v
echo "✓ M2a lifecycle tests passed"
echo ""

# Run M2a basic tests (no Docker required)
echo "4. Running M2a basic tests..."
python tests/stages/M2a/test_docker_node_basic.py
echo "✓ M2a basic tests passed"
echo ""

# Run M2b tests (socket communication)
echo "5. Running M2b tests (socket interface)..."
python tests/stages/M2b/test_socket_interface.py
echo "✓ M2b socket tests passed"
echo ""

# Manual echo service test
echo "6. Testing echo service manually..."
echo "   Starting echo container..."
docker run -d --name test-echo -p 5000:5000 xedgesim/echo:latest
sleep 2

echo "   Sending test message..."
python -c "
import socket, json, time
time.sleep(1)  # Give container time to start
s = socket.socket()
s.connect(('localhost', 5000))
test_msg = {'test': 'hello', 'time': 12345}
s.sendall((json.dumps(test_msg) + '\n').encode())
response = s.recv(1024).decode()
s.close()
print(f'   Sent: {test_msg}')
print(f'   Received: {response.strip()}')
assert json.loads(response) == test_msg, 'Echo mismatch!'
print('   ✓ Echo test passed')
"

echo "   Cleaning up..."
docker stop test-echo > /dev/null
docker rm test-echo > /dev/null
echo "✓ Echo service manual test passed"
echo ""

# Run regression tests
echo "7. Running regression tests..."
python tests/stages/M1e/test_network_metrics.py
python tests/stages/M1d/test_latency_network_model.py
echo "✓ Regression tests passed"
echo ""

echo "======================================================================"
echo "All Docker integration tests PASSED!"
echo "======================================================================"
echo ""
echo "Summary:"
echo "  - M2a: Docker lifecycle ✓"
echo "  - M2b: Socket communication ✓"
echo "  - Echo service ✓"
echo "  - Regression tests ✓"
echo ""
echo "Ready to continue with M2c (MQTT integration)"
