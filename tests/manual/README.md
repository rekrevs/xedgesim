# Manual Docker Protocol Tests

This directory contains manual test scripts for debugging the M3h Docker protocol adapter.

## Prerequisites

- Docker installed and running
- xedgesim/echo-service image built:
  ```bash
  docker build -t xedgesim/echo-service -f containers/examples/Dockerfile.echo .
  ```

## Test Scripts

### test_docker_protocol_manual.sh

Manual test of the protocol adapter using shell commands and Python subprocess.

**Usage:**
```bash
bash tests/manual/test_docker_protocol_manual.sh
```

**What it tests:**
1. INIT command - sends INIT and expects READY
2. Full protocol - INIT → ADVANCE → SHUTDOWN
3. Protocol with events - ADVANCE with actual event data
4. Python subprocess test - mimics DockerProtocolAdapter behavior

**Expected output:**
- All tests should show protocol messages being sent and received
- Test 4 (Python subprocess) most closely matches the actual adapter behavior
- If Test 4 times out, it confirms the ADVANCE timeout issue

## Debugging the ADVANCE Timeout

### Issue
- INIT works perfectly (READY received)
- ADVANCE times out (DONE not received)
- Container processes commands (confirmed in stderr logs)

### Possible Causes

1. **Buffering Issue**
   - Python stdout buffering preventing immediate flush
   - Fixed by adding `-u` flag (unbuffered mode)
   - Also changed Popen bufsize to 0

2. **Timing Issue**
   - select.select() timeout too aggressive
   - Currently using 0.1s poll interval

3. **Line Ending Issue**
   - Mismatch between \n and \r\n
   - Should not be an issue with text mode

4. **File Descriptor Issue**
   - docker exec may not properly connect stdin/stdout
   - Try alternatives: docker attach, running service as CMD

### Manual Debug Steps

1. **Test with simple echo:**
   ```bash
   docker run -d --name test xedgesim/echo-service
   echo "INIT {}" | docker exec -i test python -u -m service
   ```

2. **Test with strace:**
   ```bash
   docker exec -i test strace -e trace=write,read python -u -m service <<EOF
   INIT {}
   ADVANCE 1000
   []
   EOF
   ```

3. **Test container logs:**
   ```bash
   docker logs test 2>&1
   ```

4. **Test with timeout:**
   ```bash
   timeout 5 docker exec -i test python -u -m service <<EOF
   INIT {}
   ADVANCE 1000
   []
   SHUTDOWN
   EOF
   ```

### Verbose Logging

The DockerProtocolAdapter now has verbose logging:
- Logs every command sent
- Logs every response received
- Logs waiting states
- Logs timeout with attempt count

**Run integration tests with logging:**
```bash
pytest tests/integration/test_m3h_docker_protocol.py -v -s
```

The `-s` flag shows all print() output, including verbose logging.

## Alternative Approaches

If unbuffered mode doesn't solve the timeout:

### Option 1: Use sockets instead of stdin/stdout
- Container exposes TCP port
- Coordinator connects via socket
- More reliable but requires port management

### Option 2: Run service as main CMD
- Don't use `docker exec`
- Start container with service as main process
- Attach to stdin/stdout via `docker attach`

### Option 3: Use Docker SDK Python client
- Use `client.containers.run()` with `stdin_open=True`
- Attach to stdin/stdout via `container.attach()`
- More Pythonic API

## Expected Next Steps

1. Run manual test script with Docker access
2. Review verbose logging output
3. Identify where timeout occurs (reading DONE vs reading events JSON)
4. If buffering confirmed, verify `-u` flag fixes it
5. Re-run integration tests
6. Update M3h-report.md with final results
