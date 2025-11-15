# M1 Development Plan: Network Realism

**Major Stage Goal:** Add realistic packet-level network simulation to xEdgeSim

**Architectural References:**
- `docs/architecture.md` §7 (Conservative Synchronous Lockstep)
- `docs/architecture.md` §11.M1 (ns-3 Integration)
- `docs/implementation-guide.md` §4 (ns-3 Integration Details)
- `docs/vision.md` (M1 Success Criteria)

**Design Constraints from Critical Analysis:**
- ⚠️ **Do NOT over-engineer**: Start with simplest possible network model
- ⚠️ **Defer full ns-3**: Implement network abstraction first, ns-3 later
- ⚠️ **Keep YAML simple**: No JSON schema validation, basic parsing only
- ⚠️ **Maintain determinism**: Network must be fully deterministic (seeded RNG)
- ⚠️ **Profile before optimizing**: Measure overhead before adding complexity

---

## Current System State (Post-M0)

**What works:**
- 3 sensor nodes + 1 gateway, all Python models
- Conservative lockstep time synchronization (1ms quantum)
- Direct message routing (sensor → gateway, no network layer)
- Determinism validated (identical results with same seed)
- Performance: 4.5x realtime for simple models

**What's missing:**
- No realistic network delays/losses
- No packet-level simulation
- Hardcoded topology (no configuration files)
- No network metrics (latency, throughput, drops)

---

## M1 Success Criteria (from docs)

Per `docs/vision.md`:
- ✅ Device → ns-3 → Edge packet flow working
- ✅ YAML scenario configuration functional
- ✅ Multiple network types supported (WiFi, Zigbee, LoRa)
- ✅ Cross-tier latency breakdown measured

**Adjusted for Incremental Approach:**

We will achieve these through minor stages:
- YAML scenarios (basic)
- Network abstraction layer
- Simple deterministic network model
- ns-3 integration (if time permits, or defer to M1.5)

---

## Planned Minor Stages (Initial List)

**Note:** This list will be updated after each minor stage based on learnings.

### M1a: Test Structure Reorganization ✅ (if needed)
**Objective:** Move M0 tests to proper location, create integration test framework
**Status:** PENDING (will do first)
**Estimate:** 1 hour

### M1b: Simple YAML Scenario Parser
**Objective:** Parse basic YAML config for nodes and simulation parameters
**Scope:**
- Parse node definitions (type, id, port)
- Parse simulation parameters (duration, seed, time_quantum)
- NO network topology yet
- NO JSON schema validation
**Deliverable:** Coordinator reads from YAML instead of hardcoded config
**Estimate:** 2-3 hours

### M1c: Network Abstraction Layer
**Objective:** Introduce `NetworkModel` interface to decouple routing from coordinator
**Scope:**
- Define `NetworkModel` abstract interface
- Implement `DirectNetworkModel` (current M0 behavior: zero latency)
- Coordinator uses NetworkModel instead of direct routing
- Tests verify identical behavior to M0
**Deliverable:** Same behavior as M0, but with pluggable network layer
**Estimate:** 2-3 hours

### M1d: Simple Latency Network Model
**Objective:** Implement deterministic latency/loss network model (no ns-3 yet)
**Scope:**
- `LatencyNetworkModel` with configurable per-link latency
- Optional packet loss (percentage, deterministic based on seed)
- Event queue for in-flight packets
- YAML configuration for network parameters
**Deliverable:** Realistic network delays without ns-3 complexity
**Estimate:** 3-4 hours

### M1e: Network Metrics Collection
**Objective:** Add network-tier metrics (latency, drops, throughput)
**Scope:**
- NetworkModel emits events for: packet_sent, packet_delivered, packet_dropped
- Coordinator logs network metrics to CSV
- Tests validate metrics consistency
**Deliverable:** Network performance analysis capability
**Estimate:** 2 hours

### M1f: ns-3 Integration (OPTIONAL - may defer to M1.5)
**Objective:** Replace LatencyNetworkModel with ns-3-based model
**Scope:**
- Build ns-3 wrapper (C++) per implementation-guide.md §4
- Implement `Ns3NetworkModel` class
- Support basic 802.15.4 or WiFi topology
- Validate determinism with ns-3
**Risk:** ns-3 integration is complex; may split into sub-stages
**Estimate:** 8-12 hours (if attempted)
**Decision:** Defer until M1d is complete and validated

---

## Deferred to Later Stages

**Not in M1:**
- ❌ Multiple network types (WiFi vs Zigbee) - just one type for M1
- ❌ Complex topology parsing - basic flat list of links
- ❌ TAP/TUN networking - not needed until Docker (M2)
- ❌ Renode integration - still using Python models
- ❌ Performance optimization - profile first

**Possibly M1.5 (between M1 and M2):**
- Full ns-3 integration (if deferred from M1f)
- Multiple network protocol support
- Complex topology scenarios

---

## Risk Assessment

**High Risk:**
- ns-3 build complexity (many dependencies)
- ns-3 determinism validation
- Performance impact of ns-3 (may need profiling)

**Medium Risk:**
- YAML parsing edge cases
- Network model interface design (too generic or too specific?)

**Low Risk:**
- Test reorganization
- Simple latency model
- Metrics collection

**Mitigation:**
- Start with simplest possible implementations
- Validate determinism at each stage
- Profile before optimizing
- Consider deferring ns-3 to M1.5 if time-consuming

---

## Architecture Decisions to Make

**Q1: Should M1 include full ns-3 or just network abstraction?**
- **Decision:** Start with abstraction + simple model, defer ns-3 if complex
- **Rationale:** Critical analysis warns against over-engineering early

**Q2: How much YAML complexity?**
- **Decision:** Minimal - just node list and params, no complex validation
- **Rationale:** Per instructions, "keep YAML simple"

**Q3: Network model interface design?**
- **Decision:** Define in M1c based on M0 experience
- **Defer:** Finalize after seeing simple model in action

---

## Progress Tracking

| Minor Stage | Status | Commit | Report |
|-------------|--------|--------|--------|
| M1a: Test reorg | ✅ COMPLETE | M1a | M1a-report.md |
| M1b: YAML parser | ✅ COMPLETE | M1b | M1b-report.md |
| M1c: Network abstraction | PENDING | - | - |
| M1d: Latency model | PENDING | - | - |
| M1e: Metrics | PENDING | - | - |
| M1f: ns-3 | DEFERRED? | - | - |

---

**Last Updated:** 2025-11-14 (After M1a)
**Next Review:** After M1b completion

## Stage Completion Notes

### M1a ✅
- Test structure reorganized successfully
- All M0 tests pass from new location
- pytest configuration added
- Integration test framework created
- Ready for M1b (YAML parsing)


### M1b ✅
- YAML scenario parser implemented
- Unit tests: 8/8 passed
- Integration tests: 2/2 passed
- M0 backward compatibility verified
- Determinism maintained with YAML configs
- Ready for M1c (Network Abstraction)

