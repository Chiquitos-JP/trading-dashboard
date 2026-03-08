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
