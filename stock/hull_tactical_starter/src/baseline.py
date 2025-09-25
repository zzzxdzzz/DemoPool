
import numpy as np
import pandas as pd
from sklearn.experimental import enable_hist_gradient_boosting  # noqa: F401
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import r2_score
from .cv import PurgedWalkForwardSplit

def _rolling_vol(x: pd.Series, span: int = 63, eps: float = 1e-9):
    vol = x.ewm(span=span, adjust=False).std().clip(lower=eps)
    return vol

def train_baseline(train_df: pd.DataFrame, date_col: str, target_col: str, feature_cols: list,
                   n_splits: int = 5, test_size: int = 252, gap: int = 5,
                   target_daily_vol: float = 0.01, alloc_clip: float = 1.0, random_state: int = 42):
    """
    - Predict the *next-day excess return* (regression).
    - Convert predictions to *allocation* by scaling with inverse rolling volatility.
    - Evaluate via walk-forward CV returning out-of-fold diagnostics.
    """
    df = train_df.sort_values(date_col).reset_index(drop=True).copy()

    X = df[feature_cols].values
    y = df[target_col].values
    n = len(df)

    splitter = PurgedWalkForwardSplit(n_splits=n_splits, test_size=test_size, gap=gap)

    oof_pred = np.zeros(n, dtype=float)
    oof_alloc = np.zeros(n, dtype=float)

    model_params = dict(max_depth=None, learning_rate=0.05, max_bins=255,
                        l2_regularization=0.0, max_iter=1000, random_state=random_state)

    for tr_idx, te_idx in splitter.split(n):
        model = HistGradientBoostingRegressor(**model_params)
        model.fit(X[tr_idx], y[tr_idx])
        yhat = model.predict(X[te_idx])

        # Convert to allocation via inverse vol scaling (using *train-only* vol to avoid leakage)
        train_rets = pd.Series(y[tr_idx])
        vol = _rolling_vol(train_rets).iloc[-1]
        scale = target_daily_vol / max(vol, 1e-6)
        alloc = np.clip(yhat * scale, -alloc_clip, alloc_clip)

        oof_pred[te_idx] = yhat
        oof_alloc[te_idx] = alloc

    mask = oof_pred != 0
    r2 = r2_score(y[mask], oof_pred[mask]) if mask.sum() else np.nan

    out = pd.DataFrame({
        date_col: df[date_col],
        "target": y,
        "oof_pred": oof_pred,
        "oof_alloc": oof_alloc,
    })
    return out, r2, model_params

def train_full_and_predict(train_df: pd.DataFrame, test_df: pd.DataFrame, date_col: str, target_col: str, feature_cols: list,
                           target_daily_vol: float = 0.01, alloc_clip: float = 1.0, random_state: int = 42):
    """
    Fit on full train, predict test; output allocations (clipped) for submission.
    You must map to Kaggle's required submission format after this step.
    """
    model = HistGradientBoostingRegressor(max_iter=1000, learning_rate=0.05, max_bins=255, random_state=random_state)
    df = train_df.sort_values(date_col).reset_index(drop=True)
    X = df[feature_cols].values
    y = df[target_col].values
    model.fit(X, y)

    test_df = test_df.sort_values(date_col).reset_index(drop=True).copy()
    yhat = model.predict(test_df[feature_cols].values)

    # Use train vol proxy to set scale
    vol = _rolling_vol(pd.Series(y)).iloc[-1]
    scale = target_daily_vol / max(vol, 1e-6)
    alloc = np.clip(yhat * scale, -alloc_clip, alloc_clip)
    test_df["allocation"] = alloc
    return test_df
