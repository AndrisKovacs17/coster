"""Loaders, plan scheduler and helpers for the plan-based flow-balance simulator.

Coster's internal codes (pallet material prefixes, the finished-goods article prefix, load unit
type codes) are not in the repo. They are read from coster_codes.json in the data folder. See
coster_codes.example.json for the keys.
"""

import json
import os

import numpy as np
import pandas as pd
from history import CLASSES, HOLIDAYS, SHORT, file_date, find, load_history  # noqa: F401

CLS = CLASSES
FGC = ["Med", "High", "MedW", "HighW"]  # classes that hold finished goods
# Alert thresholds (share of capacity), fixed before any scoring. Med: "full".
THR = {"Low": 0.90, "Med": 1.00, "High": 0.90, "MedW": 0.90, "HighW": 0.60}
WORK_DOW = {0, 1, 2, 3, 4, 5}  # the plan never starts or ends a work order on Sunday


def load_codes(folder) -> dict:
    """Coster's internal codes, from coster_codes.json in the data folder (never in git)."""
    path = os.path.join(str(folder), "coster_codes.json")
    if not os.path.exists(path):
        raise SystemExit(f"{path} is missing. Copy coster_codes.example.json and fill it in.")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_f5(path):
    return load_history(path)


def load_udcmap(path):
    """Load unit type -> list of (cell class, priority), from 'UDC vs CELLE'."""
    u = pd.read_excel(path)
    u.columns = [c.strip() for c in u.columns]
    u["cls"] = u.TP_CELLA_DESC.str.strip().map(SHORT)
    m = {}
    for t, g in u.groupby("TP_UDC"):
        g = g.sort_values("PRIORITA_UTILIZZO")
        m[int(t)] = [(r.cls, int(r.PRIORITA_UTILIZZO)) for r in g.itertuples()]
    return m


def plan_udc_type(tp_pallet, n_strati, codes):
    """Plan pallet configuration -> load unit type code.

    The plan has one carton type, so the load height follows the number of layers:
    up to tall_from_layers - 1 layers fit a 1200 mm cell, more need a 2200 mm cell.
    """
    k = str(tp_pallet)[: codes["pallet_material_prefix_len"]]
    spec = codes["pallet_types"].get(k)
    if spec is None:
        return None
    return spec["tall"] if n_strati >= codes["tall_from_layers"] else spec["normal"]


def pallet_family(tp_pallet, codes):
    k = str(tp_pallet)[: codes["pallet_material_prefix_len"]]
    return codes["pallet_types"].get(k, {}).get("family", "80x120")


def pref_groups(udcmap, t):
    """Priority groups for load unit type t, each a list of classes (ties share a group)."""
    out = {}
    for c, p in udcmap[t]:
        out.setdefault(p, []).append(c)
    return [out[k] for k in sorted(out)]


def load_plan(path, udcmap, codes):
    p = pd.read_excel(path)
    p.columns = [c.strip() for c in p.columns]
    for c in ["DT_INIZIO_OdL", "DT_FINE_OdL", "DT_USCITA_MERCE"]:
        p[c] = pd.to_datetime(p[c].astype(str), format="%Y%m%d")
    for c in ["MACCHINA", "TP_PALLET", "ARTICOLO"]:
        p[c] = p[c].astype(str).str.strip()
    p["ppp"] = p.QTA_BOX * p.N_BOX_STRATO * p.N_STRATI  # pieces per full pallet
    p["npal"] = np.ceil(p.QTA / p.ppp - 1e-9).astype(int)  # pallets incl. the last partial one
    p["udc_type"] = [
        plan_udc_type(a, b, codes) for a, b in zip(p.TP_PALLET, p.N_STRATI, strict=True)
    ]
    p["prefs"] = [pref_groups(udcmap, t) for t in p.udc_type]
    p["pref1"] = [g[0][0] for g in p.prefs]
    p["fam"] = [pallet_family(a, codes) for a in p.TP_PALLET]
    return p


def load_pcs(path):
    pc = pd.read_excel(path)
    pc.columns = [c.strip() for c in pc.columns]
    pc["MACCHINA"] = pc.MACCHINA.astype(str).str.strip()
    return pc.set_index("MACCHINA")["PCS/HOUR"].astype(float)


def load_vr(path):
    v = pd.read_excel(path)
    v.columns = [c.strip() for c in v.columns]
    v["MACCHINA"] = v.MACCHINA.astype(str).str.strip()
    v["DT"] = pd.to_datetime(v.DT_REGISTRAZIONE.astype(str), format="%Y%m%d")
    return v


def load_snapshot(path, codes):
    s = pd.read_excel(path, sheet_name=0)
    s.columns = [c.strip() for c in s.columns]
    s["cls"] = s.TP_CELLA_DESC.str.strip().map(SHORT)
    s["full"] = s.ST_CELLA == 3
    s["enabled"] = s.ST_ATT == 1
    s["fg"] = s.ARTICOLO.astype(str).str.startswith(codes["finished_goods_article_prefix"])
    s["tp"] = pd.to_numeric(s.TP_UDC, errors="coerce")
    s["odv"] = pd.to_numeric(s.ODV, errors="coerce")
    s["pos"] = pd.to_numeric(s.POS, errors="coerce")
    s["xdate"] = pd.to_datetime(s.DT_ESTRAZIONE).dt.normalize()
    return s


def snapshot_level(s):
    return s[s.full & s.enabled].groupby("cls").size().reindex(CLS).fillna(0).astype(float)


def schedule(plan, rate, t0, eta=1.0, slip_days=0.0, done_qty=None, day_hours=24.0):
    """Sequential schedule per machine.

    Each work order starts at max(machine clock, planned start + slip) and runs at eta * PCS/HOUR
    on working days (Mon-Sat, day_hours per day). Returns completed pallets per work order and day
    (the last partial pallet counts at the end of the order), and the finish time of each order
    in days since t0.
    """
    done_qty = done_qty or {}
    rows, fin = [], {}
    for m, g in plan.groupby("MACCHINA"):
        r = rate.get(m, np.nan) * eta
        if not np.isfinite(r):
            r = rate.median() * eta
        clock = 0.0
        for o in g.sort_values(["DT_INIZIO_OdL", "DT_FINE_OdL", "OdL"]).itertuples():
            rem = max(o.QTA - done_qty.get(o.OdL, 0), 0)
            start = max(clock, (o.DT_INIZIO_OdL - t0).days + slip_days)
            ppp = o.ppp
            cum = o.QTA - rem
            t = start
            k_prev = int(np.floor(cum / ppp + 1e-9))
            while cum < o.QTA - 1e-6:
                day = int(np.floor(t + 1e-9))
                dd = t0 + pd.Timedelta(days=day)
                if dd.dayofweek not in WORK_DOW or dd in HOLIDAYS:
                    t = day + 1.0
                    continue
                q = min((day + 1.0 - t) * day_hours * r, o.QTA - cum)
                cum += q
                t = t + q / (day_hours * r)
                if cum < o.QTA - 1e-6:
                    k_now = int(np.floor(cum / ppp + 1e-9))
                else:
                    k_now = int(np.ceil(o.QTA / ppp - 1e-9))
                if k_now > k_prev:
                    rows.append((o.OdL, day, k_now - k_prev))
                k_prev = k_now
                if t >= day + 1.0 - 1e-9:
                    t = day + 1.0
            clock = t
            fin[o.OdL] = t
    return pd.DataFrame(rows, columns=["OdL", "day", "n"]), pd.Series(fin, dtype=float)
