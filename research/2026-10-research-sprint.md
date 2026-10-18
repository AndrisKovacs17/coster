# Research sprint, 18–19 October 2026

| | |
|---|---|
| Why | At the 16 October meeting PWFTS turned out to be poorly maintained and weak on synthetic data. Team B proposed trying several approaches in parallel instead of committing to one. |
| Goal | Collect candidate models and analog cases before Monday, then split the reading among the team |
| Added | 18 October 2026 |
| Status | Collected from abstracts and listings. Nothing here is read in full yet. Summaries are not findings. |

Each source is listed in its topic index with a link and a BibTeX key in `references.bib`:

- [forecasting-methods/](forecasting-methods/README.md)
- [uncertainty-and-evaluation/](uncertainty-and-evaluation/README.md)
- [warehouse-and-simulation/](warehouse-and-simulation/README.md)
- [alerts-and-dashboards/](alerts-and-dashboards/README.md)

## The options on the table and where to read about them

These are the approaches raised on 16 October, plus the analog cases.

| Option | Who raised it | Sources to start with | Main question for us |
|---|---|---|---|
| Deterministic flow balance (allocation cascade) plus a probabilistic range | sukhman, Zishan; also the Group 1 plan | Littig and Isken 2007, Bekker and Koeleman 2011 (hospital beds from scheduled admissions); conformal methods (Romano 2019, Gibbs and Candès 2021, Angelopoulos 2023) | How far do plans plus fixed allocation rules explain occupancy, and how wide is the leftover error? |
| Gradient boosting (LightGBM quantiles, NGBoost) | Christian | Ke 2017, Duan 2019, M5 results, arXiv 2311.00993 | Enough history to train on? Plan features vs the flow balance as a feature |
| Foundation models, zero-shot (Chronos-2, TimesFM, Moirai, TiRex, TabPFN-TS) | Christian ("Kronos 2" in the notes) | Ansari 2025, Das 2024, Woo 2024, Auer 2025, Hoo 2025, GIFT-Eval | Do they beat persistence on a short daily series with a hard capacity limit? Can they use plans as covariates? Chronos-2 and TabPFN-TS say yes. |
| PWFTS (fuzzy time series) | Zishan | Silva 2020, [pwfts-assessment.md](forecasting-methods/pwfts-assessment.md) | Already assessed: optional challenger on the residuals at most |
| Deep learning with known future inputs (TFT, DeepAR, N-HiTS) | none yet | Lim 2021, Salinas 2020, Challu 2022 | Likely too little data. Keep for later. |
| Classical baselines (ETS, Prophet) | none yet | FPP3, Taylor and Letham 2018, Shah 2021 | Shah 2021 shows how strong a plain baseline is for bed occupancy. Every candidate must beat these. |

## How to compare the options fairly

The sources point to one shared evaluation for every candidate:

1. **The same backtest.** A rolling origin, using only what was known at 06:00 on the run date (`forecast/backtest.py`). See Bergmeir 2018 for when cross-validation is valid.
2. **The same score.** CRPS or pinball loss for the range (Gneiting and Raftery 2007), plus hit rate and false-alarm rate for the 90% crossing. The second matters more to Coster.
3. **The same output.** Median, 10–90% range and P(critical by day d) per class. Any model that fits this can feed the dashboard.

## Analog domains worth more searching

The closest analog is hospital bed occupancy. Its structure matches ours: scheduled arrivals (our plans), uncertain stay times (picking, shipping slips) and a hard capacity limit. Others:

- parking occupancy (Tavafoghi 2019)
- container yards and dwell time (arXiv 2602.20540, 2503.11728)
- inventory under machine breakdowns (Takeda-Berger and Frazzon 2024). This matches the machine-stop uncertainty Alessio and Riccardo raised.

## Still to find

- The M5 **uncertainty** track paper (Makridakis et al. 2022) with its quantile results
- A paper that forecasts **occupancy or saturation of an AS/RS** specifically. None found yet. Search inside Bertolini et al. 2023.
- Sources on using **machine-stop logs** to adjust production-plan realisation (Riccardo offered these logs)
- Alert lead time and false-alarm practice in logistics or manufacturing rather than weather
- Authors and full references for the two rows marked "Authors not yet recorded"

## Suggested split for Monday

One person per row. Each fills in a note from `_TEMPLATE.md` for the two or three most relevant sources.

1. Analog cases and the flow balance: Littig and Isken, Bekker and Koeleman, Shah
2. Gradient boosting: Ke, Duan, M5 accuracy, arXiv 2311.00993
3. Foundation models: Chronos-2, TabPFN-TS, TiRex, GIFT-Eval
4. Uncertainty and alerts: Romano, Angelopoulos, Gneiting and Raftery, Roulston and Smith, Fernandes
