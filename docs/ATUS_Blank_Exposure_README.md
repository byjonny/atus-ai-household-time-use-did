# Blank-Style ATUS Exposure Analysis

This is the second analysis in the repo.

It uses the idea of **predetermined exposure**:

> Do not measure who used AI. Instead, measure which groups already spent more time on tasks where AI could later help.

Then compare those groups before and after ChatGPT.

## Run

Put these official BLS files in `raw/`:

- `atusresp-0324.zip`
- `atussum-0324.zip`
- `atusact-0324.zip`

Then run:

```bash
python3 scripts/atus_blank_exposure_design.py --run
```

## What It Produces

- activity-level AI scores
- group-level pre-ChatGPT exposure
- group-year outcomes
- DiD results
- event-study table and SVG plot
- robustness tables

Main report:

`docs/ATUS_Blank_Exposure_report.md`

## Main Warning

This design does **not** prove AI caused the changes.

It only asks whether groups with higher pre-ChatGPT exposure changed differently after ChatGPT.

To claim production-boundary movement, add CEX spending or direct AI-use survey data later.
