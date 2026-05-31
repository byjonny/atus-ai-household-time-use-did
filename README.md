# ATUS AI Exposure and Household Time Use

This repository tests whether U.S. household time use changed after the public arrival of generative AI, using the American Time Use Survey.

The main design is a **Blank-et-al.-style predetermined exposure design**:

```text
Do not measure who used AI.
Measure who, before ChatGPT, spent more time on activities where AI could later be useful.
Then test whether those more exposed groups changed differently after ChatGPT.
```

This matters for the household-production question because ATUS does not observe AI use, avoided purchases, or output quality. Predetermined exposure is therefore a first reduced-form test, not a direct proof of production-boundary movement.

## Main Analysis: Blank-Style Exposure

The core exposure measure is built before ChatGPT:

```text
Pre_AI_Exposure_g = sum(pre-ChatGPT time share in activity a for group g
                        x AI exposure score for activity a)
```

Groups are:

```text
age group x gender x education x weekly-earnings group x parent status
```

The DiD/event-study model asks whether groups with higher pre-ChatGPT AI exposure changed more after 2022:

```text
Outcome_g,t = group FE + year FE + beta(Pre_AI_Exposure_g x Post_ChatGPT_t) + error_g,t
```

The main outcome is score-weighted AI-exposed minutes. Other outcomes include household production, care, education, admin/services, leisure, market work, and total high-AI minutes.

## Main Result

For score-weighted AI-exposed minutes, the main estimate is:

```text
beta = -2.27 minutes/day per 1 SD of predetermined group exposure
p = 0.023
```

Interpretation: groups that were more exposed to AI-helpful activities before ChatGPT reduced score-weighted AI-exposed minutes after 2022 relative to less exposed groups.

Leisure moves in the opposite direction, but not significantly:

```text
beta = +2.81 minutes/day
p = 0.184
```

The careful conclusion is:

> ATUS shows a post-2022 relative decline in AI-exposed time for groups that were more exposed before ChatGPT. This is consistent with household time-saving, but it is not direct evidence that production moved across the GDP boundary.

## Main Files

- `docs/ATUS_Blank_Exposure_report.md`: full Blank-style report
- `docs/ATUS_Blank_Exposure_README.md`: short method guide
- `scripts/atus_blank_exposure_design.py`: reproducible microdata script
- `scores/activity_ai_scores.csv`: activity-level AI exposure scores
- `results/blank_exposure/did_results.csv`: main regression table
- `results/blank_exposure/high_vs_low_exposure_table.csv`: high- vs low-exposure comparison
- `results/blank_exposure/event_study_ai_score_weighted_minutes.csv`: event-study table
- `results/blank_exposure/event_study_ai_score_weighted_minutes.svg`: event-study plot
- `results/blank_exposure/robustness_results.csv`: robustness checks

## Reproduce The Main Analysis

Install the small Python dependency set:

```bash
pip install -r requirements.txt
```

Put the official BLS ATUS public-use microdata ZIPs in `raw/`:

```text
atusresp-0324.zip
atussum-0324.zip
atusact-0324.zip
```

Then run:

```bash
python3 scripts/atus_blank_exposure_design.py --run
```

The script uses the Activity Summary file for respondent-level minutes, demographics, and `TUFNWGTP` weights. It checks the Respondent and Activity ZIPs as official inputs. Raw BLS ZIPs are intentionally not committed.

## Data And Scope

- Source: official U.S. Bureau of Labor Statistics ATUS public-use microdata, 2003-2024.
- Main exposure period: 2017, 2018, 2019, and 2021.
- 2020 is excluded from the main pre-period because ATUS collection was disrupted by COVID.
- Post-ChatGPT is defined as 2023 onward, with robustness checks for 2022+ and 2024 only.
- Weights: `TUFNWGTP`.
- Income group is based on `TRERNWA` weekly earnings, not total household income.

## Secondary Check: Simple Activity-Level DiD

The older analysis is now kept separately in:

```text
docs/simple_activity_did/
scripts/simple_activity_did/
results/simple_activity_did/
```

That check does something simpler: it compares a hand-picked set of AI-exposed ATUS activity codes with low-exposure physical household tasks in BLS public annual series.

Its main estimate is:

```text
-1.50 minutes/day per high-exposure activity
p = 0.017
```

This is useful as a transparent activity-level sanity check, but it is not the main design because it does not use predetermined demographic-group exposure. Read it here: `docs/simple_activity_did/README.md`.

To rerun it:

```bash
python3 scripts/simple_activity_did/atus_did_analysis.py --make-requests

for f in raw/bls_request_*_chunk*.json; do
  out="${f/bls_request_/bls_data_}"
  curl -L -H "Content-type: application/json" \
    -d "@$f" \
    -o "$out" \
    https://api.bls.gov/publicAPI/v2/timeseries/data/
done

python3 scripts/simple_activity_did/atus_did_analysis.py --analyze
```

## Limits

This repository does not measure individual AI adoption. It also does not directly measure avoided market purchases, welfare, output quality, or GDP-boundary movement. The right interpretation is narrower and cleaner: it tests whether pre-exposed groups and activities changed differently after ChatGPT in ATUS time-use data.

For a stronger production-boundary claim, the next step should link this design to CEX spending, direct AI-use survey data, or household-service substitution measures.
