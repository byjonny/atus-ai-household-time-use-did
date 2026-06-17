#!/usr/bin/env python3
"""Build task-year positive respondent counts matched to AI exposure scores.

The output answers:

    For each ATUS task and each survey year, how many respondents reported
    strictly positive minutes on that task, and what is that task's AI score?

It uses the ATUS Activity Summary file because it has one column per activity
code and one row per respondent.
"""

from __future__ import annotations

import html
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
OUTPUT_FILE = RESULTS / "task_positive_respondents_by_year.csv"


def clean_label(value: str) -> str:
    value = html.unescape(str(value))
    value = value.replace("\xa0", " ")
    return re.sub(r"\s+", " ", value).strip()


def activity_labels_from_summary_setup() -> dict[str, str]:
    label_re = re.compile(r'label\s+t(\d{6})\s*=\s*"([^"]*)";', re.IGNORECASE)
    with zipfile.ZipFile(SUM_ZIP) as zf:
        text = zf.read("atussum_0324.sas").decode("latin1")
    return {code: clean_label(label) for code, label in label_re.findall(text)}


def read_summary_header() -> list[str]:
    with zipfile.ZipFile(SUM_ZIP) as zf:
        with zf.open(SUMMARY_MEMBER) as f:
            return f.readline().decode("utf-8").strip().split(",")


def load_scores(activity_codes: list[str]) -> pd.DataFrame:
    scores = pd.read_csv(SCORE_FILE, dtype={"activity_code": str})
    scores["activity_code"] = scores["activity_code"].str.zfill(6)
    scores = scores[scores["activity_code"].isin(activity_codes)].copy()

    labels = activity_labels_from_summary_setup()
    scores["activity_text"] = scores["activity_code"].map(labels).fillna(scores["activity_text"])

    for col in ["automation_score", "augmentation_score", "ai_exposure_score"]:
        scores[col] = pd.to_numeric(scores[col], errors="coerce").fillna(0.0).clip(0, 1)

    return scores.sort_values("activity_code")


def build_counts() -> pd.DataFrame:
    if not SUM_ZIP.exists():
        raise FileNotFoundError(f"Missing {SUM_ZIP}")
    if not SCORE_FILE.exists():
        raise FileNotFoundError(f"Missing {SCORE_FILE}")

    header = read_summary_header()
    activity_cols = sorted(c for c in header if re.fullmatch(r"t\d{6}", c))
    activity_codes = [col[1:] for col in activity_cols]
    scores = load_scores(activity_codes)
    scored_codes = scores["activity_code"].tolist()
    scored_cols = [f"t{code}" for code in scored_codes]

    with zipfile.ZipFile(SUM_ZIP) as zf:
        with zf.open(SUMMARY_MEMBER) as f:
            df = pd.read_csv(f, usecols=["TUYEAR", "TUFNWGTP", *scored_cols])

    rows = []
    score_lookup = scores.set_index("activity_code")
    for year, year_df in df.groupby("TUYEAR", sort=True):
        weights = year_df["TUFNWGTP"].astype(float)
        weighted_total = float(weights.sum())
        respondent_total = int(len(year_df))

        for code in scored_codes:
            col = f"t{code}"
            minutes = year_df[col].astype(float)
            positive = minutes.gt(0)
            positive_respondents = int(positive.sum())
            weighted_positive = float(weights[positive].sum())
            weighted_minutes = float((minutes * weights).sum())
            weighted_mean_all = weighted_minutes / weighted_total if weighted_total > 0 else np.nan
            weighted_mean_positive = (
                weighted_minutes / weighted_positive if weighted_positive > 0 else np.nan
            )
            score_row = score_lookup.loc[code]

            rows.append({
                "year": int(year),
                "activity_code": code,
                "activity_text": score_row["activity_text"],
                "positive_respondents": positive_respondents,
                "respondents_total": respondent_total,
                "positive_share_unweighted": positive_respondents / respondent_total,
                "weighted_positive_population": weighted_positive,
                "weighted_total_population": weighted_total,
                "positive_share_weighted": weighted_positive / weighted_total,
                "weighted_mean_minutes_all_respondents": weighted_mean_all,
                "weighted_mean_minutes_among_positive": weighted_mean_positive,
                "automation_score": float(score_row["automation_score"]),
                "augmentation_score": float(score_row["augmentation_score"]),
                "ai_exposure_score": float(score_row["ai_exposure_score"]),
            })

    return pd.DataFrame(rows)


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    counts = build_counts()
    counts.to_csv(OUTPUT_FILE, index=False)
    print(f"Wrote {len(counts):,} task-year rows to {OUTPUT_FILE}")
    print(f"Years: {counts['year'].min()}-{counts['year'].max()}")
    print(f"Tasks: {counts['activity_code'].nunique():,}")


if __name__ == "__main__":
    main()
