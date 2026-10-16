# PWFTS as a candidate model: assessment

| | |
|---|---|
| Sources | Silva et al. 2020 (`silva2020pwfts`), pyFTS on GitHub and PyPI, a local test run |
| Added | 16 October 2026 |
| Status | Our own evaluation, not peer-reviewed. The test used synthetic data only. |

## Summary

- PWFTS is not suited as the base model. In the paper it is univariate: it learns from the past of the series itself. Our strongest signal is the known future, the production and shipping plans.
- The team's draft never proposed it as the base model. It placed PWFTS third, after persistence and the flow balance, to model the errors between plan and actual. That role is reasonable.
- For that role there are simpler, maintained alternatives. The backtest decides which one stays.

## The team's arguments and whether they hold

| Argument in the draft | Holds? | Comment |
|---|---|---|
| We need a probabilistic forecast, not one number | Yes | Not specific to PWFTS. The flow balance with Monte Carlo plan slips gives the same kind of output. |
| PWFTS produces a distribution. Fuzzy membership is not a probability. | Yes | Accurate description |
| A candidate, not a final choice, compared with simpler methods | Yes | The right stance |
| Stages: persistence, flow balance, PWFTS on plan-vs-actual errors, backtest with gradient boosting | Yes | Same structure as the Group 1 plan |
| If plans are unreliable, PWFTS directly on the occupancy series | No longer needed | Coster provides the plans. This branch would ignore them. |
| Count only positions filled and freed, whatever the movement type | Yes | The Group 1 plan uses the same view |
| Hourly intervals | Partly | Plans are hourly, but actuals come from the daily 06:00 snapshot. There is no usable movement log, so hourly actuals cannot be measured. |
| The chance of being above 90% at hour 48 differs from crossing 90% at any time before | Yes, important | PWFTS gives a distribution per step. Crossing at any time needs sample paths, which the Monte Carlo produces directly. |
| Not all of the next 48 hours is planned | Yes | Unplanned flows (manual moves, ground buffer) show up in the error term |

What the draft does not cover:

- **Data for the error model.** Training on plan-vs-actual errors needs past plan versions. Coster offered one week.
- **A simpler competitor.** Empirical quantiles of backtest errors per horizon fill the same role with a few lines of code.
- **Capacity.** PWFTS does not know the cell limit. The flow balance has to handle it first.
- **Library maintenance.** See below.

## Library check

Checked on 16 October 2026.

- Last PyPI release: pyFTS 1.6, 7 May 2019. Its classifiers list Python 3.4 to 3.6.
- Last GitHub commit: 26 May 2023 (`setup.py` on master says 1.7).
- With pandas 2.0 or later, the package fails on import: `from pandas import datetime` was removed in pandas 2.0.
- The package also imports Keras (autoencoder transformation) when it loads.

Three changes made it run on Python 3.13 with numpy 2.5 and pandas 3.0:

1. Replace `from pandas import datetime` with `from datetime import datetime`.
2. Make the SOM and autoencoder imports in `pyFTS/common/Transformations.py` optional.
3. Install scikit-learn.

After that, `ProbabilisticWeightedFTS` ran. Settings: Grid partitioner with 15 sets, order 1, trained on 86 synthetic daily points. It returned point, interval and distribution forecasts for 14 steps and learned 10 rules. The day-2 interval reached 252.9 cells for a class with 248 cells, because the model does not know the capacity limit.

These results come from synthetic data. They show that the code runs, not how accurate it would be on Coster's data. The script is in [experiments/pwfts_check.py](experiments/pwfts_check.py).

## Maintained alternatives

Latest PyPI release, checked 16 October 2026.

| Library | Version, date | What it gives | Possible role |
|---|---|---|---|
| MAPIE | 1.5.0, 5 Aug 2026 | Conformal (distribution-free) intervals around any model | Range from the flow-balance errors, the role planned for PWFTS |
| LightGBM | 4.7.0, 18 Jul 2026 | Quantile objective | Learned distribution that can use plan features |
| chronos-forecasting | 2.3.2, 8 Sep 2026 | Pretrained models, Chronos-2 handles covariate-informed tasks (per the paper's abstract) | Zero-shot challenger with short history |
| timesfm | 3.0.2, 9 Sep 2026 | Pretrained model | Zero-shot challenger |
| statsforecast, mlforecast | 2.1.1 (16 Jul 2026), 1.1.0 (10 Jul 2026) | Classical models, conformal intervals | Simple challengers |
| darts | 0.48.0, 15 Oct 2026 | Many probabilistic models behind one interface | Quick comparisons |
| ngboost | 0.5.11, 26 Jun 2026 | Distributional regression | Alternative learned distribution |
| sktime | 1.2.0, 22 Sep 2026 | Unified forecasting interface | Quick comparisons |

Release activity is a good sign, not a guarantee of future maintenance.

## Recommendation

1. **First uncertainty layer:** empirical quantiles of the flow-balance backtest errors per horizon (split conformal). Plain numpy, or MAPIE.
2. **If a learned distribution is needed:** LightGBM with a quantile objective and the plans as features.
3. **Zero-shot challenger with short history:** Chronos-2. Check its output format in the library docs.
4. **PWFTS:** optional challenger on the flow-balance errors, in a time-boxed experiment from November, once there are a few months of data with stored plan versions. If used, keep a patched copy in the repo or write a small own implementation.
