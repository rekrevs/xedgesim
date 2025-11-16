"""
test_launcher_unit.py - Unit Tests for SimulationLauncher (M3g)

Tests that can run locally without Docker or Renode.

These tests verify:
- Scenario validation logic
- Launcher initialization
- Error handling for missing files
- Network model creation
"""

import pytest
import os
import sys
from pathlib import Path

# Add project root to path
_project_root = Path(__file__).parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from sim.config.scenario import Scenario, NetworkConfig
from sim.harness.launcher import SimulationLauncher


class TestScenarioValidation:
    """Test scenario validation logic."""

    def test_validate_simple_scenario_passes(self):
        """Test validation passes for simple valid scenario."""
        scenario = Scenario(
            duration_s=1.0,
            seed=42,
            time_quantum_us=1000,
            nodes=[
                {'id': 'sensor1', 'type': 'sensor', 'implementation': 'python_model', 'port': 5001}
            ]
        )

        launcher = SimulationLauncher(scenario)
        errors = launcher.validate_scenario()

        assert errors == []

    def test_validate_renode_missing_firmware(self, tmp_path):
        """Test validation fails when Renode firmware missing."""
        # Create platform file but not firmware
        platform_file = tmp_path / "platform.repl"
        platform_file.write_text("# Test platform")

        scenario = Scenario(
            duration_s=1.0,
            seed=42,
            time_quantum_us=1000,
            nodes=[
                {
                    'id': 'device1',
                    'type': 'sensor',
                    'implementation': 'renode_inprocess',
                    'platform': str(platform_file),
                    'firmware': str(tmp_path / "nonexistent.elf")
                }
            ]
        )

        launcher = SimulationLauncher(scenario)
        errors = launcher.validate_scenario()

        assert len(errors) > 0
        assert any("firmware" in e.lower() for e in errors)

    def test_validate_renode_missing_platform(self, tmp_path):
        """Test validation fails when Renode platform missing."""
        # Create firmware file but not platform
        firmware_file = tmp_path / "firmware.elf"
        firmware_file.write_bytes(b"FAKE_ELF")

        scenario = Scenario(
            duration_s=1.0,
            seed=42,
            time_quantum_us=1000,
            nodes=[
                {
                    'id': 'device1',
                    'type': 'sensor',
                    'implementation': 'renode_inprocess',
                    'platform': str(tmp_path / "nonexistent.repl"),
                    'firmware': str(firmware_file)
                }
            ]
        )

        launcher = SimulationLauncher(scenario)
        errors = launcher.validate_scenario()

        assert len(errors) > 0
        assert any("platform" in e.lower() for e in errors)

    def test_validate_renode_all_files_exist_passes(self, tmp_path):
        """Test validation passes when all Renode files exist."""
        platform_file = tmp_path / "platform.repl"
        platform_file.write_text("# Test platform")
        firmware_file = tmp_path / "firmware.elf"
        firmware_file.write_bytes(b"FAKE_ELF")

        scenario = Scenario(
            duration_s=1.0,
            seed=42,
            time_quantum_us=1000,
            nodes=[
                {
                    'id': 'device1',
                    'type': 'sensor',
                    'implementation': 'renode_inprocess',
                    'platform': str(platform_file),
                    'firmware': str(firmware_file)
                }
            ]
        )

        launcher = SimulationLauncher(scenario)
        errors = launcher.validate_scenario()

        assert errors == []


class TestNetworkModelCreation:
    """Test network model creation from scenario config."""

    def test_create_direct_network_model(self):
        """Test launcher creates DirectNetworkModel."""
        scenario = Scenario(
            duration_s=1.0,
            seed=42,
            time_quantum_us=1000,
            nodes=[
                {'id': 'sensor1', 'type': 'sensor', 'implementation': 'python_model', 'port': 5001}
            ],
            network=NetworkConfig(model="direct")
        )

        launcher = SimulationLauncher(scenario)
        network_model = launcher._create_network_model()

        from sim.network.direct_model import DirectNetworkModel
        assert isinstance(network_model, DirectNetworkModel)

    def test_create_latency_network_model(self):
        """Test launcher creates LatencyNetworkModel."""
        scenario = Scenario(
            duration_s=1.0,
            seed=42,
            time_quantum_us=1000,
            nodes=[
                {'id': 'sensor1', 'type': 'sensor', 'implementation': 'python_model', 'port': 5001}
            ],
            network=NetworkConfig(
                model="latency",
                default_latency_us=10000,
                default_loss_rate=0.1
            )
        )

        launcher = SimulationLauncher(scenario)
        network_model = launcher._create_network_model()

        from sim.network.latency_model import LatencyNetworkModel
        assert isinstance(network_model, LatencyNetworkModel)

    def test_create_default_network_when_none(self):
        """Test launcher creates default network model when none specified."""
        scenario = Scenario(
            duration_s=1.0,
            seed=42,
            time_quantum_us=1000,
            nodes=[
                {'id': 'sensor1', 'type': 'sensor', 'implementation': 'python_model', 'port': 5001}
            ],
            network=None
        )

        launcher = SimulationLauncher(scenario)
        network_model = launcher._create_network_model()

        from sim.network.direct_model import DirectNetworkModel
        assert isinstance(network_model, DirectNetworkModel)

    def test_invalid_network_model_raises(self):
        """Test NetworkConfig raises error for invalid network model type."""
        # NetworkConfig validation happens in __post_init__, so the error
        # is raised during construction, not later
        with pytest.raises(ValueError, match="network.model must be"):
            NetworkConfig(model="invalid_model")


class TestLauncherInitialization:
    """Test launcher initialization and configuration."""

    def test_launcher_stores_scenario(self):
        """Test launcher stores scenario reference."""
        scenario = Scenario(
            duration_s=1.0,
            seed=42,
            time_quantum_us=1000,
            nodes=[{'id': 'sensor1', 'type': 'sensor', 'implementation': 'python_model', 'port': 5001}]
        )

        launcher = SimulationLauncher(scenario)

        assert launcher.scenario is scenario
        assert launcher.processes == []
        assert launcher.docker_containers == []
        assert launcher.coordinator is None

    def test_launcher_accepts_complex_scenario(self, tmp_path):
        """Test launcher accepts complex scenario with all features."""
        platform_file = tmp_path / "platform.repl"
        platform_file.write_text("# Test platform")
        firmware_file = tmp_path / "firmware.elf"
        firmware_file.write_bytes(b"FAKE_ELF")
        model_file = tmp_path / "model.onnx"
        model_file.write_bytes(b"FAKE_MODEL")

        from sim.config.scenario import MLInferenceConfig

        scenario = Scenario(
            duration_s=10.0,
            seed=123,
            time_quantum_us=500,
            nodes=[
                {'id': 'sensor1', 'type': 'sensor', 'implementation': 'python_model', 'port': 5001},
                {'id': 'gateway1', 'type': 'gateway', 'implementation': 'python_model', 'port': 5002},
                {
                    'id': 'device1',
                    'type': 'sensor',
                    'implementation': 'renode_inprocess',
                    'platform': str(platform_file),
                    'firmware': str(firmware_file)
                }
            ],
            network=NetworkConfig(model="latency", default_latency_us=5000),
            ml_inference=MLInferenceConfig(
                placement="edge",
                edge_config={'model_path': str(model_file)}
            )
        )

        launcher = SimulationLauncher(scenario)

        # Validation should pass
        errors = launcher.validate_scenario()
        assert errors == []


class TestLauncherShutdown:
    """Test launcher shutdown and cleanup logic."""

    def test_shutdown_with_no_processes(self):
        """Test shutdown succeeds with no running processes."""
        scenario = Scenario(
            duration_s=1.0,
            seed=42,
            time_quantum_us=1000,
            nodes=[{'id': 'sensor1', 'type': 'sensor', 'implementation': 'python_model', 'port': 5001}]
        )

        launcher = SimulationLauncher(scenario)
        launcher.shutdown()  # Should not raise

    def test_shutdown_idempotent(self):
        """Test shutdown can be called multiple times safely."""
        scenario = Scenario(
            duration_s=1.0,
            seed=42,
            time_quantum_us=1000,
            nodes=[{'id': 'sensor1', 'type': 'sensor', 'implementation': 'python_model', 'port': 5001}]
        )

        launcher = SimulationLauncher(scenario)
        launcher.shutdown()
        launcher.shutdown()  # Should not raise on second call


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
