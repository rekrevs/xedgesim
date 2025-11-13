# Meta-Plan for xEdgeSim Research & Development

This document describes *how* the xEdgeSim project will be executed: phases, iteration loops, roles for ChatGPT and Claude Code, and concrete milestones. It is a living document and should be updated as the project evolves.

---

## 1. Purpose and scope

The meta-plan serves to:

- Define the **research programme** around xEdgeSim.
- Make the work **iterative and automatable**, using ChatGPT and Claude Code wherever reasonable.
- Keep a clear mapping from **code / experiments** → **paper sections** → **claims**.

### 1.1 Target artefacts

By the end of the project we aim to have:

1. **System artefact**
   - xEdgeSim: a cross-level IoT–edge–cloud simulator that:
     - runs deployable **MCU firmware** in emulation,
     - runs deployable **container images** at edge,
     - uses a **network simulator** (e.g. ns-3) for realistic links,
     - includes **cloud mocks** and **ML placement/offloading** logic.

2. **Research artefacts**
   - A full conference/journal paper (in `paper/`).
   - An open-source repo with:
     - at least one **end-to-end scenario** (vibration monitoring),
     - 2–3 **predefined experiment sets** with scripts to reproduce key figures.

---

## 2. Phases (P0–P5) and their deliverables

The work is divided into phases. P0 is already done; it remains documented here for completeness.

### P0 — Foundations & Tooling (STATUS: DONE)

**Goals**

- Create repo structure and initial docs.
- Establish a workflow for ChatGPT + Claude Code.

**Deliverables**

- Repo `xEdgeSim/` with:
  - Directory structure (`docs/`, `sim/`, `scenarios/`, `results/`, `paper/`, `scripts/`).
  - `README.md`, `docs/vision.md`.
  - `docs/related-work-notes.md` (skeleton).
  - `docs/meta-plan.md` (this document).
  - `scripts/setup_env.sh`, `Makefile`.
  - `sim/harness/run_scenario.py` stub.
  - `scenarios/vib-monitoring/config.yaml` placeholder.
  - `paper/main.tex`, `paper/refs.bib`.

### P1 — Related Work & Gap Analysis

**Goals**

- Survey existing tools and frameworks in a *structured* way.
- Make explicit the gap that xEdgeSim fills.

**Activities**

- Populate `docs/related-work-notes.md` with a table covering:
  - WSN / IoT device simulators (e.g. COOJA/Contiki).
  - Embedded / SoC emulators (e.g. Renode, QEMU-based setups).
  - Edge / fog / IoT simulators (e.g. iFogSim, EdgeCloudSim, PureEdgeSim, LEAF, EdgeAISim).
  - Network simulators & co-sim middleware (e.g. ns-3, OMNeT++, SimBricks, ns-3 cosim libs).
  - IoT + container emu frameworks (e.g. IoTNetEMU).

- For each system, record:
  - Focus (device / edge / cloud),
  - Device realism (MCU, RTOS, binary-level?),
  - Network modelling capabilities,
  - Edge/cloud realism,
  - ML support,
  - Co-simulation capabilities,
  - CI/CD integration,
  - Gaps vs xEdgeSim.

**Outputs**

- Completed comparison table in `docs/related-work-notes.md`.
- A short "Gap" subsection at the end of that file with 3–5 clear bullets on:
  - what xEdgeSim does that others do not,
  - why it is still needed in 2025.

### P2 — Architecture Design

**Goals**

- Decide on the concrete architecture and main technology choices.
- Produce a design that is directly implementable.

**Activities**

- Create and maintain `docs/architecture.md` (separate file; not part of this meta-plan) with:
  - Component diagram (device emulation, network simulation, edge containers, cloud mocks, harness).
  - **Time synchronisation model**:
    - how simulated time advances,
    - how Renode/QEMU, ns-3, and edge/cloud processes stay coherent.
  - **Data plane**:
    - how packets flow: MCU firmware → emulator → network simulator → edge containers → cloud.
  - **Control plane & instrumentation**:
    - scenario configuration (YAML),
    - metrics and logging (what, where, format).

- Decide initial technology stack:
  - Device: Renode (or QEMU) + one MCU platform (e.g. Cortex-M).
  - Network: ns-3 with TAP/cosim integration.
  - Edge: Docker Compose (broker + aggregator + offloading controller).
  - Cloud: Python-based services (possibly containerised).
  - ML: ONNXRuntime or simple Python "fake" model for early experiments.

**Outputs**

- `docs/architecture.md` with enough detail that an implementer can start M0 and M1 without further design work.
- An updated `docs/vision.md` if needed to reflect design decisions.

### P3 — Implementation (Milestones M0–M4)

P3 is subdivided into milestones. Each milestone must produce an **end-to-end runnable slice**, even if small.

#### M0 — Device-only Simulation

**Objective**

- Run a small Zephyr/FreeRTOS app in an emulator and observe network traffic over a simple link.

**Key tasks**

- Define one MCU board target (e.g. a Zephyr-supported Cortex-M board).
- Build a firmware application that:
  - generates a synthetic vibration signal (time-series),
  - computes simple features (e.g. RMS),
  - sends periodic UDP or CoAP packets to a fixed IP/port.
- Create a Renode (or equivalent) script that:
  - instantiates one or a few nodes,
  - logs packets (or prints them to console).

**Deliverables**

- Firmware source under `sim/device/`.
- Emulator config (`.resc` / similar) under `sim/device/`.
- `Makefile` target `make m0` (or similar) that runs this demo.

#### M1 — Add Network Simulator (ns-3)

**Objective**

- Replace the emulator's trivial link with an ns-3 model.

**Possible strategy**

- Use TAP/Tun + ns-3 TapBridge:
  - emulator's network interface → host TAP,
  - TAP → ns-3 node via TapBridge,
  - ns-3 node ↔ gateway / cloud nodes.

**Key tasks**

- Create ns-3 scenario code under `sim/net/` that:
  - builds a basic topology (device side nodes + gateway + cloud node),
  - models latency, jitter, and loss.
- Configure emulator network to send/receive via TAP.
- Provide scripts to start ns-3 and the emulator in a controlled way.

**Deliverables**

- `sim/net/` ns-3 code + build instructions.
- Orchestration script (may be integrated into `sim/harness/run_scenario.py` or separate at first).
- `Makefile` target `make m1`.

#### M2 — Edge Containers

**Objective**

- Introduce a realistic edge gateway running containers.

**Key tasks**

- Define Docker Compose in `sim/edge/docker-compose.yml` with:
  - MQTT broker (e.g. Mosquitto),
  - Aggregator service (Python) that:
    - subscribes to sensor topics,
    - logs data, maybe compresses or aggregates.
- Connect ns-3 "gateway" node to the container network:
  - via another TAP / veth pair, or a bridged network.
- Define how device packets are translated into MQTT messages:
  - either device speaks MQTT(SN) directly,
  - or a UDP/CoAP-to-MQTT bridge at the edge.

**Deliverables**

- Edge services source code under `sim/edge/`.
- Updated scenario harness capable of spinning up containers.
- `Makefile` target `make m2`.

#### M3 — Cloud Mock and ML Placement

**Objective**

- Add a mock cloud service and an ML inference component with configurable placement (device vs edge vs cloud).

**Key tasks**

- Implement a simple cloud service in `sim/cloud/`:
  - receives aggregated data via MQTT/HTTP,
  - runs a model (start with a "fake" model that just sleeps for X ms and returns labels).
- Implement an **offloading controller**:
  - reads policy from config (YAML/JSON),
  - decides where inference happens:
    - device (if enabled),
    - edge,
    - cloud.
- Extend firmware and edge services to support:
  - inference at device (if enabled),
  - inference at edge only,
  - inference at cloud only,
  - or hybrid: device/edge with cloud fallback.

**Deliverables**

- ML placement policy representation.
- End-to-end scenarios that compare at least:
  - "cloud-only" vs "edge-only" vs "device+fallback".
- `Makefile` target `make m3-scenario1` or similar.

#### M4 — Security & Fault Injection

**Objective**

- Add mechanisms to inject network and node faults, including "compromised edge" behaviour.

**Key tasks**

- In ns-3:
  - scripts for link degradation, partitions, increased loss/latency.
- In edge services:
  - a "fault mode" where the gateway:
    - drops a fraction of alerts,
    - tampers with alert contents,
    - or delays them.
- In the harness:
  - scenario configuration that includes time-based "fault events".

**Deliverables**

- Extended scenario configs that describe faults.
- Example runs showing measurable impact of faults.
- Optional: simple consistency/robustness checks (e.g. device-signed messages, cross-gateway voting).

### P4 — Experiment Harness & Evaluation

**Goals**

- Provide a **single entry point** to run scenarios and batches of experiments.
- Make it easy to reproduce performance plots and tables.

**Key elements**

- `sim/harness/run_scenario.py`:
  - parses YAML config,
  - starts emulator(s), ns-3, edge, cloud,
  - runs for a specified simulated or wall-clock duration,
  - collects logs in `results/raw_logs/<scenario>/<timestamp>/`.

- `sim/harness/run_batch.py`:
  - takes a set of configs or parameter ranges,
  - runs multiple scenarios,
  - produces `results/processed/summary.csv` with metrics such as:
    - mean and percentile latencies,
    - packet loss,
    - approximate device energy use,
    - edge/cloud CPU/memory load (if measured),
    - accuracy / detection quality for ML experiments.

**Outputs**

- At least one well-documented scenario in `scenarios/vib-monitoring/` with:
  - YAML config(s),
  - README,
  - example batch results.

### P5 — Writing & Packaging

**Goals**

- Turn the implementation and experiments into a coherent paper and reusable artefact.

**Activities**

- Maintain LaTeX paper in `paper/main.tex`:
  - update **Background & Related Work** after P1,
  - update **Design** after P2,
  - update **Implementation** after M2/M3,
  - update **Evaluation** after P4.
- Maintain `paper/refs.bib` with all cited works.
- Create figures (via Python/matplotlib or similar) and store them under `paper/figures/`, with generation scripts checked into the repo.

**Outputs**

- A near-submission-ready paper.
- A cleaned-up repo:
  - tidy directory structure,
  - clear instructions in `README.md`,
  - working examples.

---

## 3. Iteration loop template

For any given research question or feature, the project should follow this loop:

1. **Question → Design**
   - The question is written down in a short form (1–2 lines).
   - ChatGPT helps refine it into:
     - experiment objectives,
     - hypotheses,
     - metrics.

2. **Spec → Code Plan**
   - ChatGPT produces:
     - code skeletons,
     - TODO lists,
     - file structures.
   - Claude Code:
     - implements the TODOs,
     - runs unit tests or smoke tests,
     - iterates until the slice works.

3. **Run → Collect → Summarise**
   - Claude Code runs scenarios or batches, producing logs/CSVs.
   - Summaries/highlights of results are fed back to ChatGPT.
   - ChatGPT:
     - analyses trends,
     - suggests parameter tweaks or additional experiments.

4. **Decide → Document**
   - Human decides what to keep, what to cut, and what's next.
   - ChatGPT:
     - updates architecture docs,
     - drafts or refines paper sections,
     - updates this meta-plan if needed.

This pattern is repeated for each milestone (M0–M4) and for each major experiment set.

---

## 4. Division of labour: human, ChatGPT, Claude Code

### Human responsibilities

- Set research direction, choose venues, and define priorities.
- Make final decisions on architecture and scope.
- Judge scientific validity of results and claims.
- Perform final editing of the paper.

### ChatGPT responsibilities

- Turn high-level ideas into:
  - concrete designs,
  - experiment specifications,
  - code skeletons,
  - documentation and LaTeX text.
- Summarise related work and maintain structured comparison notes.
- Analyse experiment summaries and propose next steps.
- Suggest reasonable defaults and simplifications when uncertainty is high.

### Claude Code responsibilities

- Manipulate the actual repo:
  - create/modify files,
  - refactor code,
  - maintain scripts.
- Run commands:
  - compile firmware,
  - run emulators and simulators,
  - run Docker containers.
- Execute batch experiments and export results to `results/`.

---

## 5. Experimentation & evaluation plan (vibration monitoring)

For the initial vibration monitoring scenario, the evaluation plan includes:

- **ML placement variants**
  - Cloud-only inference.
  - Edge-only inference.
  - Device-only or device+fallback (edge/cloud) inference.

- **Network conditions**
  - Low vs high latency on device–edge and edge–cloud.
  - Different loss rates and jitter patterns.
  - Network partitions and recovery.

- **Scale**
  - Number of devices (e.g. 10, 100, 500).
  - Sampling and reporting frequencies.

- **Faults**
  - Compromised edge gateway (dropping/tampering alerts).
  - Unreliable links and nodes.

For each experiment set, define:

- A set of scenario YAML files (or parameter grids).
- The metrics to collect.
- The expected qualitative behaviour (e.g. "device+edge inference should reduce latency and network load under high WAN latency").

---

## 6. Writing plan for the paper

The paper structure in `paper/main.tex` will roughly be:

1. **Introduction**
   - Motivation, problem statement, contributions.

2. **Background and Related Work**
   - Based on `docs/related-work-notes.md`.
   - Clearly position xEdgeSim vs simulators, emulators, and co-sim frameworks.

3. **Design of xEdgeSim**
   - High-level architecture, components, abstractions.

4. **Implementation**
   - Concrete choices: Renode/ns-3/Docker/etc.
   - Milestones and design trade-offs.

5. **Evaluation**
   - Vibration monitoring scenario.
   - ML placement experiments.
   - Fault injection experiments.
   - Discussion of results and threats to validity.

6. **Discussion and Limitations**
   - What xEdgeSim can and cannot model.
   - Planned extensions.

7. **Conclusion**
   - Summary of contributions and future work.

This meta-plan should be used alongside `docs/vision.md` and `docs/architecture.md` to coordinate development and writing.

---

## 7. First two "sprints"

To keep things concrete, the next two short "sprints" are:

### Sprint A — Fill Related Work Table (P1, partial)

- Use ChatGPT to summarise:
  - COOJA/Contiki, Renode, iFogSim, EdgeCloudSim, EdgeAISim, IoTNetEMU, SimBricks, ns-3 cosim.
- Fill in the table in `docs/related-work-notes.md`.
- Draft a 3–4 bullet "Gap" subsection at the end.

### Sprint B — Implement M0 (start of P3)

- Use Claude Code to:
  - add Zephyr/FreeRTOS firmware skeleton under `sim/device/`,
  - add emulator config,
  - add a `make m0` target that runs a simple end-to-end device-only simulation.

- Use ChatGPT to:
  - refine firmware behaviour (signal model, packet fields),
  - refine emulator configuration.

After these sprints, revisit this meta-plan to update status and next steps.
