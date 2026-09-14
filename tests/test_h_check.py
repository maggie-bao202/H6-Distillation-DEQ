import numpy as np

from h6_distillation_deq import circuit_fault_distance, distillation_test_circuit, run_p_sweep


def test_noiseless_circuit_is_clean():
    circuit = distillation_test_circuit(p=0.0, m=0.0)
    assert circuit.num_detectors == 4  # 2 ancilla check + 2 X-stabilizers
    assert circuit.num_observables == 2  # X0_L, X1_L
    det, obs = circuit.compile_detector_sampler().sample(4096, separate_observables=True)
    assert not det.any()
    assert not obs.any()


def test_circuit_fault_distance_is_two():
    """The real protocol (encoder + Bell-pair H-check fused, per
    Code614.py) is fault distance 2 -- unlike LightStim's
    level1_proxy_circuit (which uses a full SE round instead of the
    paper's actual check and is fault distance 1). This is the whole
    point of the H-check: catching single physical faults before they
    become an undetected logical error."""
    assert circuit_fault_distance(p=1e-3, m=1e-3) == 2


def test_reproduces_paper_quadratic_scaling():
    """Reproduces arXiv:2506.14688 Fig. 4's level-1 scaling law
    (~26 * p^2.08) via the paper's own Clifford-substitution methodology
    (Section III): the post-selected logical error rate should scale as
    p^2, not p^1 -- this is the actual distillation-protocol claim being
    tested, not just "the circuit runs"."""
    ps = np.array([0.001, 0.002, 0.004, 0.008, 0.016])
    _, ler = run_p_sweep(ps, shots=100_000)
    assert not np.isnan(ler).any()
    slope, _ = np.polyfit(np.log(ps), np.log(ler), 1)
    assert 1.7 < slope < 2.4, f"expected ~quadratic scaling, got slope={slope:.2f}"
