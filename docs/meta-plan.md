# Meta-Plan for xEdgeSim Research & Development

This document describes the overall planning strategy for the xEdgeSim project and will guide work across P0–P5. It should be updated as the project evolves.

## 1. Purpose of this meta-plan

The goals of this meta-plan are:

- to define *how* planning, iteration, and automation will work,
- to structure the project into phases and feedback loops,
- to specify roles for Claude Code and ChatGPT,
- to provide a reproducible research workflow suitable for CI/CD and academic publication.

This document complements `docs/vision.md` by explaining *how* the vision will be executed.

---

## 2. Project phases overview

The project is divided into the following phases:

### **P0 — Foundations & Tooling**
- Create repo structure, initial documentation, scripts, stubs.
- Establish workflow for ChatGPT + Claude Code collaboration.

### **P1 — Related Work & Gap Analysis**
- Systematic survey of existing simulators, emulators, and co-simulation frameworks.
- Maintain `docs/related-work-notes.md`.
- Extract a clear problem gap motivating xEdgeSim.

### **P2 — Architecture Design**
- Define system components: device emulation, network simulation, edge containers, cloud mocks.
- Define time synchronisation, data flows, interfaces, and scenario configuration format.
- Produce `docs/architecture.md`.

### **P3 — Implementation (Incremental Milestones M0–M4)**
- **M0:** Single-device MCU firmware in emulator with simple link.
- **M1:** Integration with ns-3 via TAP/cosim.
- **M2:** Edge containers with real broker + aggregator.
- **M3:** Cloud mock + ML placement engine.
- **M4:** Security, fault injection, reliability hooks.

### **P4 — Experiment Harness & Evaluation**
- Implement scenario runner and batch runner.
- Define metrics and generate structured logs.
- Run comparative experiments across ML placements, network conditions, and faults.

### **P5 — Writing & Packaging**
- Prepare paper in `paper/`.
- Produce reproducible figures and experiment scripts.
- Clean up repo for open-source release.

---

## 3. Iterative workflow ("build–measure–learn loop")

Each research task follows the loop:

1. **Question → Design**
   You define the research question; ChatGPT creates experiment plans.

2. **Spec → Code Plan**
   ChatGPT writes TODO lists and code skeletons; Claude Code implements them.

3. **Run → Collect → Summarise**
   Claude Code runs experiments and outputs logs; ChatGPT analyses results.

4. **Decide → Document**
   You decide next steps; ChatGPT updates architecture docs and/or paper draft.

This maintains tight iteration with minimal manual overhead.

---

## 4. Division of labour: ChatGPT vs Claude Code

### **ChatGPT**
- Generates designs, code skeletons, experiment specifications.
- Summarises related work and writes LaTeX sections.
- Analyses experiment logs and proposes next steps.
- Helps maintain `docs/` and the paper.

### **Claude Code**
- Performs all file creation/modification in the repo.
- Writes and refactors code.
- Runs commands, compiles firmware, executes Renode/ns-3 containers.
- Executes batch experiments and exports metrics.
- Helps with debugging of the implementation.

---

## 5. Automation plan

The main automation mechanisms are:

- Scenario YAML → automatic orchestration by the harness.
- Batch runner for grid experiments.
- Scripts for parsing logs and generating CSV summaries.
- CI scripts (later) for regression testing.

---

## 6. Risk management

Key risks and strategies:

- **Complex toolchain integration:**
  Start with the smallest vertical slice (M0) and only add one component at a time.

- **Time synchronisation across simulators:**
  Begin with loose coupling (TAP-driven), refine to tighter integration later.

- **Simulation determinism:**
  Prioritise deterministic seeds and version-pinned environments.

- **Overambitious scope:**
  Focus first on one scenario (vibration monitoring) and one MCU platform.

---

## 7. Maintenance and updating

This meta-plan is a living document:
- Update when entering new phases.
- Add lessons learned after each milestone.
- Consolidate major changes into architectural documents and the paper.

End of file.
