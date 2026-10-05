"""H3: is the distance association weaker where pre-existing ethnic diversity is higher?

Moderators (z-scored within each estimation sample, so the ln_distance main effect is the
slope at mean diversity and the interaction is the change in that slope per 1 SD):
  foreign_share_zensus2022  municipal (varies within Kreis)
  foreign_share_2021        district, INKAR (constant within Kreis)
Same 15 controls, Land FE and Kreis FE, Germany / West / East, 2025 AfD share.
Design rule: the moderator's main effect is omitted when it is already in the model (it is one
of the controls, or it is absorbed by Kreis FE); keeping it makes the design rank-deficient and
the pinv-based cluster SE unstable. Every model is rank-checked.
Outputs: 08_h3_interactions.csv, 08b_h3_pooled_composition.csv,
         08c_h3_west_district_robustness.csv, 08d_h3_west_marginal_slopes.csv,
         08e_h3_west_terciles.csv, figures/figure4_h3_west_marginal_slope.{png,pdf}
"""
import numpy as np
import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
from common import (load_baseline, split, with_z, fit, cluster_result, cluster_stats, wcb_fast,
                    result_row, save, CTRL, CONTROLS, LAND_FE, KREIS_FE, KREIS_CONSTANT, FIG)

MODS = {"foreign_share_zensus2022": "Municipal foreign share (Zensus 2022)",
        "foreign_share_2021": "District foreign share (INKAR 2021)"}
FES = {"Land FE": LAND_FE, "Kreis FE": KREIS_FE}


def formula(mod, fe, ctrl=CTRL, x="ln_distance", extra=""):
    absorbed = (fe == KREIS_FE and mod in KREIS_CONSTANT) or mod in ctrl.split(" + ")
    core = f"{x} + {x}:Z" if absorbed else f"{x} * Z"
    return f"afd_share_2025_pct ~ {core}{extra} + {fe} + {ctrl}"


base = load_baseline()
west, east, _ = split(base)

# 1. main grid ------------------------------------------------------------------------------
rows = []
for mod, mlab in MODS.items():
    for sname, s in {"Germany": base, "West": west, "East": east}.items():
        d = with_z(s, mod)
        for fname, fe in FES.items():
            m = fit(formula(mod, fe), d)
            for term in ["ln_distance", "ln_distance:Z"]:
                rows.append(result_row(m, d, term, moderator=mlab, sample=sname, model=fname, coef=term,
                                       moderator_mean=s[mod].mean(), moderator_sd=s[mod].std()))
save(rows, "08_h3_interactions.csv")

# 2. pooled interaction = East/West composition? -------------------------------------------
rows = []
for mod, mlab in MODS.items():
    d = with_z(base, mod)
    for fname, fe in FES.items():
        absorbed = fe == KREIS_FE and mod in KREIS_CONSTANT
        for spec, extra in [("Pooled", ""),
                            ("Pooled + region-specific slope",
                             " + ln_distance:east_dummy" + ("" if absorbed else " + Z:east_dummy"))]:
            m = fit(formula(mod, fe, extra=extra), d)
            rows.append(result_row(m, d, "ln_distance:Z", moderator=mlab, model=fname, spec=spec))
save(rows, "08b_h3_pooled_composition.csv")

# 3. robustness of the West district-level interaction ------------------------------------
MOD = "foreign_share_2021"
wz = with_z(west, MOD)
COMPETING = ["unemployment_rate_2021", "tertiary_education_share_2022", "purchasing_power_pc_2021",
             "urban_dummy", "ln_population_2021", "population_density_2021", "foreign_share_zensus2022",
             "share_65plus_2021", "turnout_2021_pct", "net_migration_rate_2021"]
for v in COMPETING:
    wz["O_" + v] = (wz[v] - wz[v].mean()) / wz[v].std()
NOPT = " + ".join(c for c in CONTROLS if c not in [
    "foreign_share_zensus2022", "immig_history_share_zensus2022", "immigrated_share_zensus2022",
    "turnout_2021_pct"])
rob = []


def add(label, d, f, weights=None, term="ln_distance:Z"):
    m = fit(f, d, weights)
    rob.append(result_row(m, d, term, bootstrap=weights is None, check=label))


add("Baseline: West, Kreis FE", wz, formula(MOD, KREIS_FE))
add("Land FE instead of Kreis FE", wz, formula(MOD, LAND_FE))
for v in COMPETING:
    add(f"+ ln_distance x {v}", wz, formula(MOD, KREIS_FE, extra=f" + ln_distance:O_{v}"))
add("+ all 10 competing interactions", wz,
    formula(MOD, KREIS_FE, extra="".join(f" + ln_distance:O_{v}" for v in COMPETING)))
add("Without post-treatment controls (Zensus migration shares, turnout)", wz, formula(MOD, KREIS_FE, ctrl=NOPT))
add("Population-weighted (WLS)", wz, formula(MOD, KREIS_FE), weights="population_2021")
add("Distance in km instead of log", wz, formula(MOD, KREIS_FE, x="distance_nearest_shelter_km"),
    term="distance_nearest_shelter_km:Z")
for lab, flag in [("Exclude coarse coordinates", "nearest_shelter_coord_coarse"),
                  ("Exclude sensitivity cases", "nearest_shelter_sensitivity_case")]:
    add(lab, with_z(west[west[flag].str.lower() != "yes"], MOD), formula(MOD, KREIS_FE))
for L in sorted(west["State_code"].str.zfill(2).unique()):
    d = west[west["State_code"].str.zfill(2) != L]
    if len(west) - len(d) >= 10:                     # skips Bremen (1 municipality)
        add(f"Drop Land {L} (n={len(west) - len(d)})", with_z(d, MOD), formula(MOD, KREIS_FE))
save(rob, "08c_h3_west_district_robustness.csv")

# 4. marginal slopes, terciles, figure ------------------------------------------------------
m = fit(formula(MOD, KREIS_FE), wz)
rc, grp = cluster_result(m, wz, "Kreis_code")
names = list(m.params.index)
i, j = names.index("ln_distance"), names.index("ln_distance:Z")
V, G = rc.cov_params(), grp.nunique()
tc = stats.t.ppf(0.975, G - 1)
mu, sd = west[MOD].mean(), west[MOD].std()
grid = np.linspace(west[MOD].quantile(0.02), west[MOD].quantile(0.98), 60)
ms = []
for q, v in [(None, x) for x in grid] + [(q, west[MOD].quantile(q)) for q in [.1, .25, .5, .75, .9]]:
    zz = (v - mu) / sd
    b = m.params.iloc[i] + zz * m.params.iloc[j]
    se = np.sqrt(V[i, i] + zz ** 2 * V[j, j] + 2 * zz * V[i, j])
    ms.append(dict(percentile=q, foreign_share_2021=v, slope=b, SE=se, lo=b - tc * se, hi=b + tc * se,
                   p=2 * stats.t.sf(abs(b / se), G - 1)))
ms = pd.DataFrame(ms)
save(ms[ms.percentile.notna()], "08d_h3_west_marginal_slopes.csv")

wt = west.copy()
wt["tercile"] = pd.qcut(wt[MOD].rank(method="first"), 3, labels=["low", "mid", "high"])
mt = fit(f"afd_share_2025_pct ~ ln_distance:C(tercile) + {KREIS_FE} + {CTRL}", wt)
rt, _ = cluster_result(mt, wt, "Kreis_code")
rows = []
for t in ["low", "mid", "high"]:
    k = list(mt.params.index).index(f"ln_distance:C(tercile)[{t}]")
    sub = wt[wt.tercile == t]
    rows.append(dict(tercile=t, share_min=sub[MOD].min(), share_max=sub[MOD].max(), N=len(sub),
                     Kreise=sub.Kreis_code.nunique(), slope=mt.params.iloc[k], SE_Kreis=rt.bse[k],
                     p_Kreis=rt.pvalues[k]))
wt["hi"], wt["mid"] = (wt.tercile == "high").astype(float), (wt.tercile == "mid").astype(float)
md = fit(f"afd_share_2025_pct ~ ln_distance + ln_distance:hi + ln_distance:mid + {KREIS_FE} + {CTRL}", wt)
r = result_row(md, wt, "ln_distance:hi")
rows.append(dict(tercile="high - low", slope=r["beta"], SE_Kreis=r["SE_Kreis"], p_Kreis=r["p_Kreis"],
                 WCB_p_Kreis=r["WCB_p_Kreis"], WCB_p_shelter=r["WCB_p_shelter"]))
save(rows, "08e_h3_west_terciles.csv")

g = ms[ms.percentile.isna()]
fig, ax = plt.subplots(figsize=(7, 4.2))
ax.fill_between(g.foreign_share_2021, g.lo, g.hi, color="0.85", lw=0)
ax.plot(g.foreign_share_2021, g.slope, color="black", lw=1.6)
ax.axhline(0, color="0.4", lw=0.8, ls="--")
ax.set_xlabel("District foreign share, 2021 (%, INKAR)")
ax.set_ylabel("Slope of AfD share on ln(distance)")
ax2 = ax.twinx()
ax2.hist(west[MOD], bins=40, range=(grid.min(), grid.max()), color="0.6", alpha=0.35)
ax2.set_ylim(0, ax2.get_ylim()[1] * 4)
ax2.set_yticks([])
ax.set_zorder(ax2.get_zorder() + 1)
ax.patch.set_visible(False)
ax.set_title("West Germany: distance slope by district foreign share (Kreis FE)")
fig.text(0.01, -0.04, f"Kreis FE + 15 controls; 95% CI clustered by Kreis (G = {G}). Negative slope = closer "
         "to a centre, higher AfD share.\nHistogram: distribution of municipalities.", fontsize=8, ha="left")
fig.tight_layout()
for ext in ("png", "pdf"):
    fig.savefig(FIG / f"figure4_h3_west_marginal_slope.{ext}", dpi=300, bbox_inches="tight")
