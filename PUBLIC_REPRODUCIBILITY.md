# 公開版の再現性チェック

公開リポジトリのmainへの更新、プルリクエスト、手動実行で、
GitHub Actionsの「Public reproducibility」が次の3点を検査する。

1. 人工入力を使った単体テスト。
2. 公開前監査（非公開パス、秘密情報の既知パターン、原資料の複製など）。
3. 公開CSVからMVP版と全候補版のSVGを一時領域に再生成し、保存済みSVGとバイト単位で比較。

SVGに差があれば失敗する。成果物を自動で上書き・コミットする処理はない。
PNGはフォント・描画環境の差があるため、今回の一致検査には含めない。
テスト環境はUbuntu 24.04、Python 3.12、NumPy 2.2.6。
外部ActionsはコミットIDで固定し、リポジトリへの権限は読み取りのみとする。

## 結果の確認

[Actions一覧](https://github.com/tenseki/koyaku-watch/actions/workflows/public-reproducibility.yml)
から対象コミットの実行を開く。手動実行は「Run workflow」を選ぶ。
失敗した場合はTests、Audit public snapshot、Rebuild and compare both SVG chartsの
どの段階かを確認する。差分の理由を調べ、CSV・描画コード・図表を整合させる。
固定済み分析版に変更が必要なら、新版として理由と変更箇所を記録する。

## 手元での確認

リポジトリのルートで、テスト用環境に依存パッケージを導入して実行する。

```bash
python -m pip install -r requirements-ci.txt
python -m unittest discover -s tests -v
python scripts/audit_public_release.py
python scripts/check_public_charts.py
```

私有の投稿データ、X APIキー、AIモデルのダウンロードは必要ない。
公開CSVから図が同じように作れることを検査するものであり、
非公開の投稿ラベルからCSVを再計算したことや、判定内容の妥当性を保証するものではない。
公開前監査も既知条件の機械検査で、秘密情報・識別情報の完全な検出を保証しない。
このワークフロー自体はマージを禁止するブランチ保護の設定を変更しない。

設定の参照元：[checkout](https://github.com/actions/checkout)、
[setup-python](https://github.com/actions/setup-python)。
