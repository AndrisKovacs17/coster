"""Plan-based flow-balance Monte Carlo simulator for the finished-goods classes Med/High/MedW/HighW.

Conventions. File 5 DT_ANALISI = D is close to the state at the end of day D. File 4 (the cell
table) is extracted during the working day, not at 06:00.
Snapshot(D) = S(D-1) + phi * (S(D) - S(D-1)), phi ~ U(0.6, 1).

Stock = a non-finished-goods part (components, containers, packaging: held constant plus noise)
plus finished-goods pallets grouped by sales order (OdV). A group leaves on one day: the plan's
DT_USCITA_MERCE for its OdV (exact POS, else the earliest POS) plus jitter. Without a date, the
residual life R - a | R > a is drawn from the plan's residence distribution, scaled by m_res.

New pallets: a sequential schedule per machine at eta * PCS/HOUR, a plan slip, a pass-through
share beta, and the 'UDC vs CELLE' priority cascade into free cells. They leave at
max(U + delta_OdL, production + g).

Low is not simulated (no plan inflow, almost no finished goods): statistical model only.
"""

import numpy as np
import pandas as pd
import sim_lib as L
from history import LAYOUT_STABLE_FROM

CI = {c: i for i, c in enumerate(L.FGC)}
ETA_GRID = [0.8, 0.9, 1.0, 1.1]  # machine speed / nominal PCS/HOUR
SLIP_GRID = [-1.0, -0.5, 0.0, 0.5, 1.0, 1.5, 2.0]
SLIP_P = [0.05, 0.10, 0.25, 0.25, 0.15, 0.10, 0.10]
PREF_DEFAULT = {"L1000": [["MedW"], ["HighW"]], "80x120": [["Med"], ["High"], ["MedW", "HighW"]]}


def build_inputs(D, anchor, end_date=None, static_dir=None, f5_path=None, v_ledger=None):
    sd = static_dir or D
    codes = L.load_codes(sd)
    wide_types = set(codes["wide_load_unit_types"])
    um = L.load_udcmap(L.find(sd, "UDC vs CELLE"))
    rate = L.load_pcs(L.find(sd, "PCS-HOUR"))
    plan = L.load_plan(L.find(D, " 1 - PU"), um, codes)
    snap = L.load_snapshot(L.find(D, " 4 - PU"), codes)
    v = L.load_vr(L.find(D, " 2 - PU"))
    r = L.load_vr(L.find(D, " 3 - PU"))
    occ, cap = L.load_f5(f5_path or L.find(D, " 5 - PU"))
    t_f5, t_x = occ.index.max(), snap.xdate.iloc[0]
    fd = L.file_date(L.find(D, " 1 - PU"))
    plan_t0 = (
        fd if fd is not None else plan.DT_INIZIO_OdL.min()
    )  # plan file date (running OdLs may start earlier)
    e = snap[snap.enabled]
    if anchor == "f5":
        start, level = t_f5, occ.loc[t_f5, L.FGC]
        pool = e[e.full & (e.DT_UM <= t_f5)].copy()
    else:
        start, level = t_x, L.snapshot_level(snap)[L.FGC]
        pool = e[e.full].copy()
    capc = cap.loc[t_f5, L.FGC].values.astype(float)
    if end_date is None:
        end_date = t_f5 + pd.Timedelta(days=22)
    days = pd.date_range(min(start, plan_t0), end_date)
    d0 = days[0]
    pool["age"] = (start - pool.DT_UM).dt.days.clip(lower=0)
    pool["fam"] = np.where(pool.tp.isin(wide_types), "L1000", "80x120")
    pk = plan.set_index(["OdV", "POS"]).DT_USCITA_MERCE
    umin = plan.groupby("OdV").DT_USCITA_MERCE.min()
    pool["U"] = [
        pk.get((a, b), umin.get(a, pd.NaT)) if np.isfinite(a) else pd.NaT
        for a, b in zip(pool.odv, pool.pos, strict=False)
    ]
    # FG/NFG split per class; anchor level enforced (File-4 shares only for the f5 anchor)
    nfg, fgp = np.zeros(len(L.FGC)), []
    for c in L.FGC:
        g = pool[pool.cls == c]
        share = float(g.fg.mean()) if len(g) else 0.0
        n_fg = int(round(level[c] * share))
        nfg[CI[c]] = level[c] - n_fg
        f = g[g.fg]
        if len(f) > n_fg:
            f = f.sample(n_fg, random_state=0)
        elif len(f) < n_fg:  # young pallets that left before the File 4 extraction
            extra = pd.DataFrame(
                {
                    "cls": c,
                    "odv": -1.0 - np.arange(n_fg - len(f)),
                    "age": 0,
                    "U": pd.NaT,
                    "fam": "L1000" if c in ("MedW", "HighW") else "80x120",
                }
            )
            f = pd.concat([f[["cls", "odv", "age", "U", "fam"]], extra], ignore_index=True)
        fgp.append(f[["cls", "odv", "age", "U", "fam"]])
    fgp = pd.concat(fgp, ignore_index=True)
    fgp["odv"] = fgp.odv.fillna(-999)
    grp = fgp.groupby("odv").agg(
        a_min=("age", "min"), U=("U", "first"), fam=("fam", lambda x: x.mode().iloc[0])
    )
    grp["U_day"] = [(u - d0).days if pd.notna(u) else np.nan for u in grp.U]
    fgp["g"] = fgp.odv.map({o: i for i, o in enumerate(grp.index)})
    # running OdLs
    vv = (
        pd.concat([v, v_ledger]) if v_ledger is not None else v
    )  # optional multi-day ledger of File 2 rows
    vv = vv.drop_duplicates(subset=["OdL", "DT", "QTA"])
    done = {o: q for o, q in vv.groupby("OdL").QTA.sum().items() if o in set(plan.OdL)}
    nonplan = v[(~v.OdL.isin(plan.OdL)) & (~v.OdL.isin(r.OdL))]
    first_plan_start = plan.groupby("MACCHINA").DT_INIZIO_OdL.min()
    mfam = plan.groupby("MACCHINA").apply(lambda g: (g.fam == "L1000").mean())
    mppp = plan.groupby("MACCHINA").ppp.median()
    backlog = []
    for o in nonplan.itertuples():
        m = o.MACCHINA
        gd = [
            d
            for d in pd.date_range(plan_t0, first_plan_start.get(m, plan_t0) - pd.Timedelta(days=1))
            if d.dayofweek < 6
        ]
        backlog.append(
            dict(
                OdL=o.OdL,
                mach=m,
                days=[(d - d0).days for d in gd],
                maxq=rate.get(m, rate.median()) * 24 * len(gd),
                ppp=mppp.get(m, plan.ppp.median()),
                pL1000=float(mfam.get(m, 0.5)),
            )
        )
    sched = {}
    for et in ETA_GRID:
        for sl in SLIP_GRID:
            s, _ = L.schedule(plan, rate, plan_t0, eta=et, slip_days=sl, done_qty=done)
            s = s.merge(plan[["OdL", "fam", "DT_USCITA_MERCE", "prefs"]], on="OdL")
            s["day"] = s.day + (plan_t0 - d0).days
            s["U_day"] = (s.DT_USCITA_MERCE - d0).dt.days
            sched[(et, sl)] = s
    b = sched[(1.0, 0.0)]
    Rr = np.clip(np.maximum(b.U_day.values, b.day.values + 1) - b.day.values, 1, 60)
    resid = {
        f: np.repeat(Rr[b.fam.values == f], b.n.values[b.fam.values == f])
        for f in ["80x120", "L1000"]
    }
    sidx = (start - d0).days
    hs = {c: [L_hist_sigma(occ, c, h, t_f5) for h in range(1, len(days) + 2)] for c in L.FGC}
    fgshare = {c: 1 - nfg[CI[c]] / max(level[c], 1) for c in L.FGC}
    dows = np.array([(d0 + pd.Timedelta(days=i)).dayofweek for i in range(len(days) + 130)])
    sunday = np.where(
        dows == 6, 1, np.where(dows == 5, -1, 0)
    )  # dispatch dates on weekends: Sat->Fri, Sun->Mon
    workday = dows < 6
    wdays = np.where(dows < 6)[0]  # Mon-Sat day indices (dispatch days)
    return dict(
        plan=plan,
        sched=sched,
        resid=resid,
        fgp=fgp,
        grp=grp,
        nfg=nfg,
        cap=capc,
        start=start,
        sidx=sidx,
        plan_t0=plan_t0,
        days=days,
        d0=d0,
        backlog=backlog,
        occ=occ,
        t_f5=t_f5,
        t_x=t_x,
        anchor=anchor,
        level=level,
        hs=hs,
        fgshare=fgshare,
        sunday=sunday,
        workday=workday,
        wdays=wdays,
        r_unm=np.zeros(4),
    )


def L_hist_sigma(occ, c, h, start):
    """RMS of h-day changes (= persistence error) before start.

    Post-layout window for Low/Med/High (Set B rule),
    last 120 days for MedW/HighW (Set A rule)."""
    o = occ[c].loc[:start]
    o = o.loc[LAYOUT_STABLE_FROM:] if c in ("Low", "Med", "High") else o.iloc[-120:]
    d = (o.shift(-h) - o).dropna()
    return float(np.sqrt(np.mean(d.values**2))) if len(d) > 5 else np.nan


def littles_beta(inp):
    b = inp["sched"][(1.0, 0.0)]
    hd = 22
    out = {}
    for f in ["80x120", "L1000"]:
        lam = b.loc[(b.fam == f) & (b.day - (inp["plan_t0"] - inp["d0"]).days < hd), "n"].sum() / hd
        stock = (inp["fgp"].fam == f).sum()
        out[f] = float(min(stock / (lam * inp["resid"][f].mean()), 1.0))
    return out


def draw_params(rng, mode, mres_c, bstar):
    pr = dict(
        eta=float(rng.choice(ETA_GRID)),
        slip=float(rng.choice(SLIP_GRID, p=SLIP_P)),
        mu_d=rng.uniform(-1, 1),
        mu_g=rng.uniform(0, 1.5),
        phi=rng.uniform(0.6, 1.0),
        backlog_u=rng.uniform(0, 1),
        noise_z=1.0,
    )
    if mode == "lit" and bstar is not None:
        pr["beta80"] = float(np.clip(bstar["80x120"] * np.exp(rng.normal(0, 0.25)), 0.2, 1))
        pr["betaL"] = float(np.clip(bstar["L1000"] * np.exp(rng.normal(0, 0.25)), 0.2, 1))
        pr["m_res"] = float(np.exp(rng.normal(0, 0.3)))
    else:
        bb = rng.uniform(0.6, 1.0)
        pr["beta80"] = float(np.clip(bb + rng.normal(0, 0.05), 0.5, 1))
        pr["betaL"] = float(np.clip(bb + rng.normal(0, 0.05), 0.5, 1))
        pr["m_res"] = float(mres_c * np.exp(rng.normal(0, 0.3)))
    return pr


def add_wd(inp, start_idx, n):
    """day index of the n-th Mon-Fri day after start_idx (vectorised)."""
    w = inp["wdays"]
    pos = np.searchsorted(w, np.asarray(start_idx), side="right")
    return w[np.clip(pos + np.asarray(n) - 1, 0, len(w) - 1)]


def simulate_one(inp, pr, rng, add_noise=True, r_unm=None):
    _days, nd, sidx, capc = inp["days"], len(inp["days"]), inp["sidx"], inp["cap"]
    r_unm = inp["r_unm"] if r_unm is None else r_unm
    sun = inp["sunday"]
    s = inp["sched"][(pr["eta"], pr["slip"])]
    rep = np.repeat(np.arange(len(s)), s.n.values)
    prod = s.day.values[rep]
    fam = s.fam.values[rep]
    keep = rng.random(len(rep)) < np.where(fam == "L1000", pr["betaL"], pr["beta80"])
    keep &= prod > sidx
    rep, prod, fam = rep[keep], prod[keep], fam[keep]
    odl = s.OdL.values[rep]
    uo, inv = np.unique(odl, return_inverse=True)
    dl = np.rint(rng.normal(pr["mu_d"], 1.0, len(uo))).astype(int)[inv]
    g = 1 + rng.poisson(pr["mu_g"], len(rep))
    ex = np.maximum(s.U_day.values[rep] + dl, add_wd(inp, prod, g))
    prefs = [s.prefs.values[i] for i in rep]
    # backlog of non-plan running OdLs
    for bl in inp["backlog"]:
        npal = int(np.floor(pr["backlog_u"] * bl["maxq"] / bl["ppp"]))
        dd = np.array([d for d in bl["days"] if d > sidx])
        if npal <= 0 or len(dd) == 0:
            continue
        pdays = rng.choice(dd, npal)
        isL = rng.random(npal) < bl["pL1000"]
        kp = rng.random(npal) < np.where(isL, pr["betaL"], pr["beta80"])
        for j in np.where(kp)[0]:
            f = "L1000" if isL[j] else "80x120"
            prod = np.append(prod, pdays[j])
            ex = np.append(
                ex, add_wd(inp, pdays[j], max(int(round(rng.choice(inp["resid"][f]) * 6 / 7)), 1))
            )
            prefs.append(PREF_DEFAULT[f])
    # existing FG groups
    grp = inp["grp"]
    ng = len(grp)
    gex = np.empty(ng, dtype=int)
    groups = zip(grp.a_min.values, grp.U_day.values, grp.fam.values, strict=False)
    for i, (a, ud, f) in enumerate(groups):
        if np.isfinite(ud) and ud > sidx:
            gex[i] = max(int(ud + np.rint(rng.normal(pr["mu_d"], 1.0))), sidx + 1)
        elif np.isfinite(ud):  # past due
            gex[i] = add_wd(inp, sidx, 1 + rng.poisson(pr["mu_g"]))
        else:
            Rd = inp["resid"][f]
            cand = Rd[Rd > a]
            res = (rng.choice(cand) - a) if len(cand) else rng.exponential(30.0)
            gex[i] = add_wd(
                inp, sidx, max(int(np.ceil(res * pr["m_res"] * 6 / 7)), 1)
            )  # residual in Mon-Sat days
    ex_old = gex[inp["fgp"].g.values]
    cls_old = inp["fgp"].cls.map(CI).values
    ex = ex.astype(int)
    ex = ex + sun[np.clip(ex, 0, len(sun) - 1)]
    ex_old = ex_old + sun[np.clip(ex_old, 0, len(sun) - 1)]
    state = inp["nfg"].copy() + np.bincount(cls_old, minlength=4)
    occ_d = np.zeros((nd, 4))
    unp = np.zeros(nd)
    exits = np.zeros(nd)
    arr = np.zeros(nd)
    assigned = -np.ones(len(prod), dtype=int)
    order = rng.permutation(len(prod))
    po = prod[order]
    for t in range(nd):
        if t <= sidx:
            occ_d[t] = state
            continue
        m = ex_old == t
        if m.any():
            state -= np.bincount(cls_old[m], minlength=4)
            exits[t] += m.sum()
        m = (ex == t) & (assigned >= 0)
        if m.any():
            state -= np.bincount(assigned[m], minlength=4)
            assigned[m] = -2
            exits[t] += m.sum()
        if inp["workday"][t] and r_unm.any():  # calibrated unmodelled net flow (NFG + non-plan FG)
            state = np.clip(state + r_unm, inp["nfg"] * 0, capc)
        for i in order[po == t]:
            ok = False
            for grp_ in prefs[i]:
                fr = [
                    (capc[CI[c]] - state[CI[c]], c)
                    for c in grp_
                    if c in CI and capc[CI[c]] - state[CI[c]] >= 1
                ]
                if fr:
                    c = max(fr)[1]
                    state[CI[c]] += 1
                    assigned[i] = CI[c]
                    ok = True
                    arr[t] += 1
                    break
            if not ok:
                unp[t] += 1
                assigned[i] = -3
        occ_d[t] = state
    snapv = occ_d.copy()
    snapv[sidx + 1 :] = occ_d[sidx:-1] + pr["phi"] * (occ_d[sidx + 1 :] - occ_d[sidx:-1])
    if add_noise:
        if (
            inp["anchor"] == "f4"
        ):  # File-4 anchor is not the target series: timing/definition offset
            for c in L.FGC:
                w = (1 - inp["fgshare"][c]) + 0.25 * inp["fgshare"][c]
                snapv[sidx:, CI[c]] += rng.normal() * 0.5 * inp["hs"][c][0] * np.sqrt(w)
        z = np.cumsum(rng.normal(size=nd))
        for c in L.FGC:
            w = (1 - inp["fgshare"][c]) + 0.25 * inp["fgshare"][c]
            for t in range(sidx + 1, nd):
                h = t - sidx
                snapv[t, CI[c]] += (
                    pr["noise_z"] * (z[t] - z[sidx]) / np.sqrt(h) * inp["hs"][c][h - 1] * np.sqrt(w)
                )
    return np.clip(snapv, 0, capc), unp, occ_d, exits, arr


def run_mc(inp, N=1000, seed=0, mode="evid", mres_c=1.0, fixed=None, add_noise=True):
    rng = np.random.default_rng(seed)
    bstar = littles_beta(inp)
    out = np.zeros((N, len(inp["days"]), 4))
    unp = np.zeros((N, len(inp["days"])))
    P = []
    for k in range(N):
        pr = draw_params(rng, mode, mres_c, bstar)
        pr.update(fixed or {})
        out[k], unp[k], _, _, _ = simulate_one(inp, pr, rng, add_noise)
        pr["unplaced_total"] = unp[k].sum()
        P.append(pr)
    return out, pd.DataFrame(P), unp, bstar


def calibrate_unmodelled(inp, target_level=None, N=30, iters=5, seed=11, win=(8, 21)):
    """Per-class constant net flow r_c (cells per Mon-Sat day) for what the plan does not explain:
    non-finished goods, finished goods outside the plan, unplanned dispatch.

    Set so that the noise-free expected mean level over days win[0]..win[1] after the anchor equals
    the mean level of the 28 File 5 days before the origin (long-run balance with history, using
    pre-origin data only). Fixed-point iteration.
    """
    if target_level is None:
        target_level = inp["occ"][L.FGC].loc[: inp["t_f5"]].iloc[-28:].mean().values
    a, b = inp["sidx"] + win[0], min(inp["sidx"] + win[1], len(inp["days"]) - 1)
    wd_cum = np.cumsum(
        inp["workday"][: len(inp["days"])] & (np.arange(len(inp["days"])) > inp["sidx"])
    )
    mwd = wd_cum[a : b + 1].mean()
    r = np.zeros(4)
    hist = []
    for it in range(iters):
        rng = np.random.default_rng(seed)
        acc = []
        for _k in range(N):
            pr = draw_params(rng, "evid", 1.0, None)
            _, _, occ_d, _, _ = simulate_one(inp, pr, rng, add_noise=False, r_unm=r)
            acc.append(occ_d[a : b + 1].mean(axis=0))
        m = np.mean(acc, axis=0)
        hist.append(
            dict(
                iter=it,
                **{f"r_{c}": round(r[j], 3) for j, c in enumerate(L.FGC)},
                **{f"mean_{c}": round(m[j], 1) for j, c in enumerate(L.FGC)},
                **{f"target_{c}": round(target_level[j], 1) for j, c in enumerate(L.FGC)},
            )
        )
        r = r + 0.8 * (target_level - m) / mwd
    return r, pd.DataFrame(hist)
