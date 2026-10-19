# Research databases

Built 18 October 2026. Three research directions for the saturation forecast:
how similar automated warehouses work, what data such forecasts need, and which models turn
inputs into occupancy per cell class. Plus public datasets and analogues from other fields.

All content comes from public sources. No Coster material.

## Where things are
- `csv/`: one UTF-8 CSV per table (this folder). Text, so changes show up in pull requests.
- `coster_research.xlsx` and `coster_research.db`: the same content as an Excel workbook (filters, linked sources) and as SQLite with ready-made views. They are on the shared Drive, not in git, because the repo ignores `*.xlsx` on purpose (Coster exports are Excel).

## Tables
| File | Rows | What it holds |
|---|---|---|
| `insights.csv` | 17 | Start here. Main findings, what they mean for Coster, next action, IDs of the evidence |
| `aw_case_studies.csv` | 42 | Plants with similar automated warehouses |
| `vendors_systems.csv` | 23 | AS/RS, LGV and WMS vendors (includes the likely WLog maker) |
| `data_requirements.csv` | 59 | Data elements, where they live (SAP etc.), status at Coster, fallback if missing. `coster_file_ref = new` means not in the current data request |
| `models.csv` | 101 | Data-driven and simulation models, covariate support, fit for Coster |
| `literature.csv` | 186 | Papers and documentation, tagged by topic |
| `datasets.csv` | 42 | Public datasets and benchmarks for prototyping |
| `analogues.csv` | 28 | Hospital beds, container yards, hotels, parking, fabs |

IDs link the tables: `evidence_ids` in `insights.csv` points to rows such as `CS-002`, `MD-009`, `LIT-005`.

## How reliable is it
- Every record has a source URL. `verified = yes` means someone opened the source and it supported the record.
- 119 records (all that were only seen in search results, plus a sample of the rest) were re-checked by a second pass. 49 were corrected, none were fabricated, 2 could not be opened. See `check_note`.
- The web search limit ran out during the research. Gaps: no real sources for Aptar, Precision Valve, Mitani or Summit warehouses, thin feature documentation for several large vendors, some authors filled in from memory (marked in the records).
- That WLog is the Wise Ingegneria product, and that Coster's LGVs come from Elettric80, is likely but not confirmed. Ask Coster.
- `relevance` (1 to 5) and `coster_takeaway` are our judgement, not the sources'.
- Check licences before redistributing any dataset. Several have none stated.
