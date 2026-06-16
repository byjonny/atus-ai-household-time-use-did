#!/usr/bin/env python3
"""Blank-et-al.-style predetermined AI exposure design with ATUS microdata.

This is a respondent-microdata pipeline using the official BLS ATUS
2003-2024 public-use files. It creates transparent activity-level AI scores,
computes pre-ChatGPT exposure for demographic groups, builds group-year
outcomes, and estimates DiD/event-study models.
"""

from __future__ import annotations

import argparse
import html
import json
import math
import re
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw"
SCORES = ROOT / "scores"
RESULTS = ROOT / "results" / "blank_exposure"
DOCS = ROOT / "docs"

RESP_ZIP = RAW / "atusresp-0324.zip"
SUM_ZIP = RAW / "atussum-0324.zip"
ACT_ZIP = RAW / "atusact-0324.zip"
SURVEY_JSON = RAW / "survey_tu.json"
SCORE_FILE = SCORES / "activity_ai_scores.csv"

SUMMARY_MEMBER = "atussum_0324.dat"

BASE_PRE_YEARS = [2017, 2018, 2019, 2021]
BASE_MODEL_YEARS = [2017, 2018, 2019, 2021, 2022, 2023, 2024]
BASE_EVENT_YEAR = 2022


def clean_label(value: str) -> str:
    value = html.unescape(str(value))
    value = re.sub(r"<[^>]+>", " ", value)
    value = value.replace("\xa0", " ")
    return re.sub(r"\s+", " ", value).strip()


def ensure_inputs() -> None:
    missing = [p for p in [RESP_ZIP, SUM_ZIP, ACT_ZIP] if not p.exists() or p.stat().st_size < 10_000]
    if missing:
        raise FileNotFoundError(
            "Missing official BLS ATUS microdata ZIPs: "
            + ", ".join(str(p) for p in missing)
            + ". Put atusresp-0324.zip, atussum-0324.zip, and atusact-0324.zip in raw/."
        )


def zip_members(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as zf:
        return zf.namelist()


def read_header_from_zip(path: Path, member: str) -> list[str]:
    with zipfile.ZipFile(path) as zf:
        with zf.open(member) as f:
            return f.readline().decode("utf-8").strip().split(",")


def activity_labels_from_summary_setup() -> dict[str, str]:
    if not SUM_ZIP.exists():
        return {}
    label_re = re.compile(r'label\s+t(\d{6})\s*=\s*"([^"]*)";', re.IGNORECASE)
    with zipfile.ZipFile(SUM_ZIP) as zf:
        try:
            text = zf.read("atussum_0324.sas").decode("latin1")
        except KeyError:
            return {}
    return {code: clean_label(label) for code, label in label_re.findall(text)}


def activity_columns(columns: list[str]) -> list[str]:
    return sorted([c for c in columns if re.fullmatch(r"t\d{6}", c)])


def activity_labels_from_metadata(activity_codes: list[str]) -> pd.DataFrame:
    labels = {code: "" for code in activity_codes}
    labels.update({code: text for code, text in activity_labels_from_summary_setup().items() if code in labels})
    if SURVEY_JSON.exists():
        with SURVEY_JSON.open() as f:
            survey = json.load(f)
        activity_feature = next(
            item for item in survey["visualSurvey"]["surveyFeature"]
            if item["attributeTitle"] == "Activity"
        )
        labels.update({
            item["vm"]: clean_label(item["dm"])
            for item in activity_feature["surveyRefData"]
            if item.get("vm") in labels and not labels[item["vm"]]
        })
    return pd.DataFrame({
        "activity_code": list(labels.keys()),
        "activity_text": [labels[c] for c in labels],
    })


def score_activity(code: str, text: str) -> tuple[float, float]:
    """Transparent rule-based placeholder scores.

    These are not expert scores. They make the design runnable and auditable.
    A researcher can replace scores/activity_ai_scores.csv with external
    expert/LLM scores using the same columns.
    """
    t = text.lower()
    automation = 0.05
    augmentation = 0.05

    # Core household-professional, cognitive, informational, and admin tasks.
    if code.startswith(("0209", "0802", "0804", "1001", "1601")):
        automation = max(automation, 0.60)
        augmentation = max(augmentation, 0.65)
    if code.startswith(("0302", "0603")):
        automation = max(automation, 0.35)
        augmentation = max(augmentation, 0.80)
    if code.startswith("0601"):
        automation = max(automation, 0.20)
        augmentation = max(augmentation, 0.55)
    if code.startswith(("070", "080", "090", "100")):
        automation = max(automation, 0.25)
        augmentation = max(augmentation, 0.35)

    high_terms = [
        "financial", "bank", "homework", "research", "class", "degree",
        "education", "medical", "health", "government", "legal",
        "mail", "e-mail", "email", "message", "telephone", "organization",
        "planning", "computer", "professional", "services",
    ]
    if any(term in t for term in high_terms):
        automation = max(automation, 0.45)
        augmentation = max(augmentation, 0.60)

    very_high_terms = ["financial management", "financial services", "homework", "research", "medical", "government services"]
    if any(term in t for term in very_high_terms):
        automation = max(automation, 0.65)
        augmentation = max(augmentation, 0.75)

    # Mostly physical/presence-based activities.
    low_terms = [
        "sleep", "groom", "clean", "laundry", "food", "kitchen", "lawn",
        "garden", "vehicle", "walking", "exercise", "sports", "eating",
        "drinking", "travel", "waiting", "personal care",
    ]
    if any(term in t for term in low_terms) and not any(term in t for term in high_terms):
        automation = min(automation, 0.10)
        augmentation = min(augmentation, 0.15)

    return round(automation, 3), round(augmentation, 3)


def create_or_load_scores(activity_codes: list[str]) -> pd.DataFrame:
    SCORES.mkdir(exist_ok=True)
    labels = activity_labels_from_metadata(activity_codes)
    if SCORE_FILE.exists():
        scores = pd.read_csv(SCORE_FILE, dtype={"activity_code": str})
        required = {"activity_code", "automation_score", "augmentation_score", "ai_exposure_score"}
        if not required.issubset(scores.columns):
            raise ValueError(f"{SCORE_FILE} must contain {sorted(required)}")
        scores["activity_code"] = scores["activity_code"].str.zfill(6)
        scores = labels.merge(scores.drop(columns=["activity_text"], errors="ignore"), on="activity_code", how="left")
    else:
        rows = []
        for _, row in labels.iterrows():
            automation, augmentation = score_activity(row["activity_code"], row["activity_text"])
            rows.append({
                "activity_code": row["activity_code"],
                "activity_text": row["activity_text"],
                "automation_score": automation,
                "augmentation_score": augmentation,
                "ai_exposure_score": round(0.45 * automation + 0.55 * augmentation, 3),
            })
        scores = pd.DataFrame(rows)
        scores.to_csv(SCORE_FILE, index=False)

    scores[["automation_score", "augmentation_score", "ai_exposure_score"]] = (
        scores[["automation_score", "augmentation_score", "ai_exposure_score"]]
        .fillna(0.0)
        .clip(0, 1)
    )
    scores.to_csv(SCORE_FILE, index=False)
    return scores


def load_summary() -> tuple[pd.DataFrame, list[str]]:
    header = read_header_from_zip(SUM_ZIP, SUMMARY_MEMBER)
    tcols = activity_columns(header)
    base_cols = [
        "TUCASEID", "TUYEAR", "TUFNWGTP", "TU20FWGT",
        "TEAGE", "TESEX", "PEEDUCA", "TRERNWA", "TRCHILDNUM",
    ]
    usecols = [c for c in base_cols if c in header] + tcols
    with zipfile.ZipFile(SUM_ZIP) as zf:
        with zf.open(SUMMARY_MEMBER) as f:
            df = pd.read_csv(f, usecols=usecols)
    return df, tcols


def age_group(age: float) -> str:
    if age < 25:
        return "15_24"
    if age < 35:
        return "25_34"
    if age < 45:
        return "35_44"
    if age < 55:
        return "45_54"
    if age < 65:
        return "55_64"
    return "65_plus"


def education_group(code: float) -> str:
    if code < 39:
        return "lt_hs"
    if code == 39:
        return "hs"
    if code in [40, 41, 42]:
        return "some_college"
    if code >= 43:
        return "ba_plus"
    return "unknown"


def earnings_group(value: float) -> str:
    # TRERNWA is weekly earnings in cents for many wage/salary workers; invalid values are negative.
    if value < 0 or pd.isna(value):
        return "no_valid_earnings"
    if value < 50_000:
        return "lt_500_week"
    if value < 100_000:
        return "500_999_week"
    if value < 150_000:
        return "1000_1499_week"
    return "1500plus_week"


def add_groups(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["age_group"] = out["TEAGE"].map(age_group)
    out["gender"] = out["TESEX"].map({1: "men", 2: "women"}).fillna("unknown")
    out["education"] = out["PEEDUCA"].map(education_group)
    out["income_group"] = out["TRERNWA"].map(earnings_group)
    out["parent_status"] = np.where(out["TRCHILDNUM"].fillna(0) > 0, "parent", "nonparent")
    out["group_id"] = (
        out["age_group"] + "|" + out["gender"] + "|" + out["education"] + "|"
        + out["income_group"] + "|" + out["parent_status"]
    )
    out["analysis_weight"] = out["TUFNWGTP"].astype(float)
    return out


def cols_with_prefix(tcols: list[str], prefixes: tuple[str, ...], exclude_prefixes: tuple[str, ...] = ()) -> list[str]:
    return [
        c for c in tcols
        if any(c[1:].startswith(p) for p in prefixes)
        and not any(c[1:].startswith(p) for p in exclude_prefixes)
    ]


def build_person_outcomes(df: pd.DataFrame, tcols: list[str], scores: pd.DataFrame, score_col: str) -> pd.DataFrame:
    out = df.copy()
    score_map = scores.set_index("activity_code")[score_col].to_dict()
    score_vec = pd.Series({f"t{k}": v for k, v in score_map.items() if f"t{k}" in tcols}).reindex(tcols).fillna(0.0)
    high_cols = [f"t{c}" for c, v in score_map.items() if v >= 0.50 and f"t{c}" in tcols]

    household_cols = cols_with_prefix(tcols, ("02",), exclude_prefixes=("0209",))
    care_cols = cols_with_prefix(tcols, ("03", "04"))
    education_cols = cols_with_prefix(tcols, ("06",))
    admin_cols = cols_with_prefix(tcols, ("0209", "07", "08", "09", "10", "16"))
    leisure_cols = cols_with_prefix(tcols, ("12", "13", "14", "15"))
    work_cols = cols_with_prefix(tcols, ("05",))

    out["household_production_minutes"] = out[household_cols].sum(axis=1)
    out["care_minutes"] = out[care_cols].sum(axis=1)
    out["education_minutes"] = out[education_cols].sum(axis=1)
    out["admin_services_minutes"] = out[admin_cols].sum(axis=1)
    out["leisure_minutes"] = out[leisure_cols].sum(axis=1)
    out["market_work_minutes"] = out[work_cols].sum(axis=1)
    out["high_ai_minutes"] = out[high_cols].sum(axis=1) if high_cols else 0.0
    out["ai_score_weighted_minutes"] = out[tcols].mul(score_vec, axis=1).sum(axis=1)
    out["total_diary_minutes"] = out[tcols].sum(axis=1)
    return out


OUTCOMES = [
    "household_production_minutes",
    "care_minutes",
    "education_minutes",
    "admin_services_minutes",
    "leisure_minutes",
    "market_work_minutes",
    "high_ai_minutes",
    "ai_score_weighted_minutes",
]


def weighted_mean(values: pd.Series, weights: pd.Series) -> float:
    weights = weights.astype(float)
    denom = weights.sum()
    if denom <= 0:
        return float("nan")
    return float((values.astype(float) * weights).sum() / denom)


def build_exposure(df: pd.DataFrame, pre_years: list[int]) -> pd.DataFrame:
    pre = df[df["TUYEAR"].isin(pre_years)].copy()
    grouped = pre.groupby("group_id", sort=False)
    rows = []
    for group_id, g in grouped:
        w = g["analysis_weight"].astype(float)
        denom = (w * g["total_diary_minutes"]).sum()
        exposure = (w * g["ai_score_weighted_minutes"]).sum() / denom if denom > 0 else np.nan
        high_share = (w * g["high_ai_minutes"]).sum() / denom if denom > 0 else np.nan
        first = g.iloc[0]
        rows.append({
            "group_id": group_id,
            "pre_ai_exposure": exposure,
            "pre_high_ai_share": high_share,
            "pre_weighted_n": w.sum(),
            "age_group": first["age_group"],
            "gender": first["gender"],
            "education": first["education"],
            "income_group": first["income_group"],
            "parent_status": first["parent_status"],
        })
    exp = pd.DataFrame(rows).dropna(subset=["pre_ai_exposure"])
    std = exp["pre_ai_exposure"].std(ddof=0)
    exp["pre_ai_exposure_z"] = (exp["pre_ai_exposure"] - exp["pre_ai_exposure"].mean()) / std if std > 0 else 0.0
    exp["exposure_bin"] = pd.qcut(exp["pre_ai_exposure"], q=4, labels=["Q1_low", "Q2", "Q3", "Q4_high"], duplicates="drop")
    return exp


def build_group_year_panel(df: pd.DataFrame, exposure: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (group_id, year), g in df.groupby(["group_id", "TUYEAR"], sort=False):
        w = g["analysis_weight"].astype(float)
        row = {"group_id": group_id, "year": int(year), "cell_weight": float(w.sum()), "respondents": int(len(g))}
        for outcome in OUTCOMES:
            row[outcome] = weighted_mean(g[outcome], w)
        rows.append(row)
    panel = pd.DataFrame(rows).merge(exposure, on="group_id", how="inner")
    return panel


def normal_pvalue(t_stat: float) -> float:
    if not np.isfinite(t_stat):
        return float("nan")
    return math.erfc(abs(t_stat) / math.sqrt(2.0))


def wls_fit(df: pd.DataFrame, y_col: str, reg_cols: list[str], weight_col: str, cluster_col: str) -> dict:
    work = df.dropna(subset=[y_col, weight_col, cluster_col] + reg_cols).copy()
    y = work[y_col].astype(float).to_numpy()
    X = pd.DataFrame({"const": 1.0}, index=work.index)
    for c in reg_cols:
        X[c] = work[c].astype(float)
    group_dummies = pd.get_dummies(work["group_id"], prefix="g", drop_first=True, dtype=float)
    year_dummies = pd.get_dummies(work["year"], prefix="y", drop_first=True, dtype=float)
    X = pd.concat([X, group_dummies, year_dummies], axis=1)
    Xmat = X.to_numpy(float)
    weights = work[weight_col].astype(float).to_numpy()
    sqrt_w = np.sqrt(weights / np.nanmean(weights))
    Xw = Xmat * sqrt_w[:, None]
    yw = y * sqrt_w
    beta = np.linalg.lstsq(Xw, yw, rcond=None)[0]
    resid = y - Xmat @ beta
    n, k = Xmat.shape
    xtx_inv = np.linalg.pinv(Xw.T @ Xw)

    meat = np.zeros((k, k))
    clusters = work[cluster_col].astype(str).to_numpy()
    for cluster in np.unique(clusters):
        idx = clusters == cluster
        xg = Xmat[idx, :]
        ug = resid[idx]
        wg = weights[idx] / np.nanmean(weights)
        xu = xg.T @ (wg * ug)
        meat += np.outer(xu, xu)
    g_count = len(np.unique(clusters))
    correction = (g_count / max(g_count - 1, 1)) * ((n - 1) / max(n - k, 1))
    cov = correction * xtx_inv @ meat @ xtx_inv
    se = np.sqrt(np.maximum(np.diag(cov), 0.0))

    result = {"_meta": {"n": int(n), "k": int(k), "clusters": int(g_count)}}
    for idx, name in enumerate(X.columns):
        se_i = float(se[idx])
        t_i = float(beta[idx] / se_i) if se_i > 0 else float("nan")
        result[name] = {
            "coef": float(beta[idx]),
            "cluster_se": se_i,
            "cluster_t": t_i,
            "cluster_p_norm": normal_pvalue(t_i),
        }
    return result


def run_did(panel: pd.DataFrame, outcome: str, model_years: list[int], post_mode: str) -> dict:
    work = panel[panel["year"].isin(model_years)].copy()
    if post_mode == "post_2023plus":
        work["post"] = (work["year"] >= 2023).astype(float)
    elif post_mode == "post_2022plus":
        work["post"] = (work["year"] >= 2022).astype(float)
    elif post_mode == "post_2024only":
        work["post"] = (work["year"] == 2024).astype(float)
    else:
        raise ValueError(post_mode)
    work["exposure_x_post"] = work["pre_ai_exposure_z"] * work["post"]
    fit = wls_fit(work, outcome, ["exposure_x_post"], "cell_weight", "group_id")
    term = fit["exposure_x_post"]
    return {
        "outcome": outcome,
        "post_mode": post_mode,
        "model_years": f"{min(model_years)}-{max(model_years)} excl 2020",
        "coef_per_1sd_exposure": term["coef"],
        "cluster_se": term["cluster_se"],
        "cluster_p_norm": term["cluster_p_norm"],
        "n_obs": fit["_meta"]["n"],
        "groups": fit["_meta"]["clusters"],
    }


def run_event_study(panel: pd.DataFrame, outcome: str, model_years: list[int], base_year: int) -> pd.DataFrame:
    work = panel[panel["year"].isin(model_years)].copy()
    reg_cols = []
    for year in model_years:
        if year == base_year:
            continue
        col = f"exposure_x_year_{year}"
        work[col] = work["pre_ai_exposure_z"] * (work["year"] == year).astype(float)
        reg_cols.append(col)
    fit = wls_fit(work, outcome, reg_cols, "cell_weight", "group_id")
    rows = []
    for col in reg_cols:
        year = int(col.rsplit("_", 1)[1])
        term = fit[col]
        rows.append({
            "outcome": outcome,
            "year": year,
            "base_year": base_year,
            "coef_per_1sd_exposure": term["coef"],
            "cluster_se": term["cluster_se"],
            "cluster_p_norm": term["cluster_p_norm"],
        })
    return pd.DataFrame(rows).sort_values("year")


def high_low_table(panel: pd.DataFrame) -> pd.DataFrame:
    work = panel[panel["exposure_bin"].astype(str).isin(["Q1_low", "Q4_high"])].copy()
    work["period"] = np.where(work["year"] >= 2023, "post_2023_2024", "pre_2017_2022")
    work = work[work["year"].isin(BASE_MODEL_YEARS)]
    rows = []
    for outcome in OUTCOMES:
        for (bin_name, period), g in work.groupby(["exposure_bin", "period"], observed=True):
            rows.append({
                "outcome": outcome,
                "exposure_group": str(bin_name),
                "period": period,
                "weighted_mean_minutes": weighted_mean(g[outcome], g["cell_weight"]),
                "groups": int(g["group_id"].nunique()),
                "cell_years": int(len(g)),
            })
    return pd.DataFrame(rows)


def robustness(panel_builder, df: pd.DataFrame, scores: pd.DataFrame, tcols: list[str]) -> pd.DataFrame:
    configs = [
        ("main_ai_2017_2021_no2020", "ai_exposure_score", BASE_PRE_YEARS),
        ("pre_2017_2021_with2020", "ai_exposure_score", [2017, 2018, 2019, 2020, 2021]),
        ("pre_2017_2019", "ai_exposure_score", [2017, 2018, 2019]),
        ("pre_2015_2019", "ai_exposure_score", [2015, 2016, 2017, 2018, 2019]),
        ("automation_score", "automation_score", BASE_PRE_YEARS),
        ("augmentation_score", "augmentation_score", BASE_PRE_YEARS),
    ]
    rows = []
    for label, score_col, pre_years in configs:
        person = build_person_outcomes(df, tcols, scores, score_col)
        exposure = build_exposure(person, pre_years)
        panel = build_group_year_panel(person, exposure)
        for outcome in ["ai_score_weighted_minutes", "high_ai_minutes", "leisure_minutes"]:
            item = run_did(panel, outcome, BASE_MODEL_YEARS, "post_2023plus")
            item["robustness_spec"] = label
            item["pre_years"] = ",".join(map(str, pre_years))
            rows.append(item)
    return pd.DataFrame(rows)


def write_event_svg(event: pd.DataFrame, path: Path) -> None:
    width, height = 760, 430
    ml, mr, mt, mb = 75, 25, 35, 60
    xs = event["year"].tolist()
    ys = event["coef_per_1sd_exposure"].tolist()
    lo = (event["coef_per_1sd_exposure"] - 1.96 * event["cluster_se"]).tolist()
    hi = (event["coef_per_1sd_exposure"] + 1.96 * event["cluster_se"]).tolist()
    ymin, ymax = min(lo + [0]), max(hi + [0])
    pad = max((ymax - ymin) * 0.12, 1)
    ymin -= pad
    ymax += pad

    def sx(x: int) -> float:
        return ml + (x - min(xs)) / (max(xs) - min(xs)) * (width - ml - mr)

    def sy(y: float) -> float:
        return mt + (ymax - y) / (ymax - ymin) * (height - mt - mb)

    elems = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<line x1="{ml}" y1="{sy(0):.1f}" x2="{width-mr}" y2="{sy(0):.1f}" stroke="#999" stroke-dasharray="4 4"/>',
    ]
    pts = " ".join(f"{sx(x):.1f},{sy(y):.1f}" for x, y in zip(xs, ys))
    elems.append(f'<polyline points="{pts}" fill="none" stroke="#1f6f8b" stroke-width="2.5"/>')
    for x, y, a, b in zip(xs, ys, lo, hi):
        elems.append(f'<line x1="{sx(x):.1f}" y1="{sy(a):.1f}" x2="{sx(x):.1f}" y2="{sy(b):.1f}" stroke="#77a9bb" stroke-width="1.4"/>')
        elems.append(f'<circle cx="{sx(x):.1f}" cy="{sy(y):.1f}" r="4" fill="#1f6f8b"/>')
        elems.append(f'<text x="{sx(x):.1f}" y="{height-28}" text-anchor="middle" font-family="Arial" font-size="12">{x}</text>')
    elems.extend([
        f'<line x1="{ml}" y1="{mt}" x2="{ml}" y2="{height-mb}" stroke="#333"/>',
        f'<line x1="{ml}" y1="{height-mb}" x2="{width-mr}" y2="{height-mb}" stroke="#333"/>',
        '<text x="24" y="235" transform="rotate(-90 24 235)" font-family="Arial" font-size="13">Minutes/day per 1 SD exposure</text>',
        '<text x="380" y="24" text-anchor="middle" font-family="Arial" font-size="15" font-weight="bold">Event study: AI-exposed minutes, 2022 baseline</text>',
        '</svg>',
    ])
    path.write_text("\n".join(elems))


def write_report(did: pd.DataFrame, event: pd.DataFrame, highlow: pd.DataFrame, robustness_df: pd.DataFrame, exposure: pd.DataFrame) -> None:
    DOCS.mkdir(exist_ok=True)
    key = did[(did["outcome"] == "ai_score_weighted_minutes") & (did["post_mode"] == "post_2023plus")].iloc[0]
    leisure = did[(did["outcome"] == "leisure_minutes") & (did["post_mode"] == "post_2023plus")].iloc[0]

    report = f"""# Blank-Style Predetermined AI Exposure With ATUS Microdata

This analysis tests a simple Blank-et-al.-style design:

1. Score each ATUS activity by AI exposure.
2. Use pre-ChatGPT time allocation to measure which demographic groups were more exposed.
3. Ask whether those high-exposure groups changed time use differently after ChatGPT.

## Main Result

For the score-weighted AI-exposed-minutes outcome, the main DiD coefficient is:

`{key['coef_per_1sd_exposure']:.3f} minutes/day per 1 SD of predetermined group exposure`

Clustered SE:

`{key['cluster_se']:.3f}`

Approximate normal p-value:

`{key['cluster_p_norm']:.3f}`

For leisure, the coefficient is `{leisure['coef_per_1sd_exposure']:.3f}` minutes/day, with p-value `{leisure['cluster_p_norm']:.3f}`.

## Interpretation

A negative coefficient means more AI-exposed groups reduced that outcome after 2022 relative to less AI-exposed groups. A positive coefficient means more AI-exposed groups increased that outcome.

This does **not** directly prove production-boundary movement. It only tests whether groups with more pre-ChatGPT exposure shifted time use after ChatGPT. To claim market-to-household substitution, this should later be linked to CEX spending or a direct household AI-use survey.

## Data

- Official BLS ATUS 2003-2024 public-use microdata.
- Main computation uses the Activity Summary file because it has respondent-level minutes by activity plus demographics and `TUFNWGTP`.
- Respondent and Activity ZIPs are checked as official inputs.
- Main exposure period: 2017, 2018, 2019, 2021. I exclude 2020 because BLS warns that 2020 ATUS collection was disrupted by COVID.
- Model years: 2017, 2018, 2019, 2021, 2022, 2023, 2024.
- Event-study base year: 2022.

## Groups

Groups are:

`age_group x gender x education x income_group x parent_status`

Income group uses `TRERNWA` weekly earnings, not total household income. Non-employed or invalid earnings are kept as `no_valid_earnings`.

## Core DiD Results

{did.to_csv(index=False)}

## Strong vs Weak Exposure Table

{highlow.to_csv(index=False)}

## Robustness

{robustness_df.to_csv(index=False)}

## Exposure Distribution

Number of groups: {len(exposure)}

Mean exposure: {exposure['pre_ai_exposure'].mean():.4f}

SD exposure: {exposure['pre_ai_exposure'].std(ddof=0):.4f}

## Files

- `scores/activity_ai_scores.csv`
- `results/blank_exposure/group_pre_exposure.csv`
- `results/blank_exposure/group_year_panel.csv`
- `results/blank_exposure/did_results.csv`
- `results/blank_exposure/event_study_ai_score_weighted_minutes.csv`
- `results/blank_exposure/event_study_ai_score_weighted_minutes.svg`
- `results/blank_exposure/high_vs_low_exposure_table.csv`
- `results/blank_exposure/robustness_results.csv`
"""
    (DOCS / "ATUS_Blank_Exposure_report.md").write_text(report)


def run() -> None:
    ensure_inputs()
    RESULTS.mkdir(parents=True, exist_ok=True)

    manifest = {
        "respondent_zip": zip_members(RESP_ZIP),
        "summary_zip": zip_members(SUM_ZIP),
        "activity_zip": zip_members(ACT_ZIP),
    }
    (RESULTS / "data_manifest.json").write_text(json.dumps(manifest, indent=2))

    df, tcols = load_summary()
    scores = create_or_load_scores([c[1:] for c in tcols])
    df = add_groups(df)
    person = build_person_outcomes(df, tcols, scores, "ai_exposure_score")
    exposure = build_exposure(person, BASE_PRE_YEARS)
    panel = build_group_year_panel(person, exposure)

    exposure.to_csv(RESULTS / "group_pre_exposure.csv", index=False)
    panel.to_csv(RESULTS / "group_year_panel.csv", index=False)

    did_rows = []
    for outcome in OUTCOMES:
        for post_mode in ["post_2023plus", "post_2022plus", "post_2024only"]:
            did_rows.append(run_did(panel, outcome, BASE_MODEL_YEARS, post_mode))
    did = pd.DataFrame(did_rows)
    did.to_csv(RESULTS / "did_results.csv", index=False)

    event = run_event_study(panel, "ai_score_weighted_minutes", BASE_MODEL_YEARS, BASE_EVENT_YEAR)
    event.to_csv(RESULTS / "event_study_ai_score_weighted_minutes.csv", index=False)
    write_event_svg(event, RESULTS / "event_study_ai_score_weighted_minutes.svg")

    highlow = high_low_table(panel)
    highlow.to_csv(RESULTS / "high_vs_low_exposure_table.csv", index=False)

    robust = robustness(build_group_year_panel, df, scores, tcols)
    robust.to_csv(RESULTS / "robustness_results.csv", index=False)

    write_report(did, event, highlow, robust, exposure)
    print("Wrote Blank-style exposure outputs to", RESULTS)
    print("Report:", DOCS / "ATUS_Blank_Exposure_report.md")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if not args.run:
        parser.error("Pass --run")
    run()


if __name__ == "__main__":
    main()
