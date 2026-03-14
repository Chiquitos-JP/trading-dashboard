# Lessons Learned

エージェントが過去のエラー・修正から学んだ教訓を蓄積するファイル。
セッション開始時に参照し、同じ失敗を繰り返さない。

---

## 2026-03-09: pandas-datareader 未インストールでパイプライン失敗

- **失敗モード**: `run_all.py` のステップ [16/21]「マクロデータ取得」で `ModuleNotFoundError: No module named 'pandas_datareader'`
- **検知シグナル**: exit code 1、エラーログに `ModuleNotFoundError`
- **根本原因**: `pandas-datareader` が `.venv` に未インストール、`requirements.txt` も存在しなかった
- **対処**: `.venv/Scripts/pip install pandas-datareader` → `pip freeze > requirements.txt` で依存管理ファイルを生成
- **防止ルール**: パッケージ追加・削除時は必ず `requirements.txt` を更新する。`ModuleNotFoundError` は即座に pip install で対処し、requirements.txt に反映する

---

## 既知エラーパターン（weekly-routine.mdc より移行）

### exit code 9009: python コマンドが見つからない

- **検知シグナル**: `'python' is not recognized` または exit code 9009
- **根本原因**: Windows ARM64 環境では `python` が PATH にない
- **対処**: `py` コマンドを使用する

### WinError 32: Dropbox ファイルロック

- **検知シグナル**: `[WinError 32] The process cannot access the file`
- **根本原因**: Dropbox がファイルを同期中にロック
- **対処**: 無視可。バックアップ処理の失敗のみで、本体データに影響なし

### NaTType エラー: マクロデータの欠損

- **検知シグナル**: `NaTType` 関連のエラー
- **根本原因**: FRED 等のマクロデータに欠損がある
- **対処**: 無視可。該当チャートのみスキップされる

### タイムアウト: block_until_ms が短い

- **検知シグナル**: コマンドがバックグラウンドに移行し完了を確認できない
- **根本原因**: `block_until_ms` のデフォルト（30秒）がパイプライン実行時間に対して短い
- **対処**: `block_until_ms` を 600000（10分）に設定して再実行

---

## 2026-03-14: FRED 金価格シリーズ（GOLDPMGBD228NLBM）廃止

- **失敗モード**: マクロデータ取得で金価格のみ取得失敗（FRED が HTML エラーページを返す）
- **検知シグナル**: `⚠️ GOLDPMGBD228NLBM — 取得失敗: Unable to read URL`
- **根本原因**: 2022年1月31日にFREDがIBA（Ice Benchmark Administration）データを全削除。LBMA Gold/Silver Price、ICE Swap/Libor Rates が対象
- **対処**: `macro_data.py` で FRED_SERIES から削除し、yfinance `GC=F`（COMEX金先物）に差し替え。保存キーを `GOLD` に変更。`macro_data_visualization.py` と `_template_weekly_review.qmd` も同期更新
- **防止ルール**: FRED シリーズの取得失敗が繰り返される場合、一時障害ではなくシリーズ廃止の可能性を疑う。FRED公式ページで確認し、必要に応じ代替ソース（yfinance等）に切り替える

---

## 2026-03-14: GPT-5系モデルのAPI互換性

- **失敗モード**: `ai_analyzer.py` でOpenAIモデルを `gpt-4o-mini` → `gpt-5-mini` に更新後、API呼び出しエラー
- **検知シグナル**: `Unsupported parameter: 'max_tokens'`、`Unsupported value: 'temperature' does not support 0.7`
- **根本原因**: GPT-5系はreasoningモデルであり、旧来の `max_tokens` → `max_completion_tokens`、`temperature` はデフォルト（1）のみサポート
- **対処**: `max_tokens` → `max_completion_tokens` に変更、`temperature` パラメータを削除
- **防止ルール**: OpenAI モデルをアップグレードする際は、reasoningモデル（GPT-5系、o1系等）のAPI互換性を確認する。特に `temperature`、`max_tokens`、`top_p` は非対応の場合がある
