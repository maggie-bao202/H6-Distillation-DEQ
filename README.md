# H6-Distillation-DEQ

Generates Stim circuits for Quantinuum's Magic-H6 `[[6,2,2]]` level-1 distillation
protocol — for loading into [Bloqade Studio's QEC tool](https://bloqade.quera.com/studio/qec/)
— and exports the same circuit to Microsoft's `.deq` DSL.

All circuit-building logic is reused from [LightStim](https://github.com/QuEraComputing/LightStim)'s
existing `lightstim.qec_code.H_six` module (a direct, tested port of
[Quantinuum/Magic-H6](https://github.com/Quantinuum/Magic-H6)'s `Code614.py`), and the
`.deq` export reuses `lightstim.deq.export_deq` (currently on the `Light-DEQ` branch of
[maggie-bao202/LightStim](https://github.com/maggie-bao202/LightStim)).

## ⚠️ This is a proxy circuit, not a verified distillation result

`level1_proxy_circuit()` runs and post-selects cleanly, but per LightStim's own
`playground/magic_h6/H_six_roadmap_status.ipynb` (roadmap "Step 3"):

- `stim.Circuit.shortest_graphlike_error()` shows it is **circuit fault distance 1** — a
  single undetected physical fault can flip the logical output — so under circuit-level
  noise its post-selected output logical error rate scales as **O(p)**, not the **O(p²)**
  the Magic-H6 protocol targets.
- Magic-H6's real distillation claim is **O(p_in²) suppression of the *input* `|H⟩`-state
  infidelity** (`p_in → p_in²`), which needs a dedicated `p_in` injection channel that
  doesn't exist yet anywhere in this stack.

Treat this as a structurally-faithful starting point (correct code, correct encoder,
correct canonical logical convention — see below) to build the real, flag-verified
distillation circuit on top of, not as a finished result. `bare_dist_encoder_circuit()`
is even more minimal: just the `|0⟩⁶ → |++⟩_L` encoder, no syndrome extraction at all.

## Setup

LightStim is not on PyPI. Two ways to get it:

**Local development (sibling checkout, fastest for iterating on both repos together):**
```bash
python3 -m venv .venv
.venv/bin/pip install -e ../LightStim   # assumes LightStim checked out alongside this repo
.venv/bin/pip install -e ".[deq,dev]" --no-deps
.venv/bin/pip install deq deqagram      # for .deq validation; real, normally-installable PyPI packages
```

**From the pinned branch** (what `pyproject.toml` declares by default):
```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[deq,dev]"
```
This pulls `lightstim` from `maggie-bao202/LightStim@Light-DEQ` over SSH — update the pin
in `pyproject.toml` once the `.deq` export work merges to `main`.

## Generate the circuits

```bash
.venv/bin/python scripts/generate_circuits.py
```

Writes to `generated/`:
- `h6_dist_bare_encoder.stim` — the bare 6-qubit encoder, no detectors.
- `h6_dist_level1_proxy.stim` — encoder + one SE round + Bell-pair H-check + X readout.
- `h6_dist_level1_proxy.deq` — the same circuit as a `.deq` `CODE`/`GADGET` pair
  (`CODE c622 [[6,2]]`, matching the code's canonical logical convention below),
  validated against the real `deq`/`deqagram` grammar.

## The `[[6,2,2]]` code's canonical logical convention

(From LightStim's roadmap notebook — `HSixCode`'s registered stabilizers/logicals.)

```
S^X_1 = X0 X1 X2 X3      S^Z_1 = Z0 Z1 Z2 Z3
S^X_2 = X2 X3 X4 X5      S^Z_2 = Z2 Z3 Z4 Z5
X0_L  = X0 X2 X4         Z0_L  = Z0 Z2 Z4
X1_L  = X1 X3 X5         Z1_L  = Z1 Z3 Z5
```

Self-dual (`Hx == Hz`): transversal H is logical H, transversal S is logical S.

## Loading into Bloqade Studio

**Confirmed working**: [bloqade.quera.com/studio/qec](https://bloqade.quera.com/studio/qec/)
accepts raw `.deq` text pasted directly into its editor, and runs it through a real
`deq` compile step server-side — this is how the `OUTPUT`-emission bug documented below
was actually found (Studio's compiler caught something no local, grammar-only check
could).

Paste the contents of `generated/h6_dist_level1_proxy.deq` in. Studio's own default
example (visible as a comment in a fresh session) shows the expected shape — separate
`PrepareZ`/`Idle`/`MeasureZ`-style `GADGET`s per phase, each with matching `INPUT`/
`OUTPUT` declarations, rather than one `.stim`-shaped monolithic gadget. This repo's
generator currently emits the monolithic form (see `lightstim.deq.export_deq`'s scope
notes) — it compiles and runs, but if Studio's UI expects the multi-gadget shape for
step-by-step simulation, splitting into separate gadgets is a natural next step.

## A real bug this caught: `OUTPUT` after a destructive measurement

The circuit ends in `MX 0 1 2 3 4 5` — a full destructive readout. An earlier version of
`lightstim.deq.export_deq` still declared `OUTPUT H6Code 0 1 2 3 4 5` regardless, and
Studio's compiler correctly rejected it:

```
GADGET 'H6DistillationLevel1Proxy' is invalid: the following output stabilizer(s) cannot
be expressed as a linear combination of input-virtual and internal measurements, so they
cannot be checked by the gadget's outcome code: ...
```

There's no code left to "output" once all its qubits have been measured out. Fixed
upstream in LightStim (`export_deq` now omits `OUTPUT` whenever a patch's qubits are all
destructively measured by the end of the circuit) — regenerate with
`scripts/generate_circuits.py` to pick up the fix; `generated/h6_dist_level1_proxy.deq`
here is already current.

## Tests

```bash
.venv/bin/pytest tests/ -q
```
