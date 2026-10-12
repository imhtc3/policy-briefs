"""
How did MGNREGA work change across states in FY 2024-25?

Compares persondays generated in FY 2023-24 and FY 2024-25 for 20 major states,
looks at how many workers can't receive Aadhaar-based payments (ABPS), and
checks the gap between notified and actually paid wages.

Data sources (see data/ folder):
  - persondays.csv, abps.csv: LibTech India national tracker for FY 2024-25,
    compiled from nrega.nic.in as of 7 April 2025
  - wages_2025.csv: MGNREGA dashboard figures as reported by PRS Legislative
    Research (Demand for Grants 2026-27 analysis, Feb 2026)

West Bengal is left out of the comparisons: central funds have been stopped
since March 2022, so it shows zero work in both years.

Run:  python analysis.py
"""
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).parent
DATA = HERE / "data"
OUT = HERE / "output"
OUT.mkdir(exist_ok=True)

persondays = pd.read_csv(DATA / "persondays.csv")
abps = pd.read_csv(DATA / "abps.csv")
wages = pd.read_csv(DATA / "wages_2025.csv")

df = persondays.merge(abps, on="state")
df = df[df.state != "West Bengal"].copy()

# Change in work generated, and share of workers who can't be paid through ABPS
df["pd_change_pct"] = (df.pd_2024_25_cr - df.pd_2023_24_cr) / df.pd_2023_24_cr * 100
df["all_ineligible_pct"] = df.all_ineligible_cr / df.all_workers_cr * 100

# A rough "stress" score: bigger fall in work + more ABPS exclusion = higher.
# Each indicator is scaled 0-1, then averaged. Treat it as a pointer, not a ranking.
indicators = pd.DataFrame({
    "employment_drop": -df.pd_change_pct,
    "abps_exclusion_all": df.all_ineligible_pct,
    "abps_exclusion_active": df.active_ineligible_pct,
})
scaled = (indicators - indicators.min()) / (indicators.max() - indicators.min())
df["stress_index"] = scaled.mean(axis=1)

summary = df.sort_values("pd_change_pct")[[
    "state", "pd_2023_24_cr", "pd_2024_25_cr", "pd_change_pct",
    "all_ineligible_pct", "active_ineligible_pct", "stress_index",
]].round(2)
summary.to_csv(OUT / "state_summary.csv", index=False)
print(summary.to_string(index=False))

total_before = persondays.pd_2023_24_cr.sum()
total_after = persondays.pd_2024_25_cr.sum()
fell = (df.pd_change_pct < 0).sum()
print(f"\nPersondays: {total_before:.1f} -> {total_after:.1f} crore "
      f"({(total_after - total_before) / total_before * 100:.1f}%)")
print(f"Work fell in {fell} of {len(df)} states")

wages["shortfall_pct"] = (wages.notified_wage - wages.avg_wage_paid) / wages.notified_wage * 100
print("\nWage paid vs notified (2025):")
print(wages.sort_values("shortfall_pct", ascending=False).round(1).to_string(index=False))

# Chart
chart = df.sort_values("pd_change_pct")
fig, ax = plt.subplots(figsize=(8, 7))
colors = ["#c0392b" if v < 0 else "#2e7d32" for v in chart.pd_change_pct]
ax.barh(chart.state, chart.pd_change_pct, color=colors)
ax.axvline(0, color="black", lw=0.8)
for y, v in enumerate(chart.pd_change_pct):
    ax.text(v + (1 if v >= 0 else -1), y, f"{v:.1f}%", va="center",
            ha="left" if v >= 0 else "right", fontsize=8)
ax.set_xlabel("Change in persondays, FY 2023-24 to FY 2024-25 (%)")
ax.set_title(f"MGNREGA work fell in {fell} of {len(df)} states in FY 2024-25\n"
             "(national: -7.1%; West Bengal excluded, funds stopped)")
ax.set_xlim(-45, 50)
plt.tight_layout()
plt.savefig(OUT / "persondays_change.png", dpi=150)
print(f"\nSaved {OUT / 'persondays_change.png'} and {OUT / 'state_summary.csv'}")
