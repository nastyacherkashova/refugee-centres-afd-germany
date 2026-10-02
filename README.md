
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
