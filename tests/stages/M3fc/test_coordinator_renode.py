"""
M3fc Coordinator Integration Tests

Tests for coordinator integration with RenodeNode (in-process nodes).
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from sim.harness.coordinator import Coordinator, InProcessNodeAdapter, Event


class TestInProcessNodeAdapter:
    """Test the InProcessNodeAdapter wrapper."""

    def test_create_adapter(self):
        """Test creating an InProcessNodeAdapter."""
        # Mock node instance
        mock_node = Mock()
        mock_node.start = Mock()
        mock_node.advance = Mock(return_value=[])
        mock_node.stop = Mock()

        adapter = InProcessNodeAdapter("test_node", mock_node)

        assert adapter.node_id == "test_node"
        assert adapter.node == mock_node
        assert adapter.current_time_us == 0

    def test_connect_starts_node(self):
        """Test connect() calls node.start()."""
        mock_node = Mock()
        adapter = InProcessNodeAdapter("test_node", mock_node)

        adapter.connect()

        mock_node.start.assert_called_once()

    def test_send_init_is_noop(self):
        """Test send_init() is a no-op for in-process nodes."""
        mock_node = Mock()
        adapter = InProcessNodeAdapter("test_node", mock_node)

        # Should not raise exception
        adapter.send_init({'seed': 42})

    def test_send_advance_updates_time(self):
        """Test send_advance() updates internal time."""
        mock_node = Mock()
        adapter = InProcessNodeAdapter("test_node", mock_node)

        adapter.send_advance(1000000, [])

        assert adapter.current_time_us == 1000000

    def test_wait_done_calls_advance(self):
        """Test wait_done() calls node.advance() with current time."""
        # Create mock event from node
        class MockEvent:
            def __init__(self):
                self.time = 1000000
                self.type = "SAMPLE"
                self.value = 25.3

        mock_node = Mock()
        mock_node.advance = Mock(return_value=[MockEvent()])

        adapter = InProcessNodeAdapter("test_node", mock_node)
        adapter.current_time_us = 1000000

        events = adapter.wait_done()

        mock_node.advance.assert_called_once_with(1000000)
        assert len(events) == 1
        assert events[0].time_us == 1000000
        assert events[0].type == "SAMPLE"
        assert events[0].src == "test_node"

    def test_send_shutdown_stops_node(self):
        """Test send_shutdown() calls node.stop()."""
        mock_node = Mock()
        adapter = InProcessNodeAdapter("test_node", mock_node)

        adapter.send_shutdown()

        mock_node.stop.assert_called_once()


class TestCoordinatorInProcessNodes:
    """Test Coordinator with in-process nodes."""

    def test_add_inprocess_node(self):
        """Test adding an in-process node to coordinator."""
        coordinator = Coordinator()
        mock_node = Mock()

        coordinator.add_inprocess_node("renode_1", mock_node)

        assert "renode_1" in coordinator.nodes
        assert isinstance(coordinator.nodes["renode_1"], InProcessNodeAdapter)
        assert "renode_1" in coordinator.pending_events

    def test_coordinator_advance_inprocess_node(self):
        """Test coordinator advances in-process node correctly."""
        class MockEvent:
            def __init__(self, time, event_type, value):
                self.time = time
                self.type = event_type
                self.value = value

        # Create mock node
        mock_node = Mock()
        mock_node.start = Mock()
        mock_node.advance = Mock(return_value=[
            MockEvent(1000000, "SAMPLE", 25.3)
        ])
        mock_node.stop = Mock()

        # Create coordinator and add node
        coordinator = Coordinator(time_quantum_us=1000000)
        coordinator.add_inprocess_node("sensor_1", mock_node)

        # Connect (start) the node
        coordinator.connect_all()
        mock_node.start.assert_called_once()

        # Manually advance (test single step)
        adapter = coordinator.nodes["sensor_1"]
        adapter.send_advance(1000000, [])
        events = adapter.wait_done()

        # Verify
        assert len(events) == 1
        assert events[0].type == "SAMPLE"
        assert events[0].src == "sensor_1"
        mock_node.advance.assert_called_with(1000000)

    def test_mixed_nodes_not_implemented(self):
        """
        Test that mixing socket and in-process nodes works structurally.

        Note: This test only verifies the data structures are compatible.
        Actual mixed-node simulation testing requires running nodes,
        which is deferred to integration tests.
        """
        coordinator = Coordinator()

        # Add in-process node
        mock_node = Mock()
        coordinator.add_inprocess_node("renode_1", mock_node)

        # Add socket node (would connect to real process)
        coordinator.add_node("gateway_1", "localhost", 5001)

        # Verify both registered
        assert "renode_1" in coordinator.nodes
        assert "gateway_1" in coordinator.nodes
        assert isinstance(coordinator.nodes["renode_1"], InProcessNodeAdapter)


class TestScenarioLoading:
    """Test scenario loading with renode_inprocess nodes."""

    def test_parse_renode_inprocess_scenario(self):
        """Test parsing a scenario with renode_inprocess node."""
        from sim.config.scenario import load_scenario
        import tempfile
        import yaml

        # Create temporary YAML scenario
        scenario_dict = {
            'simulation': {
                'duration_s': 5.0,
                'seed': 42,
                'time_quantum_us': 1000000
            },
            'nodes': [
                {
                    'id': 'sensor_1',
                    'type': 'renode',
                    'implementation': 'renode_inprocess',
                    'platform': 'platforms/nrf52840.repl',
                    'firmware': 'firmware/sensor-node/build/zephyr/zephyr.elf',
                    'monitor_port': 9999,
                    'seed': 42
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(scenario_dict, f)
            temp_path = f.name

        try:
            # Load scenario
            scenario = load_scenario(temp_path)

            # Verify
            assert scenario.duration_s == 5.0
            assert scenario.seed == 42
            assert len(scenario.nodes) == 1

            node = scenario.nodes[0]
            assert node['id'] == 'sensor_1'
            assert node['type'] == 'renode'
            assert node['implementation'] == 'renode_inprocess'
            assert node['platform'] == 'platforms/nrf52840.repl'
            assert node['firmware'] == 'firmware/sensor-node/build/zephyr/zephyr.elf'
            assert node['monitor_port'] == 9999
            assert 'port' not in node  # Should not have port for in-process

        finally:
            import os
            os.unlink(temp_path)

    def test_reject_invalid_implementation(self):
        """Test that invalid implementation type is rejected."""
        from sim.config.scenario import load_scenario
        import tempfile
        import yaml

        scenario_dict = {
            'simulation': {
                'duration_s': 5.0,
                'seed': 42
            },
            'nodes': [
                {
                    'id': 'node_1',
                    'type': 'sensor',
                    'implementation': 'invalid_type',
                    'port': 5001
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(scenario_dict, f)
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="implementation must be"):
                load_scenario(temp_path)
        finally:
            import os
            os.unlink(temp_path)
