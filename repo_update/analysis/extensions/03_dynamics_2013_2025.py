"""Dynamics with GERDA 2013-2025 (constant sample: every municipality observed in all four
elections, N = 10,069; West 7,919, East 2,150). The 2013 election is the last one before the
2015-16 arrivals peak and serves as a placebo. The registry is a 2025 snapshot.

  10_gerda_change_and_placebo.csv     change 2021-25 / 2017-25 and 2013 placebo levels (AfD, NPD)
  11_coefficient_profile_by_election.csv  the same specification estimated on each election
  12_change_from_2013.csv             changes 2013->2017 / 2021 / 2025
  figures/figure5_coefficients_by_election.{png,pdf}
"""
import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
from common import (load_panel, split, with_z, fit, cluster_stats, wcb_fast, result_row, save,
                    CTRL, LAND_FE, KREIS_FE, FIG)

FE = {"Land FE": LAND_FE, "Kreis FE": KREIS_FE}

# --- 10: change outcomes and placebo levels (sample: non-missing outcome) -------------------
P = load_panel(require_years=False)
P["d_afd_21_25"] = P.afd2025 - P.afd2021
P["d_afd_17_25"] = P.afd2025 - P.afd2017
OUTC = {"d_afd_21_25": "Change AfD 2021-25", "d_afd_17_25": "Change AfD 2017-25",
        "afd2013": "Placebo: AfD 2013 level", "npd2013": "Placebo: NPD 2013 level"}
rows = []
for y, ylab in OUTC.items():
    D = P.dropna(subset=[y])
    W, E, EN = split(D)
    for sn, s in {"Germany": D, "West": W, "East": E, "East excl. MV": EN}.items():
        for fn, fe in FE.items():
            m = fit(f"{y} ~ ln_distance + {fe} + {CTRL}", s)
            rows.append(result_row(m, s, "ln_distance", outcome=ylab, spec="ln_distance", sample=sn, model=fn))
    w = with_z(W, "foreign_share_2021")
    m = fit(f"{y} ~ ln_distance + ln_distance:Z + {KREIS_FE} + {CTRL}", w)
    rows.append(result_row(m, w, "ln_distance:Z", outcome=ylab, spec="H3: ln_distance x district foreign share",
                           sample="West", model="Kreis FE"))
    for fn, fe in FE.items():
        m = fit(f"{y} ~ n_centres_50km + {fe} + {CTRL}", w)
        rows.append(result_row(m, w, "n_centres_50km", outcome=ylab, spec="n_centres_50km", sample="West", model=fn))
save(rows, "10_gerda_change_and_placebo.csv")

# --- 11 / 12: constant four-election sample -------------------------------------------------
B = load_panel(require_years=True)
W, E, EN = split(B)
W = with_z(W, "foreign_share_2021")
SPECS = [("Germany", "Land FE", B, "ln_distance", LAND_FE, ""), ("Germany", "Kreis FE", B, "ln_distance", KREIS_FE, ""),
         ("West", "Land FE", W, "ln_distance", LAND_FE, ""), ("West", "Kreis FE", W, "ln_distance", KREIS_FE, ""),
         ("East", "Land FE", E, "ln_distance", LAND_FE, ""), ("East", "Kreis FE", E, "ln_distance", KREIS_FE, ""),
         ("West", "Kreis FE (H3)", W, "ln_distance:Z", KREIS_FE, " + ln_distance:Z"),
         ("West", "Land FE (density)", W, "n_centres_50km", LAND_FE, "")]
rows = []
for sn, fn, d, term, fe, extra in SPECS:
    for y in (2013, 2017, 2021, 2025):
        rhs = "ln_distance" if term == "ln_distance:Z" else term
        m = fit(f"afd{y} ~ {rhs}{extra} + {fe} + {CTRL}", d)
        r = result_row(m, d, term, sample=sn, model=fn, term=term, year=y)
        r["mean_afd"] = d[f"afd{y}"].mean()
        rows.append(r)
prof = save(rows, "11_coefficient_profile_by_election.csv")

rows = []
for a, b in [(2013, 2017), (2013, 2021), (2013, 2025)]:
    for lab, d, term, fe, extra in [("West Kreis FE: H3 interaction", W, "ln_distance:Z", KREIS_FE, " + ln_distance:Z"),
                                    ("West Land FE: ln_distance", W, "ln_distance", LAND_FE, ""),
                                    ("West Kreis FE: ln_distance", W, "ln_distance", KREIS_FE, ""),
                                    ("East Land FE: ln_distance", E, "ln_distance", LAND_FE, ""),
                                    ("East excl. MV Land FE: ln_distance", EN, "ln_distance", LAND_FE, ""),
                                    ("East Kreis FE: ln_distance", E, "ln_distance", KREIS_FE, "")]:
        m = fit(f"I(afd{b} - afd{a}) ~ ln_distance{extra} + {fe} + {CTRL}", d)
        rows.append(result_row(m, d, term, change=f"{a}->{b}", spec=lab))
save(rows, "12_change_from_2013.csv")

# --- figure 5 -----------------------------------------------------------------------------
G = {"West": W.Kreis_code.nunique(), "East": E.Kreis_code.nunique()}
panels = [("West", "Kreis FE (H3)", "H3 (West, Kreis FE):\nln(distance) × district foreign share"),
          ("West", "Land FE", "West, Land FE:\nln(distance)"),
          ("East", "Land FE", "East, Land FE:\nln(distance)")]
fig, axs = plt.subplots(1, 3, figsize=(11, 3.6), sharex=True)
for ax, (s, mname, title) in zip(axs, panels):
    d = prof[(prof["sample"] == s) & (prof.model == mname)].sort_values("year")
    c = stats.t.ppf(.975, G[s] - 1)
    ax.errorbar(d.year, d.beta, yerr=c * d.SE_Kreis, fmt="o-", color="black", capsize=3, lw=1.2, ms=5)
    ax.axhline(0, color="0.5", ls="--", lw=.8)
    ax.axvspan(2014.6, 2016.4, color="0.9", lw=0)
    ax.set_title(title, fontsize=10)
    ax.set_xticks([2013, 2017, 2021, 2025])
axs[0].set_ylabel("Coefficient (AfD share, pp)")
fig.text(0.01, -0.06, f"Same municipalities in every year (N = {len(B):,}; West {len(W):,}, East {len(E):,}); "
         "15 controls; 95% CI clustered by Kreis.\nShaded: 2015–16 arrivals peak. AfD shares from GERDA "
         "(2021 boundaries). Registry is a 2025 snapshot.", fontsize=8)
fig.tight_layout()
for ext in ("png", "pdf"):
    fig.savefig(FIG / f"figure5_coefficients_by_election.{ext}", dpi=300, bbox_inches="tight")
