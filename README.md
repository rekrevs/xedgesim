# xEdgeSim

xEdgeSim is a research prototype for a cross-level IoT–edge–cloud simulator.

The vision is to generalise "COOJA-style" cross-level simulation from wireless sensor networks to modern heterogeneous systems with:

- **Devices:** MCU-based nodes running real firmware (e.g. Zephyr/FreeRTOS) in emulation.
- **Edge:** Linux gateways running real containers (e.g. MQTT broker, aggregation, ML inference).
- **Network:** A discrete-event network simulator (e.g. ns-3) modelling wireless, LAN, and WAN links.
- **Cloud:** Mocked or containerised services representing cloud-side processing and storage.
- **ML placement:** Experimentation with different placements of ML workloads (device, edge, cloud) and offloading policies.

## Quick Start

### Installation

Choose your installation path based on what you're working on:

- **Core Python simulator only** (~5 min): Basic Python setup for coordinator and simulation framework
- **Full development environment** (~45 min): Includes firmware toolchain and device emulation

See [Installation Guide](docs/installation/README.md) for:
- [macOS Setup](docs/installation/macos.md) - Complete guide for Apple Silicon and Intel Macs
- Linux Setup (coming soon)
- Windows Setup (coming soon)

### Quick Test

After basic Python installation:

```bash
# Clone and setup
git clone https://github.com/rekrevs/xedgesim.git
cd xedgesim
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run core tests
pytest tests/stages/M1a/ -v
pytest tests/stages/M2a/ -v
```

## Project Status

This repository is evolving in several phases:

1. ✅ P0 — Foundations & tooling
2. ✅ P1 — Related work & gap analysis
3. ✅ P2 — Architecture design
4. 🔄 P3 — Implementation in incremental milestones (M0–M4)
   - ✅ M1: Core coordinator and logical nodes
   - ✅ M2: Socket-based network nodes
   - ✅ M3a-e: Docker-based edge nodes
   - ✅ M3f: Renode-based device nodes (firmware emulation)
   - 🚧 M3g: ns-3 network simulation (planned)
   - 🚧 M4: Full integration scenarios (planned)
5. 🚧 P4 — Experiment harness and evaluation scenarios
6. 🚧 P5 — Writing and packaging for publication

Current milestone: **M3f (Renode Integration)** - Device-tier nodes running real firmware in emulation

## Documentation

- [Architecture](docs/architecture.md) - System design and component overview
- [Implementation Guide](docs/implementation-guide.md) - Development patterns and practices
- [Milestone Reports](docs/dev-log/) - Detailed development logs for each milestone
- [Firmware Guide](firmware/sensor-node/README.md) - Building and testing embedded firmware

## Repository Structure

```
xedgesim/
├── sim/                    # Python simulator core
│   ├── coordinator.py      # Discrete-event coordinator
│   ├── logical/            # Logical node implementations
│   ├── socket/             # Network socket nodes
│   ├── docker/             # Docker container nodes
│   └── device/             # Renode emulated device nodes
├── firmware/               # Embedded firmware projects
│   └── sensor-node/        # Zephyr-based sensor firmware
├── scenarios/              # Example simulation scenarios
├── tests/                  # Test suites organized by milestone
└── docs/                   # Documentation
    ├── installation/       # Setup guides
    └── dev-log/           # Development logs
```
