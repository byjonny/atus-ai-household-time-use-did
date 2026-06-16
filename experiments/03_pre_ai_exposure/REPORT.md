# Blank-Style Predetermined AI Exposure With ATUS Microdata

This analysis tests a simple Blank-et-al.-style design:

1. Score each ATUS activity by AI exposure.
2. Use pre-ChatGPT time allocation to measure which demographic groups were more exposed.
3. Ask whether those high-exposure groups changed time use differently after ChatGPT.

## Main Result

For the score-weighted AI-exposed-minutes outcome, the main DiD coefficient is:

`-2.269 minutes/day per 1 SD of predetermined group exposure`

Clustered SE:

`1.001`

Approximate normal p-value:

`0.023`

For leisure, the coefficient is `2.807` minutes/day, with p-value `0.184`.

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

outcome,post_mode,model_years,coef_per_1sd_exposure,cluster_se,cluster_p_norm,n_obs,groups
household_production_minutes,post_2023plus,2017-2024 excl 2020,0.2773305843745675,0.9962702812863576,0.780729250625289,2851,450
household_production_minutes,post_2022plus,2017-2024 excl 2020,0.201245261573348,1.0436305679051487,0.8470906225391732,2851,450
household_production_minutes,post_2024only,2017-2024 excl 2020,0.8173505459404282,1.6674435076717045,0.6240052219148013,2851,450
care_minutes,post_2023plus,2017-2024 excl 2020,0.7216583484330386,1.2124487166663525,0.551704899460314,2851,450
care_minutes,post_2022plus,2017-2024 excl 2020,0.908007360762241,0.8877353421017996,0.306385556408271,2851,450
care_minutes,post_2024only,2017-2024 excl 2020,-0.07730068680218949,1.293313564194829,0.9523392288593776,2851,450
education_minutes,post_2023plus,2017-2024 excl 2020,-4.5844806644692255,1.6098918814910073,0.004403714044530189,2851,450
education_minutes,post_2022plus,2017-2024 excl 2020,-5.257914230691355,2.5150220974136595,0.036563613501737285,2851,450
education_minutes,post_2024only,2017-2024 excl 2020,-3.334315829285458,3.1382859311557705,0.28802509190718606,2851,450
admin_services_minutes,post_2023plus,2017-2024 excl 2020,-1.7453579026167816,1.1919074848597728,0.1431010510297564,2851,450
admin_services_minutes,post_2022plus,2017-2024 excl 2020,-2.3415508604502406,1.1506895055425044,0.04185981777682189,2851,450
admin_services_minutes,post_2024only,2017-2024 excl 2020,-0.8731402107471737,1.0541323388748058,0.4074993367609916,2851,450
leisure_minutes,post_2023plus,2017-2024 excl 2020,2.8069895592193177,2.1114173940490644,0.18370490691021252,2851,450
leisure_minutes,post_2022plus,2017-2024 excl 2020,2.2475577006633785,2.7032951137144803,0.40573973083283005,2851,450
leisure_minutes,post_2024only,2017-2024 excl 2020,-1.1743874213448748,2.7655729486177707,0.6710952998451984,2851,450
market_work_minutes,post_2023plus,2017-2024 excl 2020,4.813803817020471,2.2754139261695223,0.03438115700663636,2851,450
market_work_minutes,post_2022plus,2017-2024 excl 2020,4.892690021449084,2.0521063463250715,0.01711498108148838,2851,450
market_work_minutes,post_2024only,2017-2024 excl 2020,6.052141527656715,2.8206130517649917,0.031898276898865804,2851,450
high_ai_minutes,post_2023plus,2017-2024 excl 2020,-3.3292269147464992,1.8384095887403826,0.07015203849546685,2851,450
high_ai_minutes,post_2022plus,2017-2024 excl 2020,-4.423829538004611,2.4027093603520124,0.06559462928975247,2851,450
high_ai_minutes,post_2024only,2017-2024 excl 2020,-4.595970566704494,4.09045268779396,0.26118919683257075,2851,450
ai_score_weighted_minutes,post_2023plus,2017-2024 excl 2020,-2.268761976787083,1.0014709486928375,0.023486326802949785,2851,450
ai_score_weighted_minutes,post_2022plus,2017-2024 excl 2020,-2.9672795777291086,1.2878828472477424,0.021222752656096404,2851,450
ai_score_weighted_minutes,post_2024only,2017-2024 excl 2020,-2.7974870151988824,2.055575582183232,0.17353695914330755,2851,450


## Strong vs Weak Exposure Table

outcome,exposure_group,period,weighted_mean_minutes,groups,cell_years
household_production_minutes,Q1_low,post_2023_2024,83.83393623330178,97,172
household_production_minutes,Q1_low,pre_2017_2022,75.6060131542086,113,464
household_production_minutes,Q4_high,post_2023_2024,114.005296982902,107,202
household_production_minutes,Q4_high,pre_2017_2022,100.89135029316732,113,519
care_minutes,Q1_low,post_2023_2024,32.24025497812112,97,172
care_minutes,Q1_low,pre_2017_2022,30.597158833172596,113,464
care_minutes,Q4_high,post_2023_2024,33.42172056314284,107,202
care_minutes,Q4_high,pre_2017_2022,34.25083477453781,113,519
education_minutes,Q1_low,post_2023_2024,3.269289237300775,97,172
education_minutes,Q1_low,pre_2017_2022,2.250685075495776,113,464
education_minutes,Q4_high,post_2023_2024,62.892046481071155,107,202
education_minutes,Q4_high,pre_2017_2022,69.02333880636054,113,519
admin_services_minutes,Q1_low,post_2023_2024,28.59258020865943,97,172
admin_services_minutes,Q1_low,pre_2017_2022,21.90288608874555,113,464
admin_services_minutes,Q4_high,post_2023_2024,52.98312487514306,107,202
admin_services_minutes,Q4_high,pre_2017_2022,56.36710663412423,113,519
leisure_minutes,Q1_low,post_2023_2024,257.93089781082125,97,172
leisure_minutes,Q1_low,pre_2017_2022,272.44612424109033,113,464
leisure_minutes,Q4_high,post_2023_2024,344.40913646822344,107,202
leisure_minutes,Q4_high,pre_2017_2022,346.47981681850774,113,519
market_work_minutes,Q1_low,post_2023_2024,310.7363741710975,97,172
market_work_minutes,Q1_low,pre_2017_2022,339.877170794679,113,464
market_work_minutes,Q4_high,post_2023_2024,84.34218405909863,107,202
market_work_minutes,Q4_high,pre_2017_2022,89.57837415780828,113,519
high_ai_minutes,Q1_low,post_2023_2024,25.6797684942037,97,172
high_ai_minutes,Q1_low,pre_2017_2022,17.883492476043365,113,464
high_ai_minutes,Q4_high,post_2023_2024,112.77173141497445,107,202
high_ai_minutes,Q4_high,pre_2017_2022,119.60561138472679,113,519
ai_score_weighted_minutes,Q1_low,post_2023_2024,89.97843058633748,97,172
ai_score_weighted_minutes,Q1_low,pre_2017_2022,85.44943505114111,113,464
ai_score_weighted_minutes,Q4_high,post_2023_2024,137.00802077319955,107,202
ai_score_weighted_minutes,Q4_high,pre_2017_2022,141.74722312249844,113,519


## Robustness

outcome,post_mode,model_years,coef_per_1sd_exposure,cluster_se,cluster_p_norm,n_obs,groups,robustness_spec,pre_years
ai_score_weighted_minutes,post_2023plus,2017-2024 excl 2020,-2.268761976787083,1.0014709486928375,0.023486326802949785,2851,450,main_ai_2017_2021_no2020,"2017,2018,2019,2021"
high_ai_minutes,post_2023plus,2017-2024 excl 2020,-3.3292269147464992,1.8384095887403826,0.07015203849546685,2851,450,main_ai_2017_2021_no2020,"2017,2018,2019,2021"
leisure_minutes,post_2023plus,2017-2024 excl 2020,2.8069895592193177,2.1114173940490644,0.18370490691021252,2851,450,main_ai_2017_2021_no2020,"2017,2018,2019,2021"
ai_score_weighted_minutes,post_2023plus,2017-2024 excl 2020,-2.2687620153391492,1.0014709618078785,0.023486326261747653,2851,450,pre_2017_2021_with2020,"2017,2018,2019,2020,2021"
high_ai_minutes,post_2023plus,2017-2024 excl 2020,-3.329226979253903,1.8384096128251028,0.07015203673614068,2851,450,pre_2017_2021_with2020,"2017,2018,2019,2020,2021"
leisure_minutes,post_2023plus,2017-2024 excl 2020,2.806989570942136,2.1114174071283034,0.18370490779490758,2851,450,pre_2017_2021_with2020,"2017,2018,2019,2020,2021"
ai_score_weighted_minutes,post_2023plus,2017-2024 excl 2020,-2.210795658386971,0.9929277768001961,0.02597788145116753,2830,440,pre_2017_2019,"2017,2018,2019"
high_ai_minutes,post_2023plus,2017-2024 excl 2020,-3.245180800727809,1.8309415340955506,0.07632636753323976,2830,440,pre_2017_2019,"2017,2018,2019"
leisure_minutes,post_2023plus,2017-2024 excl 2020,2.4714981889111414,2.112571347226459,0.24204102914622508,2830,440,pre_2017_2019,"2017,2018,2019"
ai_score_weighted_minutes,post_2023plus,2017-2024 excl 2020,-1.3410593642485011,0.8371063896230315,0.10915166610533544,2844,446,pre_2015_2019,"2015,2016,2017,2018,2019"
high_ai_minutes,post_2023plus,2017-2024 excl 2020,-1.7389494382438926,1.5505990132651533,0.262088084099846,2844,446,pre_2015_2019,"2015,2016,2017,2018,2019"
leisure_minutes,post_2023plus,2017-2024 excl 2020,1.811495651234793,1.923322577221144,0.3462656397736316,2844,446,pre_2015_2019,"2015,2016,2017,2018,2019"
ai_score_weighted_minutes,post_2023plus,2017-2024 excl 2020,-1.5526765028310763,0.7559133411134545,0.039971786660563634,2851,450,automation_score,"2017,2018,2019,2021"
high_ai_minutes,post_2023plus,2017-2024 excl 2020,-0.4549525192870547,0.7699709707917344,0.5546077269011895,2851,450,automation_score,"2017,2018,2019,2021"
leisure_minutes,post_2023plus,2017-2024 excl 2020,2.4991783351743777,2.160299133385584,0.24732678671859484,2851,450,automation_score,"2017,2018,2019,2021"
ai_score_weighted_minutes,post_2023plus,2017-2024 excl 2020,-2.930548427431148,1.276286852331464,0.02166720006321962,2851,450,augmentation_score,"2017,2018,2019,2021"
high_ai_minutes,post_2023plus,2017-2024 excl 2020,-3.610568875844365,1.8102709016148235,0.046098431297191454,2851,450,augmentation_score,"2017,2018,2019,2021"
leisure_minutes,post_2023plus,2017-2024 excl 2020,2.9563386094977204,2.0983316340837987,0.15886485651182913,2851,450,augmentation_score,"2017,2018,2019,2021"


## Exposure Distribution

Number of groups: 450

Mean exposure: 0.0718

SD exposure: 0.0190

## Files

- `scores/activity_ai_scores.csv`
- `results/group_pre_exposure.csv`
- `results/group_year_panel.csv`
- `results/did_results.csv`
- `results/event_study_ai_score_weighted_minutes.csv`
- `results/event_study_ai_score_weighted_minutes.svg`
- `results/high_vs_low_exposure_table.csv`
- `results/robustness_results.csv`
