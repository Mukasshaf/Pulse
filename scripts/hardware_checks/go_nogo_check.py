"""
go_nogo_check.py -- Phase 3, §3.3 Tasks 2 & 3.

Reads zero-shot and HW-LOSO result JSONs, prints the transfer gap comparison,
and applies the M3 go/no-go gate: HW-trained F1-macro ≥ 0.65.

Usage:
    python go_nogo_check.py \\
        --zero-shot  outputs/results/zero_shot_result.json \\
        --hw-loso    outputs/results/hw_loso_results.json \\
        [--out       outputs/results/transfer_gap.md]

Exit code:
    0  -> PASS (F1 ≥ 0.65, Phase 4 may begin)
    1  -> FAIL (F1 < 0.65, revisit electrode placement / sampling rate)

The exit code is machine-readable so CI / a shell script can branch on it.
"""

import argparse
import json
import sys
from pathlib import Path

M3_F1_GATE = 0.65   # workplan §3.3 Task 3 — do not lower without revising the workplan


def load_json(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def run_check(zero_shot_path: str | None,
              hw_loso_path: str,
              out_path: str | None) -> int:

    hw = load_json(hw_loso_path)
    hw_f1   = hw["aggregate"]["f1_macro"]
    hw_f1sd = hw.get("f1_std", float("nan"))
    hw_acc  = hw["aggregate"]["accuracy"]
    hw_spec = hw["aggregate"].get("specificity", float("nan"))
    hw_n    = hw["n_subjects"]

    lines = []
    lines.append("# M3 Transfer Gap Report\n")
    lines.append(f"**M3 gate:** HW-trained F1-macro ≥ {M3_F1_GATE}\n")

    # Zero-shot section
    if zero_shot_path:
        zs = load_json(zero_shot_path)
        zs_f1  = zs["f1_macro"]
        zs_acc = zs["accuracy"]
        gap    = hw_f1 - zs_f1
        gap_str = f"+{gap:.4f}" if gap >= 0 else f"{gap:.4f}"

        lines.append("## Zero-shot (WESAD model → hardware data)\n")
        lines.append(f"| Metric | Value |\n|---|---|")
        lines.append(f"| Accuracy  | {zs_acc:.4f} |")
        lines.append(f"| F1-macro  | {zs_f1:.4f} |")
        lines.append(f"| Subjects  | {zs['n_subjects']} |")
        lines.append(f"| Windows   | {zs['n_windows']} |")
        lines.append("")

        print(f"\n  Zero-shot (WESAD -> HW):")
        print(f"    acc={zs_acc:.4f}  f1={zs_f1:.4f}")
    else:
        gap = float("nan")
        gap_str = "N/A (zero-shot not run)"

    # HW-LOSO section
    lines.append("## HW-only LOSO\n")
    lines.append(f"| Metric | Value |\n|---|---|")
    lines.append(f"| Accuracy   | {hw_acc:.4f} |")
    lines.append(f"| F1-macro   | {hw_f1:.4f} ± {hw_f1sd:.4f} |")
    lines.append(f"| Specificity| {hw_spec:.4f} |")
    lines.append(f"| Subjects   | {hw_n} |")
    lines.append(f"| Windows    | {hw.get('n_windows', len(hw.get('y_true', [])))} |")
    lines.append("")

    print(f"\n  HW-LOSO:")
    print(f"    acc={hw_acc:.4f}  f1={hw_f1:.4f} (±{hw_f1sd:.4f})  spec={hw_spec:.4f}")

    # Transfer gap
    lines.append("## Transfer Gap\n")
    lines.append(f"| | Zero-shot | HW-LOSO | Gap |\n|---|---|---|---|")
    zs_str = f"{zs_f1:.4f}" if zero_shot_path else "N/A"
    lines.append(f"| F1-macro | {zs_str} | {hw_f1:.4f} | {gap_str} |")
    lines.append("")

    # M3 gate
    gate_pass = hw_f1 >= M3_F1_GATE
    verdict   = "✅ PASS — Phase 4 may begin." if gate_pass else (
        f"❌ FAIL — F1 {hw_f1:.4f} < gate {M3_F1_GATE}. "
        f"Revisit electrode placement / sampling rate before Phase 4 "
        f"(workplan §3.3 Task 3 decision point)."
    )

    lines.append("## M3 Go/No-Go Gate\n")
    lines.append(f"**Gate:** HW F1-macro ≥ {M3_F1_GATE}")
    lines.append(f"**Result:** {verdict}")
    lines.append("")

    # Per-fold breakdown
    lines.append("## Per-fold Breakdown\n")
    lines.append("| Subject | Windows | Acc | F1 | Spec |")
    lines.append("|---|---|---|---|---|")
    for fold in hw.get("fold_results", []):
        lines.append(
            f"| {fold['test_sid']} | {fold['n_test']} | "
            f"{fold['accuracy']:.3f} | {fold['f1_macro']:.3f} | "
            f"{fold['specificity']:.3f} |"
        )
    lines.append("")

    print(f"\n  === M3 Go/No-Go ===")
    print(f"  Gate: F1 ≥ {M3_F1_GATE}")
    print(f"  {'PASS' if gate_pass else 'FAIL'} — F1 = {hw_f1:.4f}")

    report = "\n".join(lines)

    if out_path:
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\n  Report saved -> {out_path}")

    return 0 if gate_pass else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="M3 go/no-go gate check")
    parser.add_argument("--zero-shot", default=None,
                        help="Path to zero_shot_result.json (optional)")
    parser.add_argument("--hw-loso",  required=True,
                        help="Path to hw_loso_results.json")
    parser.add_argument("--out",      default="outputs/results/transfer_gap.md",
                        help="Output markdown report path")
    args = parser.parse_args()

    exit_code = run_check(args.zero_shot, args.hw_loso, args.out)
    sys.exit(exit_code)
