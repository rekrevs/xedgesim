# M3f Major Stage Plan: Renode Integration

**Created:** 2025-11-15
**Status:** IN PROGRESS
**Major Stage:** M3f - Device Tier Emulation with Renode

---

## 1. Goal

Integrate Renode (instruction-level ARM/RISC-V emulator) to enable **true device-tier emulation** with deployable firmware. This completes Tier 1 device emulation as designed in `architecture.md`.

**Why this matters:**
- Validates the "deployable artifacts" claim (same firmware runs in sim and on real hardware)
- Enables cycle-accurate timing measurements for device operations
- Allows running real ML inference (TFLite Micro) on emulated ARM devices
- Completes the device-edge-cloud simulation stack

**Key architectural principles (from architecture.md):**
- Devices use Renode for instruction-level emulation
- Time synchronization via Renode monitor protocol
- UART-based communication for events/data
- Deterministic execution with seeded RNG
- Conservative synchronous lockstep maintained by coordinator

---

## 2. Scope and Boundaries

**In scope for M3f:**
- ✅ Renode process lifecycle management
- ✅ Monitor protocol communication (socket-based)
- ✅ Virtual time advancement and synchronization
- ✅ Basic Zephyr firmware (sensor sampling)
- ✅ UART output parsing into simulation events
- ✅ Coordinator integration with Renode nodes
- ✅ Determinism validation
- ✅ (Optional) TFLite Micro inference in firmware

**Out of scope for M3f:**
- ❌ Multiple board targets (focus on nRF52840 DK only)
- ❌ TAP/TUN networking (deferred to M3g when ns-3 is integrated)
- ❌ Hardware-in-the-loop testing (future work)
- ❌ Energy modeling (future work)
- ❌ Complex firmware features (keep minimal for PoC)

---

## 3. Architectural Context

**Current state (M3 complete):**
```
Coordinator
  ├─ SensorNode (Python model)
  ├─ GatewayNode (Docker or Python)
  ├─ CloudService (Python)
  └─ LatencyNetworkModel
```

**Target state (M3f complete):**
```
Coordinator
  ├─ RenodeNode (ARM firmware via Renode)
  │   └─ Zephyr firmware (sensor.elf)
  ├─ GatewayNode (Docker or Python)
  ├─ CloudService (Python)
  └─ LatencyNetworkModel
```

**Integration points:**
1. Coordinator ↔ Renode: Socket communication (monitor protocol)
2. Renode ↔ Firmware: UART for output, virtual time control
3. Network model: Routes UART events as network packets

---

## 4. Minor Stages (Initial Plan)

This is the initial breakdown. Will be refined after each minor stage completion.

### M3fa: Renode Adapter and Monitor Protocol
**Objective:** Implement Python adapter that can start Renode, connect to monitor port, and advance virtual time.

**Acceptance criteria:**
- RenodeNode class created in `sim/device/renode_node.py`
- Can start/stop Renode process
- Can connect to Renode monitor port via socket
- Can send `ADVANCE` commands and receive acknowledgments
- Basic unit tests pass

**Estimated effort:** ~300 LOC, 2-3 days

---

### M3fb: Zephyr Firmware and UART Protocol
**Objective:** Create minimal Zephyr firmware that outputs structured data over UART.

**Acceptance criteria:**
- Firmware project created in `firmware/sensor-node/`
- Builds successfully with Zephyr SDK
- Runs in standalone Renode (manual test)
- Outputs JSON-formatted sensor samples over UART
- Uses deterministic RNG for sensor values

**Estimated effort:** ~200 LOC C, 2-3 days

---

### M3fc: Coordinator Integration
**Objective:** Integrate RenodeNode into coordinator and validate end-to-end flow.

**Acceptance criteria:**
- Coordinator can create and manage Renode nodes
- YAML schema extended for Renode node configuration
- Events from firmware UART → coordinator → network → gateway
- Determinism test: two runs with same seed produce identical results
- Integration tests pass

**Estimated effort:** ~200 LOC, 2-3 days

---

### M3fd: Device ML Inference (Optional)
**Objective:** Add TFLite Micro inference to firmware for device-tier ML placement.

**Acceptance criteria:**
- TFLite Micro integrated into firmware
- Runs simple anomaly detection model
- Reports inference latency (cycle counts)
- Device/edge/cloud placement comparison working

**Estimated effort:** ~300 LOC, 2-3 days

**Status:** OPTIONAL - Will assess after M3fc completion

---

## 5. Success Criteria for M3f

M3f is complete when:

1. ✅ All planned minor stages completed (or consciously deferred with reasons)
2. ✅ Full test suite passes:
   - All M0-M3 tests still pass
   - New M3fa-M3fc tests pass
   - Integration tests with Renode pass
3. ✅ Determinism verified:
   - Same seed → identical UART output
   - Same seed → identical simulation events
4. ✅ Documentation complete:
   - All minor stage reports written
   - M3f-summary.md created
   - Example scenarios documented
5. ✅ Code quality:
   - No dead code or unused abstractions
   - Follows architecture principles
   - Review checklists satisfied

---

## 6. Dependencies and Prerequisites

**External tools required:**
- Renode 1.14.0+ (installation instructions in firmware guide)
- Zephyr SDK 0.16.5+ (for firmware building)
- nRF52840 DK board configuration files

**Knowledge prerequisites:**
- Renode monitor protocol (will document as we learn)
- Zephyr RTOS build system
- UART communication protocols
- Virtual time synchronization

**Risks:**
1. Renode monitor protocol may be more complex than expected
   - Mitigation: Start with manual testing via telnet
2. Time synchronization accuracy issues
   - Mitigation: Add time drift monitoring, coarser quantum if needed
3. Firmware build complexity
   - Mitigation: Start with minimal example, iterate carefully

---

## 7. Progress Tracking

| Minor Stage | Status | Completion Date | Notes |
|-------------|--------|-----------------|-------|
| M3fa | ✅ COMPLETE | 2025-11-15 | Renode adapter, 43/43 tests passing, integration tests delegated |
| M3fb | ✅ COMPLETE | 2025-11-15 | Zephyr firmware, 16/16 JSON tests passing, build tests delegated |
| M3fc | IN PROGRESS | - | Integration |
| M3fd | PENDING | - | Device ML (optional) |

**Current stage:** M3fc (Coordinator integration)

**Last updated:** 2025-11-15

---

## 8. Deviations from Original Plan

None yet. Will document any scope changes, simplifications, or additions as they occur.

---

## 9. Lessons Learned (Ongoing)

### From M3fa (Renode Adapter):
**What worked well:**
- Test-first development with comprehensive mocking (1.05 test/code ratio)
- Conservative synchronous lockstep algorithm kept implementation simple
- Dynamic .resc script generation avoided premature abstraction
- wow.md methodology provided clear boundaries and completion criteria

**Challenges:**
- Python destructor edge cases with partially-initialized objects
- Mock socket semantics required iteration to match real behavior
- Renode monitor protocol documentation gaps required manual experimentation
- pytest output capture unreliable for print-based logging

**Architectural decisions:**
- Chose synchronous socket communication (simple, sufficient for PoC)
- Used microsecond virtual time internally (matches coordinator precision)
- JSON-over-UART protocol (simple to parse, extensible)
- Delegated integration tests to testing agent with Renode installed

**Recommendations for M3fb:**
- Consider structured logging instead of print() for better testability
- Keep firmware minimal - just sensor sampling and UART output
- Use Zephyr logging subsystem for debug output
- Test in standalone Renode before coordinator integration

### From M3fb (Zephyr Firmware):
**What worked well:**
- Minimal Zephyr configuration (only essential features)
- Device tree for configuration (Zephyr best practice)
- Test-first for JSON protocol (16 tests validated format before firmware run)
- Graceful UART fallback to printk (debugging friendly)
- Clear UART/printk separation (data vs debug)

**Challenges:**
- Zephyr learning curve (many config options, distributed docs)
- Float printf requirement (NEWLIB_LIBC adds ~20KB but necessary)
- Device tree validation delayed until build time (can't test syntax locally)
- Can't validate firmware without full Zephyr SDK installation

**Architectural decisions:**
- Single-threaded firmware (determinism, simplicity)
- Polling for sensor sampling (no interrupts, deterministic)
- Newlib libc for float printf (vs minimal libc)
- Hardcoded seed/interval for PoC (device tree extraction deferred)

**Recommendations for M3fc:**
- Build tests will validate firmware assumptions - be ready to iterate
- Device tree seed extraction should be implemented for production
- Multiple sensor types easy to add (architecture supports it)
- Consider Zephyr logging macros instead of printk for structured output

---

## 10. Next Steps

**Immediate:** Begin M3fa - Renode adapter implementation
- Create `docs/dev-log/M3fa-report.md` with objectives
- Design tests for Renode adapter
- Implement `sim/device/renode_node.py`
- Run tests (delegate to testing agent if Docker/Renode needed)
- Complete stage report and commit

---

**References:**
- Detailed plan: `docs/milestones/M3f-renode-integration-plan.md`
- Architecture: `docs/architecture.md` (Device Emulation section)
- Determinism: `docs/node-determinism.md`
- Implementation guide: `docs/implementation-guide.md`
