"""Key results with Zensus 2022 education and unemployment added to the 15 controls.

Zensus 2022 education results are sample-based and suppressed for small municipalities, so each
municipality gets its own value where published, else its Gemeindeverband's, else its Kreis's
(abitur/novoc/unemp: 14.6% / 42.9% / 42.4% of municipalities; 67% / 12% / 21% of population).
Fill-level dummies are included. Tertiary-degree shares are suppressed almost everywhere
(86% Kreis-only) and are not used.
  13_education_controls.csv     main comparison: 15 controls vs + education/unemployment
  13b_education_robustness.csv  one variable at a time; sample with sub-Kreis measures only
Caveat: measured in 2022, i.e. after the 2013->2017 change.
"""
from common import load_panel, split, with_z, fit, result_row, save, CTRL, EDU, LAND_FE, KREIS_FE

B = load_panel(require_years=True, require_edu=True)
W, E, EN = split(B)
W = with_z(W, "foreign_share_2021")
H3 = " + ln_distance:Z"
SPECS = [
    ("2025 level", "Germany", B, "ln_distance", LAND_FE, "afd2025", ""),
    ("2025 level", "Germany", B, "ln_distance", KREIS_FE, "afd2025", ""),
    ("2025 level", "West", W, "ln_distance", LAND_FE, "afd2025", ""),
    ("2025 level", "West", W, "ln_distance", KREIS_FE, "afd2025", ""),
    ("2025 level", "East", E, "ln_distance", LAND_FE, "afd2025", ""),
    ("2025 level", "East", E, "ln_distance", KREIS_FE, "afd2025", ""),
    ("H3 2025 level", "West", W, "ln_distance:Z", KREIS_FE, "afd2025", H3),
    ("H3 change 2013-17", "West", W, "ln_distance:Z", KREIS_FE, "I(afd2017-afd2013)", H3),
    ("H3 change 2013-25", "West", W, "ln_distance:Z", KREIS_FE, "I(afd2025-afd2013)", H3),
    ("H1 change 2013-17", "West", W, "ln_distance", LAND_FE, "I(afd2017-afd2013)", ""),
    ("H1 change 2013-17", "West", W, "ln_distance", KREIS_FE, "I(afd2017-afd2013)", ""),
    ("East change 2013-17", "East", E, "ln_distance", LAND_FE, "I(afd2017-afd2013)", ""),
    ("East change 2013-17", "East excl. MV", EN, "ln_distance", LAND_FE, "I(afd2017-afd2013)", ""),
    ("East change 2013-17", "East", E, "ln_distance", KREIS_FE, "I(afd2017-afd2013)", ""),
]
rows = []
for lab, sn, d, term, fe, y, extra in SPECS:
    for clab, ctrl in [("15 controls", CTRL), ("+ education/unemployment (Zensus 2022)", CTRL + " + " + EDU)]:
        m = fit(f"{y} ~ ln_distance{extra} + {fe} + {ctrl}", d)
        r = result_row(m, d, term, result=lab, sample=sn, FE="Land FE" if fe == LAND_FE else "Kreis FE", controls=clab)
        r.update(b_abitur=m.params.get("abitur_share_z22"), b_novoc=m.params.get("novoc_share_z22"),
                 b_unemp=m.params.get("unemp_rate_z22"))
        rows.append(r)
save(rows, "13_education_controls.csv")

KEY = [("West 2025 level H1", "Land FE", W, "ln_distance", LAND_FE, "afd2025", ""),
       ("West H1 change 2013-17", "Land FE", W, "ln_distance", LAND_FE, "I(afd2017-afd2013)", ""),
       ("West H1 change 2013-17", "Kreis FE", W, "ln_distance", KREIS_FE, "I(afd2017-afd2013)", ""),
       ("West H3 change 2013-25", "Kreis FE", W, "ln_distance:Z", KREIS_FE, "I(afd2025-afd2013)", H3),
       ("East change 2013-17", "Land FE", E, "ln_distance", LAND_FE, "I(afd2017-afd2013)", "")]
VAR = {"Abitur only": "abitur_share_z22 + edu_lvl_gv + edu_lvl_kr",
       "No-vocational only": "novoc_share_z22 + edu_lvl_gv + edu_lvl_kr",
       "Unemployment only": "unemp_rate_z22 + edu_lvl_gv + edu_lvl_kr",
       "All three, no level dummies": "abitur_share_z22 + novoc_share_z22 + unemp_rate_z22",
       "All three (main)": EDU}
rows = []
for lab, fen, d, term, fe, y, extra in KEY:
    for vl, v in VAR.items():
        samples = [("all", d)] + ([("sub-Kreis measure only", d[d.abitur_share_lvl != "Kreis"])]
                                  if vl == "All three (main)" else [])
        for samp, dd in samples:
            dd = with_z(dd, "foreign_share_2021") if extra else dd
            v2 = v if samp == "all" else v.replace(" + edu_lvl_kr", "")
            m = fit(f"{y} ~ ln_distance{extra} + {fe} + {CTRL} + {v2}", dd)
            rows.append(result_row(m, dd, term, result=lab, FE=fen, variant=vl, sample=samp))
save(rows, "13b_education_robustness.csv")
