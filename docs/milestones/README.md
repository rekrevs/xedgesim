# xEdgeSim Milestone Implementation Plans

This directory contains detailed implementation plans for xEdgeSim development milestones.

## Structure

Each milestone has a comprehensive implementation plan that includes:
- Technical objectives and scope
- Architecture and design decisions
- Phase-by-phase implementation steps
- Testing strategies
- Dependencies and prerequisites
- Success criteria
- Risk mitigation
- Timeline and effort estimates

## Current Milestones

### Completed (M0-M3)
- **M0:** Minimal proof-of-concept (see `docs/first-vibe-minimal-poc.md`)
- **M1:** YAML parsing and network abstraction
- **M2:** Docker integration and MQTT broker
- **M3:** ML placement framework (edge and cloud)

### Planned (M3f-M3g)

**[M3f: Renode Integration](M3f-renode-integration-plan.md)**
- **Objective:** Add instruction-level ARM/RISC-V device emulation
- **Duration:** 3-4 weeks
- **Effort:** ~1,000 LOC
- **Key Deliverables:**
  - Renode adapter with monitor protocol
  - Zephyr firmware for sensor nodes
  - Device ML inference with TFLite
  - Validated deployability of firmware

**[M3g: ns-3 Integration](M3g-ns3-integration-plan.md)**
- **Objective:** Add packet-level network simulation
- **Duration:** 3-4 weeks
- **Effort:** ~1,200 LOC
- **Key Deliverables:**
  - Custom ns-3 module with coordinator interface
  - Python adapter for ns-3 communication
  - TAP/TUN bridges for network integration
  - WiFi, Zigbee protocol scenarios

**[M3 Extension Roadmap](M3-extension-roadmap.md)**
- **Overview:** Combined strategy for completing the architectural vision
- **Timeline:** 6-8 weeks total
- **Impact:** Completes 95%+ of original design
- **Outcome:** Production-ready federated co-simulation platform

### Future (M4+)
- **M4:** Production polish (CI/CD, performance, scalability)
- **M5+:** Additional enhancements (as needed)

## Reading Order

For new contributors or reviewers:
1. Start with [M3 Extension Roadmap](M3-extension-roadmap.md) for the big picture
2. Read [M3f: Renode Integration](M3f-renode-integration-plan.md) for device emulation details
3. Read [M3g: ns-3 Integration](M3g-ns3-integration-plan.md) for network simulation details

## Related Documentation

- **Architecture:** `../architecture.md` - Overall system architecture
- **Vision:** `../vision.md` - Research goals and motivation
- **Meta-plan:** `../meta-plan.md` - Project phases and research programme
- **Implementation Guide:** `../implementation-guide.md` - Feature-specific details

## Contributing

When implementing a milestone:
1. Create a feature branch: `feature/m3f-renode-integration` or `feature/m3g-ns3-integration`
2. Follow the phase-by-phase plan in the respective document
3. Update the plan with any deviations or learnings
4. Create tests according to the testing strategy
5. Update documentation as specified in the plan
6. Mark phases complete in the plan as you progress

## Status Tracking

Milestone completion is tracked through:
- GitHub issues/milestones
- Commit messages (e.g., "M3f: Phase 1 complete - Basic Renode control")
- Test coverage reports
- Documentation updates

---

**Last Updated:** 2025-11-15
**Status:** M3f and M3g plans ready for implementation
