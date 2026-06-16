# ATUS AI Household Time Use

This repo asks a simple question:

**Did Americans spend less time on AI-exposed household activities after ChatGPT became widely available?**

Short answer: **yes, in this preliminary ATUS test.**

## Main Idea

ATUS does not ask people whether they use AI. So the analysis does not measure AI use directly.

Instead, it uses a **Blank-style exposure design**:

1. Look at what people did **before ChatGPT**.
2. Identify groups that already spent more time on tasks where AI could later help.
3. Compare those high-exposure groups with low-exposure groups after ChatGPT.

The exposure measure is:

```text
pre-ChatGPT time share x AI exposure score
```

Groups are defined by:

```text
age x gender x education x earnings group x parent status
```

## Main Result

More AI-exposed groups reduced AI-exposed time after ChatGPT:

```text
-2.27 minutes/day per 1 SD of pre-ChatGPT AI exposure
p = 0.023
```

Leisure increased in the same design, but the estimate is not statistically significant:

```text
+2.81 minutes/day
p = 0.184
```

## How To Read This

This is consistent with AI saving households time on exposed tasks.

But it is **not proof** that AI caused the change. ATUS does not observe AI use, task quality, avoided spending, or GDP-boundary movement.

Careful interpretation:

> Groups that were more exposed to AI-helpful activities before ChatGPT spent relatively less time on those activities after ChatGPT.

## Data

- Source: official BLS American Time Use Survey public-use microdata
- Years: 2003-2024
- Main comparison years: 2017-2024, excluding 2020
- Post-ChatGPT period: 2023-2024
- Weight: `TUFNWGTP`

## Key Files

- `docs/ATUS_Blank_Exposure_report.md`: full report
- `scripts/atus_blank_exposure_design.py`: main analysis script
- `scores/activity_ai_scores.csv`: AI exposure scores by ATUS activity
- `results/blank_exposure/did_results.csv`: main regression results
- `results/blank_exposure/event_study_ai_score_weighted_minutes.svg`: event-study plot

## Run The Main Analysis

Install dependencies:

```bash
pip install -r requirements.txt
```

Put the official BLS ZIP files in `raw/`:

```text
atusresp-0324.zip
atussum-0324.zip
atusact-0324.zip
```

Run:

```bash
python3 scripts/atus_blank_exposure_design.py --run
```

Raw BLS data are not included in the repo.

## Simplest Check

There is now a very simple bundle pre/post analysis in:

```text
docs/simple_bundle_prepost/
scripts/simple_bundle_prepost.py
results/simple_bundle_prepost/
```

It compares one clear AI-exposed task bundle with one low-exposure physical household bundle.

Result:

```text
AI-exposed bundle: 26.45 -> 24.95 min/day
Low-exposure bundle: 98.89 -> 106.41 min/day
Simple bundle DiD: -9.02 min/day
```

This is the easiest version to understand. It is descriptive and has no regression.

## Secondary Check

There is also a simpler activity-level DiD check in:

```text
docs/simple_activity_did/
scripts/simple_activity_did/
results/simple_activity_did/
```

That check compares selected AI-exposed activities with low-exposure physical household tasks.

Result:

```text
-1.50 minutes/day per AI-exposed activity
p = 0.017
```

Use this only as a transparent robustness/sanity check. The main analysis is the Blank-style group-exposure design above.

## Next Step

To make a stronger production-boundary claim, link these ATUS time-use shifts to CEX spending data or direct survey data on household AI use.
