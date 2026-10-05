"""Shared setup for the extension analyses (H3, exposure, 2013-2025 dynamics, education).

Reproduces the sample construction of analysis/refugee_centres_afd_analysis.ipynb exactly
(same file, same 15 controls, same complete-case rule -> N = 10,070) and adds:
  * wcb_fast(): the notebook's restricted wild cluster bootstrap (Rademacher, H0 imposed,
    |t*| >= |t_obs|, p = (exceed+1)/(B+1)) in closed form via Frisch-Waugh-Lovell. Signs are
    drawn in the same order as the notebook, so it reproduces all six p-values in
    outputs/07_wild_cluster_bootstrap.csv exactly, in a fraction of a second each.
  * load_panel(): baseline merged with the derived data in data/derived/.
Run scripts from the repository root or from analysis/extensions/.
"""
from pathlib import Path
import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message="invalid value encountered in sqrt")

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "shelters_non-host.xlsx"
DERIVED = ROOT / "data" / "derived"
RAW = ROOT / "data" / "raw"            # optional, only needed to rebuild data/derived
OUT = ROOT / "outputs_extensions"
FIG = OUT / "figures"
OUT.mkdir(exist_ok=True)
FIG.mkdir(exist_ok=True)

SEED = 20261002
B_BOOT = 9999

CONTROLS = [
    "ln_population_2021", "population_density_2021", "purchasing_power_pc_2021",
    "share_65plus_2021", "female_share_2021", "net_migration_rate_2021",
    "urban_dummy", "suburban_dummy", "foreign_share_zensus2022",
    "immig_history_share_zensus2022", "immigrated_share_zensus2022",
    "share_60plus_zensus2022", "female_share_zensus2022", "zensus_population_2022",
    "turnout_2021_pct",
]
CTRL = " + ".join(CONTROLS)
# Zensus 2022 education/employment (municipality -> Gemeindeverband -> Kreis fill) + fill-level dummies
EDU = "abitur_share_z22 + novoc_share_z22 + unemp_rate_z22 + edu_lvl_gv + edu_lvl_kr"
LAND_FE, KREIS_FE = "C(State_code)", "C(Kreis_code)"
KREIS_CONSTANT = {"foreign_share_2021", "unemployment_rate_2021", "tertiary_education_share_2022"}


def load_baseline():
    df = pd.read_excel(DATA, sheet_name=0, dtype={"AGS8": str})
    for c in ["State_code", "Kreis_code", "nearest_shelter_id"]:
        df[c] = df[c].astype("string")
    if (df["n_shelters_in_municipality"].fillna(0) > 0).any():
        raise ValueError("expected a non-host sample")
    df["ln_distance"] = np.log(df["distance_nearest_shelter_km"])
    df["ln_population_2021"] = np.log(df["population_2021"])
    need = ["afd_share_2025_pct", "ln_distance", "State_code", "Kreis_code", "nearest_shelter_id"] + CONTROLS
    base = df.dropna(subset=need).copy()
    assert len(base) == 10_070, len(base)
    return base


def load_panel(require_years=True, require_edu=False):
    """Baseline + AfD 2013-2025 (GERDA) + exposure measures + Zensus 2022 education."""
    base = load_baseline()
    idx = base.index
    g = pd.read_csv(DERIVED / "gerda_afd_2013_2025.csv", dtype={"AGS8": str})
    ex = pd.read_csv(DERIVED / "exposure_measures.csv", dtype={"AGS8": str})
    ed = pd.read_csv(DERIVED / "education_zensus2022.csv", dtype={"AGS8": str})
    p = (base.reset_index().merge(g, on="AGS8", how="left").merge(ex, on="AGS8", how="left")
             .merge(ed, on="AGS8", how="left").set_index("index"))
    assert p.index.equals(idx)
    p["edu_lvl_gv"] = (p["abitur_share_lvl"] == "Gemeindeverband").astype(int)
    p["edu_lvl_kr"] = (p["abitur_share_lvl"] == "Kreis").astype(int)
    if require_years:
        p = p.dropna(subset=[f"afd{y}" for y in (2013, 2017, 2021, 2025)])
    if require_edu:
        p = p.dropna(subset=["abitur_share_z22", "novoc_share_z22", "unemp_rate_z22"])
    return p


def split(d):
    west = d[d["east_dummy"] == 0].copy()
    east = d[d["east_dummy"] == 1].copy()
    east_no_mv = east[east["State_code"].str.zfill(2) != "13"].copy()
    return west, east, east_no_mv


def with_z(d, var, name="Z"):
    d = d.copy()
    d[name] = (d[var] - d[var].mean()) / d[var].std()
    return d


def fit(formula, data, weights=None):
    if weights is None:
        return smf.ols(formula, data=data).fit()
    return smf.wls(formula, data=data, weights=data[weights]).fit()


def cluster_result(model, data, cluster):
    groups = data.loc[model.model.data.row_labels, cluster]
    return model.get_robustcov_results(cov_type="cluster", groups=groups), groups


def cluster_stats(model, data, cluster, term):
    r, groups = cluster_result(model, data, cluster)
    j = list(model.params.index).index(term)
    return float(r.bse[j]), float(r.pvalues[j]), int(groups.nunique())


def check_rank(model):
    X = model.model.exog
    assert np.linalg.matrix_rank(X) == X.shape[1], "rank-deficient design matrix"


def _resid_on(X0, V):
    coef, *_ = np.linalg.lstsq(X0, V, rcond=None)
    return V - X0 @ coef


def wcb_fast(model, data, term, cluster, B=B_BOOT, seed=SEED, chunk=2000):
    used = model.model.data.row_labels
    groups = data.loc[used, cluster].astype(str).to_numpy()
    _, g = np.unique(groups, return_inverse=True)
    G = g.max() + 1
    X = np.asarray(model.model.exog, float)
    y = np.asarray(model.model.endog, float)
    j = list(model.model.exog_names).index(term)
    X0 = np.delete(X, j, axis=1)
    xt = _resid_on(X0, X[:, j])
    D = xt @ xt
    r = _resid_on(X0, y)                                  # restricted residuals (H0 imposed)
    b_obs = (xt @ r) / D
    S_obs = np.bincount(g, weights=xt * (r - xt * b_obs), minlength=G)
    t_obs = b_obs / np.sqrt((S_obs ** 2).sum()) * D
    a = np.bincount(g, weights=xt * r, minlength=G)
    w = np.bincount(g, weights=xt * xt, minlength=G)
    R = np.zeros((len(y), G))
    R[np.arange(len(y)), g] = r
    PR = R - _resid_on(X0, R)
    Q = np.zeros((G, G))
    np.add.at(Q, g, xt[:, None] * PR)
    rng = np.random.default_rng(seed)
    signs = np.stack([rng.choice([-1.0, 1.0], size=G) for _ in range(B)])
    exceed = 0
    for k in range(0, B, chunk):
        s = signs[k:k + chunk]
        bs = (s @ a) / D
        S = s * a - s @ Q.T - bs[:, None] * w
        exceed += int((np.abs(bs / np.sqrt((S ** 2).sum(1)) * D) >= abs(t_obs)).sum())
    return (exceed + 1) / (B + 1)


def result_row(model, data, term, /, bootstrap=True, **meta):
    """Coefficient with Kreis- and centre-clustered SE/p and (optionally) WCB p-values."""
    check_rank(model)
    out = dict(meta, N=int(model.nobs), beta=float(model.params[term]))
    for cl, tag in [("Kreis_code", "Kreis"), ("nearest_shelter_id", "shelter")]:
        se, p, G = cluster_stats(model, data, cl, term)
        out.update({f"SE_{tag}": se, f"p_{tag}": p, f"G_{tag}": G})
        if bootstrap:
            out[f"WCB_p_{tag}"] = wcb_fast(model, data, term, cl)
    return out


def save(rows, name):
    t = pd.DataFrame(rows)
    t.to_csv(OUT / name, index=False)
    print(f"wrote outputs_extensions/{name} ({len(t)} rows)")
    return t
