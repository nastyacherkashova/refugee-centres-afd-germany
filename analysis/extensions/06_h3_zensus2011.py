"""H3 with pre-crisis diversity: foreign share from Zensus 2011 (09.05.2011), mapped to 2021
boundaries. Answers the objection that INKAR 2021 / Zensus 2022 diversity is measured after the
2015-16 arrivals. Moderators (z-scored within sample):
  kreis_foreign_share_z2011   district share, computed from all municipalities of the Kreis
  foreign_share_z2011         municipal share (varies within Kreis)
  foreign_share_2021          district share, INKAR 2021 (main specification, for comparison)
Kreis FE, constant 2013-2025 sample, with and without Zensus 2022 education controls.
Outputs: 14_h3_zensus2011_moderator.csv
         14b_zensus2011_dash_sensitivity.csv  ("-" = 0 / 1 / 2, or municipalities with "-" dropped;
                                               West, Kreis FE, with education controls)
"""
import pandas as pd
from common import load_panel, split, with_z, fit, result_row, save, CTRL, EDU, KREIS_FE, DERIVED

z = pd.read_csv(DERIVED / "zensus2011_foreign.csv", dtype={"AGS8": str})
kd = z.assign(Kreis_code=z.AGS8.str[:5]).groupby("Kreis_code")[["foreign2011_z11", "pop2011_z11"]].sum()
kshare = 100 * kd.foreign2011_z11 / kd.pop2011_z11
B = load_panel(require_years=True, require_edu=True)
B = B.reset_index().merge(z, on="AGS8", how="left").set_index("index").dropna(subset=["foreign_share_z2011"])
B["kreis_foreign_share_z2011"] = B.Kreis_code.str.zfill(5).map(kshare)
W, E, _ = split(B)
MODS = {"kreis_foreign_share_z2011": "District foreign share, Zensus 2011",
        "foreign_share_z2011": "Municipal foreign share, Zensus 2011",
        "foreign_share_2021": "District foreign share, INKAR 2021 (main)"}
OUTS = {"afd2013": "Level 2013 (placebo)", "afd2017": "Level 2017", "afd2025": "Level 2025",
        "I(afd2017-afd2013)": "Change 2013-17", "I(afd2025-afd2013)": "Change 2013-25"}
rows = []
for sn, S in [("West", W), ("East", E)]:
    for mod, mlab in MODS.items():
        d = with_z(S, mod)
        # the municipal 2011 share varies within Kreis, so its main effect stays in the model
        core = "ln_distance * Z" if mod == "foreign_share_z2011" else "ln_distance + ln_distance:Z"
        for y, ylab in OUTS.items():
            for clab, ctrl in [("15 controls", CTRL), ("+ education", CTRL + " + " + EDU)]:
                m = fit(f"{y} ~ {core} + {KREIS_FE} + {ctrl}", d)
                rows.append(result_row(m, d, "ln_distance:Z", sample=sn, moderator=mlab, outcome=ylab, controls=clab))
save(rows, "14_h3_zensus2011_moderator.csv")

# --- sensitivity to cells published as "-" (SAFE turns counts of 1-2 into 0 or 3) ------------
def shares(dash_value, drop=False):
    o = z.set_index("AGS8")
    f = o.foreign2011_z11 + dash_value * o.dash_w_z11
    muni = (100 * f / o.pop2011_z11).where(~(drop & (o.dash_w_z11 > 0)))
    k = pd.DataFrame({"f": f, "p": o.pop2011_z11}).groupby(o.index.str[:5]).sum()
    return pd.DataFrame({"muni": muni, "kreis": o.index.str[:5].map(100 * k.f / k.p)}, index=o.index)

VARIANTS = {"'-' = 0 (official: nichts vorhanden)": (0, False), "'-' = 1": (1, False),
            "'-' = 2 (upper bound under SAFE)": (2, False), "drop municipalities with '-'": (0, True)}
SENS_OUT = {"afd2013": "2013 placebo", "I(afd2017-afd2013)": "Change 2013-17", "I(afd2025-afd2013)": "Change 2013-25"}
rows = []
for vl, (v, dr) in VARIANTS.items():
    d0 = W.drop(columns=["foreign_share_z2011", "kreis_foreign_share_z2011"]).join(shares(v, dr), on="AGS8")
    for mod, core, mlab in [("kreis", "ln_distance + ln_distance:Z", "District 2011"),
                            ("muni", "ln_distance * Z", "Municipal 2011")]:
        d = with_z(d0.dropna(subset=[mod]), mod)
        for y, ylab in SENS_OUT.items():
            m = fit(f"{y} ~ {core} + {KREIS_FE} + {CTRL} + {EDU}", d)
            rows.append(result_row(m, d, "ln_distance:Z", variant=vl, moderator=mlab, outcome=ylab))
save(rows, "14b_zensus2011_dash_sensitivity.csv")
