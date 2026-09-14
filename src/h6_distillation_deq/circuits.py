"""Magic-H6 [[6,2,2]] level-1 distillation circuits, built on LightStim.

Two circuits are provided, both reusing LightStim's existing port of
Quantinuum's ``CQCL/Magic-H6`` ``Code614.py`` (``lightstim.qec_code.H_six``):

* :func:`bare_dist_encoder_circuit` — just the ``|0>^6 -> |++>_L`` encoder
  block (``get_dist_circ``), no syndrome extraction. The simplest thing to
  paste into a tool for a first look at the circuit.
* :func:`level1_proxy_circuit` — the encoder plus one native syndrome-
  extraction round, a Bell-pair H-check round, and an X-basis readout —
  reconstructed from LightStim's ``playground/magic_h6/
  H_six_roadmap_status.ipynb`` (roadmap "Step 3").

IMPORTANT — this is a Clifford *proxy*, not yet a verified distillation
circuit. Per that roadmap notebook's own conclusion: `shortest_graphlike_error`
shows this circuit is circuit fault distance 1 (a single undetected physical
fault can flip the logical output), so under circuit-level noise its
post-selected output logical error rate scales as O(p), not the O(p^2) the
Magic-H6 protocol is supposed to achieve. Magic-H6's real distillation claim
(O(p_in^2) suppression of *input* |H>-state infidelity) is a separate,
not-yet-implemented measurement (no p_in injection channel exists here) —
see the roadmap notebook's "Step 3 verdict" for the full account. Treat
`level1_proxy_circuit` as a structurally-faithful starting point to build
the real, flag-verified distillation circuit on top of, not as a finished
result.
"""

from typing import Tuple

import stim

from lightstim.ir.builder import CircuitBuilder
from lightstim.ir.qec_system import QECSystem
from lightstim.ir.tracker import SyndromeTracker
from lightstim.qec_code.H_six import (
    HSixCode,
    HSixExtractionBlock,
    HSixLogicalXCheckBlock,
    get_dist_circ,
)

__all__ = ["bare_dist_encoder_circuit", "level1_proxy_circuit"]


def bare_dist_encoder_circuit() -> stim.Circuit:
    """Just the |0>^6 -> |++>_L encoder (``get_dist_circ``) on 6 fresh qubits.

    No syndrome extraction, no detectors. Useful as a minimal, easy-to-read
    first circuit to load into an external tool (e.g. Bloqade Studio).
    """
    circuit = stim.Circuit()
    circuit.append("R", range(6))
    circuit += get_dist_circ(list(range(6)))
    return circuit


def level1_proxy_circuit() -> Tuple[stim.Circuit, QECSystem]:
    """|0>^6 -> get_dist_circ -> |++>_L, one native SE round, Bell-pair
    H-check, X readout. See the module docstring for why this is a proxy,
    not a verified distillation circuit, as-is.

    Returns ``(circuit, system)`` — the system is the one the circuit was
    actually built against (needed for ``lightstim.deq.export_deq``, which
    reads the code's stabilizers/logicals off it).
    """
    system = QECSystem()
    system.add_patch(HSixCode(h_check_ancillas=2), name="c622")
    tracker = SyndromeTracker(system.num_qubits, expected_num_logicals=system.num_logicals)
    builder = CircuitBuilder(tracker, system, if_detector=True)
    builder.write_coordinates()
    data = sorted(system.data_indices)
    builder.initialize({q: "Z" for q in data}, n=system.num_qubits)
    builder.apply_unitary_block(get_dist_circ(data))
    builder.apply_syndrome_extraction(
        circuit_chunk=HSixExtractionBlock(system).circuit, rounds=1
    )
    builder.apply_syndrome_extraction(
        circuit_chunk=HSixLogicalXCheckBlock(system).circuit, rounds=1
    )
    builder.apply_data_readout({q: "X" for q in data})
    return builder.circuit, system
