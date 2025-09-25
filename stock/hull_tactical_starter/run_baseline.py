
import pandas as pd
import numpy as np
from src.baseline import train_baseline
from src.metrics import evaluate_allocations

# ==== Replace these with real columns after you download the Kaggle data ====
DATE_COL = "date"
TARGET_COL = "excess_return_next_day"
FEATURE_COLS = ["feat1", "feat2", "feat3"]

def main():
    # Synthetic demo (replace with real CSVs inside Kaggle)
    n = 2000
    rng = np.random.default_rng(123)
    dates = pd.date_range("2015-01-01", periods=n, freq="B")
    feat1 = rng.normal(size=n)
    feat2 = rng.normal(size=n)
    feat3 = 0.3 * feat1 + 0.7 * rng.normal(size=n)
    regimes = np.sign(np.sin(np.linspace(0, 20, n)))
    noise = rng.normal(scale=0.01, size=n)
    target = 0.0005 * regimes + 0.0003 * feat1 + noise

    train = pd.DataFrame({DATE_COL: dates, "feat1": feat1, "feat2": feat2, "feat3": feat3, TARGET_COL: target})

    oof, r2, params = train_baseline(
        train, date_col=DATE_COL, target_col=TARGET_COL, feature_cols=FEATURE_COLS,
        n_splits=5, test_size=252, gap=5, target_daily_vol=0.01, alloc_clip=1.0
    )
    print(f"OOF R^2 (sanity): {r2:.4f}")
    metrics = evaluate_allocations(oof["oof_alloc"].values, oof["target"].values, target_vol=0.01)
    print("Diagnostics:", metrics)

if __name__ == "__main__":
    main()
