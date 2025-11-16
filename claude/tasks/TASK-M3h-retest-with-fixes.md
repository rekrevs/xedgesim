# TASK: M3h Retest with Unbuffered I/O Fixes

**Task ID:** M3h-retest-with-fixes
**Created:** 2025-11-15
**Assigned to:** Testing Agent
**Priority:** P0 (blocks M3h completion)
**Type:** Integration Testing - Retest

---

## Context

Development agent has identified and fixed the ADVANCE timeout issue found in initial M3h testing.

**Original issue** (from TASK-M3h-protocol-integration-tests):
- INIT works perfectly (1/1 test passing)
- ADVANCE times out waiting for DONE response (5/6 tests failing)
- Container processes commands but coordinator doesn't receive response
- Root cause: Buffering in `docker exec` stdin/stdout

**Fixes applied** (commits 7dad0c9, ae7e3c1, 74e01e3):
1. Unbuffered I/O: Added `-u` flag and `bufsize=0`
2. Verbose logging: Traces entire protocol flow
3. Manual test script: `tests/manual/test_docker_protocol_manual.sh`

---

## Objectives

1. **Rebuild echo service image** (code unchanged, but good practice)
2. **Run manual test script** to verify unbuffered mode fixes timeout
3. **Re-run integration tests with verbose logging** to see protocol flow
4. **Verify all 7 integration tests pass**
5. **Document results** (update existing results file or create new one)

---

## Test Commands

### 1. Rebuild Image
```bash
docker build -t xedgesim/echo-service -f containers/examples/Dockerfile.echo .
```

### 2. Run Manual Test Script
```bash
bash tests/manual/test_docker_protocol_manual.sh
```

**Expected:** All 4 tests should pass, especially Test 4 (Python subprocess)

### 3. Run Integration Tests with Verbose Logging
```bash
pytest tests/integration/test_m3h_docker_protocol.py -v -s
```

**The `-s` flag is critical** - it shows all print() output from verbose logging

**Expected:** All 7 tests should now pass:
- `test_protocol_init_success` ✅ (already passing)
- `test_protocol_advance_no_events` ← Should now pass
- `test_protocol_advance_with_events` ← Should now pass
- `test_protocol_event_transformation` ← Should now pass
- `test_protocol_virtual_time` ← Should now pass
- `test_protocol_shutdown_clean` ← Should now pass
- `test_protocol_error_handling` ← May still fail (error handling edge case)

### 4. Check Verbose Logging Output

With `-s` flag, you should see:
```
[DockerProtocolAdapter] Connected to container ...
[DockerProtocolAdapter] test_echo initialized (READY)
[DockerProtocolAdapter] Sending: ADVANCE 1000000
[DockerProtocolAdapter] Sending events: []
[DockerProtocolAdapter] Waiting for DONE response...
[DockerProtocolAdapter] Data available on stdout after X attempts (Y.YYs)
[DockerProtocolAdapter] Received: DONE
[DockerProtocolAdapter] Waiting for events JSON...
[DockerProtocolAdapter] Received events: []
[DockerProtocolAdapter] Received 0 events from container
```

If timeout still occurs, you'll see:
```
[DockerProtocolAdapter] Still waiting for stdout... (5.0s elapsed)
[DockerProtocolAdapter] Still waiting for stdout... (10.0s elapsed)
...
[DockerProtocolAdapter] TIMEOUT after 30.00s, 300 attempts
```

---

## Success Criteria

**Primary:**
- [ ] Manual test script: All 4 tests pass
- [ ] Integration tests: At least 6/7 passing (error handling may still be edge case)
- [ ] No ADVANCE timeouts
- [ ] Verbose logging shows DONE received

**Secondary:**
- [ ] Protocol messages clearly visible in logs
- [ ] Timing information reasonable (< 1s for ADVANCE)
- [ ] No stderr errors from container

---

## If Tests Pass

1. **Update results file:**
   - Option A: Append to `claude/results/TASK-M3h-protocol-integration-tests.md`
   - Option B: Create new `claude/results/TASK-M3h-retest-with-fixes.md`
   - Include: Test output, timing, verbose logging samples

2. **Mark M3h as complete:**
   - All acceptance criteria met
   - Protocol works end-to-end
   - Ready for production use

3. **Next steps:**
   - Development agent can proceed with M3i
   - Consider creating example service (MQTT, ML inference)

---

## If Tests Still Fail

### Analyze Verbose Logging

1. **Check where timeout occurs:**
   - Is `Sending: ADVANCE` printed? (Yes → command sent)
   - Is `Data available on stdout` printed? (No → buffering still an issue)
   - Is `Received: DONE` printed? (No → response not received)

2. **Check manual test results:**
   - Does Test 4 (Python subprocess) pass?
   - If yes: Integration test setup issue
   - If no: Buffering issue persists

3. **Check container stderr:**
   - Does container show it's processing ADVANCE?
   - Does container show it's sending DONE?
   - Any Python errors or warnings?

### Alternative Approaches to Try

**Option 1: Line-ending issue**
```python
# Try explicit line endings
self._write_line(f"ADVANCE {target_time_us}\r\n")
```

**Option 2: Explicit flush in container**
```python
# In containers/protocol_adapter.py _write_line
sys.stdout.write(line + '\n')
sys.stdout.flush()
os.fsync(sys.stdout.fileno())  # Force OS-level flush
```

**Option 3: Use Docker SDK instead of subprocess**
```python
import docker
client = docker.from_env()
container = client.containers.get(container_id)

# Attach socket for stdin/stdout
sock = container.attach_socket(params={'stdin': 1, 'stdout': 1, 'stream': 1})
```

**Option 4: Run service as main CMD (not docker exec)**
```dockerfile
# In Dockerfile
CMD ["python", "-u", "-m", "service"]
```
Then use `docker attach` instead of `docker exec`

### Report Back to Development Agent

If tests still fail, provide:
1. Full verbose logging output (paste entire pytest output with `-s`)
2. Manual test script results
3. Container stderr output
4. Which alternative approach you recommend trying

---

## Deliverables

**If successful:**
- [ ] Updated test results file
- [ ] Confirmation all tests pass
- [ ] Timing benchmarks (how fast is protocol now?)
- [ ] Screenshots/logs showing success

**If still failing:**
- [ ] Detailed analysis of verbose logging
- [ ] Recommendation for alternative approach
- [ ] Any additional debugging info gathered

---

## Estimated Time

- Rebuild + manual test: 5 minutes
- Integration tests: 5-10 minutes
- Analysis/documentation: 10-15 minutes

**Total: 20-30 minutes** (if tests pass)
**Total: 1-2 hours** (if need to debug further)

---

## Notes

- The unbuffered I/O fix (`-u` flag + `bufsize=0`) is a standard solution for this type of issue
- High confidence this will resolve the timeout
- If not, the verbose logging will clearly show where the issue is
- Manual test script allows quick iteration without full test suite

---

**Development Agent Status:** Waiting for test results before marking M3h complete
**Blocks:** M3h completion, M3i start (though M3i can proceed in parallel)
