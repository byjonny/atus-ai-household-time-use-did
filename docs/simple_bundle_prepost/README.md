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

`81.22 -> 86.78 minutes/day`

Change:

`5.57 minutes/day`

Simple bundle DiD:

`-7.07 minutes/day`

## Interpretation

A negative simple DiD means the AI-exposed bundle fell more, or rose less, than the low-exposure physical bundle after ChatGPT.

This is descriptive. It does not prove AI caused the change.

## Files

- `results/simple_bundle_prepost/bundle_mapping.csv`
- `results/simple_bundle_prepost/annual_bundle_minutes.csv`
- `results/simple_bundle_prepost/prepost_bundle_summary.csv`
- `results/simple_bundle_prepost/simple_bundle_did.csv`
- `results/simple_bundle_prepost/bundle_trends.svg`
