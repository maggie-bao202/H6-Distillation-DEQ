#!/usr/bin/env python3
"""Generate the H6-distillation circuits as .stim (for Bloqade Studio import)
and .deq (via lightstim.deq.export_deq) files under generated/.

Usage:
    python scripts/generate_circuits.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

OUT_DIR = ROOT / "generated"


def _export(name: str, circuit, system, out_dir: Path) -> None:
    stim_path = out_dir / f"{name}.stim"
    stim_path.write_text(str(circuit))
    print(
        f"wrote {stim_path}  ({circuit.num_qubits} qubits, "
        f"{circuit.num_detectors} detectors, {circuit.num_observables} observables)"
    )

    try:
        from lightstim.deq import export_deq
        from lightstim.deq.validate import deq_available, validate_deq_text
    except ImportError as exc:
        print(f"  skipping .deq export (lightstim.deq unavailable: {exc})")
        return

    deq_text = export_deq(system, circuit, gadget_name=name)
    deq_path = out_dir / f"{name}.deq"
    deq_path.write_text(deq_text)
    print(f"wrote {deq_path}")
    try:
        validate_deq_text(deq_text)
        print(f"  validated against real deq grammar: {deq_available()}")
    except Exception as exc:
        print(f"  warning: .deq validation failed: {exc}")


def main() -> None:
    from lightstim.ir.qec_system import QECSystem
    from lightstim.qec_code.H_six import HSixCode

    from h6_distillation_deq import (
        bare_dist_encoder_circuit,
        distillation_test_circuit,
        level1_proxy_circuit,
    )

    OUT_DIR.mkdir(exist_ok=True)

    bare = bare_dist_encoder_circuit()
    bare_path = OUT_DIR / "h6_dist_bare_encoder.stim"
    bare_path.write_text(str(bare))
    print(f"wrote {bare_path}  ({bare.num_qubits} qubits, {len(bare)} instructions)")

    print()
    print("--- level1_proxy_circuit (encoder + full SE round; fault distance 1, not FT) ---")
    proxy, proxy_system = level1_proxy_circuit()
    _export("h6_dist_level1_proxy", proxy, proxy_system, OUT_DIR)

    print()
    print("--- distillation_test_circuit (real paper protocol: encoder + Bell-pair")
    print("    H-check fused, per Code614.py; fault distance 2, reproduces O(p^2)) ---")
    check_system = QECSystem()
    check_system.add_patch(HSixCode(), name="c622")
    check_circuit = distillation_test_circuit(p=0.0, m=0.0)
    _export("h6_dist_check", check_circuit, check_system, OUT_DIR)

    print()
    print("--- same circuit, noisy (p = m = 0.001, near the paper's real hardware")
    print("    operating point, well below the ~0.02 breakeven threshold) ---")
    noisy_check_system = QECSystem()
    noisy_check_system.add_patch(HSixCode(), name="c622")
    noisy_check_circuit = distillation_test_circuit(p=0.001, m=0.001)
    # No "." in the GADGET name: deq's IDENT grammar is ASCII_ALPHA (ASCII_ALPHANUMERIC|"_")*.
    _export("h6_dist_check_noisy_p1en3", noisy_check_circuit, noisy_check_system, OUT_DIR)


if __name__ == "__main__":
    main()
