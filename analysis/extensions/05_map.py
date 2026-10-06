"""Figure 0: AfD vote share 2025 by district and the 157 reception centres.
Needs data/derived/{districts_vg250,laender_vg250}.geojson, kreis_afd_2025.csv and the raw
registry data/raw/refugee_centres_raw_data_2025.xlsx (not committed)."""
import numpy as np, pandas as pd, geopandas as gpd, matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.lines import Line2D
from common import DERIVED, RAW, FIG

REG = RAW / "refugee_centres_raw_data_2025.xlsx"
if not REG.exists():
    raise SystemExit("05_map.py: registry not found in data/raw/ - skipping the map")
krs = gpd.read_file(DERIVED / "districts_vg250.geojson").to_crs("EPSG:25832")
lan = gpd.read_file(DERIVED / "laender_vg250.geojson").to_crs("EPSG:25832")
k = pd.read_csv(DERIVED / "kreis_afd_2025.csv", dtype={"Kreis_code": str})
krs = krs.merge(k, on="Kreis_code", how="left")
assert krs.afd2025_pct.notna().all()
reg = pd.read_excel(REG, "Database")
c = gpd.GeoDataFrame(reg, geometry=gpd.points_from_xy(reg.Longitude, reg.Latitude), crs="EPSG:4326").to_crs("EPSG:25832")
cls = pd.cut(c.Capacity, [0, 500, 1000, np.inf], right=False, labels=["< 500", "500–999", "≥ 1,000"])
size = {"< 500": 22, "500–999": 48, "≥ 1,000": 90}

ramp = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]   # one hue, light->dark
bounds = [5, 15, 20, 25, 30, 35, 40, 50]
cmap, norm = ListedColormap(ramp), BoundaryNorm(bounds, len(ramp))
ACC, INK, MUTED = "#e8771a", "#1f1f1e", "#6b6b68"

fig, ax = plt.subplots(figsize=(8.6, 9.0))
krs.plot(ax=ax, column="afd2025_pct", cmap=cmap, norm=norm, edgecolor="white", linewidth=0.25)
lan.boundary.plot(ax=ax, color=INK, linewidth=0.7)
for lab in size:
    s = c[cls == lab]
    ax.scatter(s.geometry.x, s.geometry.y, s=size[lab], c=ACC, edgecolor="white", linewidth=0.9, zorder=3)
s = c[c.Capacity.isna()]
ax.scatter(s.geometry.x, s.geometry.y, s=30, facecolor="white", edgecolor=ACC, linewidth=1.4, zorder=3)
ax.set_axis_off()
cb = fig.colorbar(plt.cm.ScalarMappable(cmap=cmap, norm=norm), ax=ax, fraction=0.03, pad=0.01, shrink=0.42,
                  anchor=(0, 0.92), ticks=bounds, spacing="uniform")
cb.ax.set_yticklabels([""] + [str(b) for b in bounds[1:]])
cb.set_label("AfD second-vote share 2025, % (district)", color=INK, fontsize=9)
cb.ax.tick_params(labelsize=8, colors=MUTED, length=0)
cb.outline.set_visible(False)
h = [Line2D([], [], ls="", marker="o", ms=np.sqrt(size[l]), mfc=ACC, mec="white", label=l) for l in size]
h.append(Line2D([], [], ls="", marker="o", ms=np.sqrt(30), mfc="white", mec=ACC, mew=1.4, label="capacity unknown"))
leg = ax.legend(handles=h, title=f"Reception centres (N = {len(c)}), places", loc="lower left",
                bbox_to_anchor=(0.985, 0.08), frameon=False, fontsize=8, title_fontsize=8.5, labelcolor=INK)
leg.get_title().set_color(INK)
ax.set_title("AfD vote share in the 2025 Bundestag election\nand refugee reception centres", fontsize=12, color=INK, loc="left")
fig.text(0.02, 0.015, "District results computed from GERDA municipal results (votes-weighted). Centres: hand-collected registry of "
         "initial-reception facilities\n(§44 AsylG) from the official sites of all 16 Länder, 2025. Boundaries: © GeoBasis-DE / BKG, dl-de/by-2-0.",
         fontsize=6.5, color=MUTED)
for ext in ("png", "pdf"):
    fig.savefig(FIG / f"figure0_map_afd2025_centres.{ext}", dpi=300, bbox_inches="tight", facecolor="white")
print("wrote figure0_map_afd2025_centres")
