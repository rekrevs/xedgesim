"""
M3c: ML Inference Schema Tests

Tests YAML schema parsing for ML placement configuration.
These tests run locally without Docker or ML dependencies.
"""

import pytest
import tempfile
import os
from pathlib import Path

from sim.config.scenario import load_scenario, MLInferenceConfig


@pytest.fixture
def temp_model_files():
    """Create temporary model files for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create dummy model files
        edge_model = Path(tmpdir) / "edge_model.onnx"
        cloud_model = Path(tmpdir) / "cloud_model.pt"

        edge_model.touch()
        cloud_model.touch()

        yield {
            'edge': str(edge_model),
            'cloud': str(cloud_model),
            'dir': tmpdir
        }


@pytest.fixture
def base_scenario_yaml():
    """Base scenario YAML without ML inference."""
    return """
simulation:
  duration_s: 10
  seed: 42
  time_quantum_us: 1000

nodes:
  - id: sensor1
    type: sensor
    port: 5001
"""


def test_edge_placement_config(temp_model_files, base_scenario_yaml):
    """Test YAML with edge ML placement config."""
    yaml_content = base_scenario_yaml + f"""
ml_inference:
  placement: edge
  edge_config:
    model_path: {temp_model_files['edge']}
    broker_host: localhost
    broker_port: 1883
    threshold: 0.5
"""

    # Write to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(yaml_content)
        yaml_path = f.name

    try:
        # Load scenario
        scenario = load_scenario(yaml_path)

        # Verify ML inference config
        assert scenario.ml_inference is not None
        assert scenario.ml_inference.placement == 'edge'
        assert scenario.ml_inference.edge_config is not None
        assert scenario.ml_inference.edge_config['model_path'] == temp_model_files['edge']
        assert scenario.ml_inference.edge_config['broker_host'] == 'localhost'
        assert scenario.ml_inference.edge_config['broker_port'] == 1883
        assert scenario.ml_inference.edge_config['threshold'] == 0.5

    finally:
        os.unlink(yaml_path)


def test_cloud_placement_config(temp_model_files, base_scenario_yaml):
    """Test YAML with cloud ML placement config."""
    yaml_content = base_scenario_yaml + f"""
ml_inference:
  placement: cloud
  cloud_config:
    model_path: {temp_model_files['cloud']}
    broker_host: localhost
    broker_port: 1883
    latency_ms: 50
    threshold: 0.5
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(yaml_content)
        yaml_path = f.name

    try:
        scenario = load_scenario(yaml_path)

        assert scenario.ml_inference is not None
        assert scenario.ml_inference.placement == 'cloud'
        assert scenario.ml_inference.cloud_config is not None
        assert scenario.ml_inference.cloud_config['model_path'] == temp_model_files['cloud']
        assert scenario.ml_inference.cloud_config['latency_ms'] == 50

    finally:
        os.unlink(yaml_path)


def test_missing_ml_config(base_scenario_yaml):
    """Test scenario without ML config (should be optional)."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(base_scenario_yaml)
        yaml_path = f.name

    try:
        scenario = load_scenario(yaml_path)

        # ML inference should be None (optional)
        assert scenario.ml_inference is None

    finally:
        os.unlink(yaml_path)


def test_invalid_placement_value(temp_model_files, base_scenario_yaml):
    """Test invalid placement value raises error."""
    yaml_content = base_scenario_yaml + f"""
ml_inference:
  placement: device
  edge_config:
    model_path: {temp_model_files['edge']}
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(yaml_content)
        yaml_path = f.name

    try:
        with pytest.raises(ValueError, match="must be 'edge' or 'cloud'"):
            load_scenario(yaml_path)
    finally:
        os.unlink(yaml_path)


def test_missing_edge_config(base_scenario_yaml):
    """Test edge placement without edge_config raises error."""
    yaml_content = base_scenario_yaml + """
ml_inference:
  placement: edge
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(yaml_content)
        yaml_path = f.name

    try:
        with pytest.raises(ValueError, match="requires 'edge_config'"):
            load_scenario(yaml_path)
    finally:
        os.unlink(yaml_path)


def test_missing_cloud_config(base_scenario_yaml):
    """Test cloud placement without cloud_config raises error."""
    yaml_content = base_scenario_yaml + """
ml_inference:
  placement: cloud
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(yaml_content)
        yaml_path = f.name

    try:
        with pytest.raises(ValueError, match="requires 'cloud_config'"):
            load_scenario(yaml_path)
    finally:
        os.unlink(yaml_path)


def test_missing_model_path_edge(base_scenario_yaml):
    """Test edge_config without model_path raises error."""
    yaml_content = base_scenario_yaml + """
ml_inference:
  placement: edge
  edge_config:
    broker_host: localhost
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(yaml_content)
        yaml_path = f.name

    try:
        with pytest.raises(ValueError, match="must specify 'model_path'"):
            load_scenario(yaml_path)
    finally:
        os.unlink(yaml_path)


def test_missing_model_path_cloud(base_scenario_yaml):
    """Test cloud_config without model_path raises error."""
    yaml_content = base_scenario_yaml + """
ml_inference:
  placement: cloud
  cloud_config:
    broker_host: localhost
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(yaml_content)
        yaml_path = f.name

    try:
        with pytest.raises(ValueError, match="must specify 'model_path'"):
            load_scenario(yaml_path)
    finally:
        os.unlink(yaml_path)


def test_model_file_not_found_edge(base_scenario_yaml):
    """Test edge model path validation (file must exist)."""
    yaml_content = base_scenario_yaml + """
ml_inference:
  placement: edge
  edge_config:
    model_path: /nonexistent/model.onnx
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(yaml_content)
        yaml_path = f.name

    try:
        with pytest.raises(FileNotFoundError, match="Edge ML model not found"):
            load_scenario(yaml_path)
    finally:
        os.unlink(yaml_path)


def test_model_file_not_found_cloud(base_scenario_yaml):
    """Test cloud model path validation (file must exist)."""
    yaml_content = base_scenario_yaml + """
ml_inference:
  placement: cloud
  cloud_config:
    model_path: /nonexistent/model.pt
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(yaml_content)
        yaml_path = f.name

    try:
        with pytest.raises(FileNotFoundError, match="Cloud ML model not found"):
            load_scenario(yaml_path)
    finally:
        os.unlink(yaml_path)


def test_backward_compatibility(base_scenario_yaml):
    """Test existing scenarios without ml_inference still work."""
    # This is the base scenario without ML config
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(base_scenario_yaml)
        yaml_path = f.name

    try:
        scenario = load_scenario(yaml_path)

        # Should load successfully
        assert scenario.duration_s == 10
        assert scenario.seed == 42
        assert len(scenario.nodes) == 1
        assert scenario.ml_inference is None  # Optional field

    finally:
        os.unlink(yaml_path)


def test_ml_inference_config_dataclass():
    """Test MLInferenceConfig dataclass validation."""
    # Valid edge config
    config = MLInferenceConfig(
        placement='edge',
        edge_config={'model_path': 'models/test_edge.onnx'},
        cloud_config=None
    )
    assert config.placement == 'edge'

    # Valid cloud config
    config2 = MLInferenceConfig(
        placement='cloud',
        edge_config=None,
        cloud_config={'model_path': 'models/test_cloud.pt'}
    )
    assert config2.placement == 'cloud'

    # Invalid placement
    with pytest.raises(ValueError, match="must be 'edge' or 'cloud'"):
        MLInferenceConfig(placement='invalid', edge_config=None, cloud_config=None)

    # Missing edge_config
    with pytest.raises(ValueError, match="requires 'edge_config'"):
        MLInferenceConfig(placement='edge', edge_config=None, cloud_config=None)

    # Missing cloud_config
    with pytest.raises(ValueError, match="requires 'cloud_config'"):
        MLInferenceConfig(placement='cloud', edge_config=None, cloud_config=None)


def test_ml_inference_missing_placement(base_scenario_yaml):
    """Test ml_inference section without placement field."""
    yaml_content = base_scenario_yaml + """
ml_inference:
  edge_config:
    model_path: models/test.onnx
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(yaml_content)
        yaml_path = f.name

    try:
        with pytest.raises(ValueError, match="must specify 'placement'"):
            load_scenario(yaml_path)
    finally:
        os.unlink(yaml_path)
