"""Alternative exposure measures from the full registry (2025 levels).

  n_centres_25km / n_centres_50km   number of centres within the radius
  ln_cap25 / ln_cap50               log(1 + total capacity within the radius)
  inv_dist_sum                      sum over all 157 centres of 1/distance
  ln_distance x capacity            moderation by (z-scored log) capacity of the nearest centre
Germany / West / East x Land FE / Kreis FE, 15 controls. 36 tests in total; read together with
the 2013 placebo in 03_dynamics (the West density association is already present in 2013).
Output: 09_extra_exposure_all_tests.csv
"""
import numpy as np
from common import load_panel, split, fit, result_row, save, CTRL, LAND_FE, KREIS_FE

B = load_panel(require_years=False)
B["ln_capacity_nearest"] = np.log(B.nearest_shelter_capacity)
W, E, _ = split(B)
EXPO = ["n_centres_25km", "n_centres_50km", "ln_cap25", "ln_cap50", "inv_dist_sum"]
rows = []
for sn, s in {"Germany": B, "West": W, "East": E}.items():
    for fn, fe in {"Land FE": LAND_FE, "Kreis FE": KREIS_FE}.items():
        for v in EXPO:
            m = fit(f"afd_share_2025_pct ~ {v} + {fe} + {CTRL}", s)
            rows.append(result_row(m, s, v, analysis="exposure", variable=v, sample=sn, model=fn))
        d = s.dropna(subset=["ln_capacity_nearest"]).copy()
        d["Zc"] = (d.ln_capacity_nearest - d.ln_capacity_nearest.mean()) / d.ln_capacity_nearest.std()
        m = fit(f"afd_share_2025_pct ~ ln_distance * Zc + {fe} + {CTRL}", d)
        rows.append(result_row(m, d, "ln_distance", analysis="capacity moderation",
                               variable="ln_distance (at mean capacity)", sample=sn, model=fn))
        rows.append(result_row(m, d, "ln_distance:Zc", analysis="capacity moderation",
                               variable="ln_distance x capacity", sample=sn, model=fn))
save(rows, "09_extra_exposure_all_tests.csv")
