#!/usr/bin/env python3
"""Simple ATUS bundle trend and pre/post comparison.

This is the deliberately simple version of the analysis:

1. Define an AI-exposed bundle of clear household/admin/education/service tasks.
2. Define a low-exposure physical household bundle.
3. Compute TUFNWGTP-weighted minutes/day by year.
4. Compare the pre period with the post-ChatGPT period.
5. Draw a small SVG line plot.
"""

from __future__ import annotations

import csv
import html
import re
import zipfile
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw"
RESULTS = ROOT / "results" / "simple_bundle_prepost"
DOCS = ROOT / "docs" / "simple_bundle_prepost"

SUM_ZIP = RAW / "atussum-0324.zip"
SUMMARY_MEMBER = "atussum_0324.dat"

PRE_YEARS = [2017, 2018, 2019, 2021, 2022]
POST_YEARS = [2023, 2024]
PLOT_YEARS = PRE_YEARS + POST_YEARS


AI_EXPOSED_CODES = {
    # Household admin and finance
    "020901": "Financial management",
    "020902": "Household and personal organization and planning",
    "020903": "Household and personal mail and messages",
    "020904": "Household and personal e-mail and messages",
    # Education and tutoring-like work
    "030201": "Homework with household children",
    "060301": "Research/homework for class for degree/certification",
    "060302": "Research/homework for class for personal interest",
    "060399": "Research/homework, n.e.c.",
    # Finance/professional services
    "080201": "Banking",
    "080202": "Using other financial services",
    "080299": "Using financial services and banking, n.e.c.",
    # Legal services
    "080301": "Using legal services",
    "080399": "Using legal services, n.e.c.",
    # Medical services
    "080401": "Using health and care services outside the home",
    "080402": "Using in-home health and care services",
    "080499": "Using medical services, n.e.c.",
    # Government/tax/license admin
    "100103": "Obtaining licenses and paying fines, fees, taxes",
    "100199": "Using government services, n.e.c.",
}


LOW_EXPOSURE_CODES = {
    "020101": "Interior cleaning",
    "020102": "Laundry",
    "020201": "Food and drink preparation",
    "020203": "Kitchen and food cleanup",
    "020501": "Lawn, garden, and houseplant care",
    "020502": "Ponds, pools, and hot tubs",
    "020599": "Lawn and garden, n.e.c.",
    "020701": "Vehicle repair and maintenance by self",
    "020801": "Appliance, tool, and toy setup/repair/maintenance by self",
}


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


def build_bundle_tables() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    all_codes = set(AI_EXPOSED_CODES) | set(LOW_EXPOSURE_CODES)
    labels = activity_labels_from_summary_setup()
    df = read_summary(all_codes)

    ai_cols = [f"t{code}" for code in sorted(AI_EXPOSED_CODES)]
    low_cols = [f"t{code}" for code in sorted(LOW_EXPOSURE_CODES)]
    df["ai_exposed_minutes"] = df[ai_cols].sum(axis=1)
    df["low_exposure_physical_minutes"] = df[low_cols].sum(axis=1)

    rows = []
    for year, g in df.groupby("TUYEAR"):
        rows.append({
            "year": int(year),
            "ai_exposed_minutes": weighted_mean(g["ai_exposed_minutes"], g["TUFNWGTP"]),
            "low_exposure_physical_minutes": weighted_mean(g["low_exposure_physical_minutes"], g["TUFNWGTP"]),
            "respondents": int(len(g)),
            "weighted_population": float(g["TUFNWGTP"].sum()),
        })
    annual = pd.DataFrame(rows).sort_values("year")

    prepost_rows = []
    for bundle in ["ai_exposed_minutes", "low_exposure_physical_minutes"]:
        pre_mean = annual.loc[annual["year"].isin(PRE_YEARS), bundle].mean()
        post_mean = annual.loc[annual["year"].isin(POST_YEARS), bundle].mean()
        prepost_rows.append({
            "bundle": bundle,
            "pre_years": ",".join(map(str, PRE_YEARS)),
            "post_years": ",".join(map(str, POST_YEARS)),
            "pre_mean_minutes": pre_mean,
            "post_mean_minutes": post_mean,
            "post_minus_pre_minutes": post_mean - pre_mean,
        })
    prepost = pd.DataFrame(prepost_rows)
    ai_change = float(prepost.loc[prepost["bundle"].eq("ai_exposed_minutes"), "post_minus_pre_minutes"].iloc[0])
    low_change = float(prepost.loc[prepost["bundle"].eq("low_exposure_physical_minutes"), "post_minus_pre_minutes"].iloc[0])
    did = pd.DataFrame([{
        "comparison": "simple_bundle_difference_in_differences",
        "ai_exposed_change": ai_change,
        "low_exposure_physical_change": low_change,
        "difference_in_differences": ai_change - low_change,
        "interpretation": "Negative means AI-exposed bundle fell more, or rose less, than the physical low-exposure bundle.",
    }])

    mapping_rows = []
    for bundle, codes in [("ai_exposed", AI_EXPOSED_CODES), ("low_exposure_physical", LOW_EXPOSURE_CODES)]:
        for code, rationale in codes.items():
            mapping_rows.append({
                "bundle": bundle,
                "activity_code": code,
                "official_activity_text": labels.get(code, ""),
                "bundle_reason": rationale,
            })
    mapping = pd.DataFrame(mapping_rows).sort_values(["bundle", "activity_code"])
    return annual, prepost, did, mapping


def write_svg(annual: pd.DataFrame, path: Path) -> None:
    data = annual[annual["year"].isin(PLOT_YEARS)].copy()
    width, height = 820, 450
    ml, mr, mt, mb = 75, 35, 35, 70
    plot_w = width - ml - mr
    plot_h = height - mt - mb
    years = data["year"].tolist()
    series = {
        "AI-exposed bundle": ("ai_exposed_minutes", "#1f6f8b"),
        "Low-exposure physical bundle": ("low_exposure_physical_minutes", "#a85b2a"),
    }
    all_y = []
    for col, _color in series.values():
        all_y.extend(data[col].tolist())
    y_min = 0.0
    y_max = max(all_y) * 1.15

    def sx(year: int) -> float:
        return ml + (year - min(years)) / (max(years) - min(years)) * plot_w

    def sy(value: float) -> float:
        return mt + (y_max - value) / (y_max - y_min) * plot_h

    elems = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<line x1="{ml}" y1="{mt}" x2="{ml}" y2="{height-mb}" stroke="#333"/>',
        f'<line x1="{ml}" y1="{height-mb}" x2="{width-mr}" y2="{height-mb}" stroke="#333"/>',
        '<text x="410" y="24" text-anchor="middle" font-family="Arial" font-size="16" font-weight="bold">ATUS bundle minutes per day, weighted by TUFNWGTP</text>',
        '<text x="24" y="230" transform="rotate(-90 24 230)" font-family="Arial" font-size="13">Minutes per day</text>',
    ]
    tick_step = 20 if y_max > 60 else 10
    max_tick = int(((y_max + tick_step - 1) // tick_step) * tick_step)
    for tick in range(0, max_tick + 1, tick_step):
        if tick > y_max:
            continue
        y = sy(tick)
        elems.append(f'<line x1="{ml}" y1="{y:.1f}" x2="{width-mr}" y2="{y:.1f}" stroke="#eee"/>')
        elems.append(f'<text x="{ml-10}" y="{y+4:.1f}" text-anchor="end" font-family="Arial" font-size="12">{tick}</text>')

    for year in years:
        elems.append(f'<text x="{sx(year):.1f}" y="{height-34}" text-anchor="middle" font-family="Arial" font-size="12">{year}</text>')
    elems.append(f'<line x1="{sx(2022):.1f}" y1="{mt}" x2="{sx(2022):.1f}" y2="{height-mb}" stroke="#999" stroke-dasharray="4 4"/>')
    elems.append(f'<text x="{sx(2022)+8:.1f}" y="{mt+16}" font-family="Arial" font-size="12" fill="#555">2022 baseline</text>')

    legend_y = height - 18
    legend_x = ml + 15
    for i, (label, (col, color)) in enumerate(series.items()):
        values = data[col].tolist()
        pts = " ".join(f"{sx(year):.1f},{sy(value):.1f}" for year, value in zip(years, values))
        elems.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2.6"/>')
        for year, value in zip(years, values):
            elems.append(f'<circle cx="{sx(year):.1f}" cy="{sy(value):.1f}" r="4" fill="{color}"/>')
        lx = legend_x + i * 250
        elems.append(f'<line x1="{lx}" y1="{legend_y}" x2="{lx+28}" y2="{legend_y}" stroke="{color}" stroke-width="3"/>')
        elems.append(f'<text x="{lx+36}" y="{legend_y+4}" font-family="Arial" font-size="13">{label}</text>')
    elems.append("</svg>")
    path.write_text("\n".join(elems))


def write_report(annual: pd.DataFrame, prepost: pd.DataFrame, did: pd.DataFrame, mapping: pd.DataFrame) -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    ai = prepost[prepost["bundle"].eq("ai_exposed_minutes")].iloc[0]
    low = prepost[prepost["bundle"].eq("low_exposure_physical_minutes")].iloc[0]
    diff = did.iloc[0]
    report = f"""# Simple Bundle Pre/Post Analysis

This is the intentionally simple version of the ATUS analysis.

## Question

Did time in a clear AI-exposed task bundle fall after ChatGPT, compared with a low-exposure physical household bundle?

## Bundles

AI-exposed bundle: finance, household admin, mail/e-mail, homework/research, banking/financial services, legal services, medical services, government/tax/license admin.

Low-exposure physical bundle: cleaning, laundry, food preparation, kitchen cleanup, lawn/garden, vehicle repair, appliance/tool repair.

Full mapping: `results/simple_bundle_prepost/bundle_mapping.csv`

## Method

For each respondent:

`bundle_minutes = sum(minutes in selected ATUS activity codes)`

For each year:

`weighted_mean_minutes = sum(TUFNWGTP * bundle_minutes) / sum(TUFNWGTP)`

Pre period: {", ".join(map(str, PRE_YEARS))}

Post period: {", ".join(map(str, POST_YEARS))}

Pre/post means are simple averages of the annual weighted means, so each year gets equal weight.

## Result

AI-exposed bundle:

`{ai['pre_mean_minutes']:.2f} -> {ai['post_mean_minutes']:.2f} minutes/day`

Change:

`{ai['post_minus_pre_minutes']:.2f} minutes/day`

Low-exposure physical bundle:

`{low['pre_mean_minutes']:.2f} -> {low['post_mean_minutes']:.2f} minutes/day`

Change:

`{low['post_minus_pre_minutes']:.2f} minutes/day`

Simple bundle DiD:

`{diff['difference_in_differences']:.2f} minutes/day`

## Interpretation

A negative simple DiD means the AI-exposed bundle fell more, or rose less, than the low-exposure physical bundle after ChatGPT.

This is descriptive. It does not prove AI caused the change.

## Files

- `results/simple_bundle_prepost/bundle_mapping.csv`
- `results/simple_bundle_prepost/annual_bundle_minutes.csv`
- `results/simple_bundle_prepost/prepost_bundle_summary.csv`
- `results/simple_bundle_prepost/simple_bundle_did.csv`
- `results/simple_bundle_prepost/bundle_trends.svg`
"""
    (DOCS / "README.md").write_text(report)


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    annual, prepost, did, mapping = build_bundle_tables()
    mapping.to_csv(RESULTS / "bundle_mapping.csv", index=False)
    annual.to_csv(RESULTS / "annual_bundle_minutes.csv", index=False)
    prepost.to_csv(RESULTS / "prepost_bundle_summary.csv", index=False)
    did.to_csv(RESULTS / "simple_bundle_did.csv", index=False)
    write_svg(annual, RESULTS / "bundle_trends.svg")
    write_report(annual, prepost, did, mapping)
    print("Wrote simple bundle outputs to", RESULTS)
    print("Report:", DOCS / "README.md")


if __name__ == "__main__":
    main()
