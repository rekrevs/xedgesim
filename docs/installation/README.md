# xEdgeSim Installation Guide

This directory contains platform-specific installation guides for xEdgeSim.

## Quick Start

Choose your installation path based on what you're working on:

### Option 1: Core Python Simulator Only

If you're only working with the Python-based coordinator and simulation framework (M1-M3e milestones):

- **Time to install:** ~5 minutes
- **Disk space:** ~500 MB
- **Requirements:**
  - Python 3.10+
  - Basic development tools

**See:** Basic Python Setup section in platform guides below

### Option 2: Full Development Environment

If you're working with firmware and device-tier emulation (M3f+ milestones):

- **Time to install:** ~30-45 minutes
- **Disk space:** ~3-4 GB
- **Requirements:**
  - Everything from Option 1
  - Zephyr RTOS toolchain
  - Renode emulator

**See:** Complete guide for your platform below

## Platform-Specific Guides

### macOS
- [macOS Installation Guide](macos.md) - Complete setup for Apple Silicon and Intel Macs
  - Tested on macOS 14.x (Sonoma)
  - Includes Homebrew-based installation
  - Native ARM64 toolchain support

### Linux
- Linux Installation Guide (coming soon)
  - Ubuntu/Debian-based distributions
  - Arch Linux
  - Fedora/RHEL

### Windows
- Windows Installation Guide (coming soon)
  - WSL2-based setup (recommended)
  - Native Windows setup

## What Gets Installed

### Core Python Environment
- Python 3.10+ and virtual environment
- Core dependencies: pytest, numpy, matplotlib
- Network simulation libraries
- Docker (for edge-tier containers)

### Firmware Development Tools (Optional)
- **Zephyr RTOS:** Open-source RTOS for embedded devices
  - Workspace: ~1 GB (includes HALs for many MCU families)
  - SDK: ~300-500 MB (cross-compilers for ARM, RISC-V, x86, etc.)
- **West:** Zephyr's meta-tool for managing multi-repo projects
- **Build tools:** CMake, Ninja

### Device Emulation Tools (Optional)
- **Renode:** Full-system emulator for embedded devices
  - Size: ~80 MB
  - Supports ARM Cortex-M, RISC-V, and many other architectures
  - Provides deterministic emulation with virtual time

## Installation Paths

```
~/repos/                          # Recommended project location
├── xedgesim/                     # This repository
│   ├── sim/                      # Python simulator
│   ├── firmware/                 # Firmware projects
│   │   └── sensor-node/          # Example sensor firmware
│   └── tests/                    # Test suites
└── zephyrproject/                # Zephyr RTOS workspace
    ├── zephyr/                   # Zephyr kernel
    ├── modules/                  # Hardware abstraction layers
    └── bootloader/               # MCUboot bootloader

~/zephyr-sdk-0.17.4/              # Zephyr SDK (toolchains)

/Applications/Renode.app          # Renode emulator (macOS)
```

## Verification

After installation, verify your setup:

### Core Python Environment
```bash
cd ~/repos/xedgesim
pytest tests/stages/M1a/ -v
pytest tests/stages/M2a/ -v
pytest tests/stages/M3a/ -v
```

All tests should pass.

### Firmware Development
```bash
cd ~/repos/xedgesim/firmware/sensor-node
west build -b nrf52840dk/nrf52840
```

Should complete with memory usage report.

### Device Emulation
```bash
cd ~/repos/xedgesim
pytest tests/stages/M3fa/ -v
./tests/stages/M3fb/test_standalone_renode.sh
```

Should show JSON sensor samples streaming from emulated firmware.

## Troubleshooting

### Common Issues

**Build failures:** Check that all prerequisites are installed for your platform

**Import errors:** Ensure virtual environment is activated:
```bash
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
```

**Permission errors:** Don't use `sudo` for pip installs - use virtual environments

**Disk space:** Full installation requires ~4 GB free space

### Getting Help

1. Check the platform-specific troubleshooting section
2. Search existing issues: https://github.com/rekrevs/xedgesim/issues
3. Open a new issue with:
   - Your platform and version
   - Commands you ran
   - Complete error output

## Component Dependencies

```
xEdgeSim Components:

┌─────────────────────────────────────────────┐
│ Core Python Simulator (Always Required)    │
│ - Coordinator, event loop, time management  │
│ - Python 3.10+, pytest, numpy              │
└─────────────────────────────────────────────┘
              │
              ├─── M1: Logical nodes
              ├─── M2: Socket nodes (network)
              └─── M3: Docker nodes (edge)
                   │
                   └─────────────────────────────┐
┌─────────────────────────────────────────────┐ │
│ Firmware Development (M3f+, Optional)       │ │
│ - Zephyr RTOS workspace and SDK             │ │
│ - West, CMake, Ninja                        │ │
└─────────────────────────────────────────────┘ │
              │                                 │
              └─────────────────────────────────┤
┌─────────────────────────────────────────────┐ │
│ Device Emulation (M3f+, Optional)           │ │
│ - Renode emulator                           │ │
│ - Device-tier node implementation           │ │
└─────────────────────────────────────────────┘ │
                                                │
              Required together ────────────────┘
```

## Next Steps

After installation:

1. **Explore examples:**
   - `scenarios/hello-world/` - Minimal example
   - `scenarios/vib-monitoring/` - Complete vibration monitoring scenario

2. **Run tests:**
   - See [tests/README.md](../../tests/README.md) for test organization
   - Each milestone has its own test suite

3. **Build firmware:**
   - See [firmware/sensor-node/README.md](../../firmware/sensor-node/README.md)
   - Customize device tree for your sensor configuration

4. **Read architecture:**
   - [docs/architecture.md](../architecture.md) - System design
   - [docs/implementation-guide.md](../implementation-guide.md) - Development guide

## Version Compatibility

| Component | Minimum | Tested | Notes |
|-----------|---------|--------|-------|
| Python | 3.10 | 3.12 | Type hints require 3.10+ |
| Zephyr | 4.0 | 4.3.99 | Firmware uses Zephyr 4.x API |
| Renode | 1.15 | 1.16.0 | Native ARM64 support in 1.16+ |
| Docker | 20.10 | 24.0 | For edge-tier containers |
| pytest | 7.0 | 8.3 | Test framework |

## Contributing

When adding new dependencies:

1. Update `requirements.txt` for Python packages
2. Update platform installation guides
3. Update this README with component overview
4. Test on a clean installation

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for development setup.
