# xEdgeSim Installation Guide - macOS

This guide covers setting up the complete xEdgeSim development environment on macOS (tested on Apple Silicon).

## Overview

xEdgeSim has different installation requirements depending on which components you're working with:

- **Core Python simulator** (M1-M3e): Basic Python setup
- **Firmware development** (M3f+): Zephyr RTOS toolchain
- **Device emulation** (M3f+): Renode emulator

## Prerequisites

- macOS 11.0 or later (tested on macOS 14+)
- Homebrew package manager
- Python 3.10 or later
- Git

### Install Homebrew

If you don't have Homebrew installed:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

## Basic Python Setup

### 1. Install System Dependencies

```bash
# Install Python (if not already installed)
brew install python@3.12

# Install build tools
brew install cmake ninja
```

### 2. Set Up Python Virtual Environment

```bash
# Clone the repository
cd ~/repos  # or your preferred location
git clone https://github.com/rekrevs/xedgesim.git
cd xedgesim

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### 3. Verify Basic Installation

```bash
# Run core tests
pytest tests/stages/M1a/ -v
pytest tests/stages/M2a/ -v
```

If these pass, your core Python environment is working.

## Firmware Development Setup (M3f+)

For working with real firmware and device-tier emulation, you'll need additional tools.

### 1. Install West (Zephyr Meta-Tool)

```bash
pip3 install west
```

### 2. Set Up Zephyr Workspace

```bash
# Initialize Zephyr workspace (will download ~1GB)
cd ~/repos
west init zephyrproject
cd zephyrproject
west update

# Install Zephyr Python dependencies
pip3 install -r zephyr/scripts/requirements.txt
```

This will take several minutes as it downloads the full Zephyr RTOS source tree and all hardware abstraction layers.

### 3. Install Zephyr SDK

The Zephyr SDK provides cross-compilers for all supported architectures:

```bash
cd ~/repos/zephyrproject
west sdk install
```

This will:
- Download the Zephyr SDK (~300MB for macOS ARM64)
- Install to `~/zephyr-sdk-0.17.4`
- Install toolchains for ARM, RISC-V, x86, and other architectures
- Register the SDK with CMake

**Alternative manual installation:**

For Apple Silicon Macs:
```bash
cd ~
curl -L -O https://github.com/zephyrproject-rtos/sdk-ng/releases/download/v0.17.4/zephyr-sdk-0.17.4_macos-aarch64_minimal.tar.xz
tar xf zephyr-sdk-0.17.4_macos-aarch64_minimal.tar.xz
cd zephyr-sdk-0.17.4
./setup.sh
```

For Intel Macs, replace `aarch64` with `x86_64` in the URL above.

### 4. Build Sensor Node Firmware

```bash
cd ~/repos/xedgesim/firmware/sensor-node

# Set Zephyr environment
export ZEPHYR_BASE=~/repos/zephyrproject/zephyr
source $ZEPHYR_BASE/zephyr-env.sh

# Build for nRF52840 DK
west build -b nrf52840dk/nrf52840
```

**Expected output:**
```
Memory region         Used Size  Region Size  %age Used
           FLASH:       54252 B         1 MB      5.17%
             RAM:        7936 B       256 KB      3.03%
```

The build artifacts will be in `build/zephyr/`:
- `zephyr.elf` - ELF binary for Renode emulation
- `zephyr.hex` - Hex file for flashing to hardware
- `zephyr.bin` - Raw binary

### 5. Verify Firmware Build

```bash
# Check firmware was built
ls -lh build/zephyr/zephyr.elf

# Run firmware integration tests
cd ~/repos/xedgesim
pytest tests/stages/M3fa/ -v
pytest tests/stages/M3fb/test_json_protocol.py -v
```

## Device Emulation Setup (Renode)

### 1. Download and Install Renode

Download the latest Renode for macOS ARM64:

```bash
cd ~/Downloads
curl -L -O https://github.com/renode/renode/releases/download/v1.16.0/renode-1.16.0-dotnet.osx-arm64-portable.dmg

# Mount and install
hdiutil attach renode-1.16.0-dotnet.osx-arm64-portable.dmg
cp -R /Volumes/Renode_1.16.0/Renode.app /Applications/
hdiutil detach /Volumes/Renode_1.16.0
```

**For Intel Macs:** Use `renode_1.16.0.dmg` instead (Mono-based version).

### 2. Create Command-Line Wrapper

```bash
# Create wrapper script
cat > /opt/homebrew/bin/renode << 'EOF'
#!/bin/bash
exec /Applications/Renode.app/Contents/MacOS/macos_run.command "$@"
EOF

chmod +x /opt/homebrew/bin/renode
```

### 3. Verify Renode Installation

```bash
# Check version
renode --version
# Should output: Renode v1.16.0.1525

# Run standalone firmware test
cd ~/repos/xedgesim
./tests/stages/M3fb/test_standalone_renode.sh
```

**Expected output:** JSON sensor samples streaming to console:
```
{"type":"SAMPLE","value":28.9,"time":0}
{"type":"SAMPLE","value":22.5,"time":1000000}
{"type":"SAMPLE","value":26.4,"time":2000000}
...
```

Press Ctrl+C to stop the emulation.

## Troubleshooting

### Zephyr Build Issues

**Problem:** `CMake was unable to find a build program corresponding to "Ninja"`

**Solution:**
```bash
brew install ninja
```

**Problem:** `Could not find a package configuration file provided by "Zephyr-sdk"`

**Solution:**
```bash
cd ~/repos/zephyrproject
west sdk install
```

**Problem:** Board name error (e.g., `nrf52840dk_nrf52840` not found)

**Solution:** Use the new format `nrf52840dk/nrf52840` (Zephyr 4.x changed board naming)

### Renode Issues

**Problem:** `renode: command not found`

**Solution:** Create the wrapper script as shown above, or use the full path:
```bash
/Applications/Renode.app/Contents/MacOS/macos_run.command
```

**Problem:** Renode hangs or doesn't produce output

**Solution:** Check that firmware was built successfully:
```bash
ls -lh ~/repos/xedgesim/firmware/sensor-node/build/zephyr/zephyr.elf
```

### Permission Issues

**Problem:** Cannot install to `/usr/local/bin`

**Solution:** Use `/opt/homebrew/bin` instead (standard for Apple Silicon), or create wrapper in your local bin:
```bash
mkdir -p ~/.local/bin
# Add to PATH if needed
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
```

## Environment Variables

For convenience, add these to your `~/.zshrc` or `~/.bash_profile`:

```bash
# Zephyr
export ZEPHYR_BASE=~/repos/zephyrproject/zephyr

# Optional: Auto-activate Zephyr environment when entering firmware directory
alias zephyr-env='source $ZEPHYR_BASE/zephyr-env.sh'
```

## Quick Reference

### Build Firmware
```bash
cd ~/repos/xedgesim/firmware/sensor-node
export ZEPHYR_BASE=~/repos/zephyrproject/zephyr
source $ZEPHYR_BASE/zephyr-env.sh
west build -b nrf52840dk/nrf52840
```

### Run Tests
```bash
cd ~/repos/xedgesim
pytest tests/stages/M3fa/ -v      # Renode integration tests
pytest tests/stages/M3fb/ -v      # Firmware protocol tests
./tests/stages/M3fb/test_standalone_renode.sh  # Standalone emulation
```

### Clean Build
```bash
cd ~/repos/xedgesim/firmware/sensor-node
west build -b nrf52840dk/nrf52840 --pristine
```

## Next Steps

- See [firmware/sensor-node/README.md](../../firmware/sensor-node/README.md) for firmware development details
- See [docs/dev-log/M3fa-report.md](../dev-log/M3fa-report.md) for Renode integration overview
- See [docs/dev-log/M3fb-report.md](../dev-log/M3fb-report.md) for firmware testing details

## Version Information

This guide was tested with:
- macOS 14.x (Sonoma) on Apple Silicon
- Python 3.12.9
- Zephyr SDK 0.17.4
- Renode 1.16.0
- West 1.5.0
