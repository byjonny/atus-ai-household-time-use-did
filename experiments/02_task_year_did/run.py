#!/usr/bin/env python3
"""Simple task-year DiD for AI-exposed vs low-exposure ATUS tasks.

Model:

    minutes_task,t = task FE + year FE
                     + beta * AI_exposed_task * Post_t + error_task,t

The outcome is a TUFNWGTP-weighted annual mean of minutes/day for each task.
This is a transparent descriptive DiD-style check, not a strong causal design.
"""

from __future__ import annotations

import math
import html
import re
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT_DIR = Path(__file__).resolve().parent
RAW = ROOT / "raw"
RESULTS = EXPERIMENT_DIR / "results"
DOCS = EXPERIMENT_DIR

SUM_ZIP = RAW / "atussum-0324.zip"
SUMMARY_MEMBER = "atussum_0324.dat"

PRE_YEARS = [2017, 2018, 2019, 2021, 2022]
POST_YEARS = [2023, 2024]

AI_EXPOSED_CODES = {
    "020901": "Financial management",
    "020902": "Household and personal organization and planning",
    "020903": "Household and personal mail and messages",
    "020904": "Household and personal e-mail and messages",
    "030201": "Homework with household children",
    "060301": "Research/homework for class for degree/certification",
    "060302": "Research/homework for class for personal interest",
    "060399": "Research/homework, n.e.c.",
    "080201": "Banking",
    "080202": "Using other financial services",
    "080299": "Using financial services and banking, n.e.c.",
    "080301": "Using legal services",
    "080399": "Using legal services, n.e.c.",
    "080401": "Using health and care services outside the home",
    "080402": "Using in-home health and care services",
    "080499": "Using medical services, n.e.c.",
    "100103": "Obtaining licenses and paying fines, fees, taxes",
    "100199": "Using government services, n.e.c.",
}

LOW_EXPOSURE_CODES = {
    "020101": "Interior cleaning",
    "020102": "Laundry",
    "020103": "Sewing, repairing, and maintaining textiles",
    "020104": "Storing interior household items, including food",
    "020201": "Food and drink preparation",
    "020202": "Food presentation",
    "020203": "Kitchen and food cleanup",
    "020301": "Interior arrangement, decoration, and repairs",
    "020302": "Building and repairing furniture",
    "020303": "Heating and cooling",
    "020401": "Exterior cleaning",
    "020402": "Exterior repair, improvements, and decoration",
    "020501": "Lawn, garden, and houseplant care",
    "020502": "Ponds, pools, and hot tubs",
    "020599": "Lawn and garden, n.e.c.",
    "020681": "Care for animals and pets",
    "020701": "Vehicle repair and maintenance by self",
    "020801": "Appliance, tool, and toy setup/repair/maintenance by self",
    "020899": "Appliances and tools, n.e.c.",
}

MODEL_YEARS = PRE_YEARS + POST_YEARS
BASE_YEAR = 2022


def clean_label(value: str) -> str:
    value = html.unescape(str(value))
    value = value.replace("\xa0", " ")
    return re.sub(r"\s+", " ", value).strip()


def activity_labels_from_summary_setup() -> dict[str, str]:
    label_re = re.compile(r'label\s+t(\d{6})\s*=\s*"([^"]*)";', re.IGNORECASE)
    with zipfile.ZipFile(SUM_ZIP) as zf:
        text = zf.read("atussum_0324.sas").decode("latin1")
    return {code: clean_label(label) for code, label in label_re.findall(text)}


def read_summary(codes: set[str]) -> pd.DataFrame:
    if not SUM_ZIP.exists():
        raise FileNotFoundError(f"Missing {SUM_ZIP}. Put the official BLS atussum-0324.zip in raw/.")
    usecols = ["TUCASEID", "TUYEAR", "TUFNWGTP"] + [f"t{code}" for code in sorted(codes)]
    with zipfile.ZipFile(SUM_ZIP) as zf:
        with zf.open(SUMMARY_MEMBER) as f:
            df = pd.read_csv(f, usecols=usecols)
    return df[df["TUFNWGTP"].gt(0)].copy()


def weighted_mean(values: pd.Series, weights: pd.Series) -> float:
    denom = float(weights.sum())
    if denom <= 0:
        return float("nan")
    return float((values * weights).sum() / denom)


def normal_pvalue(t_stat: float) -> float:
    if not np.isfinite(t_stat):
        return float("nan")
    return math.erfc(abs(t_stat) / math.sqrt(2.0))


def build_task_year_panel() -> pd.DataFrame:
    labels = activity_labels_from_summary_setup()
    all_codes = sorted(set(AI_EXPOSED_CODES) | set(LOW_EXPOSURE_CODES))
    df = read_summary(set(all_codes))

    rows = []
    for year, g in df.groupby("TUYEAR", sort=True):
        for code in all_codes:
            col = f"t{code}"
            active = g[col].gt(0)
            rows.append({
                "activity_code": code,
                "activity_text": labels.get(code, ""),
                "bundle": "ai_exposed" if code in AI_EXPOSED_CODES else "low_exposure_physical",
                "treated_ai": 1 if code in AI_EXPOSED_CODES else 0,
                "year": int(year),
                "weighted_mean_minutes": weighted_mean(g[col], g["TUFNWGTP"]),
                "sample_n_positive_minutes": int(active.sum()),
                "weighted_engaged_population": float(g.loc[active, "TUFNWGTP"].sum()),
                "respondents_total": int(len(g)),
            })
    panel = pd.DataFrame(rows)
    panel["post_2023plus"] = panel["year"].isin(POST_YEARS).astype(int)
    panel["treated_x_post"] = panel["treated_ai"] * panel["post_2023plus"]
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


def run_main_did(panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    work = panel[panel["year"].isin(MODEL_YEARS)].copy()
    fit = ols_with_task_year_fe(work, "weighted_mean_minutes", ["treated_x_post"])
    term = fit["treated_x_post"]

    means = (
        work.assign(period=np.where(work["year"].isin(POST_YEARS), "post", "pre"))
        .groupby(["bundle", "period"])["weighted_mean_minutes"]
        .mean()
        .unstack("period")
        .reset_index()
    )
    means["post_minus_pre"] = means["post"] - means["pre"]

    ai_change = float(means.loc[means["bundle"].eq("ai_exposed"), "post_minus_pre"].iloc[0])
    low_change = float(means.loc[means["bundle"].eq("low_exposure_physical"), "post_minus_pre"].iloc[0])
    results = pd.DataFrame([{
        "model": "task_year_did_task_fe_year_fe",
        "outcome": "TUFNWGTP-weighted task minutes per day",
        "pre_years": ",".join(map(str, PRE_YEARS)),
        "post_years": ",".join(map(str, POST_YEARS)),
        "coef_treated_x_post": term["coef"],
        "se": term["se"],
        "p_norm": term["p_norm"],
        "cluster_se_by_task": term["cluster_se"],
        "cluster_p_norm": term["cluster_p_norm"],
        "n_task_years": fit["_meta"]["n"],
        "task_clusters": fit["_meta"]["clusters"],
        "ai_exposed_tasks": int(work.loc[work["treated_ai"].eq(1), "activity_code"].nunique()),
        "low_exposure_tasks": int(work.loc[work["treated_ai"].eq(0), "activity_code"].nunique()),
        "simple_ai_change": ai_change,
        "simple_low_change": low_change,
        "simple_difference_in_differences": ai_change - low_change,
    }])
    return results, means


def run_event_study(panel: pd.DataFrame) -> pd.DataFrame:
    work = panel[panel["year"].isin(MODEL_YEARS)].copy()
    reg_cols = []
    for year in MODEL_YEARS:
        if year == BASE_YEAR:
            continue
        col = f"treated_x_year_{year}"
        work[col] = work["treated_ai"] * work["year"].eq(year).astype(int)
        reg_cols.append(col)
    fit = ols_with_task_year_fe(work, "weighted_mean_minutes", reg_cols)
    rows = []
    for col in reg_cols:
        year = int(col.rsplit("_", 1)[1])
        term = fit[col]
        rows.append({
            "year": year,
            "base_year": BASE_YEAR,
            "coef": term["coef"],
            "cluster_se_by_task": term["cluster_se"],
            "cluster_p_norm": term["cluster_p_norm"],
        })
    return pd.DataFrame(rows).sort_values("year")


def write_event_svg(event: pd.DataFrame, path: Path) -> None:
    width, height = 800, 440
    ml, mr, mt, mb = 75, 35, 35, 65
    years = event["year"].tolist()
    coef = event["coef"].tolist()
    lo = (event["coef"] - 1.96 * event["cluster_se_by_task"]).tolist()
    hi = (event["coef"] + 1.96 * event["cluster_se_by_task"]).tolist()
    ymin = min(lo + [0])
    ymax = max(hi + [0])
    pad = max((ymax - ymin) * 0.12, 0.5)
    ymin -= pad
    ymax += pad

    def sx(year: int) -> float:
        return ml + (year - min(years)) / (max(years) - min(years)) * (width - ml - mr)

    def sy(value: float) -> float:
        return mt + (ymax - value) / (ymax - ymin) * (height - mt - mb)

    elems = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<text x="400" y="24" text-anchor="middle" font-family="Arial" font-size="16" font-weight="bold">Task-year DiD event study, 2022 baseline</text>',
        f'<line x1="{ml}" y1="{sy(0):.1f}" x2="{width-mr}" y2="{sy(0):.1f}" stroke="#999" stroke-dasharray="4 4"/>',
        f'<line x1="{ml}" y1="{mt}" x2="{ml}" y2="{height-mb}" stroke="#333"/>',
        f'<line x1="{ml}" y1="{height-mb}" x2="{width-mr}" y2="{height-mb}" stroke="#333"/>',
        '<text x="24" y="230" transform="rotate(-90 24 230)" font-family="Arial" font-size="13">AI vs low-exposure difference, min/day</text>',
    ]
    pts = " ".join(f"{sx(x):.1f},{sy(y):.1f}" for x, y in zip(years, coef))
    elems.append(f'<polyline points="{pts}" fill="none" stroke="#1f6f8b" stroke-width="2.6"/>')
    for year, y, a, b in zip(years, coef, lo, hi):
        x = sx(year)
        elems.append(f'<line x1="{x:.1f}" y1="{sy(a):.1f}" x2="{x:.1f}" y2="{sy(b):.1f}" stroke="#77a9bb" stroke-width="1.4"/>')
        elems.append(f'<circle cx="{x:.1f}" cy="{sy(y):.1f}" r="4" fill="#1f6f8b"/>')
        elems.append(f'<text x="{x:.1f}" y="{height-34}" text-anchor="middle" font-family="Arial" font-size="12">{year}</text>')
    elems.append("</svg>")
    path.write_text("\n".join(elems))


def write_report(results: pd.DataFrame, means: pd.DataFrame, event: pd.DataFrame) -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    row = results.iloc[0]
    ai = means[means["bundle"].eq("ai_exposed")].iloc[0]
    low = means[means["bundle"].eq("low_exposure_physical")].iloc[0]
    event_lookup = event.set_index("year")
    pre_nonflat = event[event["year"].lt(BASE_YEAR)].copy()
    strongest_pre = pre_nonflat.iloc[pre_nonflat["coef"].abs().argmax()]
    report = f"""# Simple Task-Year DiD

This is the simple regression version of the bundle comparison.

## Model

`minutes_task,t = task FE + year FE + beta * AI_exposed_task x Post_t + error_task,t`

Outcome: TUFNWGTP-weighted average minutes/day for each ATUS task-year.

Post period: {", ".join(map(str, POST_YEARS))}

Pre period: {", ".join(map(str, PRE_YEARS))}

Tasks:

- AI-exposed: {int(row['ai_exposed_tasks'])}
- Low-exposure physical: {int(row['low_exposure_tasks'])}

## Main Result

Beta:

`{row['coef_treated_x_post']:.3f} minutes/day`

Clustered SE by task:

`{row['cluster_se_by_task']:.3f}`

Approximate p-value:

`{row['cluster_p_norm']:.3f}`

## Descriptive Means

| bundle | pre | post | post - pre |
| --- | ---: | ---: | ---: |
| AI-exposed | {ai['pre']:.3f} | {ai['post']:.3f} | {ai['post_minus_pre']:.3f} |
| Low-exposure physical | {low['pre']:.3f} | {low['post']:.3f} | {low['post_minus_pre']:.3f} |

Simple difference of changes:

`{row['simple_difference_in_differences']:.3f} minutes/day`

## Event-Study Sanity Check

Baseline year: {BASE_YEAR}

Post estimates:

- 2023: {event_lookup.loc[2023, 'coef']:.3f} minutes/day, p = {event_lookup.loc[2023, 'cluster_p_norm']:.3f}
- 2024: {event_lookup.loc[2024, 'coef']:.3f} minutes/day, p = {event_lookup.loc[2024, 'cluster_p_norm']:.3f}

Pre-trend warning:

The pre-period estimates are not perfectly flat. The largest pre-period deviation is {int(strongest_pre['year'])}: {strongest_pre['coef']:.3f} minutes/day, p = {strongest_pre['cluster_p_norm']:.3f}.

That means this should be read as a simple descriptive DiD, not as strong causal evidence.

## Interpretation

A negative beta means AI-exposed tasks fell more, or rose less, than low-exposure physical tasks after 2022, after controlling for task fixed effects and year fixed effects.

This is still a descriptive check. It does not prove that AI caused the change because treated and comparison tasks may have different underlying trends.

## Files

- `results/task_year_panel.csv`
- `results/task_year_did_results.csv`
- `results/task_year_did_means.csv`
- `results/task_year_event_study.csv`
- `results/task_year_event_study.svg`
"""
    (DOCS / "README.md").write_text(report)


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    panel = build_task_year_panel()
    results, means = run_main_did(panel)
    event = run_event_study(panel)

    panel.to_csv(RESULTS / "task_year_panel.csv", index=False)
    results.to_csv(RESULTS / "task_year_did_results.csv", index=False)
    means.to_csv(RESULTS / "task_year_did_means.csv", index=False)
    event.to_csv(RESULTS / "task_year_event_study.csv", index=False)
    write_event_svg(event, RESULTS / "task_year_event_study.svg")
    write_report(results, means, event)

    print("Wrote simple task-year DiD outputs to", RESULTS)
    print("Report:", DOCS / "README.md")


if __name__ == "__main__":
    main()
