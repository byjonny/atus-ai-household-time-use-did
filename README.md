# ATUS AI Household Time Use

This repo tests one simple idea:

**Did time in AI-exposed household activities fall after ChatGPT became widely available?**

The answer is preliminary, but suggestive:

```text
AI-exposed household time falls in the simple checks.
The strongest design finds -2.27 minutes/day per 1 SD of pre-AI exposure.
```

This is not proof of AI use. ATUS measures time use, not whether someone used ChatGPT.

## The Three Experiments

### 1. Simple Bundle Comparison

Folder:

```text
experiments/01_simple_bundle_comparison/
```

Question:

```text
Did a selected AI-exposed bundle fall relative to a low-exposure physical household bundle?
```

Method:

```text
(AI_post - AI_pre) - (Low_post - Low_pre)
```

Result:

```text
AI-exposed bundle:      26.45 -> 24.95 min/day  = -1.50
Low-exposure bundle:    98.89 -> 106.41 min/day = +7.52
Simple comparison:                                  -9.02
```

Best use:

```text
Easiest intuition. Not causal.
```

### 2. Task-Year DiD

Folder:

```text
experiments/02_task_year_did/
```

Question:

```text
Did AI-exposed tasks change differently after 2022 than low-exposure tasks?
```

Model:

```text
minutes_task,t = task FE + year FE + beta * AI_exposed_task x Post_t + error
```

Result:

```text
beta = -0.479 minutes/day per task
clustered p = 0.047
```

Best use:

```text
Formal regression version of experiment 1.
Still vulnerable because AI tasks and physical tasks may have different pre-trends.
```

### 3. Pre-AI Exposure Design

Folder:

```text
experiments/03_pre_ai_exposure/
```

Question:

```text
Did groups with more pre-ChatGPT exposure to AI-helpful activities change more after ChatGPT?
```

Exposure:

```text
pre-AI exposure_g = sum(pre-ChatGPT activity share_g,a x AI exposure score_a)
```

Model:

```text
Outcome_g,t = group FE + year FE + beta * pre_ai_exposure_z_g x Post_t + error
```

Result for score-weighted AI-exposed minutes:

```text
beta = -2.27 minutes/day per 1 SD of pre-AI exposure
p = 0.023
```

Best use:

```text
Preferred design. It uses predetermined exposure rather than observed AI use.
Still reduced-form, not direct evidence of AI adoption.
```

## How To Interpret The Results

Careful interpretation:

```text
Groups and tasks that were more exposed to AI-helpful activities show relative declines after ChatGPT.
```

Do not overclaim:

```text
ATUS does not identify who used AI.
ATUS does not measure task quality.
ATUS does not measure avoided spending.
ATUS alone cannot prove production-boundary movement.
```

To make a stronger production-boundary claim, link this to CEX spending data or direct survey data on household AI use.

## Data

Source:

```text
Official BLS American Time Use Survey public-use microdata
```

Main years:

```text
2017, 2018, 2019, 2021, 2022, 2023, 2024
```

Post-ChatGPT period:

```text
2023-2024
```

Weight:

```text
TUFNWGTP
```

Raw BLS files are not included in the repo. Put them in `raw/`:

```text
atusresp-0324.zip
atussum-0324.zip
atusact-0324.zip
```

## Run

Install dependencies:

```bash
pip install -r requirements.txt
```

Run each experiment:

```bash
python3 experiments/01_simple_bundle_comparison/run.py
python3 experiments/02_task_year_did/run.py
python3 experiments/03_pre_ai_exposure/run.py --run
```

## Archive

Older exploratory analyses are in:

```text
archive/
```

They are kept for transparency, but the active repo has only the three experiments above.
