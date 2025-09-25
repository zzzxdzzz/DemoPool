
import numpy as np
import pandas as pd

def _safe_std(x, ddof=1, eps=1e-9):
    s = np.std(x, ddof=ddof)
    return max(s, eps)

def sharpe_like(returns: np.ndarray, annualize: bool = True, periods_per_year: int = 252):
    """
    Basic Sharpe approximation: mean(returns)/std(returns).
    Returns are daily PnL from allocation * realized_excess_return (not raw price changes).
    """
    r = np.asarray(returns, dtype=float)
    if r.size == 0:
        return 0.0
    sr = np.mean(r) / _safe_std(r)
    if annualize:
        sr *= np.sqrt(periods_per_year)
    return sr

def vol_penalized_score(pnl: np.ndarray, target_vol: float = 0.01, penalty_power: float = 2.0, annualize=True):
    """
    A surrogate for a 'modified Sharpe': rewards mean PnL and penalizes realized vol above target_vol.
    - target_vol: daily volatility target (e.g., 1% = 0.01). Tune on CV to mimic LB behavior.
    - penalty: (max(0, realized_vol - target_vol))^penalty_power
    """
    r = np.asarray(pnl, dtype=float)
    if r.size == 0:
        return 0.0
    realized_vol = _safe_std(r)
    penalty = max(0.0, realized_vol - target_vol) ** penalty_power
    base = sharpe_like(r, annualize=annualize)
    return base - penalty

def max_drawdown(pnl: np.ndarray):
    r = np.asarray(pnl, dtype=float)
    if r.size == 0:
        return 0.0
    equity = np.cumsum(r)
    peak = np.maximum.accumulate(equity)
    drawdown = equity - peak
    return float(np.min(drawdown))

def evaluate_allocations(alloc: np.ndarray, realized_excess_returns: np.ndarray, target_vol=0.01):
    """
    Compute PnL series and several diagnostics.
    """
    alloc = np.asarray(alloc, dtype=float)
    rets = np.asarray(realized_excess_returns, dtype=float)
    pnl = alloc * rets
    score = vol_penalized_score(pnl, target_vol=target_vol)
    sr = sharpe_like(pnl)
    mdd = max_drawdown(pnl)
    vol = _safe_std(pnl)
    return {
        "score": float(score),
        "sharpe_like": float(sr),
        "vol": float(vol),
        "max_drawdown": float(mdd),
        "mean_pnl": float(np.mean(pnl)),
    }
