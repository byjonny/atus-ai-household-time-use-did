# Task-Year Event Study

This is the dynamic version of the task-year DiD.

Instead of estimating one post-2022 coefficient, it estimates one coefficient for each year relative to 2022.

## Model

```text
minutes_task,t =
task FE
+ year FE
+ beta_y * AI_exposed_task x 1[year = y]
+ error_task,t
```

Outcome: TUFNWGTP-weighted average minutes/day for each ATUS task-year.

Baseline year: 2022

Tasks:

- AI-exposed: 18
- Low-exposure physical: 19

Task-year observations in model years: 259

## Results

| year | coefficient | clustered SE | p-value |
| ---: | ---: | ---: | ---: |
| 2017 | 0.253 | 0.175 | 0.148 |
| 2018 | 0.445 | 0.245 | 0.069 |
| 2019 | 0.518 | 0.247 | 0.036 |
| 2021 | -0.018 | 0.191 | 0.923 |
| 2023 | -0.161 | 0.130 | 0.218 |
| 2024 | -0.318 | 0.222 | 0.152 |

Post estimates:

- 2023: -0.161 minutes/day, p = 0.218
- 2024: -0.318 minutes/day, p = 0.152

Pre-trend warning:

The pre-period estimates are not perfectly flat. The largest pre-period deviation is 2019: 0.518 minutes/day, p = 0.036.

That weakens a causal interpretation because the treated and comparison tasks were already not perfectly parallel before 2023.

## Interpretation

A negative post coefficient means AI-exposed tasks fell more, or rose less, than low-exposure physical tasks in that year relative to 2022.

The event study is mainly a diagnostic: it shows both the post-ChatGPT pattern and whether the pre-period looked plausibly parallel.

## Files

- `results/task_year_panel.csv`
- `results/task_year_event_study.csv`
- `results/task_year_event_study.svg`
