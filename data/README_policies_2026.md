# 2026年衆院選 政策比較マスタ

`policies_2026.csv` は、公約PDFとX投稿の類似度比較に使う政策マスタである。公約の原文をそのまま一件とせず、人が一つの政策として判断できる意味単位に分割している。

## 比較用テキスト

- `title`：結果表示用の短い政策名
- `comparison_text`：埋め込みモデルへ入力する、主語と政策手段を補った説明
- `keywords`：略称・言い換え。`|` 区切り
- `source_text`：公約PDFの対応箇所

類似度計算では、設定ファイルの `comparison_text_fields` に指定した列を空白で連結して使用する。`source_text` は監査用であり、既定では埋め込み入力に含めない。

## 政策の差し替え

`config/policy_sets_2026.json` の `sets` に名前付きの政策ID一覧を保存する。政策本文を変更せずに、IDの追加・削除・順序変更だけで比較対象を差し替えられる。

```bash
python3 scripts/build_policy_set.py \
  --config config/policy_sets_2026.json \
  --set institution_and_foreign_policy \
  --output /tmp/policies_active.csv
```

利用可能なセットは次のコマンドで確認する。

```bash
python3 scripts/build_policy_set.py \
  --config config/policy_sets_2026.json \
  --list-sets
```

## 出典

- 自由民主党「第51回衆議院選挙 政権公約」
- PDF: https://storage.jimin.jp/pdf/pamphlet/202601_manifest.pdf
- 取得記録: `sources/jimin_2026_20260827/README.md`

`source_pages` はPDFビューア上のページ番号ではなく、冊子に印刷されたページ番号を記録する。
