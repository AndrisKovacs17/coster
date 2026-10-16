"""Loaders for Coster's Excel exports. One function per file, each returns a validated table.

Rules (docs/group1-data-forecasting/data-forecasting-plan.md, section 7):
- keep data/raw untouched, write validated tables to data/interim as parquet
- read Excel as text first, then cast each column on purpose
- map Coster's column names to ours in columns.py
- write rejected rows to a report, never drop them silently
"""
