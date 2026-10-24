# Forecasting methods

Models and baselines for the daily fill ratio per cell class. The plan's forecast ladder is in
`docs/group1-data-forecasting/data-forecasting-plan.md`, section 8.

| Source | Type | Status | Note |
|---|---|---|---|
| Silva et al. 2020, Probabilistic Forecasting With Fuzzy Time Series (`silva2020pwfts`) | Paper | read | [pwfts-assessment.md](pwfts-assessment.md) |
| pyFTS library, https://github.com/PYFTS/pyFTS | Software | tested | [pwfts-assessment.md](pwfts-assessment.md), [experiments/pwfts_check.py](experiments/pwfts_check.py) |
| Ansari et al. 2024, Chronos (`ansari2024chronos`) | Paper | to read | |
| Ansari et al. 2025, Chronos-2 (`ansari2025chronos2`) | Paper | to read | Zero-shot, covariate-informed forecasting per the abstract |
| Tan Jerome and Simon 2026, When Do Foundation Models Pay Off? (`tanjerome2026breakeven`) | Paper | to read | Cited in the forecasting research summary (Team B, Oct 2026) |

### Added in the research sprint (18 Oct 2026)

Grouped by the options raised at the 16 October meeting. The notes come from abstracts and listings
and have not been read in full yet.

**Gradient boosting and distributional regression** (Christian's proposal)

| Source | Type | Status | Note |
|---|---|---|---|
| Ke et al. 2017, LightGBM (`ke2017lightgbm`), [NeurIPS](https://proceedings.neurips.cc/paper/2017/file/6449f44a102fde848669bdd9eb6b76fa-Paper.pdf) | Paper | to read | The library paper. The quantile objective is what we would use. |
| Duan et al. 2019, NGBoost (`duan2019ngboost`), [arXiv 1910.03225](https://arxiv.org/abs/1910.03225) | Paper | to read | Boosting that outputs a full distribution. Any base learner and scoring rule. |
| Makridakis et al. 2022, M5 accuracy results (`makridakis2022m5accuracy`), [DOI](https://doi.org/10.1016/j.ijforecast.2021.11.013) | Paper | to read | Large retail benchmark won by LightGBM-based entries. The companion M5 uncertainty paper (quantiles) is still to find. |
| [arXiv 2311.00993](https://arxiv.org/abs/2311.00993), Scalable probabilistic forecasting in retail with gradient boosted trees | Paper | to read | Practitioner's view of quantile GBDT on M5-style data |
| [arXiv 2204.00778](https://arxiv.org/abs/2204.00778), distributional gradient boosting | Paper | to read | Extends the M5-winning LightGBM setup to full distributions |

**Deep learning with known future inputs** (our plans are known future inputs)

| Source | Type | Status | Note |
|---|---|---|---|
| Lim et al. 2021, Temporal Fusion Transformers (`lim2019tft`), [arXiv 1912.09363](https://arxiv.org/abs/1912.09363) | Paper | to read | Built for static, known-future and past-only inputs. Quantile outputs. Probably too data-hungry for our history. |
| Salinas et al. 2020, DeepAR (`salinas2017deepar`), [arXiv 1704.04110](https://arxiv.org/abs/1704.04110) | Paper | to read | Global probabilistic RNN, sample paths. Needs many related series. |
| Challu et al. 2022, N-HiTS (`challu2022nhits`), [arXiv 2201.12886](https://arxiv.org/abs/2201.12886) | Paper | to read | Long-horizon MLP model, in neuralforecast |

**Foundation models (zero-shot)** (Chronos-2, which the meeting notes call "Kronos 2", and its competitors)

| Source | Type | Status | Note |
|---|---|---|---|
| Das et al. 2024, TimesFM (`das2023timesfm`), [arXiv 2310.10688](https://arxiv.org/abs/2310.10688) | Paper | to read | Google, about 200M parameters, ICML 2024 |
| Woo et al. 2024, Moirai (`woo2024moirai`), [arXiv 2402.02592](https://arxiv.org/abs/2402.02592) | Paper | to read | Salesforce, any number of variates, mixture-distribution output |
| Rasul et al. 2023, Lag-Llama (`rasul2023lagllama`), [arXiv 2310.08278](https://arxiv.org/abs/2310.08278) | Paper | to read | Univariate, probabilistic, open weights |
| Auer et al. 2025, TiRex (`auer2025tirex`), [arXiv 2505.23719](https://arxiv.org/abs/2505.23719) | Paper | to read | xLSTM-based. Claims top zero-shot results on GIFT-Eval and Chronos-ZS. |
| Hoo et al. 2025, TabPFN-TS (`hoo2025tabpfnts`), [arXiv 2501.02945](https://arxiv.org/abs/2501.02945), [code](https://github.com/PriorLabs/tabpfn-time-series) | Paper, software | to read | Forecasting as tabular regression, supports covariates. Claims state of the art with covariates. Fits "plans as features". |
| Aksu et al. 2024, GIFT-Eval (`aksu2024gifteval`), [arXiv 2410.10393](https://arxiv.org/abs/2410.10393) | Benchmark | to read | Leaderboard for comparing the models above. Check the short-horizon daily results. |

**Classical baselines and practice**

| Source | Type | Status | Note |
|---|---|---|---|
| Hyndman and Athanasopoulos 2021, FPP3 (`hyndman2021fpp3`), [otexts.com/fpp3](https://otexts.com/fpp3/) | Book, free | reference | Baselines, prediction intervals, time-series cross-validation |
| Taylor and Letham 2018, Prophet (`taylor2018prophet`), [DOI](https://doi.org/10.1080/00031305.2017.1380080) | Paper | to read | Trend, seasonality and holiday regression. A common default we may be asked about. |
| Ben Taieb et al. 2012, multi-step strategies (`bentaieb2011multistep`), [arXiv 1108.3259](https://arxiv.org/abs/1108.3259) | Paper | to read | Recursive vs direct vs multi-output for a 1–14 day horizon. Multi-output did best on NN5. |

### Our studies

| Study | Type | Status | Note |
|---|---|---|---|
| Occupancy backtest on the first Coster data drop, Oct 2026 | Own experiment | done | [occupancy-backtest-2026-10.md](occupancy-backtest-2026-10.md), code in [experiments/occupancy_2026_10/](experiments/occupancy_2026_10/). Persistence, mean reversion, Ridge, LightGBM, SARIMAX, Chronos-2 zero-shot, a plan-based simulator and a pre-registered forecast. |
