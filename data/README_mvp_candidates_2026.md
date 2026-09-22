# MVP対象候補者（2026年衆院選）

`mvp_candidates_2026.csv` は、2026年1月23日の衆議院解散時点の閣僚のうち、自民党の公式候補者ページに本人のXリンクが掲載された候補者を全員収録する。該当者は13人であり、MVPの目標範囲（10〜20人）を満たすため、追加の現閣僚・閣僚経験者は採用していない。

## 選定規則

1. 2026年1月23日の衆議院解散時点で閣僚である。
2. 第51回衆議院選挙の自民党公式候補者リストに掲載されている。
3. 同リストに候補者本人のXリンクが掲載されている。

X投稿数、フォロワー数、政策内容その他の分析対象期間中の情報は、選定に使用していない。

## 再現方法

```bash
python3 scripts/build_mvp_candidate_list.py \
  --candidates data/candidates_2026.csv \
  --config config/mvp_candidates_2026_cabinet.json \
  --output data/mvp_candidates_2026.csv
```

閣僚名簿の参照先は設定ファイルに記録している。候補者・Xリンクの原データは `sources/jimin_candidates_20260827/candidate_list.json`、取得記録は同ディレクトリの `README.md` を参照する。
