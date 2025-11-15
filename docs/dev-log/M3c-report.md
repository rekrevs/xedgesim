# M3c: ML Placement YAML Schema

**Stage:** M3c
**Date:** 2025-11-15
**Status:** COMPLETE

---

## Objective

Extend YAML scenario schema to specify ML placement configurations, enabling comparison of edge vs cloud ML inference strategies.

**Scope:**
- Add `ml_inference` section to YAML scenarios
- Specify placement location (edge/cloud), model paths, and configurations
- Schema validation in sim/config/scenario.py
- Example scenarios: edge-only, cloud-only
- Integration with M3a edge container and M3b cloud service

**Explicitly excluded:**
- Auto-selection of optimal placement (manual specification only)
- Dynamic placement switching at runtime
- Multi-model inference pipelines
- Federated learning configurations

---

## Acceptance Criteria

1. ✅ YAML schema extended with `ml_inference` section
2. ✅ Supports `placement: edge` or `placement: cloud`
3. ✅ Supports model path specification
4. ✅ Supports inference configuration (latency thresholds, etc.)
5. ✅ Schema validation tests pass (6/6 local tests)
6. ✅ Example scenarios created (edge-only, cloud-only)
7. ✅ All M0-M2 regression tests still pass (8/8 M1b tests verified)

---

## Design Decisions

### YAML Schema Structure

**Design choice:** Add `ml_inference` section at scenario level (global config).

**Rationale:**
- ML placement strategy typically applies to entire scenario
- Simpler than per-node configuration
- Aligns with M2d `implementation` pattern (scenario-level choice)

**Structure:**
```yaml
scenario:
  name: "edge_ml_placement"
  duration_sec: 60
  ml_inference:
    placement: edge  # or 'cloud'
    edge_config:
      model_path: "models/anomaly_detector.onnx"
      broker_host: "localhost"
      broker_port: 1883
    cloud_config:
      model_path: "models/anomaly_detector.pt"
      broker_host: "localhost"
      broker_port: 1883
      latency_ms: 50
```

**Alternative considered:** Per-node ML configuration
- Would allow mixed placement (some nodes edge, some cloud)
- Rejected for M3c: Too complex, defer to M4+
- M3c focuses on scenario-wide comparison

### Placement Options

**Options:**
1. `placement: edge` - All inference at edge tier (M3a container)
2. `placement: cloud` - All inference at cloud tier (M3b service)
3. `placement: hybrid` - Deferred to M4+ (requires dynamic routing)

**Configuration validation:**
- If `placement: edge`, require `edge_config` section
- If `placement: cloud`, require `cloud_config` section
- Report error if required config missing

### Integration with Existing Nodes

**How nodes connect to ML inference:**

**Device nodes (sensors):**
- Generate sensor readings
- Publish to MQTT: `sensor/{device_id}/reading`
- ML inference service subscribes and processes

**Edge nodes (gateways):**
- If `placement: edge`, run ML container on gateway node
- Forward results to cloud or application tier
- If `placement: cloud`, forward raw data to cloud

**Cloud tier:**
- If `placement: cloud`, run CloudMLService
- Receive requests via MQTT
- Publish results back to device/edge

**Key insight:** ML placement is orthogonal to node topology. Same sensor network, different inference location.

### Model Path Specification

**Design choice:** Relative paths from repository root.

**Example:**
```yaml
ml_inference:
  placement: edge
  edge_config:
    model_path: "models/anomaly_detector.onnx"
```

**Rationale:**
- Consistent with M2d Docker volume mounting
- Portable across environments
- Clear where models should be stored

**Validation:**
- Check file exists at startup
- Report error if model missing
- Helps catch configuration issues early

### Inference Configuration

**Optional inference parameters:**

```yaml
ml_inference:
  placement: edge
  edge_config:
    model_path: "models/anomaly_detector.onnx"
    threshold: 0.5  # Anomaly detection threshold
    max_latency_ms: 100  # Target latency
    batch_size: 1  # For future batching
```

**M3c scope:** Support parameters in schema, but don't require full implementation yet.

**Rationale:**
- Schema should be forward-compatible
- Allows experiments to specify targets
- Implementation can come in M3d/M3e

---

## Implementation Plan

**Step 1:** Extend scenario.py schema parser
- Add `ml_inference` field parsing
- Validate placement value (edge/cloud)
- Parse edge_config and cloud_config
- Validate required fields present

**Step 2:** Update ScenarioConfig dataclass
- Add `ml_inference` field
- Store parsed configuration
- Make field optional (backward compatible)

**Step 3:** Create example scenarios
- `scenarios/m3c/edge_ml_placement.yaml` - Edge-only inference
- `scenarios/m3c/cloud_ml_placement.yaml` - Cloud-only inference
- Both scenarios use same sensor topology, different placement

**Step 4:** Create schema validation tests
- `tests/stages/M3c/test_ml_schema.py`
- Test edge placement config
- Test cloud placement config
- Test missing config error
- Test invalid placement value error
- Test model path validation

**Step 5:** Integration documentation
- Document how to specify ML placement
- Document configuration options
- Document validation rules

---

## Tests to Add

### Schema Validation Tests (tests/stages/M3c/)

**test_ml_schema.py:**
```python
def test_edge_placement_config():
    """Test YAML with edge ML placement config"""

def test_cloud_placement_config():
    """Test YAML with cloud ML placement config"""

def test_missing_ml_config():
    """Test scenario without ML config (should be optional)"""

def test_invalid_placement_value():
    """Test invalid placement value raises error"""

def test_missing_edge_config():
    """Test edge placement without edge_config raises error"""

def test_missing_cloud_config():
    """Test cloud placement without cloud_config raises error"""

def test_model_path_validation():
    """Test model path validation (file exists check)"""

def test_backward_compatibility():
    """Test existing scenarios without ml_inference still work"""
```

---

## Example YAML Scenarios

### Edge ML Placement

**scenarios/m3c/edge_ml_placement.yaml:**
```yaml
scenario:
  name: "anomaly_detection_edge"
  description: "Anomaly detection with edge ML inference"
  duration_sec: 60

  ml_inference:
    placement: edge
    edge_config:
      model_path: "models/anomaly_detector.onnx"
      broker_host: "localhost"
      broker_port: 1883
      threshold: 0.5

nodes:
  - id: sensor1
    type: sensor
    implementation: python_model
    port: 5001
    config:
      sensor_type: "vibration"
      sample_rate_hz: 10

  - id: gateway1
    type: gateway
    implementation: docker
    port: 5002
    docker:
      image: xedgesim/ml-inference:latest
      build_context: containers/ml-inference
      ports:
        5000: 5000
      environment:
        MODEL_PATH: /app/models/anomaly_detector.onnx
        MQTT_BROKER_HOST: host.docker.internal
        MQTT_BROKER_PORT: 1883
      volumes:
        models: /app/models

  - id: broker1
    type: mqtt_broker
    implementation: docker
    port: 5003
    docker:
      image: xedgesim/mosquitto:latest
      build_context: containers/mqtt-broker
      ports:
        1883: 1883
```

### Cloud ML Placement

**scenarios/m3c/cloud_ml_placement.yaml:**
```yaml
scenario:
  name: "anomaly_detection_cloud"
  description: "Anomaly detection with cloud ML inference"
  duration_sec: 60

  ml_inference:
    placement: cloud
    cloud_config:
      model_path: "models/anomaly_detector.pt"
      broker_host: "localhost"
      broker_port: 1883
      latency_ms: 50
      threshold: 0.5

nodes:
  - id: sensor1
    type: sensor
    implementation: python_model
    port: 5001
    config:
      sensor_type: "vibration"
      sample_rate_hz: 10

  - id: broker1
    type: mqtt_broker
    implementation: docker
    port: 5003
    docker:
      image: xedgesim/mosquitto:latest
      build_context: containers/mqtt-broker
      ports:
        1883: 1883

# Cloud ML service started separately (not a node in topology)
# Uses CloudMLService Python class with cloud_config parameters
```

---

## Code Structure

### sim/config/scenario.py

**ScenarioConfig dataclass extension:**
```python
@dataclass
class MLInferenceConfig:
    """ML inference configuration."""
    placement: str  # 'edge' or 'cloud'
    edge_config: Optional[Dict[str, Any]] = None
    cloud_config: Optional[Dict[str, Any]] = None

@dataclass
class ScenarioConfig:
    """Scenario configuration."""
    name: str
    description: str
    duration_sec: int
    nodes: List[Dict[str, Any]]
    ml_inference: Optional[MLInferenceConfig] = None  # M3c
```

**Schema validation:**
```python
def parse_ml_inference(ml_section: Dict[str, Any]) -> MLInferenceConfig:
    """Parse and validate ML inference configuration."""
    placement = ml_section.get('placement')

    if placement not in ['edge', 'cloud']:
        raise ValueError(f"Invalid placement: {placement}")

    if placement == 'edge' and 'edge_config' not in ml_section:
        raise ValueError("edge placement requires edge_config")

    if placement == 'cloud' and 'cloud_config' not in ml_section:
        raise ValueError("cloud placement requires cloud_config")

    # Validate model paths
    if placement == 'edge':
        model_path = ml_section['edge_config'].get('model_path')
        if not Path(model_path).exists():
            raise FileNotFoundError(f"Edge model not found: {model_path}")

    if placement == 'cloud':
        model_path = ml_section['cloud_config'].get('model_path')
        if not Path(model_path).exists():
            raise FileNotFoundError(f"Cloud model not found: {model_path}")

    return MLInferenceConfig(
        placement=placement,
        edge_config=ml_section.get('edge_config'),
        cloud_config=ml_section.get('cloud_config')
    )
```

---

## Known Limitations

**Intentional for M3c:**
- Single placement per scenario (no mixed strategies)
- Manual placement specification (no auto-selection)
- No dynamic switching at runtime
- No multi-model pipelines
- No federated learning

**Rationale:** M3c establishes schema foundation. Advanced features in M4+.

---

## Integration with M3a/M3b

**M3a Edge Container:**
- Configuration comes from YAML `edge_config`
- Environment variables set from edge_config
- Volume mount for model_path
- MQTT broker config from edge_config

**M3b Cloud Service:**
- CloudMLService initialized with cloud_config parameters
- model_path, broker_host, broker_port, latency_ms
- Started separately from topology (not a node)
- Listens on same MQTT broker as edge

**Key benefit:** Same scenario topology, just swap placement config. Enables direct comparison.

---

**Status:** IN PROGRESS
**Estimated Time:** 2-3 hours
**Started:** 2025-11-15
