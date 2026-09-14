import stim

from h6_distillation_deq import bare_dist_encoder_circuit, level1_proxy_circuit


def test_bare_encoder_prepares_plus_plus_l():
    """Noiseless get_dist_circ should prepare |++>_L: X0_L, X1_L, and both
    stabilizers deterministically +1 (per HSixCode's canonical convention)."""
    circuit = bare_dist_encoder_circuit()
    sim = stim.TableauSimulator()
    sim.do(circuit)
    for check in ("+XXXXII", "+IIXXXX", "+ZZZZII", "+IIZZZZ"):
        assert sim.peek_observable_expectation(stim.PauliString(check)) == 1
    assert sim.peek_observable_expectation(stim.PauliString("+XIXIXI")) == 1  # X0_L = X0 X2 X4
    assert sim.peek_observable_expectation(stim.PauliString("+IXIXIX")) == 1  # X1_L = X1 X3 X5


def test_level1_proxy_builds_and_is_noiseless_clean():
    circuit, system = level1_proxy_circuit()
    assert circuit.num_qubits == 12  # 6 data + 2 H-check + 2 flag-role + 2 more ancilla
    assert system.num_logicals == 2
    det, obs = circuit.compile_detector_sampler().sample(4096, separate_observables=True)
    assert not det.any(), "noiseless circuit must never fire a detector"


def test_level1_proxy_is_circuit_fault_distance_one():
    """Regression / documentation test: this is the known, documented gap —
    see the README and playground/magic_h6/H_six_roadmap_status.ipynb in
    LightStim ('Step 3 verdict: not met'). If this ever starts failing
    (i.e. distance becomes >= 2), the README's caveat should be updated,
    not this test deleted."""
    from lightstim.noise.config import NoiseConfig
    from lightstim.noise.injector import NoiseInjector

    circuit, _ = level1_proxy_circuit()
    cfg = NoiseConfig(p_1q=1e-3, p_2q=1e-3, p_meas=1e-3, p_reset=1e-3)
    noisy = NoiseInjector.from_circuit_level(cfg, list(range(circuit.num_qubits))).inject_noise(circuit)
    assert len(noisy.shortest_graphlike_error()) == 1
