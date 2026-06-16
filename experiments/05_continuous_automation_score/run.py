#!/usr/bin/env python3
"""Continuous automation-score task-year fixed-effects model.

Model:

    minutes_{a,t} = alpha_a + lambda_t
                    + beta * automation_score_a * Post_t
                    + epsilon_{a,t}

The outcome is a TUFNWGTP-weighted annual mean of minutes/day for each
ATUS task-year. The score is continuous rather than a binary treated/control
indicator.
"""

from __future__ import annotations

import html
import math
import re
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT_DIR = Path(__file__).resolve().parent
RAW = ROOT / "raw"
SCORE_FILE = ROOT / "experiments" / "03_pre_ai_exposure" / "scores" / "activity_ai_scores.csv"
RESULTS = EXPERIMENT_DIR / "results"

SUM_ZIP = RAW / "atussum-0324.zip"
SUMMARY_MEMBER = "atussum_0324.dat"

MODEL_YEARS = [2017, 2018, 2019, 2021, 2022, 2023, 2024]
PRE_YEARS = [2017, 2018, 2019, 2021, 2022]
POST_YEARS = [2023, 2024]


def clean_label(value: str) -> str:
    value = html.unescape(str(value))
    value = value.replace("\xa0", " ")
    return re.sub(r"\s+", " ", value).strip()


def normal_pvalue(t_stat: float) -> float:
    if not np.isfinite(t_stat):
        return float("nan")
    return math.erfc(abs(t_stat) / math.sqrt(2.0))


def weighted_mean(values: pd.Series, weights: pd.Series) -> float:
    denom = float(weights.sum())
    if denom <= 0:
        return float("nan")
    return float((values.astype(float) * weights.astype(float)).sum() / denom)


def read_summary_header() -> list[str]:
    with zipfile.ZipFile(SUM_ZIP) as zf:
        with zf.open(SUMMARY_MEMBER) as f:
            return f.readline().decode("utf-8").strip().split(",")


def activity_labels_from_summary_setup() -> dict[str, str]:
    label_re = re.compile(r'label\s+t(\d{6})\s*=\s*"([^"]*)";', re.IGNORECASE)
    with zipfile.ZipFile(SUM_ZIP) as zf:
        text = zf.read("atussum_0324.sas").decode("latin1")
    return {code: clean_label(label) for code, label in label_re.findall(text)}


def load_scores(activity_codes: list[str]) -> pd.DataFrame:
    scores = pd.read_csv(SCORE_FILE, dtype={"activity_code": str})
    scores["activity_code"] = scores["activity_code"].str.zfill(6)
    scores = scores[scores["activity_code"].isin(activity_codes)].copy()
    labels = activity_labels_from_summary_setup()
    scores["activity_text"] = scores["activity_code"].map(labels).fillna(scores.get("activity_text", ""))
    for col in ["automation_score", "augmentation_score", "ai_exposure_score"]:
        scores[col] = pd.to_numeric(scores[col], errors="coerce").fillna(0.0).clip(0, 1)
    score_sd = scores["automation_score"].std(ddof=0)
    scores["automation_score_z"] = (
        (scores["automation_score"] - scores["automation_score"].mean()) / score_sd
        if score_sd > 0 else 0.0
    )
    return scores


def build_task_year_panel() -> pd.DataFrame:
    if not SUM_ZIP.exists():
        raise FileNotFoundError(f"Missing {SUM_ZIP}. Put the official BLS atussum-0324.zip in raw/.")
    if not SCORE_FILE.exists():
        raise FileNotFoundError(f"Missing {SCORE_FILE}. Run or restore experiment 03 first.")

    header = read_summary_header()
    tcols = sorted(c for c in header if re.fullmatch(r"t\d{6}", c))
    activity_codes = [c[1:] for c in tcols]
    scores = load_scores(activity_codes)
    scored_codes = scores["activity_code"].tolist()
    usecols = ["TUCASEID", "TUYEAR", "TUFNWGTP"] + [f"t{code}" for code in scored_codes]
    with zipfile.ZipFile(SUM_ZIP) as zf:
        with zf.open(SUMMARY_MEMBER) as f:
            df = pd.read_csv(f, usecols=usecols)
    df = df[df["TUFNWGTP"].gt(0)].copy()

    score_lookup = scores.set_index("activity_code")
    rows = []
    for year, g in df.groupby("TUYEAR", sort=True):
        if int(year) not in MODEL_YEARS:
            continue
        for code in scored_codes:
            col = f"t{code}"
            active = g[col].gt(0)
            score_row = score_lookup.loc[code]
            rows.append({
                "activity_code": code,
                "activity_text": score_row["activity_text"],
                "year": int(year),
                "weighted_mean_minutes": weighted_mean(g[col], g["TUFNWGTP"]),
                "sample_n_positive_minutes": int(active.sum()),
                "weighted_engaged_population": float(g.loc[active, "TUFNWGTP"].sum()),
                "respondents_total": int(len(g)),
                "automation_score": float(score_row["automation_score"]),
                "automation_score_z": float(score_row["automation_score_z"]),
                "augmentation_score": float(score_row["augmentation_score"]),
                "ai_exposure_score": float(score_row["ai_exposure_score"]),
            })
    panel = pd.DataFrame(rows)
    panel["post_2023plus"] = panel["year"].isin(POST_YEARS).astype(float)
    panel["automation_x_post"] = panel["automation_score"] * panel["post_2023plus"]
    panel["automation_z_x_post"] = panel["automation_score_z"] * panel["post_2023plus"]
    return panel


def ols_with_task_year_fe(df: pd.DataFrame, y_col: str, reg_cols: list[str]) -> dict:
    work = df.dropna(subset=[y_col] + reg_cols).copy()
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


def run_models(panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for reg_col, scale in [
        ("automation_x_post", "raw_0_to_1_score"),
        ("automation_z_x_post", "one_sd_score"),
    ]:
        fit = ols_with_task_year_fe(panel, "weighted_mean_minutes", [reg_col])
        term = fit[reg_col]
        rows.append({
            "model": "task_year_fe_continuous_automation",
            "outcome": "TUFNWGTP-weighted task minutes per day",
            "regressor": reg_col,
            "scale": scale,
            "coef": term["coef"],
            "se": term["se"],
            "p_norm": term["p_norm"],
            "cluster_se_by_task": term["cluster_se"],
            "cluster_p_norm": term["cluster_p_norm"],
            "n_task_years": fit["_meta"]["n"],
            "task_clusters": fit["_meta"]["clusters"],
            "model_years": ",".join(map(str, MODEL_YEARS)),
            "pre_years": ",".join(map(str, PRE_YEARS)),
            "post_years": ",".join(map(str, POST_YEARS)),
        })
    return pd.DataFrame(rows)


def summarize_scores(panel: pd.DataFrame) -> pd.DataFrame:
    tasks = panel.drop_duplicates("activity_code").copy()
    return pd.DataFrame([{
        "tasks": int(tasks["activity_code"].nunique()),
        "automation_mean": tasks["automation_score"].mean(),
        "automation_sd": tasks["automation_score"].std(ddof=0),
        "automation_min": tasks["automation_score"].min(),
        "automation_max": tasks["automation_score"].max(),
        "share_tasks_baseline_005": float(tasks["automation_score"].eq(0.05).mean()),
        "share_tasks_ge_050": float(tasks["automation_score"].ge(0.50).mean()),
    }])


def top_tasks(panel: pd.DataFrame) -> pd.DataFrame:
    tasks = (
        panel.drop_duplicates("activity_code")
        .sort_values(["automation_score", "activity_code"], ascending=[False, True])
        [["activity_code", "activity_text", "automation_score", "augmentation_score", "ai_exposure_score"]]
    )
    return tasks.head(40)


def write_report(results: pd.DataFrame, score_summary: pd.DataFrame, top: pd.DataFrame) -> None:
    raw = results[results["scale"].eq("raw_0_to_1_score")].iloc[0]
    sd = results[results["scale"].eq("one_sd_score")].iloc[0]
    summary = score_summary.iloc[0]
    top_table = top.head(15).copy()
    top_rows = []
    for row in top_table.itertuples(index=False):
        top_rows.append(
            f"| {row.activity_code} | {row.activity_text} | {row.automation_score:.2f} |"
        )
    top_md = "\n".join([
        "| code | task | automation score |",
        "| --- | --- | ---: |",
        *top_rows,
    ])
    report = rf"""# Continuous Automation-Score Task-Year FE Model

This experiment replaces the binary AI-exposed indicator with a continuous automation score for each ATUS task.

## Estimand

Let \(a\) index ATUS activities and \(t\) index years. For every activity-year, I first compute the survey-weighted average minutes per day:

\[
m_{{a t}}
=
\frac{{\sum_i w_{{i t}} \, \text{{minutes}}_{{i a t}}}}
{{\sum_i w_{{i t}}}},
\]

where \(w_{{i t}}\) is the ATUS final person weight \(TUFNWGTP\).

The main fixed-effects model is:

\[
m_{{a t}}
=
\alpha_a
+
\lambda_t
+
\beta \left( s_a \times \text{{Post}}_t \right)
+
\varepsilon_{{a t}},
\]

where:

- \(\alpha_a\) are task fixed effects,
- \(\lambda_t\) are year fixed effects,
- \(s_a\) is the continuous automation score of task \(a\),
- \(\text{{Post}}_t = 1\) for 2023 and 2024,
- standard errors are clustered by ATUS task.

## What I Did

1. Loaded the ATUS Activity Summary file, `atussum-0324.zip`.
2. Used all task columns available in the summary file that also have a score in `experiments/03_pre_ai_exposure/scores/activity_ai_scores.csv`.
3. Built a task-year panel for 2017, 2018, 2019, 2021, 2022, 2023, and 2024.
4. For each task-year, computed \(m_{{a t}}\), the \(TUFNWGTP\)-weighted mean minutes per day.
5. Merged each task with its continuous `automation_score`.
6. Estimated the model with task fixed effects and year fixed effects.
7. Reported the coefficient both for the raw 0-to-1 score and for a one-standard-deviation increase in automation score.

## Main Results

Raw automation score, from 0 to 1:

\[
\hat\beta = {raw['coef']:.3f},
\quad
SE_{{cluster}} = {raw['cluster_se_by_task']:.3f},
\quad
p = {raw['cluster_p_norm']:.3f}.
\]

One standard deviation increase in automation score:

\[
\hat\beta_{{1SD}} = {sd['coef']:.3f},
\quad
SE_{{cluster}} = {sd['cluster_se_by_task']:.3f},
\quad
p = {sd['cluster_p_norm']:.3f}.
\]

## Interpretation

The preferred interpretation is the one-standard-deviation estimate:

\[
\hat\beta_{{1SD}} = {sd['coef']:.3f}.
\]

This means that, after 2022, a task with an automation score one standard deviation higher changed by about `{sd['coef']:.3f}` minutes per day relative to lower-scored tasks, after controlling for task fixed effects and year fixed effects.

## Score Distribution

\[
N_{{tasks}} = {int(summary['tasks'])},
\quad
\bar s = {summary['automation_mean']:.3f},
\quad
SD(s) = {summary['automation_sd']:.3f},
\quad
\min(s) = {summary['automation_min']:.3f},
\quad
\max(s) = {summary['automation_max']:.3f}.
\]

Share of tasks with baseline score \(0.05\): `{summary['share_tasks_baseline_005']:.1%}`

Share of tasks with score at least \(0.50\): `{summary['share_tasks_ge_050']:.1%}`

## Highest-Scored Tasks

{top_md}

## Critical Notes

This is cleaner than the binary task DiD because it uses all scored tasks and uses the intensity of automation exposure rather than a hand-picked treated/control split.

But it is still descriptive. The automation scores are constructed, many tasks receive the same low baseline score, and ATUS does not observe actual AI adoption. A negative \(\beta\) is consistent with time-saving on more automatable tasks, but it is not proof that AI caused the change.

## Files

- `results/task_year_panel.csv`
- `results/continuous_automation_results.csv`
- `results/automation_score_summary.csv`
- `results/top_automation_tasks.csv`
"""
    (EXPERIMENT_DIR / "README.md").write_text(report)


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    panel = build_task_year_panel()
    results = run_models(panel)
    score_summary = summarize_scores(panel)
    top = top_tasks(panel)

    panel.to_csv(RESULTS / "task_year_panel.csv", index=False)
    results.to_csv(RESULTS / "continuous_automation_results.csv", index=False)
    score_summary.to_csv(RESULTS / "automation_score_summary.csv", index=False)
    top.to_csv(RESULTS / "top_automation_tasks.csv", index=False)
    write_report(results, score_summary, top)

    print("Wrote continuous automation-score outputs to", RESULTS)
    print("Report:", EXPERIMENT_DIR / "README.md")


if __name__ == "__main__":
    main()
