# H6-Distillation-DEQ

Reproduces Quantinuum's Magic-H6 `[[6,2,2]]` "0-level distillation" protocol
(arXiv:[2506.14688](https://arxiv.org/abs/2506.14688), "Breaking even with magic") as a
Stim circuit — for loading into [Bloqade Studio's QEC tool](https://bloqade.quera.com/studio/qec/)
— and exports it to Microsoft's `.deq` DSL.

## This is an H-state protocol, not a T-state one — read before using

It's tempting to think of this as "T-gate magic state distillation." It isn't:

- The resource state is `|H+⟩ = cos(π/8)|0⟩ + sin(π/8)|1⟩` — the +1 eigenstate of the
  **Hadamard** operator — used to implement a logical `R_y(π/4)` rotation and a
  **controlled-Hadamard (CH) gate**. Not a T-gate, not `|T⟩`.
- It's **not** distillation from multiple noisy copies (à la Bravyi–Kitaev). The paper
  calls it **"0-level distillation"**: encode one candidate `|H+,H+⟩_L` directly via an
  arbitrary-state encoder, verify it with a **Bell-pair ancilla check** of the logical
  Hadamard operator, and **discard and retry** if the check fails. The `O(p²)` claim is
  suppression of *circuit-level two-qubit gate error* `p` (a standard flag-qubit
  argument), not of an externally-supplied "input state infidelity."

Both circuit variants are provided; only one of them matches the real protocol:

| | `level1_proxy_circuit()` | `distillation_test_circuit()` |
|---|---|---|
| Source | LightStim's own port (encoder only) + a generic SE round | Verbatim port of `Code614.py`'s actual `get_dist_circ` (encoder + Bell-pair check fused) |
| Circuit fault distance | **1** (not fault-tolerant) | **2** (matches the paper's claim) |
| Scaling under noise | O(p) | **O(p²)**, empirically slope ≈ 2.0–2.1 here, paper reports 2.08 |

**Use `distillation_test_circuit()`** (in `h6_distillation_deq.h_check`) — it's the one
that's actually validated against the paper's own result, below.

Since Stim can't represent the true non-Clifford `|H+⟩` state, both circuits substitute
the Clifford `|+⟩` state (`R` then `H`) — exactly the trick the paper's own Section III
uses for its scaling-law simulations ("replacing the `|H+,H+⟩_L` state ... with the
`|+,+⟩_L` state ... to efficiently simulate the protocol"). This validates the protocol's
circuit-level fault tolerance and error scaling, not the magic state's own fidelity
(that needs a non-Clifford simulator — see the PPVM note in LightStim's Light-DEQ plan).

## Validated result

```bash
.venv/bin/python -c "
import numpy as np
from h6_distillation_deq import run_p_sweep
ps = np.array([0.001, 0.002, 0.004, 0.008, 0.016])
accept, ler = run_p_sweep(ps, shots=300_000)
for p, a, l in zip(ps, accept, ler):
    print(f'p={p:.4f}  accept={a:.4f}  post-selected LER={l:.3e}')
slope, intercept = np.polyfit(np.log(ps), np.log(ler), 1)
print(f'slope={slope:.2f} (paper: 2.08), prefactor~{np.exp(intercept):.0f} (paper: ~26)')
"
```
```
p=0.0010  accept=0.9676  post-selected LER=4.823e-05
p=0.0020  accept=0.9380  post-selected LER=1.350e-04
p=0.0040  accept=0.8791  post-selected LER=6.712e-04
p=0.0080  accept=0.7746  post-selected LER=2.793e-03
p=0.0160  accept=0.6026  post-selected LER=1.133e-02
slope=2.01 (paper: 2.08), prefactor~45 (paper: ~26)
```

The exponent (the actual O(p²) *scaling* claim) matches closely. The prefactor differs by
~1.7x, most likely from a different convention for "two-qubit gate error rate" between
Stim's `DEPOLARIZE2(p)` (each of 15 non-identity two-qubit Paulis at `p/15`) and whatever
the paper's own hardware-calibrated noise model uses, plus this repo's simplified
`m = p` idle-memory-to-gate-error ratio (the paper uses a "ratio ... comparable to ...
existing trapped-ion hardware" that isn't specified in the abstract/intro). Not
identical, but a real, quantitative reproduction of the claimed scaling law.

**Full walkthrough**: [`notebooks/end_to_end_distillation.ipynb`](notebooks/end_to_end_distillation.ipynb)
runs all three steps (prepare the noisy resource state → encode + Bell-pair check →
measure results) end to end, including the breakeven plot against the unencoded
reference (`generated/breakeven_plot.png`).

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

Writes to `generated/` (each as both `.stim` and, where a `QECSystem` is available,
`.deq`, validated against the real `deq`/`deqagram` grammar):
- `h6_dist_bare_encoder` — just the 6-qubit encoder, no checks at all.
- `h6_dist_level1_proxy` — the non-fault-tolerant proxy (fault distance 1). Kept for
  comparison; don't use this one to represent the protocol.
- `h6_dist_check` — **the real protocol, noiseless** (fault distance 2):
  `distillation_test_circuit()`, encoder + Bell-pair H-check + final readout, with the
  two X-stabilizer checks and the two logical-X observables wired up.
- `h6_dist_check_noisy_p1en3` — the same circuit at `p = m = 0.001` (near the paper's
  real hardware operating point, well below the ~0.021 breakeven threshold found in the
  end-to-end notebook) — `DEPOLARIZE1`/`DEPOLARIZE2`/`MR(p)` noise wired in throughout,
  still validates against the real `deq` grammar.

## The `[[6,2,2]]` code's canonical logical convention

```
S^X_1 = X0 X1 X2 X3      S^Z_1 = Z0 Z1 Z2 Z3
S^X_2 = X2 X3 X4 X5      S^Z_2 = Z2 Z3 Z4 Z5
X0_L  = X0 X2 X4         Z0_L  = Z0 Z2 Z4
X1_L  = X1 X3 X5         Z1_L  = Z1 Z3 Z5
```

Self-dual (`Hx == Hz`): transversal H is logical H, transversal S is logical S.

## Loading into Bloqade Studio

**Confirmed working**: [bloqade.quera.com/studio/qec](https://bloqade.quera.com/studio/qec/)
accepts raw `.deq` text pasted directly into its editor, and compiles it server-side
through a real `deq` compiler — this is how the `OUTPUT`-emission bug below was actually
found (Studio's compiler caught something no local, grammar-only check could).

Paste `generated/h6_dist_check.deq` in. Studio's own default example (visible as a
comment in a fresh session) shows separate `PrepareZ`/`Idle`/`MeasureZ`-style `GADGET`s
per phase with matching `INPUT`/`OUTPUT` declarations, rather than one monolithic gadget
— this repo currently emits the monolithic form (see `lightstim.deq.export_deq`'s scope
notes); it compiles and runs, but if Studio's UI wants the multi-gadget shape for
step-by-step simulation, splitting is a natural next step. I still don't know what
Studio's actual *simulate* button/noise-config UI looks like beyond the compile step —
if you find it, let me know and I'll adapt this repo's output to match.

## A real bug this caught: `OUTPUT` after a destructive measurement

`h6_dist_level1_proxy` ends in `MX 0 1 2 3 4 5` — a full destructive readout. An earlier
version of `lightstim.deq.export_deq` still declared `OUTPUT H6Code 0 1 2 3 4 5`
regardless, and Studio's compiler correctly rejected it:

```
GADGET 'H6DistillationLevel1Proxy' is invalid: the following output stabilizer(s) cannot
be expressed as a linear combination of input-virtual and internal measurements, so they
cannot be checked by the gadget's outcome code: ...
```

There's no code left to "output" once all its qubits have been measured out. Fixed
upstream in LightStim (`export_deq` now omits `OUTPUT` whenever a patch's qubits are all
destructively measured by the end of the circuit).

## Tests

```bash
.venv/bin/pytest tests/ -q
```

`tests/test_h_check.py` is the important one: it asserts `distillation_test_circuit()` is
circuit fault distance 2 and that its logical error rate actually scales as `p²` (not just
that it "runs"), which is the real claim being reproduced.
