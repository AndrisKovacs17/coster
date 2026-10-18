# Uncertainty and evaluation

Prediction intervals, threshold-crossing probabilities, scoring rules, backtesting and alert
metrics. See the Group 1 plan, sections 8 and 9.

| Source | Type | Status | Note |
|---|---|---|---|
| Xu and Xie 2020, Conformal prediction for time series, EnbPI (`xu2020enbpi`) | Paper | to read | Cited in the forecasting research summary (Team B, Oct 2026) |
| MAPIE, https://mapie.readthedocs.io | Software | to test | Conformal intervals. Version 1.5.0 on PyPI (Aug 2026). |

### Added in the research sprint (18 Oct 2026)

| Source | Type | Status | Note |
|---|---|---|---|
| Gneiting and Raftery 2007, proper scoring rules (`gneiting2007scoring`), [DOI](https://doi.org/10.1198/016214506000001437) | Paper | to read | CRPS, interval score, pinball loss. Use it to compare all candidates on one score. |
| Romano et al. 2019, Conformalized Quantile Regression (`romano2019cqr`), [arXiv 1905.03222](https://arxiv.org/abs/1905.03222) | Paper | to read | Calibrates LightGBM quantiles. Intervals adapt to noise. |
| Gibbs and Candès 2021, Adaptive Conformal Inference (`gibbs2021aci`), [arXiv 2106.00170](https://arxiv.org/abs/2106.00170) | Paper | to read | Keeps coverage under drift, for example after the August layout change. Follow-up: [arXiv 2208.08401](https://arxiv.org/abs/2208.08401). |
| Angelopoulos et al. 2023, Conformal PID control (`angelopoulos2023conformalpid`), [arXiv 2307.16895](https://arxiv.org/abs/2307.16895), [code](https://github.com/aangelopoulos/conformal-time-series) | Paper, software | to read | Online intervals that correct for trend and seasonality. Multi-week horizon example (COVID-19 deaths). |
| Bergmeir et al. 2018, cross-validation for time series (`bergmeir2018cv`) | Paper | to read | When K-fold CV is valid for autoregressive ML models. Matters with a short history. |
| ["A scoring framework for tiered warnings and multicategorical forecasts based on fixed risk measures"](https://arxiv.org/abs/2108.12814) | Paper | to read | Scores tiered warnings such as our warning and critical levels. Authors not yet recorded. |
