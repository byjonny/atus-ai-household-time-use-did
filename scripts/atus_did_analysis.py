#!/usr/bin/env python3
"""ATUS activity-level DiD analysis for AI-exposed household tasks.

This script uses BLS PDQ metadata to map ATUS activity codes to BLS annual
time-series IDs. Network fetching is deliberately kept outside this script:
run --make-requests, fetch the generated BLS API request JSON files with curl,
then run --analyze.
"""

from __future__ import annotations

import argparse
import html
import json
import math
import re
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw"
RESULTS = ROOT / "results"
DOCS = ROOT / "docs"

SURVEY_JSON = RAW / "survey_tu.json"
SURVEY_URL = "https://data.bls.gov/PDQWeb/survey/tu"
STAT_TYPES = {
    "10101": "avg_hours_per_day",
    "30105": "pct_engaged",
}

HIGH_PRIMARY = {
    "020901": {
        "domain": "finance_accounting",
        "rationale": "Household financial management is the closest ATUS match for accountant/financial-adviser self-production.",
    },
    "080200": {
        "domain": "finance_accounting",
        "rationale": "Financial services and banking captures market-facing household finance interactions.",
    },
    "030201": {
        "domain": "tutoring_education",
        "rationale": "Helping household children with homework is the narrowest tutoring-like household activity.",
    },
    "060300": {
        "domain": "tutoring_education",
        "rationale": "Homework and research captures self-directed education tasks where AI tutors/search assistants are plausible complements.",
    },
    "010300": {
        "domain": "health_medical",
        "rationale": "Health-related self-care captures household health management outside formal care.",
    },
    "080400": {
        "domain": "health_medical",
        "rationale": "Medical and care services captures household interaction with formal care providers.",
    },
    "030300": {
        "domain": "health_medical",
        "rationale": "Activities related to household children's health capture parent-managed health production.",
    },
    "600069": {
        "domain": "legal_admin_proxy",
        "rationale": "ATUS has no clean legal-services code; government services is the closest administrative/legal-navigation proxy.",
    },
}

BROAD_EDUCATION_SENSITIVITY = {
    "030200": {
        "domain": "tutoring_education_broad",
        "rationale": "Broader parent activity related to household children's education; used as sensitivity instead of the narrow homework-help code.",
    }
}

LOW_CONTROL = {
    "020101": {
        "domain": "physical_household",
        "rationale": "Interior cleaning is a physical household task with low direct LLM substitution potential.",
    },
    "020102": {
        "domain": "physical_household",
        "rationale": "Laundry is a physical household task with low direct LLM substitution potential.",
    },
    "020201": {
        "domain": "physical_household",
        "rationale": "Food and drink preparation is mostly physical time use rather than advice/search time.",
    },
    "020203": {
        "domain": "physical_household",
        "rationale": "Kitchen and food cleanup is a physical household task.",
    },
    "020500": {
        "domain": "physical_household",
        "rationale": "Lawn and garden care is a physical household task.",
    },
    "020600": {
        "domain": "physical_household",
        "rationale": "Animal and pet care is mostly physical care time.",
    },
    "020700": {
        "domain": "physical_household",
        "rationale": "Vehicle care by self is mostly physical maintenance time.",
    },
    "020800": {
        "domain": "physical_household",
        "rationale": "Appliance, tool, and toy maintenance is mostly physical maintenance time.",
    },
}


def clean_label(value: str) -> str:
    value = html.unescape(value)
    value = re.sub(r"<[^>]+>", " ", value)
    value = value.replace("\xa0", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def download_metadata() -> None:
    RAW.mkdir(exist_ok=True)
    with urllib.request.urlopen(SURVEY_URL, timeout=60) as response:
        SURVEY_JSON.write_bytes(response.read())


def load_survey(auto_download: bool = False) -> dict:
    if auto_download and not SURVEY_JSON.exists():
        download_metadata()
    with SURVEY_JSON.open() as f:
        return json.load(f)


def activity_labels(survey: dict) -> dict[str, str]:
    features = survey["visualSurvey"]["surveyFeature"]
    activity_feature = next(f for f in features if f["attributeTitle"] == "Activity")
    return {
        item["vm"]: clean_label(item["dm"])
        for item in activity_feature["surveyRefData"]
    }


def build_mapping(survey: dict) -> pd.DataFrame:
    labels = activity_labels(survey)
    master = survey["surveyData"]["seriesMasterDataList"]

    rows = []
    code_meta = {}
    for code, meta in HIGH_PRIMARY.items():
        code_meta[code] = {"analysis_group": "high_primary", **meta}
    for code, meta in BROAD_EDUCATION_SENSITIVITY.items():
        code_meta[code] = {"analysis_group": "high_sensitivity", **meta}
    for code, meta in LOW_CONTROL.items():
        code_meta[code] = {"analysis_group": "low_control", **meta}

    for code, meta in code_meta.items():
        for stat_code, stat_name in STAT_TYPES.items():
            matches = [
                r for r in master
                if r["SEX_CODE"] == "0"
                and r["AGE_CODE"] == "000"
                and r["LFSTATW_CODE"] == "000"
                and r["PROWNHHCHILD_CODE"] == "00"
                and r["PERTYPE_CODE"] == "00"
                and r["ACTCODE_CODE"] == code
                and r["STATTYPE_CODE"] == stat_code
                and r["SERIES_ID"][8] == "A"
            ]
            if len(matches) != 1:
                raise RuntimeError(f"Expected one annual all-days series for {code=} {stat_code=}, got {len(matches)}")
            rows.append({
                "activity_code": code,
                "activity_text": labels.get(code, ""),
                "analysis_group": meta["analysis_group"],
                "domain": meta["domain"],
                "rationale": meta["rationale"],
                "stat_type_code": stat_code,
                "stat_name": stat_name,
                "series_id": matches[0]["SERIES_ID"],
            })
    return pd.DataFrame(rows).sort_values(["analysis_group", "domain", "activity_code", "stat_type_code"])


def make_requests(mapping: pd.DataFrame) -> None:
    RESULTS.mkdir(exist_ok=True)
    RAW.mkdir(exist_ok=True)
    mapping.to_csv(RESULTS / "activity_mapping.csv", index=False)
    series_ids = sorted(mapping["series_id"].unique())
    intervals = [(2003, 2012), (2013, 2022), (2023, 2024)]
    chunk_size = 25
    for start, end in intervals:
        for chunk_idx, offset in enumerate(range(0, len(series_ids), chunk_size), start=1):
            payload = {
                "seriesid": series_ids[offset:offset + chunk_size],
                "startyear": str(start),
                "endyear": str(end),
            }
            out = RAW / f"bls_request_{start}_{end}_chunk{chunk_idx}.json"
            out.write_text(json.dumps(payload, indent=2) + "\n")


def expected_response_files() -> list[Path]:
    request_files = sorted(RAW.glob("bls_request_*_chunk*.json"))
    return [
        RAW / request_file.name.replace("bls_request_", "bls_data_")
        for request_file in request_files
    ]


def load_api_data(mapping: pd.DataFrame) -> pd.DataFrame:
    response_files = expected_response_files()
    missing = [p for p in response_files if not p.exists()]
    if missing:
        raise FileNotFoundError(
            "Missing BLS API responses: "
            + ", ".join(str(p) for p in missing)
            + ". Run --make-requests and fetch the generated request files with curl."
        )

    records = []
    for path in response_files:
        payload = json.loads(path.read_text())
        if payload.get("status") != "REQUEST_SUCCEEDED":
            raise RuntimeError(f"BLS API request failed in {path}: {payload.get('message')}")
        for series in payload["Results"]["series"]:
            sid = series["seriesID"]
            for item in series.get("data", []):
                if item["period"] != "A01":
                    continue
                raw_value = item["value"]
                value = float(raw_value) if raw_value not in {"-", ""} else float("nan")
                records.append({
                    "series_id": sid,
                    "year": int(item["year"]),
                    "value": value,
                })
    values = pd.DataFrame(records).drop_duplicates(["series_id", "year"])
    df = values.merge(mapping, on="series_id", how="left")
    if df["activity_code"].isna().any():
        raise RuntimeError("Some API series IDs were not mapped back to activities.")
    df["minutes_per_day"] = np.where(
        df["stat_name"].eq("avg_hours_per_day"),
        df["value"] * 60.0,
        np.nan,
    )
    df["pct_engaged"] = np.where(
        df["stat_name"].eq("pct_engaged"),
        df["value"],
        np.nan,
    )
    return df.sort_values(["activity_code", "stat_name", "year"])


def normal_pvalue(t_stat: float) -> float:
    if not np.isfinite(t_stat):
        return float("nan")
    return math.erfc(abs(t_stat) / math.sqrt(2.0))


def ols_fit(df: pd.DataFrame, y_col: str, reg_cols: list[str], cluster_col: str | None = None) -> dict:
    y = df[y_col].astype(float).to_numpy()
    X_df = pd.DataFrame({"const": 1.0}, index=df.index)
    for col in reg_cols:
        X_df[col] = df[col].astype(float)
    activity_dummies = pd.get_dummies(df["activity_code"], prefix="act", drop_first=True, dtype=float)
    year_dummies = pd.get_dummies(df["year"], prefix="year", drop_first=True, dtype=float)
    X_df = pd.concat([X_df, activity_dummies, year_dummies], axis=1)
    X = X_df.to_numpy(dtype=float)

    beta = np.linalg.lstsq(X, y, rcond=None)[0]
    resid = y - X @ beta
    n, k = X.shape
    xtx_inv = np.linalg.pinv(X.T @ X)

    sigma2 = float((resid @ resid) / max(n - k, 1))
    cov = sigma2 * xtx_inv
    se = np.sqrt(np.maximum(np.diag(cov), 0.0))

    cluster_se = None
    if cluster_col is not None:
        meat = np.zeros((k, k), dtype=float)
        clusters = df[cluster_col].astype(str).to_numpy()
        unique_clusters = np.unique(clusters)
        for cluster in unique_clusters:
            idx = clusters == cluster
            xg = X[idx, :]
            ug = resid[idx]
            xu = xg.T @ ug
            meat += np.outer(xu, xu)
        g = len(unique_clusters)
        correction = (g / max(g - 1, 1)) * ((n - 1) / max(n - k, 1))
        cov_cluster = correction * xtx_inv @ meat @ xtx_inv
        cluster_se = np.sqrt(np.maximum(np.diag(cov_cluster), 0.0))

    result = {}
    for i, name in enumerate(X_df.columns):
        se_i = float(se[i])
        cse_i = float(cluster_se[i]) if cluster_se is not None else float("nan")
        result[name] = {
            "coef": float(beta[i]),
            "se": se_i,
            "t": float(beta[i] / se_i) if se_i > 0 else float("nan"),
            "p_norm": normal_pvalue(float(beta[i] / se_i)) if se_i > 0 else float("nan"),
            "cluster_se": cse_i,
            "cluster_t": float(beta[i] / cse_i) if cse_i > 0 else float("nan"),
            "cluster_p_norm": normal_pvalue(float(beta[i] / cse_i)) if cse_i > 0 else float("nan"),
        }
    result["_meta"] = {"n": int(n), "k": int(k), "clusters": int(df[cluster_col].nunique()) if cluster_col else None}
    return result


def analysis_panel(df: pd.DataFrame, stat_name: str, high_codes: set[str], low_codes: set[str]) -> pd.DataFrame:
    value_col = "minutes_per_day" if stat_name == "avg_hours_per_day" else "pct_engaged"
    panel = df[df["stat_name"].eq(stat_name)].copy()
    panel = panel[panel["activity_code"].isin(high_codes | low_codes)].copy()
    panel["treated"] = panel["activity_code"].isin(high_codes).astype(int)
    panel["value_for_model"] = panel[value_col].astype(float)
    panel["exposure_group"] = np.where(panel["treated"].eq(1), "high", "low")
    return panel.dropna(subset=["value_for_model"])


def run_did_spec(panel: pd.DataFrame, pre_years: list[int], post_years: list[int], label: str) -> dict:
    keep_years = set(pre_years) | set(post_years)
    reg = panel[panel["year"].isin(keep_years)].copy()
    reg["post"] = reg["year"].isin(post_years).astype(int)
    reg["treated_post"] = reg["treated"] * reg["post"]
    fit = ols_fit(reg, "value_for_model", ["treated_post"], cluster_col="activity_code")
    coef = fit["treated_post"]
    means = (
        reg.groupby(["exposure_group", "post"])["value_for_model"]
        .mean()
        .unstack("post")
        .rename(columns={0: "pre_mean", 1: "post_mean"})
    )
    row = {
        "spec": label,
        "pre_years": f"{min(pre_years)}-{max(pre_years)}",
        "post_years": f"{min(post_years)}-{max(post_years)}",
        "n_obs": fit["_meta"]["n"],
        "activity_clusters": fit["_meta"]["clusters"],
        "did_coef": coef["coef"],
        "se": coef["se"],
        "p_norm": coef["p_norm"],
        "cluster_se": coef["cluster_se"],
        "cluster_p_norm": coef["cluster_p_norm"],
        "high_pre_mean": means.loc["high", "pre_mean"],
        "high_post_mean": means.loc["high", "post_mean"],
        "low_pre_mean": means.loc["low", "pre_mean"],
        "low_post_mean": means.loc["low", "post_mean"],
    }
    return row


def has_pre_post_treated_control(panel: pd.DataFrame, pre_years: list[int], post_years: list[int]) -> bool:
    keep = panel[panel["year"].isin(set(pre_years) | set(post_years))].copy()
    keep["post"] = keep["year"].isin(post_years)
    counts = keep.groupby(["exposure_group", "post"])["value_for_model"].size()
    needed = [("high", False), ("high", True), ("low", False), ("low", True)]
    return all(counts.get(key, 0) > 0 for key in needed)


def run_domain_specs(df: pd.DataFrame, stat_name: str, low_codes: set[str]) -> pd.DataFrame:
    rows = []
    pre = list(range(2015, 2020))
    post = [2023, 2024]
    domains = sorted({meta["domain"] for meta in HIGH_PRIMARY.values()})
    for domain in domains:
        high_codes = {code for code, meta in HIGH_PRIMARY.items() if meta["domain"] == domain}
        panel = analysis_panel(df, stat_name, high_codes, low_codes)
        row = {
            "domain": domain,
            "high_codes": ";".join(sorted(high_codes)),
            "outcome": "minutes_per_day" if stat_name == "avg_hours_per_day" else "pct_engaged",
            "spec": "domain_2015_2019_vs_2023_2024",
        }
        if not has_pre_post_treated_control(panel, pre, post):
            row.update({
                "did_coef": np.nan,
                "cluster_se": np.nan,
                "cluster_p_norm": np.nan,
                "note": "Insufficient nonmissing high-domain observations in pre/post windows.",
            })
        else:
            est = run_did_spec(panel, pre, post, row["spec"])
            row.update(est)
            row["note"] = ""
        rows.append(row)
    return pd.DataFrame(rows)


def event_study(panel: pd.DataFrame, years: list[int], base_year: int) -> pd.DataFrame:
    ev = panel[panel["year"].isin(years)].copy()
    reg_cols = []
    for year in years:
        if year == base_year:
            continue
        col = f"treated_year_{year}"
        ev[col] = ((ev["treated"] == 1) & (ev["year"] == year)).astype(int)
        reg_cols.append(col)
    fit = ols_fit(ev, "value_for_model", reg_cols, cluster_col="activity_code")
    rows = []
    for col in reg_cols:
        year = int(col.rsplit("_", 1)[1])
        item = fit[col]
        rows.append({
            "year": year,
            "base_year": base_year,
            "coef": item["coef"],
            "se": item["se"],
            "cluster_se": item["cluster_se"],
            "p_norm": item["p_norm"],
            "cluster_p_norm": item["cluster_p_norm"],
        })
    return pd.DataFrame(rows).sort_values("year")


def summarize_groups(panel: pd.DataFrame) -> pd.DataFrame:
    return (
        panel.groupby(["year", "exposure_group"])
        .agg(
            total_value=("value_for_model", "sum"),
            mean_activity_value=("value_for_model", "mean"),
            activities=("activity_code", "nunique"),
        )
        .reset_index()
        .sort_values(["year", "exposure_group"])
    )


def key_activity_changes(panel: pd.DataFrame) -> pd.DataFrame:
    pivot = panel.pivot_table(index=["activity_code", "activity_text", "exposure_group", "domain"], columns="year", values="value_for_model")
    rows = []
    for idx, row in pivot.iterrows():
        out = dict(zip(["activity_code", "activity_text", "exposure_group", "domain"], idx))
        for year in [2019, 2022, 2023, 2024]:
            out[f"value_{year}"] = row.get(year, np.nan)
        out["change_2019_2024"] = out["value_2024"] - out["value_2019"]
        out["change_2022_2024"] = out["value_2024"] - out["value_2022"]
        rows.append(out)
    return pd.DataFrame(rows).sort_values(["exposure_group", "domain", "activity_code"])


def write_svg_event_study(event_df: pd.DataFrame, path: Path) -> None:
    width, height = 760, 430
    margin = {"left": 70, "right": 30, "top": 35, "bottom": 60}
    plot_w = width - margin["left"] - margin["right"]
    plot_h = height - margin["top"] - margin["bottom"]
    xs = event_df["year"].tolist()
    ys = event_df["coef"].tolist()
    lower = (event_df["coef"] - 1.96 * event_df["cluster_se"]).tolist()
    upper = (event_df["coef"] + 1.96 * event_df["cluster_se"]).tolist()
    y_min = min(lower + [0.0])
    y_max = max(upper + [0.0])
    pad = max((y_max - y_min) * 0.12, 0.05)
    y_min -= pad
    y_max += pad

    def sx(year: int) -> float:
        return margin["left"] + (year - min(xs)) / (max(xs) - min(xs)) * plot_w

    def sy(value: float) -> float:
        return margin["top"] + (y_max - value) / (y_max - y_min) * plot_h

    points = " ".join(f"{sx(x):.1f},{sy(y):.1f}" for x, y in zip(xs, ys))
    zero_y = sy(0.0)
    elems = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<line x1="{margin["left"]}" y1="{zero_y:.1f}" x2="{width-margin["right"]}" y2="{zero_y:.1f}" stroke="#999" stroke-dasharray="4 4"/>',
        f'<polyline points="{points}" fill="none" stroke="#2b6cb0" stroke-width="2.5"/>',
    ]
    for x, y, lo, hi in zip(xs, ys, lower, upper):
        px = sx(x)
        elems.append(f'<line x1="{px:.1f}" y1="{sy(lo):.1f}" x2="{px:.1f}" y2="{sy(hi):.1f}" stroke="#7397c5" stroke-width="1.4"/>')
        elems.append(f'<circle cx="{px:.1f}" cy="{sy(y):.1f}" r="4" fill="#2b6cb0"/>')
        elems.append(f'<text x="{px:.1f}" y="{height-28}" text-anchor="middle" font-family="Arial" font-size="12">{x}</text>')
    elems.extend([
        f'<line x1="{margin["left"]}" y1="{margin["top"]}" x2="{margin["left"]}" y2="{height-margin["bottom"]}" stroke="#333"/>',
        f'<line x1="{margin["left"]}" y1="{height-margin["bottom"]}" x2="{width-margin["right"]}" y2="{height-margin["bottom"]}" stroke="#333"/>',
        '<text x="20" y="235" transform="rotate(-90 20 235)" font-family="Arial" font-size="13">DiD event coefficient, minutes/day</text>',
        '<text x="380" y="24" text-anchor="middle" font-family="Arial" font-size="15" font-weight="bold">High-exposure vs low-exposure activity trend, 2019 baseline</text>',
        '</svg>',
    ])
    path.write_text("\n".join(elems))


def fmt(x: float, digits: int = 3) -> str:
    if pd.isna(x):
        return "NA"
    return f"{x:.{digits}f}"


def markdown_table(df: pd.DataFrame, max_rows: int | None = None) -> str:
    table = df.copy()
    if max_rows is not None:
        table = table.head(max_rows)
    for col in table.columns:
        if pd.api.types.is_float_dtype(table[col]):
            table[col] = table[col].map(lambda x: fmt(x))
    rows = []
    headers = [str(c) for c in table.columns]
    rows.append("| " + " | ".join(headers) + " |")
    rows.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for _, row in table.iterrows():
        rows.append("| " + " | ".join(str(row[c]) for c in table.columns) + " |")
    return "\n".join(rows)


def write_report(
    mapping: pd.DataFrame,
    did_summary: pd.DataFrame,
    event_minutes: pd.DataFrame,
    group_minutes: pd.DataFrame,
    key_minutes: pd.DataFrame,
    did_pct: pd.DataFrame,
    domain_minutes: pd.DataFrame,
    domain_pct: pd.DataFrame,
) -> None:
    DOCS.mkdir(exist_ok=True)
    high_codes = set(HIGH_PRIMARY)
    low_codes = set(LOW_CONTROL)
    post_total = group_minutes[group_minutes["year"].isin([2023, 2024])]
    pre_total = group_minutes[group_minutes["year"].isin([2015, 2016, 2017, 2018, 2019])]
    bundle_pre = pre_total.groupby("exposure_group")["total_value"].mean()
    bundle_post = post_total.groupby("exposure_group")["total_value"].mean()
    bundle_did = (bundle_post["high"] - bundle_pre["high"]) - (bundle_post["low"] - bundle_pre["low"])

    main = did_summary[(did_summary["outcome"] == "minutes_per_day") & (did_summary["spec"] == "primary_2015_2019_vs_2023_2024")].iloc[0]
    main_pct = did_pct[did_pct["spec"] == "primary_2015_2019_vs_2023_2024"].iloc[0]

    direction_sentence = "negative" if main["did_coef"] < 0 else "positive"

    report = f"""# ATUS DiD Analysis: AI-Exposed Household Activities

Generated from official BLS ATUS PDQ metadata and BLS Public Data API annual series.

## Bottom Line

Using 2023-2024 as the post-ChatGPT period and 2015-2019 as the main pre period, the activity-level fixed-effects DiD estimate is **{fmt(main['did_coef'])} minutes/day per high-exposure activity** relative to low-exposure physical household tasks. The approximate activity-clustered SE is **{fmt(main['cluster_se'])}**.

The sign is **{direction_sentence}**, not positive: the raw high-exposure activity bundle moved from **{fmt(bundle_pre['high'])} minutes/day** in 2015-2019 to **{fmt(bundle_post['high'])} minutes/day** in 2023-2024. The low-exposure physical bundle changed from **{fmt(bundle_pre['low'])}** to **{fmt(bundle_post['low'])} minutes/day**. The simple bundle-level DiD is **{fmt(bundle_did)} minutes/day**.

On the extensive margin, the DiD estimate for percent of the population engaged in the activities is **{fmt(main_pct['did_coef'])} percentage points** with approximate clustered SE **{fmt(main_pct['cluster_se'])}**.

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

High-exposure primary codes: {", ".join(sorted(high_codes))}

Low-exposure physical control codes: {", ".join(sorted(low_codes))}

Full mapping is in `results/activity_mapping.csv`.

## Reproduction Steps

1. Download the BLS ATUS PDQ metadata to `raw/survey_tu.json`.
2. Run `scripts/atus_did_analysis.py --make-requests` to build BLS API request payloads and `results/activity_mapping.csv`.
3. Fetch every `raw/bls_request_*_chunk*.json` payload from the BLS Public Data API into matching `raw/bls_data_*_chunk*.json` response files.
4. Run `scripts/atus_did_analysis.py --analyze`.

The public BLS API caps unauthenticated requests at 10 years and 25 series, so the request payloads are split by year window and series chunk.

## DiD Specification

For activity `a` and year `t`, I estimated:

`Y_at = activity FE + year FE + beta * HighExposure_a * Post_t + error_at`

The unit is an activity-year. `Y` is either average minutes per day or percent of the population engaged. Standard errors are shown both conventional and clustered by activity; with only a small number of activities, inference should be treated as descriptive.

## Main Results

{markdown_table(did_summary)}

## Domain Results

These compare each high-exposure domain separately with the same low-exposure physical control group. The legal/admin proxy is sparse in the BLS annual estimates, so it may be unestimable.

{markdown_table(domain_minutes)}

## Domain Extensive-Margin Results

{markdown_table(domain_pct)}

## Extensive-Margin Results

{markdown_table(did_pct)}

## Event Study

Event-study coefficients are high-exposure activity deviations relative to low-exposure controls, using 2019 as the omitted baseline year and excluding 2020.

{markdown_table(event_minutes)}

SVG chart: `results/event_study_minutes.svg`

## Key Activity Changes

{markdown_table(key_minutes)}

## Interpretation

The evidence does **not** show a post-2022 increase in these ATUS-measured AI-exposed household-professional domains. In the main specification, high-exposure activities are flat to down while the low-exposure physical household controls rise.

This does not falsify the production-boundary hypothesis. ATUS does not observe AI use, quality, avoided market purchases, or whether a task was completed faster. If AI automates household financial planning or medical preparation, measured time could fall even while household output rises. Conversely, if AI enables households to do more of a task themselves, measured time could rise. The ATUS signal is therefore best interpreted as a reduced-form tendency in time allocation, not a direct welfare or production-boundary estimate.

The estimates should also be read with caution because the public BLS annual activity series are rounded/suppressed for some low-incidence activities. That is why legal/admin minutes are not estimable, and why several tiny categories move in 0.6-minute increments.

## Files Produced

- `results/activity_mapping.csv`
- `results/atus_activity_year_values.csv`
- `results/did_summary.csv`
- `results/did_domain_minutes.csv`
- `results/did_domain_pct_engaged.csv`
- `results/event_study_minutes.csv`
- `results/group_year_totals_minutes.csv`
- `results/key_activity_changes_minutes.csv`
- `results/did_pct_engaged.csv`
- `results/event_study_minutes.svg`
"""
    (DOCS / "ATUS_DiD_report.md").write_text(report)


def analyze() -> None:
    RESULTS.mkdir(exist_ok=True)
    DOCS.mkdir(exist_ok=True)
    survey = load_survey()
    mapping = build_mapping(survey)
    mapping.to_csv(RESULTS / "activity_mapping.csv", index=False)
    df = load_api_data(mapping)
    df.to_csv(RESULTS / "atus_activity_year_values.csv", index=False)

    primary_high = set(HIGH_PRIMARY)
    broad_high = (set(HIGH_PRIMARY) - {"030201"}) | {"030200"}
    low = set(LOW_CONTROL)

    specs = [
        ("primary_2015_2019_vs_2023_2024", primary_high, list(range(2015, 2020)), [2023, 2024]),
        ("primary_2017_2019_vs_2023_2024", primary_high, list(range(2017, 2020)), [2023, 2024]),
        ("primary_2003_2019_vs_2023_2024", primary_high, list(range(2003, 2020)), [2023, 2024]),
        ("broad_education_2015_2019_vs_2023_2024", broad_high, list(range(2015, 2020)), [2023, 2024]),
        ("placebo_2015_2017_vs_2018_2019", primary_high, [2015, 2016, 2017], [2018, 2019]),
    ]

    did_rows = []
    did_pct_rows = []
    for label, high_codes, pre, post in specs:
        minutes_panel = analysis_panel(df, "avg_hours_per_day", high_codes, low)
        pct_panel = analysis_panel(df, "pct_engaged", high_codes, low)
        row = run_did_spec(minutes_panel, pre, post, label)
        row["outcome"] = "minutes_per_day"
        did_rows.append(row)
        pct_row = run_did_spec(pct_panel, pre, post, label)
        pct_row["outcome"] = "pct_engaged"
        did_pct_rows.append(pct_row)

    did_summary = pd.DataFrame(did_rows)
    did_pct = pd.DataFrame(did_pct_rows)
    did_summary.to_csv(RESULTS / "did_summary.csv", index=False)
    did_pct.to_csv(RESULTS / "did_pct_engaged.csv", index=False)

    domain_minutes = run_domain_specs(df, "avg_hours_per_day", low)
    domain_pct = run_domain_specs(df, "pct_engaged", low)
    domain_minutes.to_csv(RESULTS / "did_domain_minutes.csv", index=False)
    domain_pct.to_csv(RESULTS / "did_domain_pct_engaged.csv", index=False)

    minutes_panel = analysis_panel(df, "avg_hours_per_day", primary_high, low)
    pct_panel = analysis_panel(df, "pct_engaged", primary_high, low)

    event_years = [y for y in range(2014, 2025) if y != 2020]
    event_minutes = event_study(minutes_panel, event_years, base_year=2019)
    event_pct = event_study(pct_panel, event_years, base_year=2019)
    event_minutes.to_csv(RESULTS / "event_study_minutes.csv", index=False)
    event_pct.to_csv(RESULTS / "event_study_pct_engaged.csv", index=False)
    write_svg_event_study(event_minutes, RESULTS / "event_study_minutes.svg")

    group_minutes = summarize_groups(minutes_panel)
    group_pct = summarize_groups(pct_panel)
    group_minutes.to_csv(RESULTS / "group_year_totals_minutes.csv", index=False)
    group_pct.to_csv(RESULTS / "group_year_totals_pct_engaged.csv", index=False)

    key_minutes = key_activity_changes(minutes_panel)
    key_pct = key_activity_changes(pct_panel)
    key_minutes.to_csv(RESULTS / "key_activity_changes_minutes.csv", index=False)
    key_pct.to_csv(RESULTS / "key_activity_changes_pct_engaged.csv", index=False)

    write_report(mapping, did_summary, event_minutes, group_minutes, key_minutes, did_pct, domain_minutes, domain_pct)

    print("Wrote results to:")
    for path in [
        RESULTS / "activity_mapping.csv",
        RESULTS / "atus_activity_year_values.csv",
        RESULTS / "did_summary.csv",
        RESULTS / "did_domain_minutes.csv",
        RESULTS / "did_domain_pct_engaged.csv",
        RESULTS / "did_pct_engaged.csv",
        RESULTS / "event_study_minutes.csv",
        RESULTS / "group_year_totals_minutes.csv",
        RESULTS / "key_activity_changes_minutes.csv",
        DOCS / "ATUS_DiD_report.md",
    ]:
        print(f"  {path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--make-requests", action="store_true")
    parser.add_argument("--analyze", action="store_true")
    parser.add_argument("--download-metadata", action="store_true")
    args = parser.parse_args()

    if args.download_metadata:
        download_metadata()

    survey = load_survey(auto_download=args.make_requests)
    mapping = build_mapping(survey)

    if args.make_requests:
        make_requests(mapping)
        print("Wrote BLS API request payloads:")
        for path in sorted(RAW.glob("bls_request_*.json")):
            print(f"  {path}")
        print("Then fetch with curl, e.g.:")
        print("  curl -L -H 'Content-type: application/json' -d @raw/bls_request_2003_2012.json -o raw/bls_2003_2012.json https://api.bls.gov/publicAPI/v2/timeseries/data/")
    if args.analyze:
        analyze()
    if not args.make_requests and not args.analyze:
        parser.error("Pass --make-requests and/or --analyze")


if __name__ == "__main__":
    main()
