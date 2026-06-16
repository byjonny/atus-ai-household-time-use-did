# Continuous Automation-Score Task-Year FE Model

This experiment replaces the binary AI-exposed indicator with a continuous automation score for each ATUS task.

## Estimand

Let \(a\) index ATUS activities and \(t\) index years. For every activity-year, I first compute the survey-weighted average minutes per day:

\[
m_{a t}
=
\frac{\sum_i w_{i t} \, \text{minutes}_{i a t}}
{\sum_i w_{i t}},
\]

where \(w_{i t}\) is the ATUS final person weight \(TUFNWGTP\).

The main fixed-effects model is:

\[
m_{a t}
=
\alpha_a
+
\lambda_t
+
\beta \left( s_a \times \text{Post}_t \right)
+
\varepsilon_{a t},
\]

where:

- \(\alpha_a\) are task fixed effects,
- \(\lambda_t\) are year fixed effects,
- \(s_a\) is the continuous automation score of task \(a\),
- \(\text{Post}_t = 1\) for 2023 and 2024,
- standard errors are clustered by ATUS task.

## What I Did

1. Loaded the ATUS Activity Summary file, `atussum-0324.zip`.
2. Used all task columns available in the summary file that also have a score in `experiments/03_pre_ai_exposure/scores/activity_ai_scores.csv`.
3. Built a task-year panel for 2017, 2018, 2019, 2021, 2022, 2023, and 2024.
4. For each task-year, computed \(m_{a t}\), the \(TUFNWGTP\)-weighted mean minutes per day.
5. Merged each task with its continuous `automation_score`.
6. Estimated the model with task fixed effects and year fixed effects.
7. Reported the coefficient both for the raw 0-to-1 score and for a one-standard-deviation increase in automation score.

## Main Results

Raw automation score, from 0 to 1:

\[
\hat\beta = -0.088,
\quad
SE_{cluster} = 0.150,
\quad
p = 0.556.
\]

One standard deviation increase in automation score:

\[
\hat\beta_{1SD} = -0.013,
\quad
SE_{cluster} = 0.022,
\quad
p = 0.556.
\]

## Interpretation

The preferred interpretation is the one-standard-deviation estimate:

\[
\hat\beta_{1SD} = -0.013.
\]

This means that, after 2022, a task with an automation score one standard deviation higher changed by about `-0.013` minutes per day relative to lower-scored tasks, after controlling for task fixed effects and year fixed effects.

## Score Distribution

\[
N_{tasks} = 431,
\quad
\bar s = 0.118,
\quad
SD(s) = 0.149,
\quad
\min(s) = 0.050,
\quad
\max(s) = 0.650.
\]

Share of tasks with baseline score \(0.05\): `78.4%`

Share of tasks with score at least \(0.50\): `6.3%`

## Highest-Scored Tasks

| code | task | automation score |
| --- | --- | ---: |
| 020901 | Financial management | 0.65 |
| 030201 | Homework (hh children) | 0.65 |
| 020902 | Household & personal organization and planning | 0.60 |
| 020903 | HH & personal mail & messages (except e-mail) | 0.60 |
| 020904 | HH & personal e-mail and messages | 0.60 |
| 020905 | Home security | 0.60 |
| 020999 | Household management, n.e.c.* | 0.60 |
| 080201 | Banking | 0.60 |
| 080202 | Using other financial services | 0.60 |
| 080203 | Waiting associated w/banking/financial services | 0.60 |
| 080299 | Using financial services and banking, n.e.c.* | 0.60 |
| 080401 | Using health and care services outside the home | 0.60 |
| 080402 | Using in-home health and care services | 0.60 |
| 080403 | Waiting associated with medical services | 0.60 |
| 080499 | Using medical services, n.e.c.* | 0.60 |

## Critical Notes

This is cleaner than the binary task DiD because it uses all scored tasks and uses the intensity of automation exposure rather than a hand-picked treated/control split.

But it is still descriptive. The automation scores are constructed, many tasks receive the same low baseline score, and ATUS does not observe actual AI adoption. A negative \(\beta\) is consistent with time-saving on more automatable tasks, but it is not proof that AI caused the change.

## Files

- `results/task_year_panel.csv`
- `results/continuous_automation_results.csv`
- `results/automation_score_summary.csv`
- `results/top_automation_tasks.csv`
