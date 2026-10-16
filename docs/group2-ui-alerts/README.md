# Group 2: UI and alerts

The Group 2 plan goes in this folder: dashboard views per cell class, the 14-day forecast with
uncertainty, warning and critical levels, notification channels, alert content, and how the
alert logic reads the `forecast` table.

Code lives in `src/coster/alerts/` and `src/coster/dashboard/`. Both read the two contract
tables only (see `src/coster/common/schemas.py`).
