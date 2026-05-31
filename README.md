# ATUS AI Household Time-Use DiD

This repo asks a small question:

**After consumer AI became widely available, did Americans spend more or less time on household tasks that AI could help with?**

Short answer: **less, not more**.

## Main Finding

I compared AI-exposed activities with low-exposure physical household tasks in the American Time Use Survey.

The main difference-in-differences estimate is:

```text
-1.50 minutes per day per AI-exposed activity
```

That means the AI-exposed activities fell by about **1.5 minutes/day more** than the low-exposure comparison activities after 2022.

Approximate clustered p-value:

```text
p = 0.017
```

So yes: in this simple descriptive setup, the time decline is statistically significant.

## Interpretation

This is consistent with the idea that AI may save households time on cognitive/admin tasks.

But it is not causal proof. ATUS does not ask people whether they used AI. It only measures time use.

So the careful conclusion is:

> In ATUS, time spent in AI-exposed household-professional activities falls after 2022 relative to physical household tasks. This is consistent with household time-saving, but not proof that AI caused it.

## Activities Used

High AI exposure:

- Financial management
- Financial services and banking
- Helping children with homework
- Homework and research
- Health-related self care
- Medical and care services
- Children's health activities
- Government services, as a weak legal/admin proxy

Low AI exposure comparison group:

- Interior cleaning
- Laundry
- Food and drink preparation
- Kitchen cleanup
- Lawn and garden care
- Animal and pet care
- Vehicle care
- Appliance/tool maintenance

## Important Caveat

ATUS has no clean "lawyer" activity code.

The closest public-series proxy is **Government services**, but it is sparse. So this repo should not be cited as strong evidence about legal AI specifically.

## Files

- `docs/ATUS_DiD_report.md`: readable full report
- `scripts/atus_did_analysis.py`: reproducible analysis script
- `results/did_summary.csv`: main DiD results
- `results/did_domain_minutes.csv`: results by domain
- `results/key_activity_changes_minutes.csv`: activity-level changes
- `results/event_study_minutes.csv`: event-study table
- `results/event_study_minutes.svg`: small visual check

## Reproduce

Requirements:

```text
python3
pandas
numpy
curl
```

Run:

```bash
python3 scripts/atus_did_analysis.py --make-requests

for f in raw/bls_request_*_chunk*.json; do
  out="${f/bls_request_/bls_data_}"
  curl -L -H "Content-type: application/json" \
    -d "@$f" \
    -o "$out" \
    https://api.bls.gov/publicAPI/v2/timeseries/data/
done

python3 scripts/atus_did_analysis.py --analyze
```

The script downloads BLS ATUS metadata, creates small BLS API requests, then rebuilds the result tables.

## Data Source

Data come from the U.S. Bureau of Labor Statistics American Time Use Survey public annual time-use series.

- https://data.bls.gov/PDQWeb/tu
- https://api.bls.gov/publicAPI/v2/timeseries/data/
