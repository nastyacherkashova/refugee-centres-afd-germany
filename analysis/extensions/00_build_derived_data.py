"""Rebuild data/derived/*.csv from the raw sources (only needed if you want to rebuild them;
the derived files are committed). Put the raw files in data/raw/:

  federal_muni_harm_21.xlsx                    GERDA, federal elections at municipality level,
                                               harmonised to 2021 boundaries (1990-2025)
  Regionaltabelle_Bildung_Erwerbstaetigkeit.xlsx  Zensus 2022 Regionaltabelle "Bildung und
                                               Erwerbstaetigkeit" (Destatis, dl-de/by-2-0)
  refugee_centres_raw_data_2025.xlsx           hand-collected registry of 157 reception centres
                                               (sheet "Database")
Any file that is missing is skipped and the committed derived file is kept.
"""
import numpy as np
import pandas as pd
from common import RAW, DERIVED, DATA

DERIVED.mkdir(exist_ok=True)
num = lambda s: pd.to_numeric(s.replace("/", np.nan), errors="coerce")

# --- 1. GERDA: AfD (and NPD 2013) shares, 2013-2025, percent --------------------------------
f = RAW / "federal_muni_harm_21.xlsx"
if f.exists():
    g = pd.read_excel(f)
    g = g[g.election_year.isin([2013, 2017, 2021, 2025])]
    g["AGS8"] = g.ags.astype(int).astype(str).str.zfill(8)
    w = g.pivot_table(index="AGS8", columns="election_year", values="afd", aggfunc="first") * 100
    w.columns = [f"afd{y}" for y in w.columns]
    w["npd2013"] = 100 * g[g.election_year == 2013].set_index("AGS8").npd
    w.reset_index().to_csv(DERIVED / "gerda_afd_2013_2025.csv", index=False)
    print("gerda_afd_2013_2025.csv:", len(w))

# --- 2. Zensus 2022 education / employment --------------------------------------------------
f = RAW / "Regionaltabelle_Bildung_Erwerbstaetigkeit.xlsx"
if f.exists():
    width = {"Gemeinde": 12, "Gemeindeverband": 9, "Stadtkreis/kreisfreie Stadt/Landkreis": 5}

    def sheet(name):
        d = pd.read_excel(f, name, dtype={"_RS": str})
        d = d[d.Regionalebene.isin(width)].copy()
        d.index = [r.zfill(width[l]) for r, l in zip(d._RS, d.Regionalebene)]
        return d

    S, B, E = (sheet(s) for s in ["CSV-Hoechster_Schulabschluss", "CSV-Hoechster_berufl_Abschluss",
                                  "CSV-Erwerbsstatus"])
    measures = {
        # Abitur among persons 15+ who are no longer in school
        "abitur_share": 100 * num(S.SCHULABS_STP__24) / (num(S.SCHULABS_STP) - num(S.SCHULABS_STP__1)),
        # no vocational qualification among persons 15+
        "novoc_share": 100 * num(B.BERUFABS_AUSF_STP__2) / num(B.BERUFABS_AUSF_STP),
        # Erwerbslose / Erwerbspersonen
        "unemp_rate": 100 * num(E.ERWERBSTAT_KURZ_STP__12) / num(E.ERWERBSTAT_KURZ_STP__1),
    }
    ars = [k for k, l in B.Regionalebene.items() if l == "Gemeinde"]
    out = pd.DataFrame({"ARS": ars})
    out["AGS8"] = out.ARS.str[:5] + out.ARS.str[9:]
    for name, v in measures.items():
        gm, gv, kr = (v.reindex(out.ARS.str[:n]).values for n in (12, 9, 5))
        out[f"{name}_z22"] = np.where(~np.isnan(gm), gm, np.where(~np.isnan(gv), gv, kr))
        out[f"{name}_lvl"] = np.where(~np.isnan(gm), "Gemeinde",
                                      np.where(~np.isnan(gv), "Gemeindeverband", "Kreis"))
    out.drop(columns="ARS").to_csv(DERIVED / "education_zensus2022.csv", index=False)
    print("education_zensus2022.csv:", len(out), out.abitur_share_lvl.value_counts().to_dict())

# --- 3. Exposure measures from the full registry ------------------------------------------
f = RAW / "refugee_centres_raw_data_2025.xlsx"
if f.exists():
    reg = pd.read_excel(f, "Database")
    m = pd.read_excel(DATA, dtype={"AGS8": str})
    lat1, lon1 = np.radians(m.bkg_rep_lat.values)[:, None], np.radians(m.bkg_rep_lon.values)[:, None]
    lat2, lon2 = np.radians(reg.Latitude.values)[None, :], np.radians(reg.Longitude.values)[None, :]
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    D = 2 * 6371.0088 * np.arcsin(np.sqrt(a))
    assert np.abs(D.min(1) - m.distance_nearest_shelter_km.values).max() < 1e-6, "registry/distance mismatch"
    cap = reg.Capacity.values.astype(float)
    out = pd.DataFrame({"AGS8": m.AGS8})
    for r in (25, 50):
        W = D <= r
        out[f"n_centres_{r}km"] = W.sum(1)
        out[f"capacity_{r}km"] = np.where(W, np.nan_to_num(cap), 0).sum(1)
        out[f"ln_cap{r}"] = np.log1p(out[f"capacity_{r}km"])
        out[f"capacity_{r}km_missing"] = (W & np.isnan(cap)[None, :]).sum(1)
    out["inv_dist_sum"] = (1 / D).sum(1)
    out.to_csv(DERIVED / "exposure_measures.csv", index=False)
    print("exposure_measures.csv:", len(out))

# --- 4. District AfD result 2025 (votes-weighted, all municipalities incl. hosts) -----------
f = RAW / "federal_muni_harm_21.xlsx"
if f.exists():
    g25 = pd.read_excel(f).query("election_year == 2025").copy()
    g25["Kreis_code"] = g25.county.astype(int).astype(str).str.zfill(5)
    g25["afd_votes"] = g25.afd * g25.valid_votes
    k = g25.groupby("Kreis_code")[["afd_votes", "valid_votes"]].sum()
    k["afd2025_pct"] = 100 * k.afd_votes / k.valid_votes
    k[["afd2025_pct"]].reset_index().to_csv(DERIVED / "kreis_afd_2025.csv", index=False)
    print("kreis_afd_2025.csv:", len(k))

# --- 5. District and Land boundaries from BKG VG250 municipalities -------------------------
# Source: vg250.rda from the R package github.com/dimfalk/vg250 (data (c) GeoBasis-DE / BKG,
# dl-de/by-2-0). Municipality polygons carry names only, so each polygon gets the Kreis code of
# the sample municipality whose representative point lies inside it; host municipalities are
# matched by name+Land to GERDA; the remaining unpopulated areas (<= 110 inhabitants) take the
# Kreis of the neighbour sharing the longest border.
f, fg = RAW / "vg250.rda", RAW / "federal_muni_harm_21.xlsx"
if f.exists() and fg.exists():
    import rdata, warnings
    import geopandas as gpd
    from shapely.geometry import Polygon, MultiPolygon
    warnings.filterwarnings("ignore")
    v = rdata.conversion.convert(rdata.parser.parse_file(f))["vg250"]
    poly = lambda rings: Polygon(np.asarray(rings[0]), [np.asarray(r) for r in rings[1:]])
    geom = [poly(x) if isinstance(x[0], np.ndarray) else MultiPolygon([poly(p) for p in x]) for x in v.geom]
    gem = gpd.GeoDataFrame(v.drop(columns="geom"), geometry=geom, crs="EPSG:4326").reset_index(drop=True)
    gem["geometry"] = gem.geometry.make_valid()
    m = pd.read_excel(DATA, dtype={"AGS8": str, "Kreis_code": str})
    pts = gpd.GeoDataFrame(m[["Kreis_code"]], geometry=gpd.points_from_xy(m.bkg_rep_lon, m.bkg_rep_lat), crs="EPSG:4326")
    j = gpd.sjoin(pts, gem[["geometry"]], how="inner", predicate="within")
    gem["Kreis_code"] = j.assign(Kreis_code=j.Kreis_code.str.zfill(5)).groupby("index_right").Kreis_code.first()
    gg = pd.read_excel(fg).query("election_year == 2025")
    gg["state_name"] = gg.state_name.replace({"Bavaria": "Bayern", "Hesse": "Hessen",
        "North Rhine-Westphalia": "Nordrhein-Westfalen", "Rhineland-Palatinate": "Rheinland-Pfalz",
        "Saxony": "Sachsen", "Saxony-Anhalt": "Sachsen-Anhalt", "Thuringia": "Thüringen"})
    gg["nm"] = gg.ags_name.str.split(",").str[0].str.strip().str.lower()
    gg["county"] = gg.county.astype(int).astype(str).str.zfill(5)
    uniq = gg.groupby(["state_name", "nm"]).county.agg(lambda s: s.iloc[0] if s.nunique() == 1 else None).dropna()
    miss = gem.Kreis_code.isna()
    gem.loc[miss, "Kreis_code"] = [uniq.get((l, n.split(",")[0].strip().lower()))
                                   for l, n in zip(gem.loc[miss, "LAN"], gem.loc[miss, "GEM"])]
    gem.loc[gem.GEM.eq("Oldenburg (Oldb)") & gem.LAN.eq("Niedersachsen"), "Kreis_code"] = "03403"
    coded = gem[gem.Kreis_code.notna()]
    for i, r in gem[gem.Kreis_code.isna()].iterrows():
        nb = coded[coded.intersects(r.geometry.buffer(0.001))]
        if len(nb):
            gem.at[i, "Kreis_code"] = nb.assign(l=nb.intersection(r.geometry.buffer(0.001)).area).sort_values("l").Kreis_code.iloc[-1]
    gem = gem.dropna(subset=["Kreis_code"]).to_crs("EPSG:25832")
    assert gem.Kreis_code.nunique() == 400
    for name, by in [("districts_vg250.geojson", "Kreis_code"), ("laender_vg250.geojson", "LAN")]:
        shp = gem.dissolve(by, as_index=False)[[by, "geometry"]]
        shp["geometry"] = shp.geometry.simplify(150)          # metres; enough for a national map
        shp.to_crs("EPSG:4326").to_file(DERIVED / name, driver="GeoJSON")
        print(name, len(shp))

# --- 6. Zensus 2011 foreign population, mapped to 2021 municipal boundaries -----------------
# Raw: data/raw/1000X-1015_de.xlsx (Zensusdatenbank table 1000X-1015 "Personen:
# Staatsangehoerigkeit", Gemeinden, Gebietsstand 09.05.2011) and data/raw/ags_crosswalks.csv
# (GERDA / BBSR municipal crosswalks to 2021 boundaries with population weights,
# github.com/awiedem/german_election_data, data/crosswalks/final/). Each 2011 municipality is
# matched to the crosswalk year (31.12.2010 or 31.12.2011) whose population fits best
# (Mecklenburg-Vorpommern changed all codes in its September 2011 district reform), then counts
# are allocated to 2021 municipalities with the population weights.
# "-" in the Zensus tables means "nichts vorhanden" (zero). Because the SAFE confidentiality method
# turns original counts of 1-2 into 0 or 3, dash_w_z11 keeps the crosswalk weight of all 2011
# components published as "-", so 06_h3_zensus2011.py can re-estimate with "-" = 1 or 2.
f, fc = RAW / "1000X-1015_de.xlsx", RAW / "ags_crosswalks.csv"
if f.exists() and fc.exists():
    d = pd.read_excel(f, header=None)
    r = d[(d[3] == "Anzahl") & d[0].astype(str).str.fullmatch(r"\d{12}")]
    cnt = lambda s: pd.to_numeric(s.astype(str).str.replace(".", "", regex=False).replace({"-": "0"}), errors="coerce")
    z = pd.DataFrame({"ARS": r[0].astype(str).values, "pop2011": cnt(r[4]).values, "foreign2011": cnt(r[6]).values,
                      "is_dash": r[6].astype(str).eq("-").values})
    z["AGS8"] = z.ARS.str[:5] + z.ARS.str[9:]
    cw = pd.read_csv(fc, dtype={"ags": str, "ags_21": str})
    cw = cw[cw.year.isin([2010, 2011])].assign(ags=lambda c: c.ags.str.zfill(8), ags_21=lambda c: c.ags_21.str.zfill(8))
    cand = []
    for y in (2011, 2010):
        pop = cw[cw.year == y].groupby("ags").population.first() * 1000
        cand.append(z[["AGS8", "pop2011"]].assign(year=y, cwpop=z.AGS8.map(pop)))
    cand = pd.concat(cand).dropna(subset=["cwpop"])
    cand["dev"] = np.abs(np.log(cand.pop2011 / cand.cwpop))
    pick = cand.sort_values("dev").drop_duplicates("AGS8")[["AGS8", "year"]]
    assert len(pick) == len(z), "unmatched 2011 municipalities"
    j = z.merge(pick, on="AGS8").merge(cw[["ags", "year", "pop_cw", "ags_21"]], left_on=["AGS8", "year"], right_on=["ags", "year"])
    j["pop2011_z11"], j["foreign2011_z11"] = j.pop2011 * j.pop_cw, j.foreign2011 * j.pop_cw
    j["dash_w_z11"] = j.is_dash * j.pop_cw
    out = j.groupby("ags_21")[["pop2011_z11", "foreign2011_z11", "dash_w_z11"]].sum()
    assert abs(out.pop2011_z11.sum() - z.pop2011.sum()) < 1
    out["foreign_share_z2011"] = 100 * out.foreign2011_z11 / out.pop2011_z11
    out.rename_axis("AGS8").reset_index().to_csv(DERIVED / "zensus2011_foreign.csv", index=False)
    print("zensus2011_foreign.csv:", len(out))
