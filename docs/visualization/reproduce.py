#!/usr/bin/env python3
"""Build the judge-rerunnable GQH research dashboard from tracked result artifacts.

This rebuilds the charts and every displayed summary from the repository's committed result
files. It deliberately does not invent daily NAV, drawdown paths, Monte Carlo paths, or regime
returns: those source ledgers are not currently committed.
"""
from __future__ import annotations

import csv
import argparse
import hashlib
import html
import json
import math
from pathlib import Path

import plotly.graph_objects as go
from plotly.offline import get_plotlyjs
from plotly.subplots import make_subplots


HERE = Path(__file__).resolve().parent
# visualization/ -> docs -> repository root
ROOT = HERE.parents[1]
RESULTS = ROOT / "results"
OUT_HTML = HERE / "dashboard.html"
OUT_MANIFEST = HERE / "reproduction-manifest.json"
DAILY_PATH: Path | None = None
TRADES_PATH: Path | None = None
SPLIT_DATE: str | None = None
STARTING_NAV = 100.0
MC_SEED = 2603

COLORS = {
    "bg": "#17191c",
    "surface": "#20252b",
    "fg": "#edf1f5",
    "muted": "#a7b2bf",
    "grid": "#343d47",
    "accent": "#82b9f2",
    "secondary": "#b2a4cb",
    "negative": "#dc9393",
    "positive": "#9bbfaa",
    "warning": "#e2bd77",
}

INPUTS = (
    "three-sleeve-portfolio.json",
    "walk-forward.json",
    "walk-forward-z.json",
    "intensity-timesplit-study.json",
    "intensity-factor-study.json",
    "regime-state-daily.csv",
    "regime-state-summary.json",
)


def read_json(name: str) -> dict:
    return json.loads((RESULTS / name).read_text())


def input_manifest() -> list[dict]:
    rows = []
    for name in INPUTS:
        path = RESULTS / name
        if not path.is_file():
            raise FileNotFoundError(f"Required tracked research artifact is missing: {path}")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        row_count = None
        if path.suffix == ".csv":
            with path.open(newline="") as handle:
                row_count = max(0, sum(1 for _ in csv.reader(handle)) - 1)
        rows.append({"path": path.relative_to(ROOT).as_posix(), "sha256": digest,
                     "bytes": path.stat().st_size, "data_rows": row_count})
    return rows


def make_figure(fig: go.Figure, height: int = 390) -> dict:
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=COLORS["bg"],
        plot_bgcolor=COLORS["bg"],
        font={"family": "system-ui, sans-serif", "size": 12, "color": COLORS["fg"]},
        margin={"l": 70, "r": 28, "t": 44, "b": 62},
        height=height,
        hovermode="x unified",
        legend={"orientation": "h", "y": -0.24, "x": 0},
    )
    fig.update_xaxes(gridcolor=COLORS["grid"], zerolinecolor=COLORS["grid"], automargin=True)
    fig.update_yaxes(gridcolor=COLORS["grid"], zerolinecolor=COLORS["grid"], automargin=True)
    return json.loads(fig.to_json())


def pct(value: float) -> str:
    return f"{value * 100:+.2f}%"


def load_ledger(path: Path) -> list[dict]:
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"Ledger is empty: {path}")
    return rows


def number(row: dict, *names: str) -> float | None:
    for name in names:
        value = row.get(name)
        if value not in (None, ""):
            return float(value)
    return None


def daily_groups(rows: list[dict]) -> dict[str, list[dict]]:
    if not {"date"}.issubset(rows[0]):
        raise ValueError("Daily ledger requires canonical `date` column (ISO YYYY-MM-DD)")
    groups: dict[str, list[dict]] = {}
    for row in rows:
        key = row.get("baseline") or row.get("strategy") or "Strategy"
        groups.setdefault(key, []).append(row)
    for label, group in groups.items():
        group.sort(key=lambda row: row["date"])
        for left, right in zip(group, group[1:]):
            if left["date"] == right["date"]:
                raise ValueError(f"Duplicate date {left['date']} for baseline {label}")
        if not any(number(row, "net_return", "return") is not None or number(row, "nav") is not None for row in group):
            raise ValueError("Daily ledger requires `net_return` or `nav`; returns must be decimal fractions")
    return groups


def returns_and_nav(rows: list[dict]) -> tuple[list[str], list[float], list[float]]:
    dates = [row["date"] for row in rows]
    navs = [number(row, "nav") for row in rows]
    if all(value is not None for value in navs):
        source_nav = [float(value) for value in navs]
        if source_nav[0] <= 0:
            raise ValueError("NAV must start above zero")
        rets = [0.0]
        rets.extend(source_nav[i] / source_nav[i - 1] - 1 if source_nav[i - 1] else 0.0 for i in range(1, len(source_nav)))
        nav = [value / source_nav[0] * STARTING_NAV for value in source_nav]
        return dates, rets, nav
    rets = [number(row, "net_return", "return") for row in rows]
    if any(value is None for value in rets):
        raise ValueError("A daily ledger may not mix missing NAV and return observations")
    nav = []
    current = STARTING_NAV
    for ret in rets:
        current *= 1 + float(ret)
        nav.append(current)
    return dates, [float(value) for value in rets], nav


def observed_periods(rows: list[dict], dates: list[str], returns: list[float]) -> tuple[list[str], list[float]]:
    """Return only dated returns actually observable from the input representation.

    An end-of-day NAV series does not reveal the return before its first NAV point;
    that first point is an anchor, not a zero-return observation.
    """
    if all(number(row, "nav") is not None for row in rows):
        return dates[1:], returns[1:]
    return dates, returns


def max_drawdown(nav: list[float]) -> list[float]:
    # All plotted NAV curves are rebased to 100. Include that initial capital
    # before the first return observation so first-period losses count.
    high, out = STARTING_NAV, []
    for value in nav:
        high = max(high, value)
        out.append(value / high - 1 if high else 0.0)
    return out


def daily_metrics(rows: list[dict], trades: list[dict] | None = None) -> dict:
    dates, returns, nav = returns_and_nav(rows)
    return_dates, period_returns = observed_periods(rows, dates, returns)
    n = len(period_returns)
    mean = sum(period_returns) / n if n else 0
    variance = sum((r - mean) ** 2 for r in period_returns) / (n - 1) if n > 1 else 0
    sd = math.sqrt(variance)
    downside = math.sqrt(sum(min(r, 0) ** 2 for r in period_returns) / n) if n else 0
    dd = max_drawdown(nav)
    total_return = nav[-1] / STARTING_NAV - 1 if nav else 0
    annual = (nav[-1] / STARTING_NAV) ** (252 / n) - 1 if n and nav[-1] > 0 else None
    selected = trades or []
    pnls = [number(row, "net_pnl", "pnl", "realized_pnl") for row in selected]
    pnls = [value for value in pnls if value is not None]
    wins = [value for value in pnls if value > 0]
    losses = [value for value in pnls if value < 0]
    turnover_values = [number(row, "turnover", "gross_turnover") for row in rows]
    turnover_values = [value for value in turnover_values if value is not None]
    costs = [number(row, "costs", "total_cost", "fees") for row in rows]
    costs = [value for value in costs if value is not None]
    return {
        "observations": n, "start": return_dates[0] if return_dates else None, "end": return_dates[-1] if return_dates else None,
        "pnl_index": nav[-1] - STARTING_NAV if nav else None, "total_return": total_return,
        "annualized_return": annual, "sharpe": math.sqrt(252) * mean / sd if sd else None,
        "sortino": math.sqrt(252) * mean / downside if downside else None,
        "max_drawdown": min(dd) if dd else None,
        "calmar": annual / abs(min(dd)) if annual is not None and dd and min(dd) < 0 else None,
        "annualized_volatility": sd * math.sqrt(252),
        "trade_count": len(pnls) if selected else None,
        "profit_factor": sum(wins) / abs(sum(losses)) if losses else None,
        "win_rate": len(wins) / len(pnls) if pnls else None,
        "average_win": sum(wins) / len(wins) if wins else None,
        "average_loss": sum(losses) / len(losses) if losses else None,
        "cost_total": sum(costs) if costs else None,
        "mean_daily_turnover": sum(turnover_values) / len(turnover_values) if turnover_values else None,
    }


def ledger_figures(daily: dict[str, list[dict]], trades: list[dict] | None) -> tuple[list[dict], list[list[str]], list[dict]]:
    """Build the full diagnostic suite only from explicit daily/trade ledgers."""
    figures: list[dict] = []
    stats: list[list[str]] = []
    metric_manifest: list[dict] = []
    prepared = {name: returns_and_nav(rows) for name, rows in daily.items()}
    trade_groups: dict[str, list[dict]] = {name: [] for name in daily}
    if trades:
        for trade in trades:
            name = trade.get("baseline") or trade.get("strategy") or "Strategy"
            if name in trade_groups:
                trade_groups[name].append(trade)

    all_metrics = {}
    for name, rows in daily.items():
        metrics = daily_metrics(rows, trade_groups[name])
        all_metrics[name] = metrics
        metric_manifest.append({"baseline": name, **metrics})
        stats.append([name, str(metrics["observations"]), pct(metrics["total_return"]),
                      f'{metrics["pnl_index"]:+.2f}',
                      f'{metrics["sharpe"]:.3f}' if metrics["sharpe"] is not None else "—",
                      f'{metrics["sortino"]:.3f}' if metrics["sortino"] is not None else "—",
                      f'{metrics["calmar"]:.3f}' if metrics["calmar"] is not None else "—",
                      pct(metrics["max_drawdown"] or 0),
                      f'{metrics["profit_factor"]:.3f}' if metrics["profit_factor"] is not None else "—",
                      pct(metrics["win_rate"] or 0) if metrics["win_rate"] is not None else "—",
                      f'{metrics["average_win"]:.2f}' if metrics["average_win"] is not None else "—",
                      f'{metrics["average_loss"]:.2f}' if metrics["average_loss"] is not None else "—",
                      str(metrics["trade_count"] if metrics["trade_count"] is not None else "—"),
                      pct(metrics["annualized_volatility"]),
                      f'{metrics["mean_daily_turnover"]:.3f}×' if metrics["mean_daily_turnover"] is not None else "—"])

    # Full-period portfolio equity and drawdown, with matching source dates per baseline.
    eq = go.Figure(); ddfig = go.Figure(); rolling = go.Figure(); sortino_fig = go.Figure(); volfig = go.Figure(); turnover_fig = go.Figure()
    corr_names = list(daily)
    ret_maps = {}
    for name, (dates, rets, nav) in prepared.items():
        return_dates, period_returns = observed_periods(daily[name], dates, rets)
        color = COLORS["accent"] if len(eq.data) == 0 else COLORS["secondary"] if len(eq.data) == 1 else None
        eq.add_trace(go.Scatter(x=dates, y=nav, mode="lines", name=name,
                                line={"width": 2.4, **({"color": color} if color else {})}))
        ddfig.add_trace(go.Scatter(x=dates, y=[100 * value for value in max_drawdown(nav)], mode="lines",
                                   name=name, fill="tozeroy", line={"width": 1.8}))
        ret_maps[name] = dict(zip(return_dates, period_returns))
        window = 63
        rs, rsortino, rv = [], [], []
        for i in range(len(period_returns)):
            segment = period_returns[max(0, i-window+1):i+1]
            mu = sum(segment)/len(segment)
            sigma = math.sqrt(sum((r-mu)**2 for r in segment)/(len(segment)-1)) if len(segment)>1 else 0
            rs.append(math.sqrt(252)*mu/sigma if sigma else None)
            down=math.sqrt(sum(min(r,0)**2 for r in segment)/len(segment))
            rsortino.append(math.sqrt(252)*mu/down if down else None)
            rv.append(sigma*math.sqrt(252)*100)
        rolling.add_trace(go.Scatter(x=return_dates, y=rs, mode="lines", name=name, line={"width": 1.8}))
        sortino_fig.add_trace(go.Scatter(x=return_dates, y=rsortino, mode="lines", name=name, line={"width": 1.8}))
        volfig.add_trace(go.Scatter(x=return_dates, y=rv, mode="lines", name=name, line={"width": 1.8}))
        turnovers=[number(row,"turnover","gross_turnover") for row in rows]
        if any(value is not None for value in turnovers):
            turnover_fig.add_trace(go.Scatter(x=dates,y=turnovers,mode="lines",name=name,line={"width":1.8}))
    rolling.add_hline(y=0, line_dash="dot", line_color=COLORS["muted"])
    for title, fig, ylabel, caption, height in (
        ("Daily equity curves by baseline", eq, "NAV index (base 100)", "Compounded from the provided net-return ledger; if NAV was supplied, daily returns are derived from adjacent observations. No missing dates are filled.", 440),
        ("Drawdown from running peak", ddfig, "Drawdown (%)", "Same baseline NAV curves as above; drawdown is shown below zero from each running peak.", 330),
        ("Rolling 63-session Sharpe", rolling, "Annualized Sharpe", "Rolling mean / sample standard deviation × √252; first windows are shorter until 63 observations accumulate.", 330),
        ("Rolling 63-session Sortino", sortino_fig, "Annualized Sortino", "Rolling mean / downside deviation × √252; downside deviation is RMS of negative daily net returns.", 330),
        ("Rolling realized volatility", volfig, "Annualized volatility (%)", "Rolling sample standard deviation × √252. Uses the supplied net daily return series.", 330),
    ):
        fig.update_xaxes(title="Date")
        fig.update_yaxes(title=ylabel)
        if "Drawdown" in title:
            fig.add_hline(y=0, line_color=COLORS["muted"], line_dash="dot")
        figures.append({"title": title, "caption": caption, "figure": make_figure(fig, height)})
    if turnover_fig.data:
        turnover_fig.update_xaxes(title="Date")
        turnover_fig.update_yaxes(title="Turnover (ledger units)")
        figures.append({"title":"Daily turnover", "caption":"Source: turnover or gross_turnover from the daily output ledger. The producer must define units (e.g., notional, NAV multiple) in its metadata.", "figure":make_figure(turnover_fig,330)})
    else:
        figures.append(unavailable("Daily turnover", "Daily ledger has no turnover/gross_turnover field. Add executed notional and define units."))

    # Baseline cross-correlation, matched by date intersection.
    common = sorted(set.intersection(*(set(ret_maps[name]) for name in corr_names))) if corr_names else []
    if len(corr_names) >= 2 and len(common) >= 2:
        matrix = []
        vectors = [[ret_maps[name][day] for day in common] for name in corr_names]
        for a in vectors:
            row = []
            for b in vectors:
                ma, mb = sum(a)/len(a), sum(b)/len(b)
                den = math.sqrt(sum((x-ma)**2 for x in a)*sum((y-mb)**2 for y in b))
                row.append(sum((x-ma)*(y-mb) for x,y in zip(a,b))/den if den else 0)
            matrix.append(row)
        heat = go.Figure(go.Heatmap(x=corr_names, y=corr_names, z=matrix, zmin=-1, zmax=1, zmid=0,
                 colorscale=[[0, COLORS["negative"]],[0.5,COLORS["bg"]],[1,COLORS["accent"]]],
                 colorbar={"title":"ρ"}, hovertemplate="%{y} × %{x}<br>Daily return ρ=%{z:.3f}<extra></extra>"))
        heat.update_yaxes(autorange="reversed")
        figures.append({"title":"Daily net-return correlation across baselines",
                        "caption":f"Pearson correlation over the {len(common)} dates common to every baseline. Returns are aligned by exact date; no forward fill.",
                        "figure":make_figure(heat, 390)})
    else:
        figures.append(unavailable("Baseline correlation heatmap", "Requires two or more baselines with at least two aligned daily returns."))

    if trades:
        pnlfig = go.Figure(); activity = go.Figure(); outcome_fig = go.Figure()
        has_dates = all(trade.get("entry_date") or trade.get("date") for trade in trades)
        for name, subset in trade_groups.items():
            vals = [number(row, "net_pnl", "pnl", "realized_pnl") for row in subset]
            vals = [value for value in vals if value is not None]
            if vals:
                outcome_fig.add_trace(go.Histogram(x=vals, name=name, opacity=.68, nbinsx=45))
                wins = [v for v in vals if v > 0]; losses = [v for v in vals if v < 0]
                pnlfig.add_trace(go.Box(y=vals, name=name, boxpoints="outliers"))
            if has_dates and subset:
                monthly: dict[str, list[dict]] = {}
                for row in subset:
                    day = row.get("entry_date") or row.get("date")
                    month = day[:7]
                    monthly.setdefault(month, []).append(row)
                months = sorted(monthly)
                activity.add_trace(go.Bar(x=months, y=[len(monthly[m]) for m in months], name=f"{name} · entries"))
        if outcome_fig.data:
            outcome_fig.update_layout(barmode="overlay")
            outcome_fig.add_vline(x=0, line_color=COLORS["muted"], line_dash="dot")
            outcome_fig.update_xaxes(title="Closed-trade net P&L (input currency)")
            outcome_fig.update_yaxes(title="Trade count")
            figures.append({"title":"Trade net-P&L distribution", "caption":"Closed trade outcomes from the supplied trade ledger. The zero line separates gains and losses; boundary or open trades are included only if provided.", "figure":make_figure(outcome_fig,390)})
            pnlfig.update_yaxes(title="Closed-trade net P&L (input currency)")
            figures.append({"title":"Trade outcome spread", "caption":"Box plot by baseline. Summary win/loss statistics appear in the performance table.", "figure":make_figure(pnlfig,350)})
        if activity.data:
            activity.update_layout(barmode="group")
            activity.update_xaxes(title="Entry month")
            activity.update_yaxes(title="Trade count")
            figures.append({"title":"Trade frequency by entry month", "caption":"Counts are derived from entry_date (or date) in the trade ledger.", "figure":make_figure(activity,350)})
            sizes = {name:[number(row,"size","quantity","notional","entry_notional") for row in subset] for name,subset in trade_groups.items()}
            if any(any(v is not None for v in values) for values in sizes.values()):
                sizefig=go.Figure()
                for name,subset in trade_groups.items():
                    vals=[number(row,"size","quantity","notional","entry_notional") for row in subset]
                    vals=[v for v in vals if v is not None]
                    if vals: sizefig.add_trace(go.Box(y=vals,name=name,boxpoints="outliers"))
                sizefig.update_yaxes(title="Trade size (as supplied; retain units)")
                figures.append({"title":"Trade-size distribution", "caption":"Uses first available field among size, quantity, notional, and entry_notional; values are not normalized across units.", "figure":make_figure(sizefig,350)})
            # Trade-level factor correlations: only numeric fields explicitly present are used.
            fields=[("Net P&L",("net_pnl","pnl","realized_pnl")),("Size",("size","quantity","notional","entry_notional")),
                    ("Costs",("costs","fees","transaction_cost")),("Duration",("holding_days","duration_days"))]
            labels=[]; vectors=[]
            for label, aliases in fields:
                values=[number(row,*aliases) for row in trades]
                if values and all(value is not None for value in values):
                    labels.append(label); vectors.append(values)
            if len(labels)>=2:
                matrix=[]
                for a in vectors:
                    row=[]
                    for b in vectors:
                        ma=sum(a)/len(a); mb=sum(b)/len(b)
                        den=math.sqrt(sum((x-ma)**2 for x in a)*sum((y-mb)**2 for y in b))
                        row.append(sum((x-ma)*(y-mb) for x,y in zip(a,b))/den if den else 0)
                    matrix.append(row)
                tradeheat=go.Figure(go.Heatmap(x=labels,y=labels,z=matrix,zmin=-1,zmax=1,zmid=0,
                    colorscale=[[0,COLORS["negative"]],[.5,COLORS["bg"]],[1,COLORS["accent"]]],
                    hovertemplate="%{y} × %{x}<br>Pearson ρ=%{z:.3f}<extra></extra>"))
                tradeheat.update_yaxes(autorange="reversed")
                figures.append({"title":"Trade size, costs, duration, and outcome correlation", "caption":"Pearson correlations across complete rows in the trade ledger. Correlation is descriptive; it does not establish causality. Units must be consistent within each field.", "figure":make_figure(tradeheat,380)})
            else:
                figures.append(unavailable("Trade size and outcome correlation", "Requires two or more fully populated numeric fields among net P&L, size/notional, costs, and duration."))

            # Rolling monthly quality diagnostics, computed from realized trade outcomes.
            quality=go.Figure()
            for name,subset in trade_groups.items():
                dated=[]
                for row in subset:
                    day=row.get("entry_date") or row.get("date")
                    value=number(row,"net_pnl","pnl","realized_pnl")
                    if day and value is not None: dated.append((day[:7],value))
                months=sorted({m for m,_ in dated})
                if months:
                    wr=[]; pf=[]
                    for i,month in enumerate(months):
                        recent=[value for m,value in dated if max(0,i-5)<=months.index(m)<=i]
                        wins=[v for v in recent if v>0]; losses=[v for v in recent if v<0]
                        wr.append(100*len(wins)/len(recent) if recent else None)
                        pf.append(sum(wins)/abs(sum(losses)) if losses and sum(losses)!=0 else None)
                    quality.add_trace(go.Scatter(x=months,y=wr,mode="lines+markers",name=f"{name} · win rate (%)"))
                    quality.add_trace(go.Scatter(x=months,y=pf,mode="lines+markers",name=f"{name} · profit factor",yaxis="y2"))
            if quality.data:
                quality.update_layout(yaxis={"title":"Rolling 6-month win rate (%)"},yaxis2={"title":"Rolling 6-month profit factor","overlaying":"y","side":"right"})
                quality.update_xaxes(title="Entry month")
                figures.append({"title":"Rolling trade win rate and profit factor", "caption":"Trailing six entry-month buckets; values are withheld where no loss occurred (profit factor undefined) or no trades exist.", "figure":make_figure(quality,370)})
    else:
        for title, reason in (("Trade outcome distribution", "Requires a trade ledger with baseline and net_pnl (or pnl)."),
                              ("Trade frequency and size", "Requires entry_date plus a size/quantity/notional field in a trade ledger.")):
            figures.append(unavailable(title, reason))

    # Monte Carlo uses a seeded circular block bootstrap on supplied daily net returns.
    mc = go.Figure(); terminal = go.Figure(); mddfig = go.Figure()
    rng = __import__("numpy").random.default_rng(MC_SEED)
    import numpy as np
    mc_block_sizes=[]
    observed_mdds = {}
    observed_terminals = {}
    for name, rows in daily.items():
        dates, rets, nav = prepared[name]
        _, period_returns = observed_periods(rows, dates, rets)
        if len(period_returns) < 40:
            continue
        horizon = min(252, len(period_returns))
        paths_n, block = 250, min(20, max(2, len(period_returns)//2))
        mc_block_sizes.append(block)
        starts = rng.integers(0, len(period_returns), size=(paths_n, math.ceil(horizon/block)))
        indices = (starts[:,:,None] + np.arange(block)) % len(period_returns)
        sampled = np.asarray(period_returns)[indices.reshape(paths_n,-1)[:,:horizon]]
        curves = STARTING_NAV*np.cumprod(1+sampled,axis=1)
        for i in range(min(60, paths_n)):
            mc.add_trace(go.Scatter(x=list(range(horizon+1)),y=np.r_[STARTING_NAV,curves[i]],mode="lines",showlegend=False,
                                    line={"color":"rgba(130,185,242,0.13)","width":1},hoverinfo="skip"))
        # The displayed actual path and simulated paths both show a start point at 100,
        # followed by exactly `horizon` one-period returns.
        observed_returns = period_returns[-horizon:]
        observed_curve = STARTING_NAV * np.r_[1.0, np.cumprod(1 + np.asarray(observed_returns))]
        observed_dd = float(np.min(observed_curve / np.maximum.accumulate(observed_curve) - 1))
        observed_terminal = float(observed_curve[-1] / STARTING_NAV - 1)
        observed_mdds[name] = observed_dd
        observed_terminals[name] = observed_terminal
        mc.add_trace(go.Scatter(x=list(range(horizon+1)),y=observed_curve,
                                mode="lines",name=f"Observed · {name}",line={"color":COLORS["accent"],"width":3.2}))
        finals=curves[:,-1]/STARTING_NAV-1
        mcmeta={"baseline":name,"seed":MC_SEED,"method":"circular block bootstrap","paths":paths_n,
                "block_sessions":block,"horizon_sessions":horizon,"observed_horizon_return":observed_terminal,
                "observed_horizon_max_drawdown":observed_dd,
                "simulated_terminal_p05":float(np.quantile(finals,.05)),"simulated_terminal_median":float(np.quantile(finals,.5)),
                "simulated_terminal_p95":float(np.quantile(finals,.95))}
        metric_manifest.append({"monte_carlo":mcmeta})
        terminal.add_trace(go.Histogram(x=finals*100,name=name,opacity=.7,nbinsx=35))
        path_matrix=np.column_stack([np.full(paths_n,STARTING_NAV),curves])
        simdds=np.min(path_matrix[:,1:]/np.maximum.accumulate(path_matrix,axis=1)[:,1:]-1,axis=1)
        mddfig.add_trace(go.Histogram(x=simdds*100,name=name,opacity=.7,nbinsx=35))
    if mc.data:
        mc.add_hline(y=STARTING_NAV,line_color=COLORS["muted"],line_dash="dot")
        mc.update_xaxes(title="Sessions from matched starting capital (session 0 = 100)")
        mc.update_yaxes(title="Rebased equity index (start = 100)")
        figures.append({"title":"Circular block-bootstrap paths · observed versus simulated", "caption":f"Seed {MC_SEED}; 250 paths per baseline, circular block sizes {sorted(set(mc_block_sizes))} sessions, horizon capped at 252 sessions. Thin paths are simulations; bold line is observed over the same horizon and rebased to 100. A bootstrap is a sensitivity diagnostic, not a forecast or proof of edge.", "figure":make_figure(mc,450)})
        terminal.update_layout(barmode="overlay")
        for name, value in observed_terminals.items():
            terminal.add_vline(x=value * 100, line_color=COLORS["accent"], line_dash="dash",
                               annotation_text=f"Observed · {name}", annotation_position="top")
        terminal.update_xaxes(title="Simulated terminal return (%)")
        terminal.update_yaxes(title="Bootstrap path count")
        figures.append({"title":"Monte Carlo terminal-return distribution", "caption":"Same fixed-seed block-bootstrap paths as the overlay. Tails are conditional on the supplied observed returns.", "figure":make_figure(terminal,350)})
        mddfig.update_layout(barmode="overlay")
        for name, value in observed_mdds.items():
            mddfig.add_vline(x=value * 100, line_color=COLORS["accent"], line_dash="dash",
                             annotation_text=f"Observed · {name}", annotation_position="top")
        mddfig.update_xaxes(title="Simulated maximum drawdown (%)")
        mddfig.update_yaxes(title="Bootstrap path count")
        figures.append({"title":"Monte Carlo maximum-drawdown distribution", "caption":"Drawdown from each simulated path's own running peak, including initial NAV=100.", "figure":make_figure(mddfig,350)})
    else:
        figures.append(unavailable("Monte Carlo paths and risk distributions", "Requires at least 40 valid daily net-return observations. Existing annual summary values cannot substitute for daily returns."))

    # Separate sample views only when the provider explicitly labels samples or a declared split is passed.
    samples: dict[str, list[dict]] = {}
    if SPLIT_DATE:
        samples = {"In sample": [], "Out of sample": []}
        for name, rows in daily.items():
            for row in rows:
                samples["In sample" if row["date"] < SPLIT_DATE else "Out of sample"].append({**row,"baseline":name})
    elif all("sample" in row for rows in daily.values() for row in rows):
        aliases={"is":"In sample","in sample":"In sample","in_sample":"In sample","train":"In sample",
                 "oos":"Out of sample","out of sample":"Out of sample","out_of_sample":"Out of sample","test":"Out of sample"}
        sample_values={str(row["sample"]).strip().lower() for rows in daily.values() for row in rows}
        if sample_values and all(value in aliases for value in sample_values):
            for name, rows in daily.items():
                for row in rows:
                    samples.setdefault(aliases[str(row["sample"]).strip().lower()], []).append({**row,"baseline":name})
    if samples and len(samples) >= 2:
        fig=make_subplots(rows=1,cols=2,subplot_titles=list(samples),shared_yaxes=False,horizontal_spacing=.12)
        for col,(sample, rows) in enumerate(samples.items(),1):
            for name in daily:
                subset=sorted([r for r in rows if (r.get("baseline") or r.get("strategy") or "Strategy")==name],key=lambda r:r["date"])
                if subset:
                    dates,_,nav=returns_and_nav(subset)
                    fig.add_trace(go.Scatter(x=dates,y=nav,mode="lines",name=name,legendgroup=name,
                                             showlegend=col==1,line={"width":2}),row=1,col=col)
        fig.update_xaxes(title="Date"); fig.update_yaxes(title="Sample-local NAV (base 100)")
        figures.append({"title":"Chronological in-sample versus out-of-sample equity", "caption":f"Split defined by {'CLI date '+SPLIT_DATE if SPLIT_DATE else 'the explicit sample column in the ledger'}. Each sample is independently rebased to 100; the OOS panel is never used to tune the strategy.", "figure":make_figure(fig,430)})
    else:
        figures.append(unavailable("In-sample versus out-of-sample figures", "Provide a `sample` column with explicit IS/OOS labels or pass a predeclared `--split-date YYYY-MM-DD`. Do not choose the split after inspecting returns."))
    return figures, stats, metric_manifest


def unavailable(title: str, reason: str) -> dict:
    fig = go.Figure()
    fig.add_annotation(text="NOT AVAILABLE · NO SOURCE LEDGER", x=.5, y=.58, xref="paper", yref="paper",
                       showarrow=False, font={"size":16,"color":COLORS["muted"]})
    fig.add_annotation(text=reason, x=.5, y=.38, xref="paper", yref="paper", showarrow=False,
                       font={"size":12,"color":COLORS["warning"]}, align="center")
    fig.update_xaxes(visible=False); fig.update_yaxes(visible=False)
    return {"title":title,"caption":"This panel will populate when the required actual ledger is supplied. No synthetic values are shown.","figure":make_figure(fig,250)}


def metric_rows(three: dict, raw: dict, zed: dict) -> list[list[str]]:
    rows = []
    for label, metrics in (
        ("Three-sleeve · equal gross", three["portfolios"]["equal_gross"]["metrics"]),
        ("Three-sleeve · inverse vol", three["portfolios"]["inverse_vol"]["metrics"]),
        ("Three-sleeve · inverse vol + target", three["portfolios"]["inverse_vol_vol_target"]["metrics"]),
    ):
        rows.append(summary_metric_row(label, metrics))
    for label, file in (("Walk-forward · raw surprise", raw), ("Walk-forward · standardized surprise", zed)):
        for name in ("equal_gross", "inverse_vol"):
            m = file["portfolios"][name]["metrics"]
            rows.append(summary_metric_row(f"{label} · {name.replace('_', ' ')}", m))
    for sleeve, payload in three["sleeves"].items():
        m = payload["metrics"]
        rows.append(summary_metric_row(f"Three-sleeve · {sleeve}", m))
    return rows


def summary_metric_row(label: str, metrics: dict) -> list[str]:
    annual = metrics.get("annual_return")
    drawdown = metrics.get("max_drawdown")
    calmar = annual / abs(drawdown) if annual is not None and drawdown else None
    fmt = lambda value: f"{value:.3f}" if value is not None else "—"
    hit_rate = metrics.get("hit_rate")
    return [label, str(metrics.get("days", "—")), pct(metrics["total_return"]),
            pct(annual), pct(metrics.get("annual_vol")), fmt(metrics.get("sharpe")),
            "—", fmt(calmar), pct(drawdown), fmt(metrics.get("profit_factor")),
            "—", pct(hit_rate) if hit_rate is not None else "—"]


def build() -> dict:
    three = read_json("three-sleeve-portfolio.json")
    raw = read_json("walk-forward.json")
    zed = read_json("walk-forward-z.json")
    split = read_json("intensity-timesplit-study.json")
    factor = read_json("intensity-factor-study.json")
    regime_summary = read_json("regime-state-summary.json")
    with (RESULTS / "regime-state-daily.csv").open(newline="") as handle:
        regimes = list(csv.DictReader(handle))

    if three.get("scope") != "development_only" or zed.get("scope") != "development_only":
        raise ValueError("Unexpected result scope; review before presenting as judge-facing evidence")
    if len(regimes) != regime_summary["months"]:
        raise ValueError("Regime timeline row count does not match its summary artifact")

    manifest_inputs = input_manifest()
    for path, kind in ((DAILY_PATH,"daily_ledger"),(TRADES_PATH,"trade_ledger")):
        if path:
            resolved=path.expanduser().resolve()
            if not resolved.is_file():
                raise FileNotFoundError(resolved)
            blob=resolved.read_bytes()
            manifest_inputs.append({"path":str(resolved),"kind":kind,"sha256":hashlib.sha256(blob).hexdigest(),"bytes":len(blob)})
    figures: list[dict] = []
    ledger_metrics: list[dict] = []
    ledger_rows: list[list[str]] = []
    ledger_ready = False
    if DAILY_PATH:
        raw_rows = load_ledger(DAILY_PATH)
        groups = daily_groups(raw_rows)
        trade_rows = load_ledger(TRADES_PATH) if TRADES_PATH else None
        extra_figures, ledger_rows, ledger_metrics = ledger_figures(groups, trade_rows)
        figures.extend(extra_figures)
        ledger_ready = True

    # The annual contributions are the highest-resolution walk-forward performance series
    # actually tracked in the repo. These are annualized means, not compounded equity returns.
    yearly = zed["yearly_contributions"]
    years = sorted(yearly["revenue"], key=int)
    fig = go.Figure()
    for key, label, color in (
        ("revenue", "Revenue sleeve · annualized mean daily net contribution", COLORS["accent"]),
        ("capex", "Capex sleeve · annualized mean daily net contribution", COLORS["secondary"]),
    ):
        fig.add_trace(go.Scatter(
            x=years, y=[100 * yearly[key][year] for year in years], mode="lines+markers",
            name=label, line={"color": color, "width": 2.7}, marker={"size": 7},
        ))
    fig.add_hline(y=0, line_color=COLORS["muted"], line_dash="dot")
    fig.update_xaxes(title="Walk-forward year (2026 is partial)")
    fig.update_yaxes(title="Annualized mean daily net contribution (%/year)")
    figures.append({"title": "Walk-forward sleeve contribution by year",
                    "caption": "Source: results/walk-forward-z.json · 2019–2026, with 2026 partial through August. These yearly sleeve summaries are not a daily NAV path or compounded calendar-year return.",
                    "figure": make_figure(fig)})

    # Era study: preserve spread sign and horizon, with actual event counts in hover labels.
    horizons = ["5", "20", "60"]
    fig = go.Figure()
    for period, label, color in (("early", "Early · through 2024-12-31", COLORS["accent"]),
                                 ("late", "Late · from 2025-01-01", COLORS["secondary"])):
        block = split["windows"][period]["horizons"]
        fig.add_trace(go.Scatter(
            x=[f"{h} sessions" for h in horizons],
            y=[100 * block[h]["tercile_spread"] for h in horizons],
            mode="lines+markers", name=label, line={"color": color, "width": 2.7},
            marker={"size": 8},
            text=[f'n={block[h]["n"]}; quarters={block[h]["quarters"]}; p={block[h]["two_sided_permutation_p"]:.3f}' for h in horizons],
            hovertemplate="%{x}<br>Top-minus-bottom spread: %{y:.2f}%<br>%{text}<extra>%{fullData.name}</extra>",
        ))
    fig.add_hline(y=0, line_color=COLORS["muted"], line_dash="dot")
    fig.update_xaxes(title="Forward-return horizon")
    fig.update_yaxes(title="Top-minus-bottom tercile excess return spread (%)")
    figures.append({"title": "Intensity association by sample era",
                    "caption": "Source: results/intensity-timesplit-study.json · early N=229 across 21 quarters; late N=97–105 across 4–5 quarters. Development-only, overlapping forward windows; the late 60-session estimate is a sign reversal with wide uncertainty.",
                    "figure": make_figure(fig)})

    # Group-by-horizon factor correlations are best read as a zero-centered heatmap.
    group_names = ["power", "hyperscaler", "data_center_reit", "fuel_and_nuclear", "buildout", "compute_and_ai"]
    group_labels = ["Power", "Hyperscaler", "Data-center REIT", "Fuel / nuclear", "Buildout", "Compute / AI"]
    horizon_labels = ["5 sessions", "20 sessions", "60 sessions"]
    zvals = []
    for h in ("5", "20", "60"):
        zvals.append([factor["horizons"][h]["complex"]["per_group_rho"][name] for name in group_names])
    heat = go.Figure(go.Heatmap(
        x=group_labels, y=horizon_labels, z=zvals, zmin=-0.30, zmax=0.30, zmid=0,
        colorscale=[[0, COLORS["negative"]], [0.5, COLORS["bg"]], [1, COLORS["accent"]]],
        colorbar={"title": "Spearman ρ"},
        hovertemplate="%{y} · %{x}<br>Mean within-quarter Spearman ρ: %{z:.3f}<extra></extra>",
    ))
    heat.update_xaxes(title="Exposure group", tickangle=-15)
    heat.update_yaxes(title="Forward horizon", autorange="reversed")
    figures.append({"title": "Factor association by group and horizon",
                    "caption": f"Source: results/intensity-factor-study.json · {factor['observations']} observations, {factor['names']} names, 29 quarters. Color is zero-centered; correlations are descriptive, small/mixed, and not evidence of causality.",
                    "figure": make_figure(heat, height=360)})

    # Regime strip. Build categorical month segments from the actual monthly source rows.
    phase_order = ["buildout", "overbuild", "shakeout", "shortage", "consolidation"]
    phase_colors = {"buildout": COLORS["positive"], "overbuild": COLORS["warning"],
                    "shakeout": COLORS["negative"], "shortage": COLORS["accent"],
                    "consolidation": COLORS["secondary"]}
    phase_vals = [row["phase"] for row in regimes]
    fig = go.Figure()
    start = 0
    while start < len(regimes):
        end = start + 1
        while end < len(regimes) and phase_vals[end] == phase_vals[start]:
            end += 1
        phase = phase_vals[start]
        fig.add_trace(go.Scatter(
            x=[regimes[start]["month"], regimes[end - 1]["month"]], y=[1, 1],
            mode="lines", name=phase.replace("_", " ").title(),
            legendgroup=phase, showlegend=phase not in phase_vals[:start],
            line={"color": phase_colors.get(phase, COLORS["muted"]), "width": 20},
            hovertemplate=f"{regimes[start]['month']} to {regimes[end - 1]['month']}<br>{phase.replace('_', ' ').title()} · {end-start} months<extra></extra>",
        ))
        start = end
    fig.update_xaxes(title="Monthly phase classification", type="date", tickformat="%Y")
    fig.update_yaxes(visible=False, range=[0.8, 1.2])
    figures.append({"title": "Infrastructure-phase timeline · context, not strategy P&L",
                    "caption": "Source: results/regime-state-daily.csv · Jan 2014–Dec 2024 (132 months). This fitted classifier is not an independent event sample and has no walk-forward daily returns joined to it.",
                    "figure": make_figure(fig, height=230)})

    # Compare stored walk-forward variants using the reported Sharpe summary only.
    fig = go.Figure()
    categories = ["Equal gross", "Inverse volatility", "Inverse volatility + vol target"]
    raw_values = [raw["portfolios"]["equal_gross"]["metrics"]["sharpe"],
                  raw["portfolios"]["inverse_vol"]["metrics"]["sharpe"],
                  raw["portfolios"]["inverse_vol"]["metrics_vol_target"]["sharpe"]]
    z_values = [zed["portfolios"]["equal_gross"]["metrics"]["sharpe"],
                zed["portfolios"]["inverse_vol"]["metrics"]["sharpe"],
                zed["portfolios"]["inverse_vol"]["metrics_vol_target"]["sharpe"]]
    for label, values, color in (("Raw surprise", raw_values, COLORS["accent"]),
                                 ("Standardized surprise (z)", z_values, COLORS["secondary"])):
        fig.add_trace(go.Scatter(x=categories, y=values, mode="lines+markers", name=label,
                                 line={"color": color, "width": 2.7}, marker={"size": 8}))
    fig.add_hline(y=0, line_color=COLORS["muted"], line_dash="dot")
    fig.update_xaxes(title="Portfolio construction")
    fig.update_yaxes(title="Reported walk-forward Sharpe (unitless)")
    figures.append({"title": "Raw versus standardized-surprise walk-forward summary",
                    "caption": "Sources: results/walk-forward.json and results/walk-forward-z.json · same 2019–2026 development scope. Sealed windows are spent. Entry-clock audit remains unresolved in the stored artifacts; do not present these as validated strategy performance.",
                    "figure": make_figure(fig)})

    if not DAILY_PATH:
        for title, reason in (
            ("Observed daily equity curves by baseline", "Requires date plus daily net_return or NAV for each baseline."),
            ("Daily drawdown curves", "Requires daily net returns or NAV; annual maximum drawdown cannot reconstruct the path."),
            ("Rolling Sharpe and Sortino", "Requires the chronological daily net-return series."),
            ("Rolling win rate, profit factor, average winner and loser", "Requires complete closed-trade P&L observations and entry dates."),
            ("Trade frequency and position size", "Requires a closed-trade ledger with entry dates and a consistently defined notional/quantity field."),
            ("Daily strategy-return correlation heatmap", "Requires at least two baseline return series on aligned dates."),
            ("Volatility and turnover over time", "Requires daily returns and executed notional/turnover fields with defined units."),
            ("Monte Carlo paths, terminal returns and drawdowns", "Requires actual daily net returns; simulations are derived from the observed ledger, never the summary table."),
            ("Separate in-sample and out-of-sample equity curves", "Requires explicit sample labels or a split date fixed before reviewing the results."),
        ):
            figures.append(unavailable(title, reason))

    table_rows = metric_rows(three, raw, zed)
    metrics = []
    # Explicitly expose headline from the three-sleeve summary with its source and caveat.
    headline = three["portfolios"]["inverse_vol_vol_target"]["metrics"]
    metrics.extend([
        {"label": "Stored three-sleeve · inverse-vol vol-target Sharpe", "value": f'{headline["sharpe"]:.3f}'},
        {"label": "Stored max drawdown", "value": pct(headline["max_drawdown"])},
        {"label": "Walk-forward sessions", "value": str(zed["portfolios"]["inverse_vol"]["metrics"]["days"])},
        {"label": "Regime panel months", "value": str(len(regimes))},
    ])

    # A compact prose-first mechanism statement, not a claim that these results establish the mechanism.
    mechanism = (
        "Research object: unexpected changes in issuer fundamentals and capital intensity may be "
        "priced through future cash-flow timing, delivery constraints, and financing burden. "
        "This dashboard shows stored development research; it does not certify an executable edge."
    )
    manifest = {
        "builder": "docs/visualization/reproduce.py",
        "scope": "deterministic dashboard rebuild from hashed summary artifacts and optional hashed daily/trade ledgers; not a raw-data backtest rerun",
        "inputs": manifest_inputs,
        "limitations": [
            "daily price cache results/bar-cache is gitignored and absent from this checkout",
            "no daily NAV/return/cost ledger is tracked; equity and drawdown paths cannot be reconstructed",
            "no daily return series means no valid Monte Carlo path, terminal-return, or drawdown distributions",
            "regime panel ends 2024-12 and is not point-in-time joined to walk-forward returns",
            "stored three-sleeve results predate the entry-clock correction audit",
        ],
        "displayed_summary_rows": len(table_rows),
        "daily_ledger": str(DAILY_PATH) if DAILY_PATH else None,
        "trade_ledger": str(TRADES_PATH) if TRADES_PATH else None,
        "split_date": SPLIT_DATE,
        "ledger_metrics": ledger_metrics,
        "dashboard_figures": len(figures),
    }

    output_manifest = dict(manifest)
    output_manifest["inputs"] = manifest_inputs
    OUT_MANIFEST.write_text(json.dumps(output_manifest, indent=2, sort_keys=True) + "\n")

    def fig_section(index: int, item: dict) -> str:
        fig_id = f"gqh-fig-{index}"
        payload = json.dumps(item["figure"], separators=(",", ":"), allow_nan=False).replace("<", "\\u003c")
        return (
            '<section class="figure-section">'
            f'<h2>{html.escape(item["title"])}</h2>'
            f'<div id="{fig_id}" class="plot" role="img" aria-label="{html.escape(item["title"])}"></div>'
            f'<p class="caption">{html.escape(item["caption"])}</p>'
            f'<script type="application/json" class="figure-data" id="{fig_id}-data">{payload}</script>'
            '</section>'
        )

    manifest_list = "".join(
        f'<li><code>{html.escape(row["path"])}</code> · SHA-256 <code>{row["sha256"]}</code></li>'
        for row in manifest_inputs
    )
    table_html = "".join(
        f'<tr>{"".join(f"<td>{html.escape(cell)}</td>" for cell in row)}</tr>'
        for row in table_rows
    )
    ledger_table_html = "".join(f'<tr>{"".join(f"<td>{html.escape(cell)}</td>" for cell in row)}</tr>' for row in ledger_rows)
    ledger_table = (f'<section class="figure-section"><h2>Backtest metrics by baseline</h2><div class="tablewrap"><table><thead><tr>{"".join(f"<th>{label}</th>" for label in ["Baseline","Sessions","Total return","P&amp;L index pts","Sharpe","Sortino","Calmar","Max drawdown","Profit factor","Win rate","Average win","Average loss","Trades","Ann. volatility","Mean daily turnover"])}</tr></thead><tbody>{ledger_table_html}</tbody></table></div><p class="caption">Metrics are recomputed from the supplied daily and trade ledgers. NAV is rebased to 100 unless a source NAV series is supplied. Profit factor, win rate, average gain/loss, and trade count use supplied complete closed-trade P&amp;L; net P&amp;L is expressed as change in the rebased NAV index unless the producer provides absolute P&amp;L separately.</p></section>' if ledger_rows else '')
    stat_html = "".join(
        f'<div class="stat"><strong>{html.escape(item["value"])}</strong><span>{html.escape(item["label"])}</span></div>'
        for item in metrics
    )
    sections_html = "".join(fig_section(i, item) for i, item in enumerate(figures))
    page = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>VECTOR · GQH research dashboard</title>
<style>
:root{{--bg:{COLORS['bg']};--surface:{COLORS['surface']};--fg:{COLORS['fg']};--muted:{COLORS['muted']};--line:{COLORS['grid']};--accent:{COLORS['accent']};--warning:{COLORS['warning']}}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--fg);font:14px/1.5 system-ui,sans-serif}}
main{{max-width:1500px;padding:22px 28px 48px;margin:auto}} h1{{font-size:25px;line-height:1.15;margin:5px 0 8px;font-weight:620}}
h2{{font-size:18px;line-height:1.3;margin:0 0 7px;font-weight:590}} p{{max-width:110ch;margin:6px 0}} .eyebrow,.caption,.muted{{color:var(--muted)}}
.eyebrow{{letter-spacing:.11em;text-transform:uppercase;font-size:11px;font-weight:650}} .caption{{font-size:11px;max-width:none;margin:8px 0 0}}
.banner{{margin:18px 0;padding:12px 16px;background:var(--surface);border-left:3px solid var(--warning)}}
.grid-stats{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:18px 0 24px}}
.stat{{border-top:1px solid var(--line);padding:10px 8px 6px 0;display:flex;flex-direction:column;gap:3px;min-width:0}}
.stat strong{{font:600 20px/1.2 ui-monospace,monospace}} .stat span{{color:var(--muted);font-size:11px}}
.figure-section{{border-top:1px solid var(--line);padding:22px 0 18px;margin-top:18px}} .plot{{width:100%;min-height:300px}}
.tablewrap{{overflow:auto;max-height:390px;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}}
table{{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}} th,td{{padding:9px 12px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}}
th{{position:sticky;top:0;background:var(--surface);text-align:left}} td:first-child{{text-align:left;font-family:system-ui,sans-serif}} td{{font-family:ui-monospace,monospace}}
.blocker{{border:1px solid var(--line);padding:14px 16px;margin:14px 0;background:var(--surface)}} .blocker h2{{font-size:16px}}
code{{font-family:ui-monospace,monospace;overflow-wrap:anywhere}} footer{{border-top:1px solid var(--line);margin-top:30px;padding-top:16px;color:var(--muted);font-size:12px}}
*{{scrollbar-color:var(--line) var(--bg);scrollbar-width:thin}}::-webkit-scrollbar{{height:10px;width:10px}}::-webkit-scrollbar-thumb{{background:var(--line)}}
@media(max-width:800px){{main{{padding:16px}}.grid-stats{{grid-template-columns:repeat(2,minmax(0,1fr))}}}}
@media(max-width:520px){{.grid-stats{{grid-template-columns:1fr 1fr}}.plot{{min-width:680px}}}}
@media(forced-colors:active){{*{{scrollbar-color:auto}}}}
</style></head><body><main>
<div class="eyebrow">VECTOR · GATOR QUANT HACKS · RESEARCH OBSERVATORY</div>
<h1>Delivery risk, market response, and evidence quality</h1>
<p class="muted">{html.escape(mechanism)}</p>
<div class="banner"><strong>DEVELOPMENT-ONLY · REPRODUCIBLE RESEARCH VIEW</strong><br>
Numbers rebuild from the hashed result artifacts shown below. The stored portfolio summaries predate an entry-clock correction audit. No claim of validated performance is made.{' Full daily ledger panels are computed from the provided source ledger; this does not rerun the upstream data pipeline.' if ledger_ready else ' Full daily portfolio paths are unavailable because no daily return ledger was supplied.'}</div>
<div class="grid-stats">{stat_html}</div>
<section class="figure-section"><h2>Stored portfolio and sleeve summary</h2>
<div class="tablewrap"><table><thead><tr><th>Run / sleeve</th><th>Sessions</th><th>Total return</th><th>Annual return</th><th>Annual volatility</th><th>Sharpe</th><th>Sortino</th><th>Calmar*</th><th>Max drawdown</th><th>Profit factor</th><th>Trade win rate</th><th>Daily hit rate</th></tr></thead><tbody>{table_html}</tbody></table></div>
<p class="caption">Source: results/three-sleeve-portfolio.json, walk-forward.json, walk-forward-z.json. Sortino, trade win rate, and profit factor are unavailable in these stored summary artifacts. *Calmar is derived as reported annual return / absolute reported maximum drawdown. Daily hit rate is not trade win rate. These are recorded summaries, not recalculated from unavailable daily bars. Sealed windows are spent; see the entry-clock audit caveat.</p></section>
{ledger_table}
<section class="blocker"><h2>{'Upstream full-backtest rerun remains separate' if ledger_ready else 'Full daily performance panels require the source ledger'}</h2>
<p>{'Supplying a ledger unlocks accurate descriptive curves and diagnostics; it does not make the original strategy computation reproducible unless its source prices, point-in-time features, and declared configuration are also available.' if ledger_ready else 'Not plotted from existing summaries: no daily portfolio NAV/return/cost ledger is checked in, and <code>results/bar-cache/</code> is explicitly gitignored. Summary Sharpe/return values cannot reconstruct the path. We will not draw synthetic curves or simulate from annual summaries. To unlock these panels, supply daily CSV with date, net_return or nav, optional baseline, gross_return, pnl, costs, turnover, sample/regime, and run/config/source hashes, plus a closed-trade CSV with baseline, net_pnl, entry_date, and size.'}</p>
<p>The regime file contains monthly labels only through Dec 2024. It is not joined point-in-time to daily walk-forward results through Aug 2026, and its fitted labels need a lookahead audit before conditioning strategy returns.</p></section>
{sections_html}
<footer><h2>Judge reproduction</h2>
<p>From the repository root, install the pinned plot dependency once, then run this one command:</p>
<p><code>python3 -m pip install -r docs/visualization/requirements.txt</code><br>
<code>python3 docs/visualization/reproduce.py</code>{'<br><code>python3 docs/visualization/reproduce.py --daily-ledger path/to/daily.csv --trade-ledger path/to/trades.csv --split-date YYYY-MM-DD</code> for complete ledgers.'}</p>
<p>This uses no API keys, credentials, network access, or database. It regenerates this standalone offline HTML and <code>reproduction-manifest.json</code> from the tracked artifacts below. That reproduces every number shown in this dashboard; it does not rerun the upstream backtest fit because the raw price cache is not distributed.</p>
<details><summary>Input artifact hashes</summary><ul>{manifest_list}</ul></details>
<p>Generated by Python + Plotly; plots support hover, zoom, pan, legend toggles, and PNG export. No synthetic market or strategy results are used.</p></footer>
<script>{get_plotlyjs()}</script><script>
for(const node of document.querySelectorAll('.figure-data')){{
  const fig=JSON.parse(node.textContent); const target=node.id.slice(0,-5);
  Plotly.newPlot(target,fig.data,fig.layout,{{responsive:true,displaylogo:false,toImageButtonOptions:{{format:'png',scale:2}}}});
}}
</script></main></body></html>'''
    OUT_HTML.write_text(page)
    return {"dashboard": str(OUT_HTML), "manifest": str(OUT_MANIFEST),
            "figures": len(figures), "summary_rows": len(table_rows),
            "input_files": len(manifest_inputs), "offline": True,
        "full_daily_paths_available": ledger_ready}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--daily-ledger", type=Path, help="Actual daily output CSV: date, net_return OR nav; optional baseline/sample/costs/turnover")
    parser.add_argument("--trade-ledger", type=Path, help="Actual closed trade CSV: baseline, net_pnl, entry_date, optional size")
    parser.add_argument("--split-date", help="Predeclared YYYY-MM-DD IS/OOS boundary; ignored if daily ledger has sample labels")
    args = parser.parse_args()
    DAILY_PATH = args.daily_ledger
    TRADES_PATH = args.trade_ledger
    SPLIT_DATE = args.split_date
    if TRADES_PATH and not DAILY_PATH:
        parser.error("--trade-ledger requires --daily-ledger")
    print(json.dumps(build(), indent=2))
