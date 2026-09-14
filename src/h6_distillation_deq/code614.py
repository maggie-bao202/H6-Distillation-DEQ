"""Verbatim port of Quantinuum's ``Code614.py`` ``get_dist_circ``.

Source: github.com/Quantinuum/Magic-H6, ``Stim/ConcatenatedMSProtocolSim/Code614.py``
(Apache-2.0, Copyright 2025 Quantinuum). This is the ACTUAL circuit behind
arXiv:2506.14688 ("Breaking even with magic") — encoder + Bell-pair ancilla
H-check fused into one circuit, with built-in ``p`` (two-qubit gate /
measurement depolarizing strength) and ``m`` (one-qubit idle-memory
depolarizing strength) noise parameters matching the paper's own benchmark
methodology (Fig. 4).

LightStim's ``lightstim.qec_code.H_six.get_dist_circ`` only ports the
ENCODER half of this function (the first 10 gates) — it drops the Bell-pair
ancilla check entirely. This module ports the complete original instead, so
the resulting circuit's fault-tolerance properties (circuit fault distance,
O(p^2) scaling) match the paper's, not a subset of it.
"""

import stim

__all__ = ["get_dist_circ"]


def get_dist_circ(start: int, aux: int, p: float = 0.0, m: float = 0.0) -> stim.Circuit:
    """Distills a [[6,2,2]] H state.

    Args:
        start: First of 6 consecutive qubit indices holding the (Clifford
            substitute for the) magic state to be encoded/verified.
        aux: First of 2 consecutive qubit indices for the Bell-pair check
            ancilla.
        p: Two-qubit-gate / measurement depolarizing strength.
        m: One-qubit idle-memory depolarizing strength.
    """
    c = stim.Circuit()
    c.append("H", [start, start + 1])  # The magic state we are distilling/encoding
    c.append("H", [start + 2, start + 4])
    c.append("CX", [start + 2, start + 3])
    c.append("DEPOLARIZE2", [start + 2, start + 3], p)
    c.append("CX", [start + 4, start + 5])
    c.append("DEPOLARIZE2", [start + 4, start + 5], p)
    c.append("DEPOLARIZE1", [start, start + 1], m)

    c.append("CX", [start + 2, start])
    c.append("DEPOLARIZE2", [start + 2, start], p)
    c.append("CX", [start + 3, start + 1])
    c.append("DEPOLARIZE2", [start + 3, start + 1], p)
    c.append("DEPOLARIZE1", [start + 4, start + 5], m)

    c.append("CX", [start, start + 4])
    c.append("DEPOLARIZE2", [start, start + 4], p)
    c.append("CX", [start + 1, start + 5])
    c.append("DEPOLARIZE2", [start + 1, start + 5], p)
    c.append("DEPOLARIZE1", [start + 2, start + 3], m)

    c.append("CX", [start + 4, start + 2])
    c.append("DEPOLARIZE2", [start + 4, start + 2], p)
    c.append("CX", [start + 5, start + 3])
    c.append("DEPOLARIZE2", [start + 5, start + 3], p)
    c.append("DEPOLARIZE1", [start, start + 1], m)

    c.append("H", [aux])  # Creating the Bell-pair ancilla
    c.append("CX", [aux, aux + 1])
    c.append("DEPOLARIZE2", [aux, aux + 1], p)

    c.append("CX", [aux, start])
    c.append("DEPOLARIZE2", [aux, start], p)
    c.append("CX", [aux + 1, start + 1])
    c.append("DEPOLARIZE2", [aux + 1, start + 1], p)
    c.append("DEPOLARIZE1", [start + 2, start + 3, start + 4, start + 5], m)

    c.append("CX", [aux, start + 2])
    c.append("DEPOLARIZE2", [aux, start + 2], p)
    c.append("CX", [aux + 1, start + 3])
    c.append("DEPOLARIZE2", [aux + 1, start + 3], p)
    c.append("DEPOLARIZE1", [start, start + 1, start + 4, start + 5], m)

    c.append("CX", [aux, start + 4])
    c.append("DEPOLARIZE2", [aux, start + 4], p)
    c.append("CX", [aux + 1, start + 5])
    c.append("DEPOLARIZE2", [aux + 1, start + 5], p)
    c.append("DEPOLARIZE1", [start + 2, start + 3, start, start + 1], m)

    c.append("CX", [aux, aux + 1])
    c.append("DEPOLARIZE2", [aux, aux + 1], p)

    c.append("H", [aux])
    c.append("MR", [aux, aux + 1], p)
    c.append("DEPOLARIZE1", [start, start + 1, start + 2, start + 3, start + 4, start + 5], m)

    return c
