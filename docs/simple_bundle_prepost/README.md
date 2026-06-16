# Simple Bundle Pre/Post Analysis

This is the intentionally simple version of the ATUS analysis.

## Question

Did time in a clear AI-exposed task bundle fall after ChatGPT, compared with a low-exposure physical household bundle?

## Bundles

AI-exposed bundle: finance, household admin, mail/e-mail, homework/research, banking/financial services, legal services, medical services, government/tax/license admin.

Low-exposure physical bundle: cleaning, laundry, food preparation, kitchen cleanup, lawn/garden, vehicle repair, appliance/tool repair.

Full mapping: `results/simple_bundle_prepost/bundle_mapping.csv`

## Method

For each respondent:

`bundle_minutes = sum(minutes in selected ATUS activity codes)`

For each year:

`weighted_mean_minutes = sum(TUFNWGTP * bundle_minutes) / sum(TUFNWGTP)`

Pre period: 2017, 2018, 2019, 2021, 2022

Post period: 2023, 2024

Pre/post means are simple averages of the annual weighted means, so each year gets equal weight.

## Result

AI-exposed bundle:

`26.45 -> 24.95 minutes/day`

Change:

`-1.50 minutes/day`

Low-exposure physical bundle:

`98.89 -> 106.41 minutes/day`

Change:

`7.52 minutes/day`

Simple bundle DiD:

`-9.02 minutes/day`

## Sample Counts

Sample counts are unweighted respondent counts with positive minutes in the bundle in that year.

Plot: `results/simple_bundle_prepost/bundle_sample_counts.svg`

Annual sample count table: `results/simple_bundle_prepost/annual_bundle_sample_counts.csv`

## AI-Exposed Task Detail

This table breaks the AI-exposed bundle into individual ATUS tasks.

| activity_code | official_activity_text | pre_mean_minutes | post_mean_minutes | post_minus_pre_minutes | pre_avg_sample_n_positive | post_avg_sample_n_positive |
| --- | --- | --- | --- | --- | --- | --- |
| 060301 | Research/homework for class for degree, certification, or licensure | 10.211 | 8.990 | -1.222 | 284.000 | 204.000 |
| 020902 | Household & personal organization and planning | 6.591 | 6.799 | 0.208 | 1484.600 | 1267.500 |
| 080401 | Using health and care services outside the home | 2.911 | 2.927 | 0.016 | 286.600 | 254.000 |
| 020904 | HH & personal e-mail and messages | 1.736 | 1.802 | 0.066 | 491.200 | 456.500 |
| 020901 | Financial management | 1.655 | 1.573 | -0.082 | 325.400 | 264.500 |
| 030201 | Homework (hh children) | 1.219 | 0.967 | -0.252 | 209.200 | 116.000 |
| 020903 | HH & personal mail & messages (except e-mail) | 0.973 | 0.751 | -0.222 | 490.000 | 363.000 |
| 060399 | Research/homework n.e.c.* | 0.339 | 0.273 | -0.066 | 14.800 | 14.500 |
| 080201 | Banking | 0.268 | 0.195 | -0.073 | 152.200 | 109.000 |
| 060302 | Research/homework for class for pers. interest | 0.222 | 0.281 | 0.060 | 16.600 | 22.500 |
| 080202 | Using other financial services | 0.095 | 0.172 | 0.077 | 12.200 | 9.500 |
| 100103 | Obtaining licenses & paying fines, fees, taxes | 0.081 | 0.056 | -0.025 | 14.600 | 9.500 |
| 080402 | Using in-home health and care services | 0.075 | 0.098 | 0.024 | 11.000 | 7.500 |
| 080301 | Using legal services | 0.041 | 0.019 | -0.022 | 3.600 | 4.000 |
| 100199 | Using government services, n.e.c.* | 0.016 | 0.018 | 0.002 | 1.800 | 2.000 |
| 080399 | Using legal services, n.e.c.* | 0.007 | 0.000 | -0.007 | 0.600 | 0.000 |
| 080499 | Using medical services, n.e.c.* | 0.006 | 0.019 | 0.013 | 2.800 | 1.000 |
| 080299 | Using financial services and banking, n.e.c.* | 0.003 | 0.009 | 0.006 | 0.400 | 1.000 |

Task detail files:

- `results/simple_bundle_prepost/ai_exposed_task_annual_detail.csv`
- `results/simple_bundle_prepost/ai_exposed_task_prepost_detail.csv`
- `results/simple_bundle_prepost/ai_task_prepost_change.svg`

## Interpretation

A negative simple DiD means the AI-exposed bundle fell more, or rose less, than the low-exposure physical bundle after ChatGPT.

This is descriptive. It does not prove AI caused the change.

## Files

- `results/simple_bundle_prepost/bundle_mapping.csv`
- `results/simple_bundle_prepost/annual_bundle_minutes.csv`
- `results/simple_bundle_prepost/prepost_bundle_summary.csv`
- `results/simple_bundle_prepost/simple_bundle_did.csv`
- `results/simple_bundle_prepost/bundle_trends.svg`
- `results/simple_bundle_prepost/bundle_sample_counts.svg`
