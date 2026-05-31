# Secondary Check: Simple Activity-Level DiD

This is the older, simpler analysis in the repository. It is kept here as a transparent activity-level sanity check, while the main README now foregrounds the Blank-style predetermined exposure design.

Generated from official BLS ATUS PDQ metadata and BLS Public Data API annual series.

## Bottom Line

Using 2023-2024 as the post-ChatGPT period and 2015-2019 as the main pre period, the activity-level fixed-effects DiD estimate is **-1.504 minutes/day per high-exposure activity** relative to low-exposure physical household tasks. The approximate activity-clustered SE is **0.629**.

The sign is **negative**, not positive: the raw high-exposure activity bundle moved from **23.040 minutes/day** in 2015-2019 to **20.100 minutes/day** in 2023-2024. The low-exposure physical bundle changed from **87.240** to **96.000 minutes/day**. The simple bundle-level DiD is **-11.700 minutes/day**.

On the extensive margin, the DiD estimate for percent of the population engaged in the activities is **-1.297 percentage points** with approximate clustered SE **0.795**.

## Data Source

- BLS ATUS one-screen metadata endpoint: `https://data.bls.gov/PDQWeb/survey/tu`
- BLS Public Data API: `https://api.bls.gov/publicAPI/v2/timeseries/data/`
- I first attempted the BLS public microdata ZIPs, but the shell received BLS bot-protection `Access Denied` pages. I therefore used the official BLS PDQ/API aggregate annual series rather than individual respondent microdata.
- Population: both sexes, age 15+, all labor-force statuses, all own-child statuses.
- Day type: all days.
- Measures: average hours/day and percent engaged in activity on an average day.
- Years used: 2003-2024; main DiD excludes 2020-2022 because 2020 collection was disrupted by COVID and 2021-2022 remain a transition/post-pandemic but mostly pre-generative-AI period.

## Activity Mapping

High exposure means the activity is plausibly exposed to AI assistants acting like accountants, financial advisers, tutors, doctors, or lawyers/administrative navigators. ATUS has no clean legal-services code, so `600069 Government services` is used only as a legal/admin proxy.

High-exposure primary codes: 010300, 020901, 030201, 030300, 060300, 080200, 080400, 600069

Low-exposure physical control codes: 020101, 020102, 020201, 020203, 020500, 020600, 020700, 020800

Full mapping is in `results/simple_activity_did/activity_mapping.csv`.

## Reproduction Steps

1. Download the BLS ATUS PDQ metadata to `raw/survey_tu.json`.
2. Run `scripts/simple_activity_did/atus_did_analysis.py --make-requests` to build BLS API request payloads and `results/simple_activity_did/activity_mapping.csv`.
3. Fetch every `raw/bls_request_*_chunk*.json` payload from the BLS Public Data API into matching `raw/bls_data_*_chunk*.json` response files.
4. Run `scripts/simple_activity_did/atus_did_analysis.py --analyze`.

The public BLS API caps unauthenticated requests at 10 years and 25 series, so the request payloads are split by year window and series chunk.

## DiD Specification

For activity `a` and year `t`, I estimated:

`Y_at = activity FE + year FE + beta * HighExposure_a * Post_t + error_at`

The unit is an activity-year. `Y` is either average minutes per day or percent of the population engaged. Standard errors are shown both conventional and clustered by activity; with only a small number of activities, inference should be treated as descriptive.

## Main Results

| spec | pre_years | post_years | n_obs | activity_clusters | did_coef | se | p_norm | cluster_se | cluster_p_norm | high_pre_mean | high_post_mean | low_pre_mean | low_post_mean | outcome |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| primary_2015_2019_vs_2023_2024 | 2015-2019 | 2023-2024 | 104 | 15 | -1.504 | 0.333 | 0.000 | 0.629 | 0.017 | 3.291 | 3.092 | 10.905 | 12.000 | minutes_per_day |
| primary_2017_2019_vs_2023_2024 | 2017-2019 | 2023-2024 | 74 | 15 | -1.601 | 0.374 | 0.000 | 0.629 | 0.011 | 3.286 | 3.092 | 10.800 | 12.000 | minutes_per_day |
| primary_2003_2019_vs_2023_2024 | 2003-2019 | 2023-2024 | 289 | 16 | -1.523 | 0.369 | 0.000 | 0.787 | 0.053 | 3.087 | 3.092 | 10.782 | 12.000 | minutes_per_day |
| broad_education_2015_2019_vs_2023_2024 | 2015-2019 | 2023-2024 | 104 | 15 | -1.578 | 0.333 | 0.000 | 0.632 | 0.013 | 3.360 | 3.092 | 10.905 | 12.000 | minutes_per_day |
| placebo_2015_2017_vs_2018_2019 | 2015-2017 | 2018-2019 | 75 | 15 | 0.439 | 0.248 | 0.077 | 0.341 | 0.198 | 3.286 | 3.300 | 11.075 | 10.650 | minutes_per_day |

## Domain Results

These compare each high-exposure domain separately with the same low-exposure physical control group. The legal/admin proxy is sparse in the BLS annual estimates, so it may be unestimable.

| domain | high_codes | outcome | spec | pre_years | post_years | n_obs | activity_clusters | did_coef | se | p_norm | cluster_se | cluster_p_norm | high_pre_mean | high_post_mean | low_pre_mean | low_post_mean | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| finance_accounting | 020901;080200 | minutes_per_day | domain_2015_2019_vs_2023_2024 | 2015-2019 | 2023-2024 | 69.000 | 10.000 | -1.371 | 0.622 | 0.028 | 0.657 | 0.037 | 1.200 | 1.200 | 10.905 | 12.000 |  |
| health_medical | 010300;030300;080400 | minutes_per_day | domain_2015_2019_vs_2023_2024 | 2015-2019 | 2023-2024 | 77.000 | 11.000 | -1.395 | 0.489 | 0.004 | 0.689 | 0.043 | 2.800 | 2.500 | 10.905 | 12.000 |  |
| legal_admin_proxy | 600069 | minutes_per_day | domain_2015_2019_vs_2023_2024 | nan | nan | NA | NA | NA | NA | NA | NA | NA | NA | NA | NA | NA | Insufficient nonmissing high-domain observations in pre/post windows. |
| tutoring_education | 030201;060300 | minutes_per_day | domain_2015_2019_vs_2023_2024 | 2015-2019 | 2023-2024 | 70.000 | 10.000 | -1.815 | 0.571 | 0.001 | 0.687 | 0.008 | 6.120 | 5.400 | 10.905 | 12.000 |  |

## Domain Extensive-Margin Results

| domain | high_codes | outcome | spec | pre_years | post_years | n_obs | activity_clusters | did_coef | se | p_norm | cluster_se | cluster_p_norm | high_pre_mean | high_post_mean | low_pre_mean | low_post_mean | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| finance_accounting | 020901;080200 | pct_engaged | domain_2015_2019_vs_2023_2024 | 2015-2019 | 2023-2024 | 70 | 10 | -1.626 | 0.675 | 0.016 | 0.810 | 0.045 | 2.690 | 1.975 | 18.407 | 19.319 |  |
| health_medical | 010300;030300;080400 | pct_engaged | domain_2015_2019_vs_2023_2024 | 2015-2019 | 2023-2024 | 77 | 11 | -0.901 | 0.552 | 0.103 | 0.803 | 0.262 | 3.740 | 3.750 | 18.407 | 19.319 |  |
| legal_admin_proxy | 600069 | pct_engaged | domain_2015_2019_vs_2023_2024 | 2015-2019 | 2023-2024 | 63 | 9 | -1.011 | 0.961 | 0.293 | 0.820 | 0.218 | 0.400 | 0.300 | 18.407 | 19.319 |  |
| tutoring_education | 030201;060300 | pct_engaged | domain_2015_2019_vs_2023_2024 | 2015-2019 | 2023-2024 | 70 | 10 | -1.706 | 0.681 | 0.012 | 0.867 | 0.049 | 4.420 | 3.625 | 18.407 | 19.319 |  |

## Extensive-Margin Results

| spec | pre_years | post_years | n_obs | activity_clusters | did_coef | se | p_norm | cluster_se | cluster_p_norm | high_pre_mean | high_post_mean | low_pre_mean | low_post_mean | outcome |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| primary_2015_2019_vs_2023_2024 | 2015-2019 | 2023-2024 | 112 | 16 | -1.297 | 0.341 | 0.000 | 0.795 | 0.103 | 3.230 | 2.844 | 18.407 | 19.319 | pct_engaged |
| primary_2017_2019_vs_2023_2024 | 2017-2019 | 2023-2024 | 80 | 16 | -1.275 | 0.373 | 0.001 | 0.741 | 0.085 | 3.167 | 2.844 | 18.367 | 19.319 | pct_engaged |
| primary_2003_2019_vs_2023_2024 | 2003-2019 | 2023-2024 | 304 | 16 | -2.124 | 0.449 | 0.000 | 1.218 | 0.081 | 3.308 | 2.844 | 17.659 | 19.319 | pct_engaged |
| broad_education_2015_2019_vs_2023_2024 | 2015-2019 | 2023-2024 | 112 | 16 | -1.314 | 0.342 | 0.000 | 0.798 | 0.100 | 3.277 | 2.875 | 18.407 | 19.319 | pct_engaged |
| placebo_2015_2017_vs_2018_2019 | 2015-2017 | 2018-2019 | 80 | 16 | -0.037 | 0.194 | 0.846 | 0.301 | 0.901 | 3.267 | 3.175 | 18.429 | 18.375 | pct_engaged |

## Event Study

Event-study coefficients are high-exposure activity deviations relative to low-exposure controls, using 2019 as the omitted baseline year and excluding 2020.

| year | base_year | coef | se | cluster_se | p_norm | cluster_p_norm |
| --- | --- | --- | --- | --- | --- | --- |
| 2014 | 2019 | -0.332 | 0.537 | 0.537 | 0.536 | 0.536 |
| 2015 | 2019 | -0.375 | 0.537 | 0.519 | 0.485 | 0.470 |
| 2016 | 2019 | -0.557 | 0.537 | 0.407 | 0.300 | 0.171 |
| 2017 | 2019 | -0.546 | 0.537 | 0.409 | 0.309 | 0.182 |
| 2018 | 2019 | -0.107 | 0.537 | 0.323 | 0.842 | 0.740 |
| 2021 | 2019 | -0.964 | 0.537 | 0.417 | 0.073 | 0.021 |
| 2022 | 2019 | -1.195 | 0.550 | 0.579 | 0.030 | 0.039 |
| 2023 | 2019 | -1.520 | 0.550 | 0.609 | 0.006 | 0.013 |
| 2024 | 2019 | -2.100 | 0.537 | 0.894 | 0.000 | 0.019 |

SVG chart: `results/simple_activity_did/event_study_minutes.svg`

## Key Activity Changes

| activity_code | activity_text | exposure_group | domain | value_2019 | value_2022 | value_2023 | value_2024 | change_2019_2024 | change_2022_2024 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 020901 | Financial management | high | finance_accounting | 1.800 | 1.800 | 1.200 | 1.800 | 0.000 | 0.000 |
| 080200 | Financial services and banking | high | finance_accounting | 0.600 | NA | NA | 0.600 | 0.000 | NA |
| 010300 | Health-related self care | high | health_medical | 4.800 | 4.800 | 4.200 | 3.000 | -1.800 | -1.800 |
| 030300 | Activities related to household children's health | high | health_medical | 0.600 | 0.600 | 0.600 | 0.600 | 0.000 | 0.000 |
| 080400 | Medical and care services | high | health_medical | 3.600 | 3.600 | 3.600 | 3.000 | -0.600 | -0.600 |
| 600069 | Government services | high | legal_admin_proxy | NA | NA | NA | NA | NA | NA |
| 030201 | Helping household children with homework | high | tutoring_education | 1.200 | 1.200 | 1.200 | 1.200 | 0.000 | 0.000 |
| 060300 | Homework and research | high | tutoring_education | 11.400 | 9.000 | 9.600 | 9.600 | -1.800 | 0.600 |
| 020101 | Interior cleaning | low | physical_household | 18.600 | 21.000 | 22.200 | 24.000 | 5.400 | 3.000 |
| 020102 | Laundry | low | physical_household | 10.800 | 10.200 | 10.800 | 10.200 | -0.600 | 0.000 |
| 020201 | Food and drink preparation | low | physical_household | 28.200 | 30.000 | 30.600 | 31.800 | 3.600 | 1.800 |
| 020203 | Kitchen and food cleanup | low | physical_household | 7.800 | 8.400 | 7.800 | 7.800 | 0.000 | -0.600 |
| 020500 | Lawn and garden care | low | physical_household | 10.200 | 10.800 | 10.200 | 12.000 | 1.800 | 1.200 |
| 020600 | Animal and pet care | low | physical_household | 7.200 | 9.000 | 9.000 | 9.000 | 1.800 | 0.000 |
| 020700 | Vehicle care (by self) | low | physical_household | 2.400 | 2.400 | 2.400 | 1.800 | -0.600 | -0.600 |
| 020800 | Appliance, tool, and toy maintenance (by self) | low | physical_household | 0.600 | 0.600 | 1.200 | 1.200 | 0.600 | 0.600 |

## Interpretation

The evidence does **not** show a post-2022 increase in these ATUS-measured AI-exposed household-professional domains. In the main specification, high-exposure activities are flat to down while the low-exposure physical household controls rise.

This does not falsify the production-boundary hypothesis. ATUS does not observe AI use, quality, avoided market purchases, or whether a task was completed faster. If AI automates household financial planning or medical preparation, measured time could fall even while household output rises. Conversely, if AI enables households to do more of a task themselves, measured time could rise. The ATUS signal is therefore best interpreted as a reduced-form tendency in time allocation, not a direct welfare or production-boundary estimate.

The estimates should also be read with caution because the public BLS annual activity series are rounded/suppressed for some low-incidence activities. That is why legal/admin minutes are not estimable, and why several tiny categories move in 0.6-minute increments.

## Files Produced

- `results/simple_activity_did/activity_mapping.csv`
- `results/simple_activity_did/atus_activity_year_values.csv`
- `results/simple_activity_did/did_summary.csv`
- `results/simple_activity_did/did_domain_minutes.csv`
- `results/simple_activity_did/did_domain_pct_engaged.csv`
- `results/simple_activity_did/event_study_minutes.csv`
- `results/simple_activity_did/group_year_totals_minutes.csv`
- `results/simple_activity_did/key_activity_changes_minutes.csv`
- `results/simple_activity_did/did_pct_engaged.csv`
- `results/simple_activity_did/event_study_minutes.svg`
