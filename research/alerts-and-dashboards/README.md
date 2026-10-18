# Alerts and dashboards

Alert thresholds and lead times, notification practice, false-alarm handling and dashboard design.
The forecasting research summary (Team B, Oct 2026) found no solid published evidence on alert
thresholds yet, so add sources here as we find them.

| Source | Type | Status | Note |
|---|---|---|---|
| Roulston and Smith 2004, The boy who cried wolf revisited (`roulston2004crywolf`), [PDF](https://www.lse.ac.uk/CATS/Assets/PDFs/Publications/Papers/2004/Roulston-and-Smith-searchable-The-boy-who-cried-wolf.pdf) | Paper, open | to read | Cost-loss view of warning thresholds when users dislike false alarms. Directly relevant to the 2-day email. |
| [Cost-loss model](https://en.wikipedia.org/wiki/Cost-loss_model) | Overview | read | Warn when P(event) > cost of acting / loss avoided. A simple rule for setting the alert probability. |
| ANSI/ISA-18.2 and EEMUA 191, alarm management | Standards, paywalled | to check | Common target is about 1 alarm per 10 minutes per operator. Secondary sources disagree on daily figures (for example [Emerson](https://d1-live.emerson.com/documents/automation/article-alarm-management-by-numbers-deltav-en-38292.pdf)). Use the idea of an alarm budget, not the numbers. |
| Kay et al. 2016, When(ish) is my bus? (`kay2016whenish`), [page](https://idl.uw.edu/papers/when-ish-is-my-bus) | Paper, open | to read | Introduces quantile dotplots for showing forecast uncertainty to non-experts |
| Fernandes et al. 2018, quantile dotplots or CDFs improve decisions (`fernandes2018dotplots`), [PDF](https://mucollective.northwestern.edu/files/2018-UncertainBusDecisions-CHI.pdf) | Paper, open | to read | Dotplots and CDF plots beat text intervals for decisions. A candidate display for the 14-day range. |
| Hullman et al., In Pursuit of Error: survey of uncertainty visualization evaluation, [page](https://idl.uw.edu/papers/uncertainty-eval-survey) | Review | to read | How such displays are tested with users |
| Maybe, Maybe Not: survey on uncertainty in visualization, [arXiv 2301.07687](https://arxiv.org/abs/2301.07687) | Review, open | to read | Broad survey |
