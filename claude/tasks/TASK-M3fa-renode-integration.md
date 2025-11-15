# TASK: M3fa Renode Integration Testing

**Status:** PENDING
**Created:** 2025-11-15
**Stage:** M3fa - Renode Adapter and Monitor Protocol
**Priority:** HIGH (blocks M3fb)

---

## Context

M3fa has implemented the RenodeNode adapter class that manages Renode emulator processes via the monitor protocol. All unit tests (43/43) pass with mocking, but we need to validate integration with actual Renode.

**What was implemented:**
- `sim/device/renode_node.py` - RenodeNode class
- Monitor protocol communication (TCP socket)
- Virtual time advancement
- UART output parsing
- Process lifecycle management

**Files involved:**
- `sim/device/renode_node.py` (production code)
- `tests/stages/M3fa/test_renode_node.py` (unit tests - already passing)
- `tests/stages/M3fa/test_renode_integration.py` (NEW - integration tests for you to create and run)

---

## Your Task

Create and run integration tests with actual Renode installation to validate:

1. **Renode Installation**: Install Renode 1.14.0+ if not already installed
2. **Integration Tests**: Create `tests/stages/M3fa/test_renode_integration.py` with tests that:
   - Start real Renode process
   - Connect to monitor port
   - Send time advancement commands
   - Verify responses
   - Clean up processes

3. **Test Execution**: Run integration tests and verify they pass
4. **Debug Issues**: Fix any issues found (in code or tests)
5. **Document Results**: Record test output, issues, and fixes

---

## Prerequisites

### Renode Installation

**Ubuntu/Debian:**
```bash
wget https://github.com/renode/renode/releases/download/v1.14.0/renode_1.14.0_amd64.deb
sudo apt install ./renode_1.14.0_amd64.deb
renode --version
```

**macOS:**
```bash
brew install renode
renode --version
```

**Verification:**
```bash
# Should show Renode version 1.14.0 or later
renode --version
```

### Test Firmware

For basic integration tests, we can use Renode's built-in test platforms without custom firmware yet.  The tests should use Renode's example platforms to validate our adapter works.

---

## Integration Tests to Create

Create `tests/stages/M3fa/test_renode_integration.py` with these tests:

### Test 1: Process Lifecycle
```python
def test_renode_process_starts_and_stops():
    """Test RenodeNode can start and stop real Renode process."""
    # Use Renode's built-in test platform
    config = {
        'platform': get_test_platform_path(),  # Helper to find renode test platform
        'firmware': get_test_firmware_path(),  # Helper for test firmware
        'monitor_port': 12345,
        'working_dir': '/tmp'
    }

    node = RenodeNode('test', config)
    node.start()

    # Verify process running
    assert node.renode_process is not None
    assert node.renode_process.poll() is None

    # Verify socket connected
    assert node.monitor_socket is not None

    node.stop()

    # Verify cleanup
    assert node.renode_process.poll() is not None  # Exited
```

### Test 2: Monitor Protocol Communication
```python
def test_monitor_protocol_basic_commands():
    """Test can send commands to Renode monitor."""
    node = create_test_renode_node()
    node.start()

    try:
        # Send a simple query command
        response = node._send_command('version')
        assert 'Renode' in response
        assert '(monitor)' in response

        # Send help command
        response = node._send_command('help')
        assert 'help' in response or 'available commands' in response.lower()

    finally:
        node.stop()
```

### Test 3: Time Advancement
```python
def test_time_advancement_with_real_renode():
    """Test virtual time advancement works with real Renode."""
    node = create_test_renode_node()
    node.start()

    try:
        # Advance 1ms
        initial_time = node.current_time_us
        events = node.advance(initial_time + 1000)

        assert node.current_time_us == initial_time + 1000

        # Advance 1s
        events = node.advance(initial_time + 1_000_000)
        assert node.current_time_us == initial_time + 1_000_000

    finally:
        node.stop()
```

### Test 4: Script Generation and Loading
```python
def test_generated_script_loads_in_renode():
    """Test generated .resc script is valid and loads in Renode."""
    node = create_test_renode_node()

    # Generate script (doesn't start Renode)
    script_path = node._create_renode_script()

    # Verify script exists
    assert script_path.exists()

    # Verify script content is valid
    content = script_path.read_text()
    assert 'mach create' in content
    assert 'LoadPlatformDescription' in content

    # Now start with this script (validates it's loadable)
    node.start()
    node.stop()
```

### Test 5: Error Handling
```python
def test_connection_fails_gracefully():
    """Test error handling when cannot connect to monitor."""
    config = {
        'platform': get_test_platform_path(),
        'firmware': get_test_firmware_path(),
        'monitor_port': 9999,  # Likely unused port
        'working_dir': '/tmp'
    }

    node = RenodeNode('test', config)

    # Start will fail to connect
    # (We'll mock Renode failure by using wrong port or killing process)
    # Test should raise RenodeConnectionError appropriately

    # Implementation depends on how we can simulate failure
```

---

## Helper Functions to Implement

You'll need helper functions to locate Renode test resources:

```python
def get_test_platform_path():
    """Find a Renode test platform file."""
    # Renode usually has test platforms in its installation
    # Try common locations:
    # - /opt/renode/platforms/
    # - /usr/local/share/renode/platforms/
    # - $(brew --prefix)/share/renode/platforms/ (macOS)

    # For testing, any simple platform works
    # Example: nrf52840.repl or cortex-m.repl
    pass

def get_test_firmware_path():
    """Find or create minimal test firmware."""
    # Simplest: empty ELF or Renode test binary
    # Could create minimal empty file as placeholder
    # Renode can load without executing if we don't run
    pass

def create_test_renode_node():
    """Create RenodeNode with test configuration."""
    import tempfile
    temp_dir = tempfile.mkdtemp()

    config = {
        'platform': get_test_platform_path(),
        'firmware': get_test_firmware_path(),
        'monitor_port': 12345,
        'working_dir': temp_dir
    }

    return RenodeNode('test_node', config)
```

---

## Expected Results

### Success Criteria:
- [ ] Renode installed and `renode --version` works
- [ ] Integration test file created
- [ ] At least 3-5 integration tests implemented
- [ ] All integration tests pass
- [ ] No resource leaks (processes cleaned up)
- [ ] Test output documented in results file

### If Tests Fail:

1. **Renode won't start:**
   - Check Renode installation: `renode --version`
   - Check paths in config
   - Try running Renode manually: `renode --disable-xwt --port 12345`

2. **Connection timeout:**
   - Increase connection retry delays
   - Check firewall/port availability
   - Verify monitor port argument works: `renode --help | grep port`

3. **Script loading fails:**
   - Validate .resc syntax manually
   - Try loading in Renode REPL
   - Check platform/firmware paths are absolute

4. **Time advancement doesn't work:**
   - Check Renode quantum settings
   - Verify `emulation RunFor` command syntax
   - Test command manually in Renode monitor

---

## Document Results

Create `claude/results/TASK-M3fa-renode-integration.md` with:

### Required Sections:

1. **Status**: ✅ SUCCESS / ❌ FAILED / ⚠️ PARTIAL

2. **Environment:**
   - OS and version
   - Renode version installed
   - Python version

3. **Test Results:**
   ```bash
   pytest tests/stages/M3fa/test_renode_integration.py -v
   ```
   - Copy full output
   - Note any failures
   - Include timing information

4. **Issues Found:**
   - List any bugs or issues discovered
   - Include error messages
   - Note any code that needed fixing

5. **Fixes Applied:**
   - Describe any changes made to production code
   - Show diffs for clarity
   - Explain rationale

6. **Commits Made:**
   ```bash
   git log --oneline --author="$(git config user.name)" | head -5
   ```
   - List all commits you made
   - Include commit messages

7. **Next Steps for Developer Agent:**
   - Any recommendations
   - Issues that need developer attention
   - Suggestions for M3fb

---

## Deliverables

When complete, you should have:

1. ✅ Renode installed and working
2. ✅ `tests/stages/M3fa/test_renode_integration.py` created
3. ✅ Integration tests passing
4. ✅ `claude/results/TASK-M3fa-renode-integration.md` completed
5. ✅ Code fixes committed (if any)
6. ✅ All committed and pushed to branch

---

## Timeline

**Estimated effort:** 1-2 hours
- 15 min: Renode installation and verification
- 30 min: Writing integration tests
- 15-30 min: Running and debugging tests
- 15 min: Documenting results

---

## Questions or Issues?

If you encounter blockers:
1. Document the issue in results file
2. Mark status as PARTIAL
3. Explain what worked and what didn't
4. Provide enough detail for developer agent to help

---

## Notes

- These are **integration tests**, not unit tests
  - They require real Renode installation
  - They may be slower (seconds vs milliseconds)
  - They validate actual protocol behavior

- Keep tests simple
  - Focus on validating our adapter, not Renode itself
  - Use Renode's test resources when possible
  - Don't need complex firmware yet (M3fb will create that)

- If Renode installation is problematic:
  - Try Docker: `docker run -it antmicro/renode`
  - Document issues for different platforms
  - Partial success is acceptable (document what works)

---

**Status:** PENDING
**Next action:** Testing agent reads this file and begins work
