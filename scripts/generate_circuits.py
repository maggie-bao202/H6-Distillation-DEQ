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


def main() -> None:
    from h6_distillation_deq import bare_dist_encoder_circuit, level1_proxy_circuit

    OUT_DIR.mkdir(exist_ok=True)

    bare = bare_dist_encoder_circuit()
    bare_path = OUT_DIR / "h6_dist_bare_encoder.stim"
    bare_path.write_text(str(bare))
    print(f"wrote {bare_path}  ({bare.num_qubits} qubits, {len(bare)} instructions)")

    proxy, system = level1_proxy_circuit()
    proxy_stim_path = OUT_DIR / "h6_dist_level1_proxy.stim"
    proxy_stim_path.write_text(str(proxy))
    print(
        f"wrote {proxy_stim_path}  ({proxy.num_qubits} qubits, "
        f"{proxy.num_detectors} detectors, {proxy.num_observables} observables)"
    )

    try:
        from lightstim.deq import export_deq
    except ImportError as exc:
        print(f"skipping .deq export (lightstim.deq unavailable: {exc})")
        return

    deq_text = export_deq(system, proxy, gadget_name="H6DistillationLevel1Proxy")
    proxy_deq_path = OUT_DIR / "h6_dist_level1_proxy.deq"
    proxy_deq_path.write_text(deq_text)
    print(f"wrote {proxy_deq_path}")

    try:
        from lightstim.deq.validate import validate_deq_text, deq_available
        validate_deq_text(deq_text)
        print(f"validated against real deq grammar: {deq_available()}")
    except Exception as exc:
        print(f"warning: .deq validation failed: {exc}")


if __name__ == "__main__":
    main()
