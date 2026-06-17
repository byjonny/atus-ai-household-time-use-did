#!/usr/bin/env python3
"""Participation-rate model using continuous AI exposure scores.

This experiment asks whether tasks with higher AI exposure scores show a
different post-ChatGPT change in participation rates.

Main outcome:

    100 * positive_share_weighted

This is the TUFNWGTP-weighted share of respondents with strictly positive
minutes in a task on the ATUS diary day, expressed in percentage points.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT_DIR = Path(__file__).resolve().parent
RESULTS = EXPERIMENT_DIR / "results"

COUNTS_FILE = (
    ROOT
    / "experiments"
    / "05_continuous_automation_score"
    / "results"
    / "task_positive_respondents_by_year.csv"
)

MODEL_YEARS = [2017, 2018, 2019, 2021, 2022, 2023, 2024]
PRE_YEARS = [2017, 2018, 2019, 2021, 2022]
POST_YEARS = [2023, 2024]


def normal_pvalue(t_stat: float) -> float:
    if not np.isfinite(t_stat):
        return float("nan")
    return math.erfc(abs(t_stat) / math.sqrt(2.0))


def load_panel() -> pd.DataFrame:
    if not COUNTS_FILE.exists():
        raise FileNotFoundError(
            f"Missing {COUNTS_FILE}. Run "
            "experiments/05_continuous_automation_score/"
            "build_positive_respondent_counts.py first."
        )

    panel = pd.read_csv(COUNTS_FILE, dtype={"activity_code": str})
    panel["activity_code"] = panel["activity_code"].str.zfill(6)
    panel = panel[panel["year"].isin(MODEL_YEARS)].copy()
    panel["post_2023plus"] = panel["year"].isin(POST_YEARS).astype(float)

    panel["participation_rate_weighted_pp"] = panel["positive_share_weighted"] * 100.0
    panel["participation_rate_unweighted_pp"] = panel["positive_share_unweighted"] * 100.0

    score_mean = panel.drop_duplicates("activity_code")["ai_exposure_score"].mean()
    score_sd = panel.drop_duplicates("activity_code")["ai_exposure_score"].std(ddof=0)
    panel["ai_exposure_score_z"] = (
        (panel["ai_exposure_score"] - score_mean) / score_sd
        if score_sd > 0
        else 0.0
    )
    panel["ai_exposure_x_post"] = panel["ai_exposure_score"] * panel["post_2023plus"]
    panel["ai_exposure_z_x_post"] = panel["ai_exposure_score_z"] * panel["post_2023plus"]
    return panel


def ols(df: pd.DataFrame, y_col: str, x_cols: list[str]) -> dict:
    work = df.dropna(subset=[y_col, *x_cols]).copy()
    y = work[y_col].astype(float).to_numpy()
    x = pd.DataFrame({"const": 1.0}, index=work.index)
    for col in x_cols:
        x[col] = work[col].astype(float)
    xmat = x.to_numpy(float)
    beta = np.linalg.lstsq(xmat, y, rcond=None)[0]
    resid = y - xmat @ beta
    n, k = xmat.shape
    xtx_inv = np.linalg.pinv(xmat.T @ xmat)
    sigma2 = float((resid @ resid) / max(n - k, 1))
    cov = sigma2 * xtx_inv
    se = np.sqrt(np.maximum(np.diag(cov), 0.0))
    out = {"_meta": {"n": int(n), "k": int(k)}}
    for idx, name in enumerate(x.columns):
        se_i = float(se[idx])
        t_i = float(beta[idx] / se_i) if se_i > 0 else float("nan")
        out[name] = {
            "coef": float(beta[idx]),
            "se": se_i,
            "p_norm": normal_pvalue(t_i),
        }
    return out


def ols_with_task_year_fe(df: pd.DataFrame, y_col: str, reg_cols: list[str]) -> dict:
    work = df.dropna(subset=[y_col, *reg_cols]).copy()
    y = work[y_col].astype(float).to_numpy()

    x = pd.DataFrame({"const": 1.0}, index=work.index)
    for col in reg_cols:
        x[col] = work[col].astype(float)
    task_dummies = pd.get_dummies(work["activity_code"], prefix="task", drop_first=True, dtype=float)
    year_dummies = pd.get_dummies(work["year"], prefix="year", drop_first=True, dtype=float)
    x = pd.concat([x, task_dummies, year_dummies], axis=1)
    xmat = x.to_numpy(float)

    beta = np.linalg.lstsq(xmat, y, rcond=None)[0]
    resid = y - xmat @ beta
    n, k = xmat.shape
    xtx_inv = np.linalg.pinv(xmat.T @ xmat)
    sigma2 = float((resid @ resid) / max(n - k, 1))
    cov = sigma2 * xtx_inv
    se = np.sqrt(np.maximum(np.diag(cov), 0.0))

    meat = np.zeros((k, k))
    clusters = work["activity_code"].astype(str).to_numpy()
    for cluster in np.unique(clusters):
        idx = clusters == cluster
        xu = xmat[idx, :].T @ resid[idx]
        meat += np.outer(xu, xu)
    g_count = len(np.unique(clusters))
    correction = (g_count / max(g_count - 1, 1)) * ((n - 1) / max(n - k, 1))
    cov_cluster = correction * xtx_inv @ meat @ xtx_inv
    cluster_se = np.sqrt(np.maximum(np.diag(cov_cluster), 0.0))

    out = {"_meta": {"n": int(n), "k": int(k), "clusters": int(g_count)}}
    for idx, name in enumerate(x.columns):
        se_i = float(se[idx])
        cse_i = float(cluster_se[idx])
        t_i = float(beta[idx] / se_i) if se_i > 0 else float("nan")
        ct_i = float(beta[idx] / cse_i) if cse_i > 0 else float("nan")
        out[name] = {
            "coef": float(beta[idx]),
            "se": se_i,
            "p_norm": normal_pvalue(t_i),
            "cluster_se": cse_i,
            "cluster_p_norm": normal_pvalue(ct_i),
        }
    return out


def build_prepost_means(panel: pd.DataFrame) -> pd.DataFrame:
    work = panel.copy()
    work["period"] = np.where(work["year"].isin(POST_YEARS), "post", "pre")
    grouped = (
        work.groupby(["activity_code", "activity_text", "period"], as_index=False)
        .agg(
            participation_rate_weighted_pp=("participation_rate_weighted_pp", "mean"),
            participation_rate_unweighted_pp=("participation_rate_unweighted_pp", "mean"),
            positive_respondents=("positive_respondents", "mean"),
            respondents_total=("respondents_total", "mean"),
            ai_exposure_score=("ai_exposure_score", "first"),
            ai_exposure_score_z=("ai_exposure_score_z", "first"),
            automation_score=("automation_score", "first"),
            augmentation_score=("augmentation_score", "first"),
        )
    )
    grouped["post_2023plus"] = grouped["period"].eq("post").astype(float)
    grouped["ai_exposure_x_post"] = grouped["ai_exposure_score"] * grouped["post_2023plus"]
    grouped["ai_exposure_z_x_post"] = grouped["ai_exposure_score_z"] * grouped["post_2023plus"]
    return grouped


def run_prepost_slope_models(prepost: pd.DataFrame) -> pd.DataFrame:
    rows = []
    specs = [
        ("weighted", "participation_rate_weighted_pp"),
        ("unweighted", "participation_rate_unweighted_pp"),
    ]
    for label, y_col in specs:
        x_cols = ["post_2023plus", "ai_exposure_score", "ai_exposure_x_post"]
        fit = ols(prepost, y_col, x_cols)
        interaction = fit["ai_exposure_x_post"]
        score = fit["ai_exposure_score"]
        rows.append({
            "model": "prepost_slope_comparison",
            "outcome": y_col,
            "scale": "raw_0_to_1_ai_exposure_score",
            "coef": interaction["coef"],
            "se": interaction["se"],
            "p_norm": interaction["p_norm"],
            "pre_slope": score["coef"],
            "post_slope": score["coef"] + interaction["coef"],
            "n_rows": fit["_meta"]["n"],
            "tasks": prepost["activity_code"].nunique(),
        })

        x_cols_z = ["post_2023plus", "ai_exposure_score_z", "ai_exposure_z_x_post"]
        fit_z = ols(prepost, y_col, x_cols_z)
        interaction_z = fit_z["ai_exposure_z_x_post"]
        score_z = fit_z["ai_exposure_score_z"]
        rows.append({
            "model": "prepost_slope_comparison",
            "outcome": y_col,
            "scale": "one_sd_ai_exposure_score",
            "coef": interaction_z["coef"],
            "se": interaction_z["se"],
            "p_norm": interaction_z["p_norm"],
            "pre_slope": score_z["coef"],
            "post_slope": score_z["coef"] + interaction_z["coef"],
            "n_rows": fit_z["_meta"]["n"],
            "tasks": prepost["activity_code"].nunique(),
        })
    return pd.DataFrame(rows)


def build_change_panel(prepost: pd.DataFrame) -> pd.DataFrame:
    id_cols = [
        "activity_code",
        "activity_text",
        "ai_exposure_score",
        "ai_exposure_score_z",
        "automation_score",
        "augmentation_score",
    ]
    wide = prepost.pivot_table(
        index=id_cols,
        columns="period",
        values=[
            "participation_rate_weighted_pp",
            "participation_rate_unweighted_pp",
            "positive_respondents",
            "respondents_total",
        ],
        aggfunc="first",
    )
    wide.columns = [f"{value}_{period}" for value, period in wide.columns]
    wide = wide.reset_index()
    wide["weighted_participation_change_pp"] = (
        wide["participation_rate_weighted_pp_post"]
        - wide["participation_rate_weighted_pp_pre"]
    )
    wide["unweighted_participation_change_pp"] = (
        wide["participation_rate_unweighted_pp_post"]
        - wide["participation_rate_unweighted_pp_pre"]
    )
    return wide


def run_change_models(change_panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    specs = [
        ("weighted", "weighted_participation_change_pp"),
        ("unweighted", "unweighted_participation_change_pp"),
    ]
    for label, y_col in specs:
        for x_col, scale in [
            ("ai_exposure_score", "raw_0_to_1_ai_exposure_score"),
            ("ai_exposure_score_z", "one_sd_ai_exposure_score"),
        ]:
            fit = ols(change_panel, y_col, [x_col])
            term = fit[x_col]
            rows.append({
                "model": "post_minus_pre_change_regression",
                "outcome": y_col,
                "scale": scale,
                "coef": term["coef"],
                "se": term["se"],
                "p_norm": term["p_norm"],
                "n_tasks": fit["_meta"]["n"],
            })
    return pd.DataFrame(rows)


def run_task_year_fe_models(panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    specs = [
        ("weighted", "participation_rate_weighted_pp"),
        ("unweighted", "participation_rate_unweighted_pp"),
    ]
    for label, y_col in specs:
        for reg_col, scale in [
            ("ai_exposure_x_post", "raw_0_to_1_ai_exposure_score"),
            ("ai_exposure_z_x_post", "one_sd_ai_exposure_score"),
        ]:
            fit = ols_with_task_year_fe(panel, y_col, [reg_col])
            term = fit[reg_col]
            rows.append({
                "model": "task_year_fe",
                "outcome": y_col,
                "scale": scale,
                "coef": term["coef"],
                "se": term["se"],
                "p_norm": term["p_norm"],
                "cluster_se_by_task": term["cluster_se"],
                "cluster_p_norm": term["cluster_p_norm"],
                "n_rows": fit["_meta"]["n"],
                "tasks": fit["_meta"]["clusters"],
            })
    return pd.DataFrame(rows)


def write_report(
    panel: pd.DataFrame,
    prepost: pd.DataFrame,
    change_panel: pd.DataFrame,
    change_results: pd.DataFrame,
    prepost_results: pd.DataFrame,
    fe_results: pd.DataFrame,
) -> None:
    main = change_results[
        change_results["outcome"].eq("weighted_participation_change_pp")
        & change_results["scale"].eq("one_sd_ai_exposure_score")
    ].iloc[0]
    main_raw = change_results[
        change_results["outcome"].eq("weighted_participation_change_pp")
        & change_results["scale"].eq("raw_0_to_1_ai_exposure_score")
    ].iloc[0]
    fe = fe_results[
        fe_results["outcome"].eq("participation_rate_weighted_pp")
        & fe_results["scale"].eq("one_sd_ai_exposure_score")
    ].iloc[0]

    score_tasks = panel.drop_duplicates("activity_code")
    score_mean = score_tasks["ai_exposure_score"].mean()
    score_sd = score_tasks["ai_exposure_score"].std(ddof=0)

    readme = rf"""# Participation-Rate AI Exposure Pre/Post Model

This experiment asks whether ATUS tasks with higher AI exposure scores have a different post-ChatGPT change in participation.

## Outcome

For task \(a\) and year \(t\), the main outcome is the weighted participation rate:

\[
P_{{a t}}
=
100
\times
\frac{{\sum_i w_{{i t}} \mathbf{{1}}[minutes_{{i a t}} > 0]}}
{{\sum_i w_{{i t}}}}.
\]

So \(P_{{a t}}\) is measured in percentage points. It is not minutes. It is the share of the weighted ATUS population that reported doing task \(a\) on the diary day.

## Years

\[
Pre = \{{2017, 2018, 2019, 2021, 2022\}},
\quad
Post = \{{2023, 2024\}}.
\]

The year 2020 is excluded, matching the other models.

## Main Change Model

First, I average \(P_{{a t}}\) within the pre and post periods:

\[
\bar P_{{a p}}
=
\frac{{1}}{{|T_p|}}
\sum_{{t \in T_p}} P_{{a t}}.
\]

Then I take the post-minus-pre change:

\[
\Delta P_a
=
\bar P_{{a,post}}
-
\bar P_{{a,pre}}.
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
\hat\beta_{{1SD}}
=
{main['coef']:.4f}
\quad
SE
=
{main['se']:.4f}
\quad
p
=
{main['p_norm']:.3f}.
\]

Interpretation:

\[
\hat\beta_{{1SD}} = {main['coef']:.4f}
\]

means that a task with an AI exposure score one standard deviation higher had a post-minus-pre participation-rate change that was about \({main['coef']:.4f}\) percentage points different from lower-exposure tasks.

Using the raw 0-to-1 AI exposure score:

\[
\hat\beta
=
{main_raw['coef']:.4f},
\quad
SE
=
{main_raw['se']:.4f},
\quad
p
=
{main_raw['p_norm']:.3f}.
\]

## Pre/Post Slope Comparison

As a descriptive check, I also compare the cross-sectional relationship between participation and AI exposure before and after ChatGPT:

\[
\bar P_{{a p}}
=
\alpha
+
\delta Post_p
+
\gamma s_a
+
\beta(s_a \times Post_p)
+
\varepsilon_{{a p}}.
\]

This gives the same point estimate for \(\beta\), but it is less clean because task-level baseline participation differs enormously across activities.

## Task-Year Fixed-Effects Check

I also estimate the annual task-year fixed-effects version:

\[
P_{{a t}}
=
\alpha_a
+
\lambda_t
+
\beta(s_a \times Post_t)
+
\varepsilon_{{a t}}.
\]

For the weighted participation rate and a one-standard-deviation AI exposure score:

\[
\hat\beta_{{FE,1SD}}
=
{fe['coef']:.4f}
\quad
SE_{{cluster}}
=
{fe['cluster_se_by_task']:.4f}
\quad
p
=
{fe['cluster_p_norm']:.3f}.
\]

## Data Used

\[
N_{{tasks}} = {panel['activity_code'].nunique()},
\quad
N_{{task-years}} = {len(panel)},
\quad
N_{{\text{{change tasks}}}} = {len(change_panel)},
\quad
\bar s = {score_mean:.3f},
\quad
SD(s) = {score_sd:.3f}.
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
"""
    (EXPERIMENT_DIR / "README.md").write_text(readme)


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    panel = load_panel()
    prepost = build_prepost_means(panel)
    change_panel = build_change_panel(prepost)
    change_results = run_change_models(change_panel)
    prepost_results = run_prepost_slope_models(prepost)
    fe_results = run_task_year_fe_models(panel)

    panel.to_csv(RESULTS / "participation_task_year_panel.csv", index=False)
    prepost.to_csv(RESULTS / "prepost_task_means.csv", index=False)
    change_panel.to_csv(RESULTS / "post_minus_pre_task_changes.csv", index=False)
    change_results.to_csv(RESULTS / "post_minus_pre_participation_exposure_results.csv", index=False)
    prepost_results.to_csv(RESULTS / "prepost_participation_exposure_results.csv", index=False)
    fe_results.to_csv(RESULTS / "task_year_fe_participation_exposure_results.csv", index=False)
    write_report(panel, prepost, change_panel, change_results, prepost_results, fe_results)

    print("Wrote participation exposure outputs to", RESULTS)
    print("Main result:")
    print(
        change_results[
            change_results["outcome"].eq("weighted_participation_change_pp")
            & change_results["scale"].eq("one_sd_ai_exposure_score")
        ].to_string(index=False)
    )
    print("Task-year FE check:")
    print(
        fe_results[
            fe_results["outcome"].eq("participation_rate_weighted_pp")
            & fe_results["scale"].eq("one_sd_ai_exposure_score")
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()
