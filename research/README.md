# Research

Everything we read, test or compare that informs a decision goes here: papers, library checks,
small experiments and benchmark notes. The aim is that anyone in the team can see why we chose
a method, and what we already ruled out.

## Structure

| Folder | What goes in it |
|---|---|
| `forecasting-methods/` | Forecasting models and baselines: flow balance, statistical, ML, fuzzy, foundation models |
| `uncertainty-and-evaluation/` | Prediction intervals, conformal methods, scoring rules, backtesting, alert metrics |
| `warehouse-and-simulation/` | AS/RS and warehouse simulation, storage assignment, digital twins, analog domains |
| `alerts-and-dashboards/` | Alert design, thresholds, notification practice, dashboard design |
| `databases/` | Cross-topic research databases (CSV): similar warehouses, data needs, models, literature, datasets. Start with `insights.csv` |
| `references.bib` | One BibTeX entry per source, used by all folders |
| `_TEMPLATE.md` | Template for a note on one source |

Each topic folder has a `README.md` with an index table of its sources.

## How to add a source

1. Copy `_TEMPLATE.md` into the topic folder. Name it `<year>-<first-author>-<short-title>.md`, for example `2020-silva-pwfts.md`.
2. Fill in the note. Say what the source claims, what evidence it gives, and what it means for us.
3. Add a BibTeX entry to `references.bib`.
4. Add a row to the index table in the topic folder's `README.md`.

Small experiments (a script that tests a library or a method) go in `<topic>/experiments/`.
They are not part of the `coster` package and must not read Coster's data from the repo.

## Rules

- **PDFs:** only open-access papers (arXiv, open licence), up to 10 MB. For paywalled papers, store
  the DOI link and our notes only.
- **No Coster material here.** Briefs, exports, screenshots and meeting notes with Coster data stay in
  the shared Drive. We signed a confidentiality agreement.
- **Claims need a source.** Mark our own judgement as such. Mark anything unverified as unverified.
