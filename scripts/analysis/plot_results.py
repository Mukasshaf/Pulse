import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# The true canonical domains from src/domains.py
DOMAINS = [
    "academic_pressure",
    "peer_influence",
    "impulsivity_gratification",
    "risk_reward",
    "rule_ambiguity",
    "future_uncertainty",
    "social_evaluation"
]

def load_and_aggregate(csv_path: Path):
    """Calculates mean HR (from pulse) and GSR per domain."""
    if not csv_path.exists():
        return None
        
    df = pd.read_csv(csv_path)
    # Exclude undefined/transitional periods
    df = df[df["active_domain"].isin(DOMAINS + ["baseline"])]
    
    # Simple proxy metrics for raw plotting:
    # 1. GSR Raw (lower resistance = higher sweat/stress in Grove GSR)
    # 2. Pulse variance/amplitude proxy
    agg = df.groupby("active_domain")[["gsr_raw", "pulse_raw"]].mean().to_dict('index')
    return agg

def plot_radar_for_subject(agg_data, sid, ax):
    """Plots a radar chart for a single subject normalized against their baseline."""
    if not agg_data or "baseline" not in agg_data:
        ax.set_title(f"{sid} (Data Missing)")
        return

    # Normalize domain GSR relative to baseline (Baseline = 1.0)
    # Grove GSR goes DOWN when sweating, so we invert the ratio: baseline / domain
    base_gsr = agg_data["baseline"]["gsr_raw"]
    
    values = []
    for d in DOMAINS:
        val = agg_data.get(d, {"gsr_raw": base_gsr})["gsr_raw"]
        ratio = base_gsr / val if val > 0 else 1.0
        values.append(ratio)
        
    # Close the loop for radar chart
    values += values[:1]
    angles = np.linspace(0, 2 * np.pi, len(DOMAINS), endpoint=False).tolist()
    angles += angles[:1]
    
    ax.plot(angles, values, linewidth=2, linestyle='solid', label=sid, color='#ff3366')
    ax.fill(angles, values, '#ff3366', alpha=0.25)
    
    # Plot baseline reference circle (1.0)
    ax.plot(angles, [1.0]*len(angles), 'k--', linewidth=1, alpha=0.5, label="Resting Baseline")
    
    # Formatting
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels([d.replace("_", "\n").title() for d in DOMAINS], size=8)
    ax.set_title(f"Subject {sid}\nPhysiological Activation", size=12, weight='bold', pad=20)
    ax.set_ylim(0.8, max(max(values)*1.1, 1.2))

def main():
    fig, axes = plt.subplots(1, 3, figsize=(16, 5), subplot_kw=dict(polar=True))
    fig.suptitle("GPAMS Domain-Specific Stress Activation Maps", fontsize=16, weight='bold', y=1.05)
    
    for idx, sid in enumerate(["S01", "S02", "S03"]):
        csv_path = Path(f"outputs/aligned/{sid}_aligned.csv")
        agg = load_and_aggregate(csv_path)
        plot_radar_for_subject(agg, sid, axes[idx])
        
    plt.tight_layout()
    plt.savefig("outputs/PPT_Radar_Charts.png", dpi=300, bbox_inches='tight')
    print("Success! Radar charts saved to outputs/PPT_Radar_Charts.png")

if __name__ == "__main__":
    main()``