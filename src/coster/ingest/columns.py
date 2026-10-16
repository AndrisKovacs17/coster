"""Coster column name -> our column name, per source file.

Fill these in when the first sample files arrive. If an export changes,
only this mapping changes. Our names follow the data request spreadsheet.
"""

COLUMN_MAPS: dict[str, dict[str, str]] = {
    "cell_master": {},
    "loadunit_type_master": {},
    "snapshot_0600": {},
    "assembly_work_orders": {},
    "moulding_punching_plan": {},
}
