
# Refugee Reception Centres and AfD Voting in Germany

This repository contains the data, analysis code, and generated outputs
for a municipality-level study of the association between proximity to
refugee reception centres and AfD second-vote share in the 2025 German
federal election.

## Repository structure

``` text
.
├── analysis/
│   └── refugee_centres_afd_analysis.ipynb
├── data/
│   └── shelters_non-host.xlsx
└── outputs/
    ├── 00_run_manifest.csv
    ├── 01_descriptives_east_west.csv
    ├── 02_specification_ladder.csv
    ├── 03_main_models_by_region.csv
    ├── 04_east_distance_bins.csv
    ├── 04b_east_bin_joint_tests.csv
    ├── 05_final_robustness.csv
    ├── 06_east_leave_one_cluster_out.csv
    ├── 07_wild_cluster_bootstrap.csv
    ├── 99_output_inventory.csv
    ├── 99_reproducibility_checks.csv
    └── figures/
```

## Data

The unit of analysis is the German municipality.

The final analysis dataset is `data/shelters_non-host.xlsx`.
Municipalities that contain a refugee reception centre are excluded from
the analytical sample.

The dataset combines information on:

-   2025 Bundestag election results at the municipality level;
-   distance to the nearest refugee reception centre;
-   municipality characteristics and socioeconomic controls;
-   urbanity and regional classifications;
-   Land and Kreis identifiers.

The refugee-centre data are based on a manually compiled registry of
state-run primary reception facilities. Distance is measured as
straight-line distance from the municipality representative point to the
nearest facility.

The main dependent variable is:

`afd_share_2025_pct` --- AfD second-vote share in the 2025 Bundestag
election.

The main exposure is:

`ln_distance = log(distance_nearest_shelter_km)`

## Analysis

The notebook estimates a sequence of specifications designed to examine
how the municipality-level distance--vote association changes after
accounting for regional geography and municipality characteristics.

The main analyses include:

-   a constant-sample specification ladder;
-   Land fixed-effects models;
-   Kreis fixed-effects models;
-   separate analyses for East and West Germany;
-   categorical distance specifications;
-   robustness checks;
-   leave-one-cluster-out analyses;
-   wild cluster bootstrap inference using both nearest-shelter and
    Kreis clusters.

For the regional analysis, East Germany refers to the five eastern
Länder excluding Berlin.

The main complete-case estimation sample contains 10,070 municipalities.

## Reproducing the analysis

The repository is organized so that the notebook can be run from the
`analysis/` directory.

1.  Open `analysis/refugee_centres_afd_analysis.ipynb`.
2.  Run all cells in order.
3.  The notebook reads the dataset from
    `../data/shelters_non-host.xlsx`.
4.  Generated tables and figures are written to `../outputs/`.

A full reproduction uses 9,999 wild-cluster-bootstrap replications and
therefore takes longer than the standard regression sections.

The notebook uses a fixed random seed for reproducibility.

## Outputs

`outputs/02_specification_ladder.csv` contains the main specification
sequence.

`outputs/03_main_models_by_region.csv` contains the Germany, West, and
East models.

`outputs/04_east_distance_bins.csv` and
`outputs/04b_east_bin_joint_tests.csv` contain the categorical distance
analysis and associated joint tests.

`outputs/05_final_robustness.csv` contains the main robustness
specifications.

`outputs/06_east_leave_one_cluster_out.csv` contains the
leave-one-cluster-out analysis.

`outputs/07_wild_cluster_bootstrap.csv` contains wild cluster bootstrap
inference.

The `outputs/figures/` directory contains the figures generated directly
by the analysis notebook.

`00_run_manifest.csv`, `99_output_inventory.csv`, and
`99_reproducibility_checks.csv` provide information for checking the
reproducibility of a complete run.

## Interpretation

The raw municipality-level association between distance to the nearest
reception centre and AfD vote share attenuates substantially after
accounting for regional geography and municipality characteristics. In
pooled specifications, the conditional association is close to zero.

A positive association remains in East Germany in specifications with
Land fixed effects, but it is sensitive to the exclusion of
Mecklenburg-Vorpommern and disappears when comparisons are made within
Kreis. The categorical specifications provide evidence of differences
between municipalities very close to reception centres and
municipalities farther away in the full East sample, but they do not
establish a monotonic distance gradient.

These results are descriptive associations and should not be interpreted
as evidence that proximity to a reception centre causes changes in AfD
voting.

## Notes

Some controls are highly collinear and their individual coefficients are
not interpreted substantively. The 2022 Census controls also require
caution with respect to temporal ordering. Kreis fixed-effects
specifications contain singleton Kreise and are used primarily to assess
within-Kreis variation in the main distance coefficient.

## Extensions (H3, dynamics 2013–2025, education)

`analysis/extensions/` adds analyses that are run as plain Python scripts, so a `Run All` of the
notebook (which rebuilds `outputs/` from scratch) never deletes them. Results go to
`outputs_extensions/`.

``` text
analysis/extensions/
├── common.py                    sample construction identical to the notebook (N = 10,070),
│                                cluster SEs, fast exact wild cluster bootstrap
├── 00_build_derived_data.py     rebuilds data/derived/ from data/raw/ (optional)
├── 01_h3_moderation.py          H3: distance × ethnic diversity              -> 08–08e, figure 4
├── 02_exposure_capacity.py      centres/capacity within 25/50 km, capacity moderation -> 09
├── 03_dynamics_2013_2025.py     GERDA 2013–2025: placebo, changes, profile   -> 10–12, figure 5
├── 04_education_controls.py     + Zensus 2022 education & unemployment       -> 13, 13b
├── 05_map.py                    map of AfD 2025 by district and the centres -> figure 0
└── run_all.py
data/derived/                    inputs used by the scripts (committed)
outputs_extensions/              tables 08–13b and figures 0, 4, 5
```

Run `python analysis/extensions/run_all.py` (about 5 minutes). Wild cluster bootstrap p-values use
the notebook's algorithm and seed (restricted, Rademacher, 9,999 replications); `wcb_fast()`
computes it in closed form and reproduces all six p-values of `outputs/07_wild_cluster_bootstrap.csv`
exactly. Every model is checked for a full-rank design matrix.

**Derived data** (`data/derived/`)

| file | content | source |
|---|---|---|
| `gerda_afd_2013_2025.csv` | AfD second-vote share 2013, 2017, 2021, 2025 and NPD 2013, % | GERDA, federal elections, municipalities harmonised to 2021 boundaries |
| `education_zensus2022.csv` | share with Abitur, share without vocational qualification, unemployment rate; plus the level each value comes from | Zensus 2022 Regionaltabelle "Bildung und Erwerbstätigkeit" (Destatis, dl-de/by-2-0) |
| `exposure_measures.csv` | centres and capacity within 25/50 km, Σ 1/distance | registry of 157 centres |
| `kreis_afd_2025.csv` | district AfD result 2025 (votes-weighted, all municipalities) | GERDA |
| `districts_vg250.geojson`, `laender_vg250.geojson` | simplified boundaries | © GeoBasis-DE / BKG (VG250), dl-de/by-2-0, via github.com/dimfalk/vg250 |

Zensus 2022 education results are sample-based and suppressed for small municipalities. Each
municipality gets its own value where published, otherwise its Gemeindeverband's, otherwise its
Kreis's (14.6% / 42.9% / 42.4% of municipalities; 67% / 12% / 21% of the population); fill-level
dummies enter the models. Raw files are not committed (`data/raw/` is ignored); the map script
needs the raw registry.

**Main extension results**

* *Timing.* With the same municipalities observed in 2013, 2017, 2021 and 2025, none of the
  distance associations exists in 2013, the last election before the 2015–16 arrivals; they appear
  in 2017 (`11_…`, figure 5).
* *West, H1 in changes.* AfD gains 2013→2017 were larger closer to a centre: −0.44 per log-km with
  Land FE (WCB p = 0.027 / 0.012) and −0.21 within Kreis (0.046 / 0.043); with Zensus 2022
  education and unemployment −0.58 (0.001 / <0.001) and −0.26 (0.010 / 0.008) (`12_…`, `13_…`).
* *West, H3.* Within Kreis, the distance slope depends on the district foreign share: +0.54 per SD
  in 2025 levels (WCB p = 0.002 / 0.003), +0.36 for the 2013→2017 change and +0.63 for 2013→2025
  (p ≤ 0.001); zero in 2013. Closer means more AfD in low-diversity districts and not in
  high-diversity ones (`08_…`, figure 4). The pooled Germany interaction is an East/West
  composition artefact (`08b_…`). Municipal foreign share (Zensus 2022) does not moderate.
* *East.* With Land FE the positive coefficient appears in 2017 (change 2013→2017: +1.38,
  WCB p = 0.003 / <0.001) and is partly accounted for by unemployment (+1.00 with education
  controls); it is zero within Kreis.
* *Not supported.* Capacity of the nearest centre does not moderate; the number of centres within
  50 km (West) is already associated with AfD in 2013, so it reflects where centres are placed.

The registry is a 2025 snapshot without opening dates for most facilities, the 2013 AfD differs
from today's party, and the Zensus 2022 variables are measured after the 2013→2017 change.
