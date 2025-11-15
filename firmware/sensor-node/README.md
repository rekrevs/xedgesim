# xEdgeSim Sensor Node Firmware

Minimal Zephyr RTOS firmware for nRF52840 DK that demonstrates device-tier emulation with deployable artifacts.

## Features

- **Deterministic sensor sampling** using seeded RNG
- **JSON-over-UART protocol** for structured event output
- **Virtual time tracking** synchronized with Renode
- **Portable across simulation and hardware** (same binary)

## Prerequisites

### Zephyr SDK Installation

**Ubuntu/Debian:**
```bash
wget https://github.com/zephyrproject-rtos/sdk-ng/releases/download/v0.16.5/zephyr-sdk-0.16.5_linux-x86_64.tar.xz
tar xf zephyr-sdk-0.16.5_linux-x86_64.tar.xz
cd zephyr-sdk-0.16.5
./setup.sh
```

**macOS:**
```bash
brew install zephyr-sdk
```

### Zephyr Workspace Setup

```bash
# Install west (Zephyr meta-tool)
pip3 install west

# Initialize workspace
west init ~/zephyrproject
cd ~/zephyrproject
west update

# Install Python dependencies
pip3 install -r zephyr/scripts/requirements.txt
```

## Building

### Quick Build

```bash
cd firmware/sensor-node

# Set Zephyr environment
export ZEPHYR_BASE=~/zephyrproject/zephyr
source $ZEPHYR_BASE/zephyr-env.sh

# Build for nRF52840 DK
west build -b nrf52840dk_nrf52840
```

### Build Output

Successful build produces:
- `build/zephyr/zephyr.elf` - ELF binary for Renode/debugging
- `build/zephyr/zephyr.hex` - Hex file for flashing hardware
- `build/zephyr/zephyr.bin` - Raw binary

### Clean Build

```bash
west build -b nrf52840dk_nrf52840 --pristine
```

## Testing in Renode

### Standalone Test

```bash
# Start Renode
renode --disable-xwt

# In Renode console:
mach create "sensor"
machine LoadPlatformDescription @platforms/cpus/nrf52840.repl
sysbus LoadELF @build/zephyr/zephyr.elf

# Show UART output
showAnalyzer sysbus.uart0

# Run emulation
start
emulation RunFor @5.0
```

**Expected output:**
```
{"type":"SAMPLE","value":25.3,"time":0}
{"type":"SAMPLE","value":26.1,"time":1000000}
{"type":"SAMPLE","value":24.7,"time":2000000}
...
```

### With xEdgeSim Coordinator

```yaml
# scenario.yaml
nodes:
  sensor_1:
    type: renode
    platform: platforms/nrf52840.repl
    firmware: firmware/sensor-node/build/zephyr/zephyr.elf
    seed: 12345
```

```bash
python sim/coordinator.py --scenario scenario.yaml
```

## Flashing to Hardware

### Using west

```bash
# Connect nRF52840 DK via USB
west flash
```

### Using nrfjprog

```bash
nrfjprog --program build/zephyr/zephyr.hex --chiperase --verify
nrfjprog --reset
```

### Monitor UART Output

```bash
# On Linux
screen /dev/ttyACM0 115200

# On macOS
screen /dev/tty.usbmodem* 115200
```

## Configuration

### RNG Seed

Edit `boards/nrf52840dk_nrf52840.overlay`:
```dts
rng_config {
    seed = <YOUR_SEED>;
};
```

### Sample Interval

Edit device tree overlay:
```dts
sensor_config {
    sample-interval-us = <500000>;  /* 500ms */
};
```

### Sensor Range

Edit `src/main.c`:
```c
#define SENSOR_MIN_VALUE 15.0f
#define SENSOR_MAX_VALUE 35.0f
```

## JSON Protocol

### Event Format

```json
{"type":"SAMPLE","value":25.3,"time":1000000}
```

**Fields:**
- `type`: Event type ("SAMPLE", "ALERT", etc.)
- `value`: Sensor reading (float, 1 decimal place)
- `time`: Virtual time in microseconds (uint64)

**Properties:**
- One JSON object per line (newline-delimited)
- Compact format (no whitespace)
- Maximum line length: 256 bytes
- Output over UART0 at 115200 baud

### Adding New Event Types

```c
output_json_event("ALERT", threshold_value, current_time_us);
output_json_event("STATUS", status_code, current_time_us);
```

## Troubleshooting

### Build Errors

**"Cannot find ZEPHYR_BASE":**
```bash
export ZEPHYR_BASE=~/zephyrproject/zephyr
source $ZEPHYR_BASE/zephyr-env.sh
```

**"Device tree error":**
- Check overlay file syntax
- Ensure `compatible` strings match bindings
- Verify board name matches exactly

### Renode Issues

**"Cannot load ELF":**
- Check file path is absolute or relative to Renode CWD
- Verify ELF was built successfully
- Use `@` prefix for paths: `@build/zephyr/zephyr.elf`

**No UART output:**
- Verify `showAnalyzer sysbus.uart0` was called
- Check UART is enabled in device tree
- Ensure firmware is actually running (`start` command)

### Hardware Issues

**Device not found:**
```bash
# Check USB connection
lsusb | grep Nordic

# Check permissions (Linux)
sudo usermod -a -G dialout $USER
# Log out and back in
```

**Garbled UART output:**
- Verify baud rate matches (115200)
- Check UART pin configuration in overlay
- Ensure correct /dev/tty* device

## File Structure

```
firmware/sensor-node/
├── CMakeLists.txt              # Zephyr build configuration
├── prj.conf                    # Kernel configuration
├── README.md                   # This file
├── boards/
│   └── nrf52840dk_nrf52840.overlay  # Device tree overlay
└── src/
    └── main.c                  # Main application
```

## Development Notes

### Code Style

- Follow Zephyr coding style (Linux kernel style)
- Use Zephyr APIs, not POSIX where possible
- Keep functions short and focused
- Document all public functions

### Testing

- Build test: `west build` completes without errors
- Renode test: Firmware runs and outputs JSON
- Determinism test: Same seed → identical output
- Hardware test: Firmware runs on real nRF52840 DK

### Future Enhancements

- Multiple sensor types (temperature, humidity, accelerometer)
- Sleep modes for power efficiency
- Firmware update over UART
- TFLite Micro for on-device ML

## References

- [Zephyr Documentation](https://docs.zephyrproject.org/)
- [nRF52840 DK](https://www.nordicsemi.com/Products/Development-hardware/nrf52840-dk)
- [Renode Documentation](https://renode.readthedocs.io/)
- [xEdgeSim Architecture](../../docs/architecture.md)
