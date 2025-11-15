# Building Firmware with Emulation Mode

The emulation mode code is complete in `src/main.c`, but the firmware needs to be rebuilt to include it.

## Current Status

- ✅ `CONFIG_XEDGESIM_EMULATION=y` enabled in `prj.conf`
- ✅ Emulation mode code added to `src/main.c` (lines 147-199)
- ✅ Kconfig option defined in `Kconfig`
- ❌ Firmware not yet rebuilt (current binary from Nov 15 14:44, before changes)

## Prerequisites

### Zephyr SDK and Workspace

If not already set up:

```bash
# Install west
pip3 install west

# Initialize Zephyr workspace (one-time setup)
cd ~/repos
west init zephyrproject
cd zephyrproject
west update

# Install Python dependencies
pip3 install -r zephyr/scripts/requirements.txt

# On macOS, also install Zephyr SDK
brew install zephyr-sdk
```

## Building

### Option 1: Build with Emulation Mode (for E2E tests)

```bash
cd /Users/sverker/repos/xedgesim/firmware/sensor-node

# Set Zephyr environment
export ZEPHYR_BASE=~/repos/zephyrproject/zephyr

# Build with emulation mode enabled (already in prj.conf)
west build -b nrf52840dk/nrf52840 -p

# Or explicitly use emulation config
west build -b nrf52840dk/nrf52840 -p -- -DOVERLAY_CONFIG=prj_emulation.conf
```

### Option 2: Build Production Mode (for hardware deployment)

```bash
# First, disable emulation mode in prj.conf:
# Change: CONFIG_XEDGESIM_EMULATION=y
# To:     CONFIG_XEDGESIM_EMULATION=n

# Then build
cd /Users/sverker/repos/xedgesim/firmware/sensor-node
export ZEPHYR_BASE=~/repos/zephyrproject/zephyr
west build -b nrf52840dk/nrf52840 -p
```

## Expected Output

### With Emulation Mode

The firmware will:
- Print: `*** EMULATION MODE: Deterministic sampling ***`
- Emit exactly 10 samples at 1-second intervals
- Output: `{"type":"SAMPLE","value":XX.X,"time":NNNNNN}`
- Enter idle after 10 samples

### Without Emulation Mode

The firmware will:
- Run infinite sampling loop
- Sample every 1 second indefinitely
- Use `k_usleep()` for timing

## Verification

After rebuilding, check the build date:

```bash
ls -lh build/zephyr/zephyr.elf
stat -f "Last modified: %Sm" build/zephyr/zephyr.elf
```

Should show a timestamp AFTER the config changes were made.

## Testing

Once rebuilt with emulation mode:

```bash
# Run E2E test
cd /Users/sverker/repos/xedgesim
./tests/stages/M3fc/test_e2e_renode.sh

# Expected output:
# [RenodeNode:sensor_device] Advanced to 1000000us, 1 events
# [RenodeNode:sensor_device] Advanced to 2000000us, 1 events  <-- Should now get 1 event per step
```

## Troubleshooting

### "west: unknown command 'build'"

You're not in a Zephyr workspace. Make sure:
1. You've run `west init` in the parent directory
2. You're in the `firmware/sensor-node` directory when building
3. ZEPHYR_BASE is set correctly

### "No such file: zephyr-env.sh"

This file may not exist in newer Zephyr versions. It's optional - just set `ZEPHYR_BASE` directly.

### Build fails with CMake errors

Try a pristine build:
```bash
rm -rf build
west build -b nrf52840dk/nrf52840 -p
```

## Alternative: Docker Build

If local Zephyr setup is problematic, consider using Docker:

```bash
docker run -it -v $(pwd):/workspace \
  zephyrprojectrtos/ci:latest \
  /bin/bash -c "cd /workspace && west build -b nrf52840dk/nrf52840"
```

---

**Status:** Ready to build - code complete, awaiting compilation
**Next Step:** Rebuild firmware, then run E2E test for validation
