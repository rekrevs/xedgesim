# M1d: Simple Latency Network Model

**Stage:** M1d
**Date:** 2025-11-15
**Status:** IN PROGRESS

---

## Objective

Implement a deterministic network model with configurable latency and optional packet loss, without requiring ns-3 integration.

**Scope:**
- Implement `LatencyNetworkModel` with per-link latency configuration
- Event queue for in-flight packets
- Optional packet loss (percentage-based, deterministic)
- YAML configuration for network parameters
- Maintain determinism (seeded RNG for packet loss)

**Explicitly excluded:**
- ns-3 integration (deferred to M1f)
- Complex topology routing (simple point-to-point links)
- Bandwidth constraints (just latency and loss)
- Reordering effects (FIFO delivery)

---

## Acceptance Criteria

1. ⬜ `LatencyNetworkModel` class implements NetworkModel interface
2. ⬜ Configurable per-link latency (microseconds)
3. ⬜ Optional packet loss (percentage, deterministic based on seed)
4. ⬜ Event queue maintains in-flight packets
5. ⬜ YAML schema extended for network configuration
6. ⬜ Determinism test passes (same seed → same results)
7. ⬜ Unit tests for LatencyNetworkModel
8. ⬜ Integration test validates latency behavior
9. ⬜ Git commit with clean implementation

---

## Design Decisions

### LatencyNetworkModel Architecture

**State:**
- Event queue (priority queue sorted by delivery time)
- RNG for packet loss (seeded deterministically)
- Link configuration (latency and loss per link)

**Configuration:**
```yaml
network:
  model: latency  # or "direct" for DirectNetworkModel
  default_latency_us: 10000  # 10ms default
  links:
    - src: sensor1
      dst: gateway
      latency_us: 5000   # 5ms
      loss_rate: 0.01    # 1% packet loss
    - src: sensor2
      dst: gateway
      latency_us: 8000   # 8ms
      loss_rate: 0.0     # No loss
```

**Algorithm:**
```python
def route_message(event):
    # Look up link configuration
    link = find_link(event.src, event.dst)

    # Determine if packet is dropped (deterministic RNG)
    if random() < link.loss_rate:
        return []  # Packet dropped

    # Calculate delivery time
    delivery_time = event.time_us + link.latency_us

    # Create delayed event
    delayed_event = Event(
        time_us=delivery_time,
        type=event.type,
        src=event.src,
        dst=event.dst,
        payload=event.payload,
        size_bytes=event.size_bytes
    )

    # Add to event queue
    event_queue.push(delayed_event)

    return []  # No immediate delivery

def advance_to(target_time_us):
    # Deliver all events up to target time
    ready_events = []
    while event_queue and event_queue.peek().time_us <= target_time_us:
        ready_events.append(event_queue.pop())
    return ready_events
```

### YAML Schema Extension

Add `network` section to scenario YAML:

```yaml
simulation:
  duration_s: 10
  seed: 42
  time_quantum_us: 1000

network:
  model: latency
  default_latency_us: 10000
  default_loss_rate: 0.0
  links:
    - src: sensor1
      dst: gateway
      latency_us: 5000
      loss_rate: 0.01

nodes:
  - id: sensor1
    type: sensor_model
    port: 5001
  # ... (unchanged)
```

**Backward compatibility:**
- If `network` section missing, default to DirectNetworkModel
- If `network.model: direct`, use DirectNetworkModel
- If `network.model: latency`, use LatencyNetworkModel

### Determinism Strategy

**Critical:** Packet loss must be deterministic.

**Approach:**
1. Seed RNG with simulation seed + link identifier
2. Use same RNG sequence for each link across runs
3. Validate with hash-based determinism test

**Implementation:**
```python
def __init__(self, config, seed):
    # Deterministic RNG per link
    self.rngs = {}
    for link in config.links:
        link_id = f"{link.src}_{link.dst}"
        hash_input = f"{link_id}_{seed}".encode('utf-8')
        hash_digest = hashlib.sha256(hash_input).digest()
        link_seed = int.from_bytes(hash_digest[:8], 'big')
        self.rngs[link_id] = random.Random(link_seed)
```

---

## Tests to Add

### 1. Unit Tests (tests/stages/M1d/)

**test_latency_network_model.py:**
- `test_route_with_latency()` - Event delayed by configured latency
- `test_advance_delivers_ready_events()` - Events delivered at correct time
- `test_advance_keeps_future_events()` - Events not yet ready remain queued
- `test_packet_loss_deterministic()` - Same seed → same drops
- `test_default_latency()` - Use default if link not configured
- `test_reset_clears_queue()` - reset() empties event queue
- `test_fifo_ordering()` - Events delivered in time order

### 2. Integration Tests

**test_coordinator_with_latency.py:**
- Create scenario with LatencyNetworkModel
- Verify messages delayed correctly
- Verify packet loss works
- Verify determinism (same seed → identical results)

### 3. Regression Tests

**Ensure M0, M1b, M1c tests still pass:**
- M0 determinism (DirectNetworkModel still default)
- M1b YAML scenarios (backward compatible)
- M1c DirectNetworkModel tests

---

## Implementation Plan

**Step 1:** Extend YAML schema
- Update `sim/config/scenario.py` to parse `network` section
- Add `NetworkConfig` dataclass
- Validate network configuration

**Step 2:** Write unit tests for LatencyNetworkModel
- Test latency behavior
- Test packet loss (deterministic)
- Test event queue management

**Step 3:** Implement LatencyNetworkModel
- Create `sim/network/latency_model.py`
- Implement event queue (heapq)
- Implement deterministic packet loss
- Implement link configuration lookup

**Step 4:** Update coordinator to use network config
- Load network model based on YAML config
- Pass network config to LatencyNetworkModel

**Step 5:** Integration testing
- Create test scenarios with latency
- Verify message delays
- Verify determinism with latency model

---

## Known Limitations

**Intentional for M1d:**
- No bandwidth constraints (just latency)
- No packet reordering (FIFO delivery)
- No congestion simulation
- Simple point-to-point links (no routing)
- No protocol-specific behavior (TCP/UDP)

**Design constraints:**
- Must maintain determinism
- Must not break backward compatibility
- Interface already defined by NetworkModel ABC

---

## Next Steps

After M1d:
- M1e will add network metrics collection
- M1f may add ns-3 integration (or defer to M1.5)

---

**Status:** IN PROGRESS
**Estimated Time:** 3-4 hours
**Started:** 2025-11-15
