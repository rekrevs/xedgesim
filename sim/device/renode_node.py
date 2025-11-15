#!/usr/bin/env python3
"""
Renode Device Node Adapter

This module provides integration between the xEdgeSim coordinator and Renode,
an instruction-level emulator for ARM/RISC-V microcontrollers.

Architecture:
    Coordinator ← socket → RenodeNode ← monitor protocol → Renode process
                                              ↓
                                          ARM firmware

The RenodeNode class manages:
- Renode process lifecycle (start, stop)
- Monitor protocol communication (TCP socket)
- Virtual time synchronization
- UART output capture and parsing

Design principles (from architecture.md and node-determinism.md):
- Virtual time only (no wall-clock time)
- Event-driven architecture
- Conservative synchronous lockstep
- Deterministic execution (seeded RNG in firmware)

Author: xEdgeSim Project
Created: 2025-11-15
Stage: M3fa
"""

import os
import socket
import subprocess
import time
import json
import re
import select
from typing import List, Optional, Dict, Any
from pathlib import Path
from dataclasses import dataclass, asdict


@dataclass
class Event:
    """Simulation event from device firmware."""
    type: str              # Event type (e.g., "SAMPLE", "UART", "METRIC")
    time_us: int          # Event time in microseconds (virtual time)
    src: str              # Source node ID
    dst: Optional[str] = None         # Destination node ID (optional)
    payload: Optional[Any] = None     # Event payload (varies by type)
    size_bytes: int = 0   # Payload size in bytes


class RenodeConnectionError(Exception):
    """Raised when cannot connect to Renode monitor port."""
    pass


class RenodeTimeoutError(Exception):
    """Raised when Renode command times out."""
    pass


class RenodeNode:
    """
    Adapter for Renode-emulated ARM/RISC-V device nodes.

    This class wraps a Renode emulator process and provides a standard
    simulation node interface compatible with xEdgeSim's coordinator.

    Key responsibilities:
    1. Start/stop Renode emulator process
    2. Generate Renode script (.resc) from configuration
    3. Communicate via Renode monitor protocol (TCP socket)
    4. Advance virtual time in lockstep with coordinator
    5. Parse UART output into simulation events

    Usage:
        config = {
            'platform': 'path/to/nrf52840.repl',
            'firmware': 'path/to/sensor.elf',
            'monitor_port': 1234
        }
        node = RenodeNode('sensor_1', config)
        node.start()
        events = node.advance(1000000)  # Advance 1 second
        node.stop()

    Thread safety: Not thread-safe. Single-threaded use only.
    """

    def __init__(self, node_id: str, config: dict):
        """
        Initialize Renode node adapter.

        Args:
            node_id: Unique node identifier (e.g., "sensor_1")
            config: Node configuration dict with keys:
                - platform: Path to .repl platform description file
                - firmware: Path to .elf firmware file
                - monitor_port: TCP port for monitor protocol (default 1234)
                - renode_path: Path to renode executable (default 'renode')
                - working_dir: Working directory for Renode (default /tmp)
                - uart_device: UART device name (default 'sysbus.uart0')
                - time_quantum_us: Renode time quantum in microseconds (default 10)

        Raises:
            ValueError: If required config keys are missing
            FileNotFoundError: If platform or firmware files don't exist
        """
        self.node_id = node_id
        self.config = config
        self.current_time_us = 0  # Virtual time (not wall-clock!)

        # Validate and extract configuration
        self._validate_config()

        self.platform_file = Path(config['platform'])
        self.firmware_path = Path(config['firmware'])
        self.monitor_port = config.get('monitor_port', 1234)
        self.renode_path = config.get('renode_path', 'renode')
        self.working_dir = Path(config.get('working_dir', '/tmp'))
        self.uart_device = config.get('uart_device', 'sysbus.uart0')
        self.time_quantum_us = config.get('time_quantum_us', 10)

        # Process and communication state
        self.renode_process: Optional[subprocess.Popen] = None
        self.monitor_socket: Optional[socket.socket] = None
        self.script_path: Optional[Path] = None
        self.log_file_path: Optional[Path] = None

        # UART buffer for incomplete lines
        self.uart_buffer = ""
        self.log_file_position = 0  # Track position in log file for incremental reads

    def _validate_config(self):
        """
        Validate configuration has required keys and files exist.

        Raises:
            ValueError: If required keys missing
            FileNotFoundError: If files don't exist
        """
        required_keys = ['platform', 'firmware']
        for key in required_keys:
            if key not in self.config:
                raise ValueError(f"Missing required config key: {key}")

        # Check files exist (will check when starting, not at init)
        # This allows for late binding of paths

    def start(self):
        """
        Start Renode emulator process and connect to monitor.

        This method:
        1. Validates platform and firmware files exist
        2. Generates Renode script (.resc)
        3. Starts Renode process in headless mode
        4. Waits for Renode to be ready
        5. Connects to monitor port
        6. Initializes emulation (sends 'start' command)

        Raises:
            FileNotFoundError: If platform or firmware files not found
            RenodeConnectionError: If cannot connect to monitor
            subprocess.CalledProcessError: If Renode process fails to start

        Note: Blocks until Renode is ready (typically 2-3 seconds)
        """
        # Validate files exist
        if not self.platform_file.exists():
            raise FileNotFoundError(
                f"Platform file not found: {self.platform_file}"
            )
        if not self.firmware_path.exists():
            raise FileNotFoundError(
                f"Firmware file not found: {self.firmware_path}"
            )

        # Generate Renode script
        self.script_path = self._create_renode_script()

        # Start Renode process
        cmd = [
            self.renode_path,
            '--disable-xwt',  # No GUI (headless mode)
            '--port', str(self.monitor_port),  # Monitor port
            str(self.script_path)
        ]

        print(f"[RenodeNode:{self.node_id}] Starting Renode process...")
        print(f"[RenodeNode:{self.node_id}] Command: {' '.join(cmd)}")

        self.renode_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(self.working_dir)
        )

        # Wait for Renode to start (process should not exit immediately)
        time.sleep(0.5)
        if self.renode_process.poll() is not None:
            # Process already exited - something wrong
            stdout, stderr = self.renode_process.communicate()
            raise subprocess.CalledProcessError(
                self.renode_process.returncode,
                cmd,
                stdout,
                stderr
            )

        # Wait a bit more for monitor port to open
        time.sleep(2.0)

        # Connect to monitor port
        self._connect_monitor()

        # Note: We don't send 'start' here because RunFor will start
        # the emulation automatically. Sending 'start' would cause
        # continuous execution which conflicts with time-stepped control.
        print(f"[RenodeNode:{self.node_id}] Ready for time-stepped execution")

    def _create_renode_script(self) -> Path:
        """
        Generate Renode .resc script for this node.

        The script:
        - Creates machine with node_id as name
        - Loads platform description (.repl)
        - Loads firmware (.elf)
        - Configures UART analyzer for output capture
        - Sets external time source mode for coordinator control

        Returns:
            Path to generated script file

        Example generated script:
            # xEdgeSim Renode Script - sensor_1
            mach create "sensor_1"
            machine LoadPlatformDescription @/path/to/nrf52840.repl
            sysbus LoadELF @/path/to/sensor.elf
            showAnalyzer sysbus.uart0
            emulation SetGlobalQuantum "0.00001"
            emulation SetAdvanceImmediately false
        """
        script_content = f"""# xEdgeSim Renode Script - {self.node_id}
# Auto-generated by RenodeNode
# Created: {time.strftime('%Y-%m-%d %H:%M:%S')}

# Create machine
mach create "{self.node_id}"

# Load platform description
machine LoadPlatformDescription @{self.platform_file.absolute()}

# Load firmware ELF
sysbus LoadELF @{self.firmware_path.absolute()}

# Configure UART analyzer (for output capture in GUI mode)
showAnalyzer {self.uart_device}

# Configure UART file backend (captures actual UART data to file)
# The 'true' parameter enables immediate flushing
{self.uart_device} CreateFileBackend @{self.working_dir.absolute()}/uart_data.txt true

# Configure external time source (for coordinator control)
# Quantum: minimum time step in virtual seconds
emulation SetGlobalQuantum "{self.time_quantum_us / 1_000_000.0}"

# Note: We don't use SetAdvanceImmediately false because it prevents
# the start command from working properly. Instead, we control time
# advancement explicitly using start followed by RunFor commands.

# Start emulation briefly to boot firmware, then pause for time-stepping
# This allows firmware to initialize before coordinator takes control
start
pause

# Ready for time stepping from coordinator
"""

        # Write script to temporary file
        script_path = self.working_dir / f'xedgesim_{self.node_id}.resc'
        with open(script_path, 'w') as f:
            f.write(script_content)

        # Set UART data file path (will be created by Renode's CreateFileBackend)
        self.log_file_path = self.working_dir / 'uart_data.txt'

        print(f"[RenodeNode:{self.node_id}] Created script: {script_path}")
        print(f"[RenodeNode:{self.node_id}] UART data will be written to: {self.log_file_path}")
        return script_path

    def _connect_monitor(self, max_retries: int = 3, retry_delay: float = 1.0):
        """
        Connect to Renode monitor port via TCP socket.

        Args:
            max_retries: Maximum connection attempts
            retry_delay: Delay between retries (seconds)

        Raises:
            RenodeConnectionError: If connection fails after retries
        """
        for attempt in range(max_retries):
            try:
                print(
                    f"[RenodeNode:{self.node_id}] "
                    f"Connecting to monitor port {self.monitor_port} "
                    f"(attempt {attempt + 1}/{max_retries})..."
                )

                self.monitor_socket = socket.socket(
                    socket.AF_INET,
                    socket.SOCK_STREAM
                )
                self.monitor_socket.settimeout(5.0)  # 5 second timeout
                self.monitor_socket.connect(('localhost', self.monitor_port))

                print(f"[RenodeNode:{self.node_id}] Connected to monitor")
                return

            except (socket.timeout, ConnectionRefusedError) as e:
                if attempt < max_retries - 1:
                    print(
                        f"[RenodeNode:{self.node_id}] "
                        f"Connection failed: {e}, retrying..."
                    )
                    time.sleep(retry_delay)
                else:
                    raise RenodeConnectionError(
                        f"Failed to connect to Renode monitor port "
                        f"{self.monitor_port} after {max_retries} attempts"
                    ) from e

    def _send_command(
        self,
        cmd: str,
        timeout: float = 10.0
    ) -> str:
        """
        Send command to Renode monitor and receive response.

        The monitor protocol is text-based:
        - Send: "command\\n"
        - Receive: response text ending with "(monitor) " prompt

        Args:
            cmd: Command string (without newline)
            timeout: Response timeout in seconds

        Returns:
            Complete response text (including prompt)

        Raises:
            RenodeTimeoutError: If response not received in time
            RenodeConnectionError: If socket is not connected
        """
        if self.monitor_socket is None:
            raise RenodeConnectionError("Monitor socket not connected")

        # Send command with newline
        cmd_bytes = (cmd + '\n').encode('utf-8')
        self.monitor_socket.sendall(cmd_bytes)

        # Receive response until we see the prompt
        response = b''
        start_time = time.time()

        while True:
            # Check timeout
            elapsed = time.time() - start_time
            if elapsed > timeout:
                raise RenodeTimeoutError(
                    f"Command '{cmd}' timed out after {timeout}s"
                )

            # Receive chunk
            try:
                chunk = self.monitor_socket.recv(4096)
                if not chunk:
                    raise RenodeConnectionError(
                        "Monitor socket closed unexpectedly"
                    )
                response += chunk

                # Check if we have the prompt (indicates command complete)
                # Prompt can be (monitor) or (machine_name) depending on context
                # After script runs, prompt changes to (node_id)
                machine_prompt = f'({self.node_id})'.encode('utf-8')
                if b'(monitor)' in response or machine_prompt in response:
                    break

            except socket.timeout:
                # Socket timeout - continue waiting
                continue

        return response.decode('utf-8', errors='replace')

    def advance(self, target_time_us: int) -> List[Event]:
        """
        Advance Renode emulation to target virtual time.

        This implements the conservative synchronous lockstep algorithm:
        1. Calculate time delta from current to target
        2. Convert delta to Renode virtual seconds
        3. Send "emulation RunFor @<seconds>" command
        4. Wait for command completion
        5. Parse UART output for events
        6. Update current_time_us

        Args:
            target_time_us: Target virtual time in microseconds

        Returns:
            List of events generated during time advancement

        Raises:
            ValueError: If target_time_us < current_time_us (time going backwards)
            RenodeTimeoutError: If Renode doesn't respond
            RenodeConnectionError: If monitor connection lost

        Note: This method may take significant wall-clock time for large
              time deltas or complex firmware. Typical: 0.1-1s wall time
              per 1s virtual time.
        """
        if target_time_us < self.current_time_us:
            raise ValueError(
                f"Cannot advance backwards: target={target_time_us} < "
                f"current={self.current_time_us}"
            )

        if target_time_us == self.current_time_us:
            # No advancement needed
            return []

        # Calculate time delta
        delta_us = target_time_us - self.current_time_us

        # Convert to Renode virtual seconds
        virtual_seconds = self._us_to_virtual_seconds(delta_us)

        # Send RunFor command
        # Format: emulation RunFor @<seconds>
        # The @ prefix is Renode's syntax for numeric literals
        cmd = f'emulation RunFor @{virtual_seconds}'

        print(
            f"[RenodeNode:{self.node_id}] "
            f"Advancing {delta_us}us (virtual {virtual_seconds}s)..."
        )

        response = self._send_command(cmd, timeout=30.0)

        # UART output is written to log file by Renode's logFile command
        # Read new log file content (incremental read)
        uart_output = self._read_log_file(wait_time=0.1)

        # Debug logging (can be disabled in production)
        if uart_output:
            print(f"[RenodeNode:{self.node_id}] Captured {len(uart_output)} bytes from UART")

        # Parse UART output from log file
        events = self._parse_uart_output(uart_output, target_time_us)

        # Update current time
        self.current_time_us = target_time_us

        print(
            f"[RenodeNode:{self.node_id}] "
            f"Advanced to {target_time_us}us, {len(events)} events"
        )

        return events

    def _us_to_virtual_seconds(self, time_us: int) -> float:
        """
        Convert microseconds to Renode virtual seconds.

        Args:
            time_us: Time in microseconds

        Returns:
            Time in virtual seconds (float)

        Examples:
            1_000_000 us → 1.0 s
            1_000 us → 0.001 s (1 ms)
            100 us → 0.0001 s
        """
        return time_us / 1_000_000.0

    def _read_log_file(self, wait_time: float = 0.1) -> str:
        """
        Read new content from Renode UART log file.

        Reads only content added since last read (using file position tracking).
        This captures UART output that Renode writes via the 'logFile' command.

        Args:
            wait_time: Time to wait for log file to be written (seconds)

        Returns:
            String containing new log content since last read
        """
        if not self.log_file_path:
            return ""

        # Wait a bit for Renode to write to log file
        time.sleep(wait_time)

        try:
            # Check if log file exists yet
            if not self.log_file_path.exists():
                return ""

            # Open and seek to last position
            with open(self.log_file_path, 'r', encoding='utf-8', errors='replace') as f:
                f.seek(self.log_file_position)
                new_content = f.read()
                # Update position for next read
                self.log_file_position = f.tell()

            return new_content

        except Exception as e:
            print(
                f"[RenodeNode:{self.node_id}] "
                f"Warning: Error reading log file: {e}"
            )
            return ""

    def _parse_uart_output(
        self,
        uart_text: str,
        current_time: int
    ) -> List[Event]:
        """
        Parse UART output text into simulation events.

        The firmware outputs JSON-formatted events over UART:
        {"type":"SAMPLE","value":25.3,"time":1000000}

        This method:
        1. Extracts JSON objects from text (may have other output)
        2. Parses each JSON object as an event
        3. Sets event time and source

        Args:
            uart_text: Raw UART output text
            current_time: Current virtual time (for events without timestamp)

        Returns:
            List of parsed events

        Note: Non-JSON output is ignored. Malformed JSON is logged and skipped.
        """
        events = []

        # Add to buffer (may have incomplete lines from previous calls)
        self.uart_buffer += uart_text

        # Split into lines
        lines = self.uart_buffer.split('\n')

        # Keep last incomplete line in buffer
        self.uart_buffer = lines[-1]
        complete_lines = lines[:-1]

        # Parse each line
        for line in complete_lines:
            line = line.strip()
            if not line:
                continue

            # Try to find JSON object in line
            # Format: {...}
            json_match = re.search(r'\{.*\}', line)
            if not json_match:
                # Not JSON - could be Renode output, ignore
                continue

            try:
                data = json.loads(json_match.group())

                # Create event from JSON
                event = Event(
                    type=data.get('type', 'UART'),
                    time_us=data.get('time', current_time),
                    src=self.node_id,
                    dst=data.get('dst'),
                    payload=data,
                    size_bytes=len(line)
                )

                events.append(event)

            except json.JSONDecodeError as e:
                print(
                    f"[RenodeNode:{self.node_id}] "
                    f"Warning: Malformed JSON in UART output: {line}"
                )
                print(f"[RenodeNode:{self.node_id}] JSON error: {e}")
                # Continue parsing other lines

        return events

    def stop(self):
        """
        Stop Renode emulator process gracefully.

        This method:
        1. Sends 'quit' command to monitor
        2. Closes monitor socket
        3. Terminates Renode process
        4. Waits for process exit (with timeout)
        5. Cleans up generated script file

        Note: Safe to call multiple times (idempotent)
        """
        print(f"[RenodeNode:{self.node_id}] Stopping Renode...")

        # Send quit command if connected
        if self.monitor_socket is not None:
            try:
                self._send_command('quit')
            except (RenodeTimeoutError, RenodeConnectionError):
                # Ignore errors during shutdown
                pass

            self.monitor_socket.close()
            self.monitor_socket = None

        # Terminate process if running
        if self.renode_process is not None:
            try:
                self.renode_process.terminate()
                self.renode_process.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                # Force kill if doesn't terminate gracefully
                print(
                    f"[RenodeNode:{self.node_id}] "
                    f"Process didn't terminate, force killing..."
                )
                self.renode_process.kill()
                self.renode_process.wait()

            self.renode_process = None

        # Clean up script file
        if self.script_path and self.script_path.exists():
            self.script_path.unlink()
            self.script_path = None

        print(f"[RenodeNode:{self.node_id}] Stopped")

    def __del__(self):
        """Destructor - ensure cleanup on garbage collection."""
        # Only call stop if object is fully initialized
        if hasattr(self, 'monitor_socket'):
            self.stop()

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"RenodeNode(id={self.node_id}, "
            f"firmware={self.firmware_path.name}, "
            f"time={self.current_time_us}us)"
        )
