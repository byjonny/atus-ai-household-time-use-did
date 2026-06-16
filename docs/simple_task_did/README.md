# Simple Task-Year DiD

This is the simple regression version of the bundle comparison.

## Model

`minutes_task,t = task FE + year FE + beta * AI_exposed_task x Post_t + error_task,t`

Outcome: TUFNWGTP-weighted average minutes/day for each ATUS task-year.

Post period: 2023, 2024

Pre period: 2017, 2018, 2019, 2021, 2022

Tasks:

- AI-exposed: 18
- Low-exposure physical: 19

## Main Result

Beta:

`-0.479 minutes/day`

Clustered SE by task:

`0.241`

Approximate p-value:

`0.047`

## Descriptive Means

| bundle | pre | post | post - pre |
| --- | ---: | ---: | ---: |
| AI-exposed | 1.469 | 1.386 | -0.083 |
| Low-exposure physical | 5.205 | 5.600 | 0.396 |

Simple difference of changes:

`-0.479 minutes/day`

## Event-Study Sanity Check

Baseline year: 2022

Post estimates:

- 2023: -0.161 minutes/day, p = 0.218
- 2024: -0.318 minutes/day, p = 0.152

Pre-trend warning:

The pre-period estimates are not perfectly flat. The largest pre-period deviation is 2019: 0.518 minutes/day, p = 0.036.

That means this should be read as a simple descriptive DiD, not as strong causal evidence.

## Interpretation

A negative beta means AI-exposed tasks fell more, or rose less, than low-exposure physical tasks after 2022, after controlling for task fixed effects and year fixed effects.

This is still a descriptive check. It does not prove that AI caused the change because treated and comparison tasks may have different underlying trends.

## Files

- `results/simple_task_did/task_year_panel.csv`
- `results/simple_task_did/task_year_did_results.csv`
- `results/simple_task_did/task_year_did_means.csv`
- `results/simple_task_did/task_year_event_study.csv`
- `results/simple_task_did/task_year_event_study.svg`
