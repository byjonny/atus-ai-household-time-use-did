# Participation-Rate AI Exposure Pre/Post Model

This experiment asks whether ATUS tasks with higher AI exposure scores have a different post-ChatGPT change in participation.

## Outcome

For task \(a\) and year \(t\), the main outcome is the weighted participation rate:

\[
P_{a t}
=
100
\times
\frac{\sum_i w_{i t} \mathbf{1}[minutes_{i a t} > 0]}
{\sum_i w_{i t}}.
\]

So \(P_{a t}\) is measured in percentage points. It is not minutes. It is the share of the weighted ATUS population that reported doing task \(a\) on the diary day.

## Years

\[
Pre = \{2017, 2018, 2019, 2021, 2022\},
\quad
Post = \{2023, 2024\}.
\]

The year 2020 is excluded, matching the other models.

## Main Change Model

First, I average \(P_{a t}\) within the pre and post periods:

\[
\bar P_{a p}
=
\frac{1}{|T_p|}
\sum_{t \in T_p} P_{a t}.
\]

Then I take the post-minus-pre change:

\[
\Delta P_a
=
\bar P_{a,post}
-
\bar P_{a,pre}.
\]

The main model is:

\[
\Delta P_a
=
\alpha
+
\beta s_a
+
\varepsilon_a,
\]

where \(s_a\) is the continuous AI exposure score of task \(a\).

## Main Result

Using the standardized AI exposure score:

\[
\hat\beta_{1SD}
=
-0.0128
\quad
SE
=
0.0241
\quad
p
=
0.594.
\]

Interpretation:

\[
\hat\beta_{1SD} = -0.0128
\]

means that a task with an AI exposure score one standard deviation higher had a post-minus-pre participation-rate change that was about \(-0.0128\) percentage points different from lower-exposure tasks.

Using the raw 0-to-1 AI exposure score:

\[
\hat\beta
=
-0.0736,
\quad
SE
=
0.1382,
\quad
p
=
0.594.
\]

## Pre/Post Slope Comparison

As a descriptive check, I also compare the cross-sectional relationship between participation and AI exposure before and after ChatGPT:

\[
\bar P_{a p}
=
\alpha
+
\delta Post_p
+
\gamma s_a
+
\beta(s_a \times Post_p)
+
\varepsilon_{a p}.
\]

This gives the same point estimate for \(\beta\), but it is less clean because task-level baseline participation differs enormously across activities.

## Task-Year Fixed-Effects Check

I also estimate the annual task-year fixed-effects version:

\[
P_{a t}
=
\alpha_a
+
\lambda_t
+
\beta(s_a \times Post_t)
+
\varepsilon_{a t}.
\]

For the weighted participation rate and a one-standard-deviation AI exposure score:

\[
\hat\beta_{FE,1SD}
=
-0.0128
\quad
SE_{cluster}
=
0.0178
\quad
p
=
0.470.
\]

## Data Used

\[
N_{tasks} = 431,
\quad
N_{task-years} = 3017,
\quad
N_{\text{change tasks}} = 431,
\quad
\bar s = 0.134,
\quad
SD(s) = 0.175.
\]

## Interpretation

This is an extensive-margin test. It asks whether high-AI-exposure tasks became more or less likely to appear on respondents' diary days after ChatGPT.

A negative \(\beta\) would mean that participation in high-exposure tasks fell relative to low-exposure tasks. A positive \(\beta\) would mean that participation rose.

This does not measure task duration. For time-saving among people who still do the task, use the conditional-duration outcome from the positive respondent table.

## Files

- `results/participation_task_year_panel.csv`
- `results/prepost_task_means.csv`
- `results/post_minus_pre_task_changes.csv`
- `results/post_minus_pre_participation_exposure_results.csv`
- `results/prepost_participation_exposure_results.csv`
- `results/task_year_fe_participation_exposure_results.csv`
