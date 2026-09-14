"""The real Magic-H6 "0-level distillation" protocol (encoder + Bell-pair
H-check, from ``code614.get_dist_circ``), wired with detectors/observables
so its fault-tolerance can be tested the way LightStim tests every other
code: ``shortest_graphlike_error`` for circuit fault distance, and Monte
Carlo sampling for the logical error rate vs physical error rate scaling.

Per arXiv:2506.14688 ("Breaking even with magic") §III, the real protocol
distills a pair of non-Clifford |H+>_L magic states, which Stim's stabilizer
formalism can't represent — so, following the paper's OWN methodology for
its scaling-law simulations, this substitutes the Clifford |+,+>_L state
(reset -> H, instead of the true magic state) and studies how the
post-selected output logical error rate scales with the physical two-qubit
gate error rate `p`. This reproduces the paper's Fig. 4 (~26 * p^2.08 for
the unconcatenated, level-1 protocol) rather than measuring magic-state
fidelity directly (which needs an actual non-Clifford/PPVM simulator).

Acceptance criterion: post-select on both Bell-pair ancilla measurements
reading 0 (deterministic in the noiseless case -- a nontrivial outcome
means a detected fault). Failure criterion, among accepted shots: either
logical X observable (X0_L, X1_L) reading anything other than its
noiseless-expected value.
"""

from typing import Tuple

import numpy as np
import stim

from .code614 import get_dist_circ

__all__ = ["distillation_test_circuit", "circuit_fault_distance", "run_p_sweep"]

_DATA = list(range(6))
_AUX = (6, 7)


def distillation_test_circuit(p: float = 0.0, m: float = 0.0) -> stim.Circuit:
    """The full encode+check+readout circuit, with DETECTOR/OBSERVABLE_INCLUDE
    for the Bell-pair ancilla check and the two X-logicals (X0_L, X1_L).

    Data qubits are reset to |0> before the encoder (the Clifford substitute
    for the true |H+,H+>_L magic-state input -- see module docstring).
    """
    circuit = stim.Circuit()
    circuit.append("R", _DATA + list(_AUX))
    circuit += get_dist_circ(0, _AUX[0], p=p, m=m)
    # get_dist_circ's own trailing MR[aux, aux+1]: both deterministically 0.
    circuit.append("DETECTOR", [stim.target_rec(-2)])
    circuit.append("DETECTOR", [stim.target_rec(-1)])

    circuit.append("MX", _DATA)
    # rec[-6..-1] = qubits 0..5's X-basis outcomes, in order.
    circuit.append(
        "DETECTOR", [stim.target_rec(k) for k in (-6, -5, -4, -3)]
    )  # S^X_1 = X0*X1*X2*X3
    circuit.append(
        "DETECTOR", [stim.target_rec(k) for k in (-4, -3, -2, -1)]
    )  # S^X_2 = X2*X3*X4*X5
    circuit.append(
        "OBSERVABLE_INCLUDE", [stim.target_rec(k) for k in (-6, -4, -2)], 0
    )  # X0_L = X0*X2*X4
    circuit.append(
        "OBSERVABLE_INCLUDE", [stim.target_rec(k) for k in (-5, -3, -1)], 1
    )  # X1_L = X1*X3*X5
    return circuit


def circuit_fault_distance(p: float = 1e-3, m: float = 1e-3) -> int:
    """Length of the shortest graphlike error at physical error rate `p`/`m`.

    >= 2 means no single physical fault both evades every DETECTOR and
    flips a logical observable -- the standard flag-qubit fault-tolerance
    criterion, and the property LightStim's own (encoder-only,
    check-free) `level1_proxy_circuit` was found to fail (distance 1).
    """
    circuit = distillation_test_circuit(p=p, m=m)
    return len(circuit.shortest_graphlike_error())


def run_p_sweep(
    ps: np.ndarray, shots: int = 200_000, m_ratio: float = 1.0
) -> Tuple[np.ndarray, np.ndarray]:
    """Post-selected acceptance rate and joint-logical-error rate at each p.

    `m_ratio` scales the idle-memory depolarizing strength `m` relative to
    `p` (the paper uses a fixed hardware-realistic ratio between gate and
    memory error rates; `m_ratio=1.0` is the simplest choice, m == p).

    Returns (accept_rate, logical_error_rate), each shaped like `ps`.
    `logical_error_rate` is NaN where zero shots were accepted.
    """
    accept = np.zeros_like(ps, dtype=float)
    ler = np.full_like(ps, np.nan, dtype=float)
    for i, p in enumerate(ps):
        circuit = distillation_test_circuit(p=float(p), m=float(p) * m_ratio)
        det, obs = circuit.compile_detector_sampler().sample(shots, separate_observables=True)
        keep = ~det.any(axis=1)
        accept[i] = keep.mean()
        if keep.sum():
            ler[i] = obs[keep].any(axis=1).mean()
    return accept, ler
