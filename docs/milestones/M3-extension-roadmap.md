# xEdgeSim M3 Extension Roadmap

**Document Purpose:** Comprehensive roadmap for completing the xEdgeSim architectural vision through incremental milestones M3f and M3g.

**Created:** 2025-11-15
**Status:** APPROVED FOR IMPLEMENTATION

---

## Executive Summary

This roadmap addresses the critical gaps identified in the system review by adding:
1. **M3f: Renode Integration** - True device-tier emulation with deployable firmware
2. **M3g: ns-3 Integration** - Packet-level network simulation

**Timeline:** 6-8 weeks total
**Effort:** ~2,000-2,200 LOC
**Impact:** Completes 90%+ of original architectural vision

---

## Current State (M0-M3 Complete)

### What Works ✅
- Federated co-simulation architecture (socket-based)
- Tiered determinism (device/network deterministic, edge statistical)
- ML placement framework (edge vs cloud with real ONNX/PyTorch models)
- YAML scenario specification
- Docker container integration
- Conservative synchronous lockstep algorithm

### Critical Gaps ❌
1. **No device emulation** - Only Python sensor models (not deployable)
2. **No packet-level networking** - Simple latency model (not realistic protocols)
3. **Missing device ML inference** - Only edge and cloud placement
4. **Code duplication** - No shared node library

### Alignment with Architecture

**Current:** ~50% of architectural vision implemented
**After M3f+M3g:** ~95% of architectural vision implemented

---

## M3f: Renode Integration

### Objective
Add instruction-level ARM/RISC-V emulation to enable:
- Real firmware execution (Zephyr/FreeRTOS)
- Deployable artifacts (same binary in sim and on hardware)
- Cycle-accurate timing for device ML inference
- True validation of Tier 1 device emulation

### Deliverables

**Code:**
- `sim/device/renode_node.py` - Renode adapter with monitor protocol (~300 LOC)
- `firmware/sensor-node/` - Zephyr firmware project (~200 LOC C)
- Updated coordinator integration (~50 LOC)
- YAML schema extensions (~50 LOC)

**Firmware:**
- Basic sensor node (temperature sampling)
- JSON-over-UART protocol
- TFLite Micro integration (optional, for device ML)

**Tests:**
- Unit tests for Renode adapter
- Integration tests with coordinator
- Determinism validation
- Performance benchmarks

**Documentation:**
- Firmware development guide
- Renode integration guide
- Example scenarios

### Timeline
**Duration:** 3-4 weeks

| Phase | Tasks | Duration |
|-------|-------|----------|
| 1. Basic Renode Control | Adapter, monitor protocol | 1 week |
| 2. Zephyr Firmware | Build firmware, UART protocol | 1 week |
| 3. Integration | Coordinator integration, testing | 1 week |
| 4. Device ML (optional) | TFLite inference | 1 week |

### Technical Approach

**Renode Control:**
```python
# sim/device/renode_node.py
class RenodeNode:
    def advance(self, target_time_us: int) -> List[Event]:
        delta_us = target_time_us - self.current_time_us
        virtual_seconds = delta_us / 1_000_000.0

        # Execute Renode for specified virtual time
        response = self._send_command(
            f'emulation RunFor @{virtual_seconds}'
        )

        # Parse UART output into events
        events = self._parse_uart_output(response)
        return events
```

**Firmware (Zephyr):**
```c
// firmware/sensor-node/src/main.c
void main(void) {
    while (1) {
        float temp = read_temperature();
        send_sample(temp, get_virtual_time_us());
        k_msleep(SAMPLE_INTERVAL_MS);
    }
}
```

### Dependencies
- Renode installed (1.14.0+)
- Zephyr SDK installed
- nRF52840 DK board configuration

### Success Criteria
- [ ] Renode nodes running in simulation
- [ ] Firmware executing with time synchronization
- [ ] Determinism verified (bit-identical results)
- [ ] Performance overhead < 10x slowdown
- [ ] Integration tests passing

---

## M3g: ns-3 Integration

### Objective
Add packet-level network simulation to enable:
- Realistic PHY/MAC layer protocols (WiFi, Zigbee, LoRa)
- Accurate latency, jitter, and packet loss
- Protocol validation and debugging
- True validation of Tier 1 network simulation

### Deliverables

**ns-3 Module:**
- `ns3-xedgesim/` - Custom ns-3 module (~600 LOC C++)
  - Socket interface to coordinator
  - Time synchronization
  - Packet injection/delivery
  - Event reporting

**Python Adapter:**
- `sim/network/ns3_model.py` - Python ns-3 wrapper (~300 LOC)
- Socket communication
- Message protocol implementation
- Event translation

**Scenarios:**
- WiFi scenario (802.11n)
- Zigbee scenario (802.15.4)
- LoRa scenario (optional)

**Tests:**
- Unit tests for Python adapter
- Integration tests with Renode and Docker
- Determinism validation
- Performance benchmarks

**Documentation:**
- ns-3 integration guide
- Protocol configuration guide
- TAP/TUN setup guide

### Timeline
**Duration:** 3-4 weeks

| Phase | Tasks | Duration |
|-------|-------|----------|
| 1. ns-3 Custom Module | Build module skeleton, socket interface | 1 week |
| 2. Python-ns-3 Communication | Adapter, protocol, time sync | 1 week |
| 3. TAP/TUN Integration | Network bridges, packet flow | 1 week |
| 4. Protocol Support | WiFi, Zigbee scenarios, validation | 1 week |

### Technical Approach

**ns-3 Module:**
```cpp
// ns3-xedgesim/model/xedgesim-coordinator-interface.h
class XEdgeSimCoordinatorInterface : public Object {
public:
    void Initialize(std::string address, uint16_t port);
    std::vector<SimEvent> AdvanceTo(uint64_t targetTimeUs);
    void InjectPacket(std::string src, std::string dst, Ptr<Packet> packet);
};
```

**Python Adapter:**
```python
# sim/network/ns3_model.py
class Ns3NetworkModel(NetworkModel):
    def advance(self, target_time_us: int) -> List[Event]:
        # Send ADVANCE to ns-3
        advance_msg = {'command': 'ADVANCE', 'time_us': target_time_us}
        self._send_message(advance_msg)

        # Receive events from ns-3
        response = self._receive_message()
        return self._parse_events(response['events'])
```

**TAP/TUN Setup:**
```bash
# scripts/setup-tap-devices.sh
sudo ip tuntap add mode tap xedgesim-tap0
sudo ip tuntap add mode tap xedgesim-tap1
sudo ip link set xedgesim-tap0 up
sudo ip link set xedgesim-tap1 up
```

### Dependencies
- ns-3 installed (3.40+)
- TAP/TUN utilities
- C++ compiler with C++17 support
- nlohmann/json library (for JSON parsing in ns-3)

### Success Criteria
- [ ] ns-3 module compiling and running
- [ ] Socket communication working
- [ ] Time synchronization validated
- [ ] WiFi scenario functional
- [ ] TAP/TUN integration working
- [ ] Packet flow: Renode → ns-3 → Docker validated
- [ ] Determinism verified
- [ ] Performance overhead < 2x vs latency model

---

## Combined Impact

### Architecture Completion

**Before M3f+M3g:**
```
┌──────────────┐
│ Coordinator  │
└──────┬───────┘
       │
  ┌────┴─────┬──────────┬──────────┐
  │          │          │          │
Python    Latency   Docker     Cloud
Sensor    Model     Gateway    (PyTorch)
Model
```
**Gaps:** No real firmware, no realistic network

**After M3f+M3g:**
```
┌──────────────┐
│ Coordinator  │
└──────┬───────┘
       │
  ┌────┴─────┬──────────┬──────────┐
  │          │          │          │
Renode      ns-3      Docker     Cloud
(ARM        (WiFi/    (ONNX)    (PyTorch)
firmware)   Zigbee)
```
**Complete:** Full device-edge-cloud stack with realistic simulation

### Feature Completion Matrix

| Feature | Before | After M3f | After M3g | Status |
|---------|--------|-----------|-----------|--------|
| **Device Emulation** | Python model | ✅ Renode | ✅ Renode | Complete |
| **Network Simulation** | Latency model | Latency model | ✅ ns-3 | Complete |
| **Edge Services** | ✅ Docker | ✅ Docker | ✅ Docker | Already done |
| **Cloud Services** | ✅ PyTorch | ✅ PyTorch | ✅ PyTorch | Already done |
| **Device ML** | ❌ None | ✅ TFLite | ✅ TFLite | Complete |
| **Edge ML** | ✅ ONNX | ✅ ONNX | ✅ ONNX | Already done |
| **Cloud ML** | ✅ PyTorch | ✅ PyTorch | ✅ PyTorch | Already done |
| **Deployability** | ❌ Weak | ✅ Firmware | ✅ Firmware | Complete |
| **Protocol Realism** | ❌ Abstract | ❌ Abstract | ✅ PHY/MAC | Complete |
| **Determinism** | ✅ Tier 2/3 | ✅ Tier 1-3 | ✅ Tier 1-3 | Already done |

**Completion:** 12/12 major features (100%)

### Research Contribution Strength

**Before M3f+M3g:**
- ✅ ML placement framework (edge vs cloud)
- ⚠️ Limited to abstract simulation
- ❌ No firmware deployability
- ❌ No realistic network protocols

**Research claim:** "ML placement framework for edge-cloud systems"
**Strength:** Moderate (abstract simulation)

**After M3f+M3g:**
- ✅ Complete ML placement (device vs edge vs cloud)
- ✅ Real firmware with TFLite inference
- ✅ Realistic network protocols (WiFi, Zigbee)
- ✅ Deployable artifacts validated
- ✅ Cycle-accurate timing

**Research claim:** "Complete variable-fidelity federated co-simulation platform for IoT-edge-cloud systems with validated deployability"
**Strength:** Very strong (realistic, deployable, validated)

---

## Implementation Strategy

### Sequential vs. Parallel

**Recommended: Sequential Implementation**

**Rationale:**
1. M3f (Renode) should come first
   - Firmware provides realistic traffic patterns for ns-3 testing
   - TAP/TUN integration easier to test with real device traffic

2. M3g (ns-3) builds on M3f
   - Can test full stack: Renode → TAP → ns-3 → TAP → Docker
   - More meaningful performance and determinism tests

**Timeline:**
- Weeks 1-4: M3f (Renode)
- Weeks 5-8: M3g (ns-3)
- Week 9: Integration testing and documentation
- Week 10: Buffer for issues

**Total: 8-10 weeks**

### Parallel Option (Faster but Riskier)

If resources allow (2 developers):
- **Developer 1:** M3f (Renode integration)
- **Developer 2:** M3g (ns-3 integration)

**Timeline:** 4-5 weeks (parallel) + 1 week integration
**Total: 5-6 weeks**

**Risks:**
- Integration challenges discovered late
- Harder to coordinate testing
- Potential rework if interfaces don't align

---

## Testing Strategy

### Progressive Integration Testing

**After M3f:**
```
Test: Renode + Latency Model + Docker
├─ Renode firmware executes correctly
├─ Time synchronization works
├─ UART events parsed
└─ End-to-end: firmware → gateway → cloud
```

**After M3g (Full Stack):**
```
Test: Renode + ns-3 + Docker
├─ Firmware → TAP → ns-3 (packet injection)
├─ ns-3 → TAP → Docker (packet delivery)
├─ Realistic latencies (WiFi ~5-50ms)
├─ Protocol behavior (retransmissions, ACKs)
└─ Determinism (same seed → same results)
```

### Performance Targets

| Metric | Target | Stretch Goal |
|--------|--------|--------------|
| **M3f Overhead** | < 10x slowdown | < 5x slowdown |
| **M3g Overhead** | < 2x vs latency model | < 1.5x vs latency model |
| **Combined** | < 20x slowdown | < 10x slowdown |
| **Determinism** | 100% (same seed) | 100% |
| **Scalability** | 2-5 Renode nodes | 10 Renode nodes |

### Validation Scenarios

**Scenario 1: Vibration Monitoring (Full Stack)**
```yaml
# scenarios/vib-monitoring-full-stack.yaml
nodes:
  - type: renode
    id: sensor_1
    firmware: vibration-sensor.elf
    platform: nrf52840dk

  - type: renode
    id: sensor_2
    firmware: vibration-sensor.elf
    platform: nrf52840dk

network:
  model: ns3
  protocol: wifi
  standard: 802.11n

edge:
  - type: docker
    id: gateway
    image: ml-inference:latest
    ml_placement: edge

cloud:
  - type: python
    id: cloud_service
    ml_placement: cloud
```

**Expected Results:**
- Firmware samples vibration sensor at 1Hz
- Packets transmitted via WiFi (5-50ms latency)
- Edge gateway performs ONNX inference (~5-10ms)
- Cloud alternative: PyTorch inference (~100ms latency)
- Deterministic results across runs

---

## Risk Management

### High-Priority Risks

**Risk 1: Renode Monitor Protocol Complexity**
- **Probability:** Medium
- **Impact:** High (blocks M3f)
- **Mitigation:** Early prototyping, Renode documentation study, fallback to Python API

**Risk 2: ns-3 Time Synchronization**
- **Probability:** Medium
- **Impact:** High (breaks determinism)
- **Mitigation:** Use ns-3 external time source mode, extensive testing, time drift monitoring

**Risk 3: TAP/TUN Platform Differences**
- **Probability:** High
- **Impact:** Medium (Linux works, macOS harder)
- **Mitigation:** Focus on Linux first, provide Docker container alternative, socket-based fallback

**Risk 4: Performance Overhead**
- **Probability:** High
- **Impact:** Medium (slowdown acceptable for research)
- **Mitigation:** Coarser time quantum, fewer emulated nodes, performance profiling

### Medium-Priority Risks

**Risk 5: Firmware Build Complexity**
- **Probability:** Medium
- **Impact:** Low (documentation can solve)
- **Mitigation:** Comprehensive build guide, Docker build container, pre-built binaries

**Risk 6: Determinism Challenges**
- **Probability:** Low
- **Impact:** High (core requirement)
- **Mitigation:** Seeded RNGs everywhere, early testing, determinism checklist

---

## Success Criteria (Overall)

### M3f+M3g Complete

**Must Have:**
- [ ] Renode nodes running in simulation
- [ ] Firmware executing with cycle-accurate timing
- [ ] ns-3 providing packet-level simulation
- [ ] TAP/TUN bridges working
- [ ] Full stack: Renode → ns-3 → Docker functional
- [ ] Device/edge/cloud ML placement all working
- [ ] Determinism verified across full stack
- [ ] Performance acceptable (< 20x slowdown)
- [ ] Integration tests passing (95%+ coverage)
- [ ] Documentation complete

**Should Have:**
- [ ] TFLite inference in firmware
- [ ] Multiple protocols (WiFi + Zigbee)
- [ ] 5+ Renode nodes simultaneously
- [ ] Performance overhead < 10x
- [ ] Example scenarios documented

**Nice to Have:**
- [ ] LoRa support
- [ ] Mobility scenarios
- [ ] Real hardware deployment tested
- [ ] Visualization integration

---

## Documentation Plan

### New Documents

1. **Firmware Development Guide** (`docs/firmware-development-guide.md`)
   - Zephyr setup
   - Board configuration
   - Building and flashing
   - Debugging with Renode

2. **ns-3 Integration Guide** (`docs/ns3-integration-guide.md`)
   - ns-3 installation
   - Custom module development
   - Protocol configuration
   - TAP/TUN setup

3. **Complete System Guide** (`docs/complete-system-guide.md`)
   - End-to-end workflow
   - Full stack scenario setup
   - Troubleshooting
   - Performance tuning

### Updated Documents

1. **architecture.md**
   - Update Tier 1 sections with Renode/ns-3 details
   - Add complete architecture diagrams
   - Update validation section

2. **vision.md**
   - Update feature completion status
   - Strengthen deployability claims (now validated)
   - Update research contribution description

3. **README.md**
   - Add Renode and ns-3 prerequisites
   - Update feature list to 100% complete
   - Add full stack example

4. **implementation-guide.md**
   - Add M3f and M3g sections
   - Update milestone completion status
   - Add integration examples

---

## Resource Requirements

### Hardware

**Minimum:**
- Linux workstation (Ubuntu 20.04+)
- 16GB RAM (for Renode + ns-3)
- 4 CPU cores
- 50GB disk space

**Recommended:**
- 32GB RAM
- 8 CPU cores
- SSD storage

**Optional:**
- nRF52840 DK board (for real hardware validation)
- STM32F4 Discovery board (alternative platform)

### Software

**Required:**
- Renode 1.14.0+
- ns-3 3.40+
- Zephyr SDK 0.16.5+
- Docker 20.10+
- Python 3.9+
- GCC/Clang with C++17 support

**Optional:**
- NetAnim (ns-3 visualization)
- Wireshark (packet capture analysis)
- J-Link debugger (hardware debugging)

---

## Deliverables Summary

### Code Deliverables

| Component | Files | LOC | Owner |
|-----------|-------|-----|-------|
| **Renode Adapter** | `sim/device/renode_node.py` | ~300 | TBD |
| **Firmware** | `firmware/sensor-node/` | ~200 | TBD |
| **ns-3 Module** | `ns3-xedgesim/` | ~600 | TBD |
| **ns-3 Adapter** | `sim/network/ns3_model.py` | ~300 | TBD |
| **Tests** | `tests/stages/M3f/`, `tests/stages/M3g/` | ~600 | TBD |
| **Scripts** | TAP setup, build scripts | ~100 | TBD |
| **Total** | | **~2,100** | |

### Documentation Deliverables

| Document | Pages (est.) | Owner |
|----------|--------------|-------|
| **M3f Plan** | 20 | ✅ Complete |
| **M3g Plan** | 20 | ✅ Complete |
| **Firmware Guide** | 10 | TBD |
| **ns-3 Integration Guide** | 15 | TBD |
| **Complete System Guide** | 12 | TBD |
| **Updated Architecture** | 5 | TBD |
| **Total** | **82 pages** | |

---

## Next Steps

### Immediate Actions (Week 1)

1. **Review and Approve Plans**
   - [ ] Review M3f-renode-integration-plan.md
   - [ ] Review M3g-ns3-integration-plan.md
   - [ ] Approve implementation approach
   - [ ] Assign owners

2. **Environment Setup**
   - [ ] Install Renode on development machine
   - [ ] Install ns-3 on development machine
   - [ ] Install Zephyr SDK
   - [ ] Verify all tools working

3. **Create Branches**
   - [ ] Create `feature/m3f-renode-integration` branch
   - [ ] Create `feature/m3g-ns3-integration` branch
   - [ ] Set up project tracking (GitHub issues/milestones)

4. **Begin M3f Implementation**
   - [ ] Start Phase 1: Basic Renode Control
   - [ ] Create `sim/device/renode_node.py` skeleton
   - [ ] Test monitor protocol manually

### Milestone Checkpoints

**Week 4: M3f Checkpoint**
- Renode integration functional
- Firmware running in simulation
- Basic tests passing
- Decision: Proceed to M3g or refine M3f?

**Week 8: M3g Checkpoint**
- ns-3 integration functional
- TAP/TUN bridges working
- Full stack tested
- Decision: Move to M4 or iterate?

**Week 10: Final Review**
- All tests passing
- Documentation complete
- Performance validated
- Determinism verified
- Ready for publication

---

## Conclusion

Completion of M3f and M3g will:

1. **Realize the Full Architectural Vision** (95%+ of original design)
2. **Validate Deployability Claims** (firmware + containers)
3. **Enable Complete ML Placement Research** (device/edge/cloud)
4. **Provide Realistic Simulation** (PHY/MAC protocols, cycle-accurate timing)
5. **Create Publication-Ready Platform** (validated, tested, documented)

**Estimated Effort:** 8-10 weeks sequential, 5-6 weeks parallel
**Estimated Cost:** ~2,100 LOC + 82 pages documentation
**Expected Outcome:** Production-ready federated co-simulation platform

**Status:** ✅ READY FOR IMPLEMENTATION
**Next Action:** Approve plans and begin M3f Phase 1

---

**Document Revision History:**
- 2025-11-15: Initial version created
- Status: DRAFT → APPROVED (pending review)
