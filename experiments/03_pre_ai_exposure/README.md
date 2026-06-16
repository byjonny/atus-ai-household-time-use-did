# Experiment 3: Pre-AI Exposure Design

This is the preferred research design in the repo.

## Question

Did groups that were more exposed to AI-helpful activities before ChatGPT change their time use more after ChatGPT?

## Core Idea

ATUS does not observe AI use. So this experiment does not ask who used AI.

Instead, it measures predetermined exposure:

```text
pre-AI exposure of group g
= sum(pre-ChatGPT activity share_g,a x AI exposure score_a)
```

Then it tests whether high-exposure groups changed differently after ChatGPT.

## Model

```text
Outcome_g,t =
group FE + year FE + beta * pre_ai_exposure_z_g x post_t + error_g,t
```

Groups are:

```text
age x gender x education x earnings group x parent status
```

## Main Result

For score-weighted AI-exposed minutes:

```text
beta = -2.27 minutes/day per 1 SD of pre-AI exposure
p = 0.023
```

Interpretation:

```text
More pre-exposed groups reduced AI-exposed time more after ChatGPT.
```

## Important Limits

This is still reduced-form evidence. It does not directly observe AI adoption, task quality, household spending, or production-boundary movement.

## Files

- `run.py`: analysis script
- `scores/activity_ai_scores.csv`: task-level AI scores
- `results/did_results.csv`: main regressions
- `results/event_study_ai_score_weighted_minutes.svg`: event-study plot
- `REPORT.md`: detailed generated report
