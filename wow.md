### xEdgeSim POC – Iterative Implementation Instructions

You are working on the xEdgeSim repository. The conceptual architecture and roadmap (M0–M4) are already defined in the docs under `docs/` (e.g. `architecture.md`, `implementation-guide.md`, `vision.md`, determinism and node-library notes).

A minimal M0 Python proof-of-concept already exists (coordinator + sensor/gateway nodes + determinism test).  Your task is to extend this into a richer POC system **iteratively**, with very small, well-scoped steps and very strict testing and git hygiene.

Below, “major stages” are M1, M2, … as in the architecture docs; “minor stages” are M1a, M1b, M2a, etc.

---

## 1. Overall constraints

1. Treat the existing design documents as **architectural constraints and guidance**, not as a backlog to fully implement at once. In particular, follow:

   * Milestone scopes M0–M4 (what belongs to M1 vs M2, etc.).
   * Implementation philosophy: minimal M0, then gradually add complexity (“Make it work → right → fast”; avoid over-engineering).
   * Determinism and node design rules for simulation nodes.

2. We are building a **research system**, not a production system. For each stage you should prioritise:

   * Clear demonstration that the concept works for realistic, small scenarios.
   * Determinism and reproducibility where required (device + network tiers).
   * Simplicity and explainability of the code over generality and feature completeness.

3. **No code bloat, no evasive workarounds.**

   * Don’t introduce generic abstractions, configuration options, or plugin frameworks unless they are directly needed by the current stage and grounded in the architecture docs.
   * If something is hard, do not “paper over it” – either solve it properly in-scope or explicitly document it as a deferred issue in the stage report.

---

## 2. Stage and step structure

### 2.1 Major vs minor stages

* Major stages: `M1`, `M2`, `M3`, `M4` as defined in `architecture.md` / `implementation-guide.md` (e.g. M1 = add network realism/ns-3; M2 = edge realism/Docker; M3 = ML placement; M4 = polish & scalability).
* Minor stages: `M1a`, `M1b`, … are the **atomic development steps** (each should correspond to one small, clean commit or very small set of commits).

### 2.2 Planning responsibility

You must plan **only as far as is sensible right now**, and refine the plan as you go.

For each **major stage `Mn`**:

1. Before touching code:

   * Read/refresh the relevant parts of the docs for that stage (e.g. for M1, the ns-3 and scenario sections in `architecture.md` + `implementation-guide.md`; for M2, Docker and edge integration sections, etc.).
   * Create or update `docs/dev-log/Mn-plan.md` with:

     * A short description of the goal of this major stage, in your own words.
     * A **first list** of 2–5 candidate minor stages (`Mna`, `Mnb`, …) with one-line objectives each. Keep them small.

2. After each minor stage is completed:

   * Revisit `docs/dev-log/Mn-plan.md`.
   * Update the remaining minor stages (split, merge, re-order, or add new ones) based on what you learned.
   * Do **not** attempt to fully plan all minor stages from the beginning; planning is explicitly incremental.

---

## 3. Process for each minor stage (M1a, M1b, …)

For every minor stage `Mxy` (example: `M1a`), follow this exact sequence:

1. **Define the objective and scope**

   * At the top of `docs/dev-log/Mxy-report.md`, write:

     * A short objective (1–3 sentences) stating what this minor stage adds or changes.
     * A short list of **acceptance criteria** that can be tested (behaviour, metrics, invariants).
   * The objective must:

     * Be clearly achievable in one small iteration.
     * Contribute directly to the corresponding major stage goal.
     * Stay within that major stage’s scope as defined in the architecture docs (e.g. M1 should not start Docker/ML work).

2. **Design tests first (for this minor stage)**

   For this minor stage, you must design and implement tests **before or in parallel with** the production code:

   * **Test structure**

     * The test tree must be organised by stages as follows:

       * `tests/stages/M0/` – M0-specific tests (existing ones from the minimal PoC).
       * `tests/stages/M1a/`, `tests/stages/M1b/`, … – tests specific to each minor stage.
       * `tests/integration/` – cumulative integration tests (up to the current major stage).
     * If existing tests are currently in a different layout (e.g. a single `test_m0_poc.py` script), refactor them as part of an early minor stage so that they fit this structure, while preserving their behaviour.

   * **Kinds of tests you must include for each minor stage:**

     1. **Unit tests**

        * For key functions/classes added or changed in this stage.
        * Keep them small and focused; prefer Python’s `pytest` or `unittest` style (follow what is already used in the repo).
     2. **Runtime checks/assertions**

        * Add explicit assertions in core logic (e.g. invariants about time, event ordering, determinism assumptions, non-empty collections where required).
        * These should fail loudly rather than silently masking unexpected situations.
     3. **Integration / system tests**

        * At least one test that drives the full simulation loop (or a meaningful subset) to exercise the new behaviour end-to-end.
        * Use small, fast scenarios derived from the M0 POC or from the roadmap (e.g. minimal ns-3 or edge config when you reach those stages).

   * In `docs/dev-log/Mxy-report.md`, write down:

     * Which new tests you added.
     * What each test is intended to prove.

3. **Implement the production code for this minor stage**

   * Modify only what is needed for the stage objective.
   * Follow the architectural principles from the docs:

     * Coordinator remains lightweight; avoid pushing unrelated responsibilities into it.
     * Respect deterministic node design (virtual time, seeded RNG, event-driven behaviour) where applicable.
     * Defer complexity in line with the milestone plan (e.g. don’t bring in Docker before M2, ML placement before M3).
   * Avoid:

     * Creating generic extension points “just in case”.
     * Introducing configuration options or flags that are unused in this stage.
     * Duplicating logic; if needed, refactor to a common helper as part of the same stage.

4. **Run tests for this minor stage**

   After coding, run:

   1. **Stage-specific tests**

      * Run only the tests for this minor stage and its major stage, for example:

        * `tests/stages/M1a/` (and optionally `tests/stages/M1/` if you introduce a major-stage-level suite).
      * Fix any failing tests or adjust the code until they pass.

   2. **Cumulative integration tests up to this stage**

      * Run all tests up to and including the current major stage, e.g.:

        * `tests/stages/M0/`, all minor stages for M1, plus `tests/integration/`.

      * If changes legitimately require adjusting earlier tests (e.g. to reflect a refined invariant), update those tests but **preserve** their original intent and document the change in the stage report.

   * In the stage report, record:

     * Exact test commands used (e.g. pytest invocations).
     * The fact that they all passed at the end of the stage.

5. **Source-level review for elegance and minimality**

   After tests pass, you must perform a brief but explicit source-level review before committing:

   * Create or update a simple **checklist** in `docs/dev-log/Mxy-review-checklist.md` (or keep a common checklist if it’s shared) covering at least:

     * No unused functions, parameters, config keys, or dead code.
     * No obvious duplication that could have been factored without adding complexity.
     * Functions, methods, and modules are short, cohesive, and named clearly.
     * The stage keeps aligned with the implementation philosophy (“do one thing well”, avoid premature optimisation and premature abstraction).
     * Determinism assumptions are either upheld (and tested) or clearly documented as relaxed for specific tiers.
   * Check the code against this list and note any trade-offs or deliberate deviations in `docs/dev-log/Mxy-report.md`.

6. **Write the stage report**

   Update `docs/dev-log/Mxy-report.md` with:

   * The final objective and whether all acceptance criteria were met.
   * Summary of design decisions and alternatives considered (especially where you had to choose between simplicity and generality).
   * Summary of tests, including:

     * New/changed tests.
     * Determinism/regression aspects tested if relevant.
   * Any **known limitations or technical debt** deliberately left for a later minor or major stage (clearly labeled as such).
   * How this minor stage moves the system towards the major stage goal defined in `Mn-plan.md`.

7. **Git hygiene: commit and push**

   * Ensure the working tree is clean except for changes belonging to this minor stage.

   * Commit with a concise message following this pattern:

     * `Mn[a]: short description`
       Examples: `M1a: introduce basic ns3 adapter interface`, `M2b: bridge ns3 gateway to Docker network`.

   * Push to the appropriate branch when the minor stage is complete and all tests pass.

8. **Update the major stage plan**

   * Return to `docs/dev-log/Mn-plan.md`.
   * Mark this minor stage as completed (with a one-line summary and a link to the stage report).
   * Adjust the remaining minor stages list based on what you learned (split, merge, add or drop steps as needed).

---

## 4. Major stage completion (M1, M2, …)

A **major stage `Mn`** is considered complete only after:

1. **All planned minor stages for `Mn` are done**, or the plan has been consciously simplified/trimmed with reasons documented in `Mn-plan.md`.

2. You have run:

   * The **full test suite**, i.e.:

     * All `tests/stages/M0/` + all minor stages for every major stage up to and including `Mn`.
     * All `tests/integration/`.
   * Determinism/reproducibility checks, where applicable, still pass for tiers expected to be deterministic (e.g. M0 deterministic POC, M1 deterministic device+network).

3. You have written or updated `docs/dev-log/Mn-summary.md` with:

   * What the system can do at the end of this major stage.
   * Which parts of the architecture/implementation-guide have been realised vs explicitly deferred.
   * Any important open design questions to be addressed in the next stages.

4. Optionally, if the repo workflow supports it:

   * Tag the commit (e.g. `git tag Mn-complete`) or note the commit hash in `Mn-summary.md`.

---

## 5. Determinism, node behaviour, and libraries

Throughout all stages:

1. Follow the determinism model from the determinism docs:

   * Simulation components that are meant to be deterministic (device tier, network tier, deterministic models) must:

     * Use virtual time only, never wall-clock time, inside the simulation loop.
     * Use seeded RNGs derived from scenario seed + node ID.
     * Be event-driven and single-threaded from the coordinator’s perspective.
   * Tiers that are allowed to be statistical (e.g. Docker edge containers) must have:

     * Tests that characterise distributions (latency, throughput) rather than single exact values.
     * Clear documentation in the stage reports that determinism is not expected there.

2. When you introduce or extend node libraries (Python, Go) per the node-library design doc, do so as part of explicit minor stages and:

   * Use them to **reduce boilerplate** and make deterministic node construction easier (event queues, virtual time, seeded RNG).
   * Add tests that show the old and new node APIs behave identically at the observable level.

---

These instructions are binding for all remaining POC work on xEdgeSim. For each change, keep stages small, tests comprehensive for that stage, and code minimal and in line with the architecture and implementation guides.
