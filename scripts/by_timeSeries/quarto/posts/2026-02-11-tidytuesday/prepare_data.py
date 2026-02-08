"""
Risk Valuation Matrices - 共通指標の計算

realized_pl と daily_balance から勝率・R・最大DD・連敗・口座サイズを算出し、
risk_metrics.parquet と daily_pl.parquet を data/ に保存する。
MakeoverMonday と TidyTuesday の両方で利用可能。
"""

import pandas as pd
import numpy as np
from pathlib import Path

# プロジェクトルートを探す
base_path = Path(__file__).resolve().parent
while base_path.name != "05_stockTrading" and base_path.parent != base_path:
    base_path = base_path.parent
if not (base_path / "data").exists():
    base_path = Path(__file__).resolve().parent
    while not (base_path / "data" / "trading_account").exists() and base_path.parent != base_path:
        base_path = base_path.parent

pl_path = base_path / "data" / "trading_account" / "realized_pl" / "silver" / "realized_pl.parquet"
balance_path = base_path / "data" / "trading_account" / "account_balance" / "daily_balance.parquet"

output_dir = Path(__file__).resolve().parent / "data"
output_dir.mkdir(parents=True, exist_ok=True)

def compute_risk_metrics():
    """realized_pl と daily_balance から指標を計算"""
    metrics = {}
    daily_pl = None

    if pl_path.exists():
        df = pd.read_parquet(pl_path)
        df["settlement_date"] = pd.to_datetime(df["settlement_date"])
        # 日次集計
        daily_pl = df.groupby(df["settlement_date"].dt.date).agg(
            profit_jpy=("profit_jpy", "sum"),
            n_trades=("profit_jpy", "count"),
        ).reset_index()
        daily_pl["date"] = pd.to_datetime(daily_pl["settlement_date"])
        daily_pl = daily_pl[["date", "profit_jpy", "n_trades"]]

        wins = daily_pl[daily_pl["profit_jpy"] > 0]
        losses = daily_pl[daily_pl["profit_jpy"] < 0]
        n_days = len(daily_pl)
        n_win_days = len(wins)
        n_loss_days = len(losses)
        win_rate = (n_win_days / n_days * 100) if n_days > 0 else 0
        avg_profit_jpy = wins["profit_jpy"].mean() if len(wins) > 0 else 0
        avg_loss_jpy = losses["profit_jpy"].mean() if len(losses) > 0 else 0
        # 近似 R: 平均利 / |平均損|
        if avg_loss_jpy != 0:
            r_multiple = avg_profit_jpy / abs(avg_loss_jpy)
        else:
            r_multiple = 1.0 if avg_profit_jpy > 0 else 0.5

        # 最大連敗日数
        daily_pl["is_loss"] = daily_pl["profit_jpy"] < 0
        daily_pl["streak_id"] = (~daily_pl["is_loss"]).cumsum()
        losing_streaks = daily_pl[daily_pl["is_loss"]].groupby("streak_id").size()
        max_consecutive_losing_days = int(losing_streaks.max()) if len(losing_streaks) > 0 else 0

        metrics["win_rate_pct"] = round(win_rate, 2)
        metrics["r_multiple"] = round(r_multiple, 3)
        metrics["avg_profit_jpy"] = round(avg_profit_jpy, 0)
        metrics["avg_loss_jpy"] = round(avg_loss_jpy, 0)
        metrics["n_trades_total"] = int(df["profit_jpy"].count())
        metrics["n_days_traded"] = int(n_days)
        metrics["max_consecutive_losing_days"] = max_consecutive_losing_days
    else:
        metrics["win_rate_pct"] = 55.0
        metrics["r_multiple"] = 1.5
        metrics["avg_profit_jpy"] = 0
        metrics["avg_loss_jpy"] = 0
        metrics["n_trades_total"] = 0
        metrics["n_days_traded"] = 0
        metrics["max_consecutive_losing_days"] = 0

    if balance_path.exists():
        balance = pd.read_parquet(balance_path)
        balance["date"] = pd.to_datetime(balance["date"])
        equity = balance.groupby("date").agg(pat_balance=("pat_balance", "sum")).reset_index().sort_values("date")
        equity["cummax"] = equity["pat_balance"].cummax()
        equity["drawdown_pct"] = np.where(
            equity["cummax"] > 0,
            np.clip((equity["cummax"] - equity["pat_balance"]) / equity["cummax"] * 100, 0, 100),
            0,
        )
        max_dd = min(equity["drawdown_pct"].max(), 100.0)
        account_size_jpy = float(equity["pat_balance"].iloc[-1]) if len(equity) > 0 else 0
        metrics["max_drawdown_pct"] = round(max_dd, 2)
        metrics["account_size_jpy"] = round(account_size_jpy, 0)
    else:
        metrics["max_drawdown_pct"] = 0.0
        metrics["account_size_jpy"] = 0.0

    # ポジションサイズ%（取得金額が無い場合は未設定、記事では 2% 等を使用）
    metrics["position_size_pct"] = 2.0

    return pd.DataFrame([metrics]), daily_pl

if __name__ == "__main__":
    risk_df, daily_pl_df = compute_risk_metrics()
    risk_df.to_parquet(output_dir / "risk_metrics.parquet", index=False)
    if daily_pl_df is not None:
        daily_pl_df.to_parquet(output_dir / "daily_pl.parquet", index=False)
    print("Saved:", output_dir / "risk_metrics.parquet")
    if daily_pl_df is not None:
        print("Saved:", output_dir / "daily_pl.parquet")
    print(risk_df.T.to_string())
