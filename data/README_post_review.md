# 投稿単位レビュー形式

`data/private/post_review_working.csv` は、487投稿を一度ずつ確認し、AI一次判定と人手確定を分けて保存する非公開の作業表である。

## 判定値の書式

`ai_policy_labels` と `human_policy_labels` は次のいずれかとする。

- 23政策のどれにも該当しない：`none`
- 1政策に該当：`FOR-004=specific_measure`
- 複数政策に該当：`FOR-004=specific_measure|FOR-007=policy_direction`

政策IDは `data/policies_2026.csv`、ラベル定義は `data/README_labeling.md` に従う。

## AIが入力する列

- `ai_policy_labels`：AIが提案する政策IDと具体性ラベル
- `ai_policy_titles`：提案した政策名。判定者が政策IDを暗記しなくてよいように表示する
- `ai_reason`：短い根拠。`none` の場合も理由を書く
- `ai_confidence`：`high`、`medium`、`low`
- `ai_model`：一次判定に使ったモデル名
- `ai_rules_version`：適用したラベリング規則の版

## 人が入力する列

- `human_policy_labels`：AI提案を確認して確定した値。正しければ同じ値を入れ、違えば修正する
- `human_reason`：修正理由または確認上の注記
- `human_verified`：確認後に `true`
- `annotator`：固定した判定者名
- `reviewed_at`：`YYYY-MM-DD`形式の確認日

AI列は人手修正で上書きしない。両方を残すことで、AIの誤り方と人手修正履歴を評価できる。

## 補助列

- `review_batch`：40投稿単位の作業バッチ
- `review_stratum`：初回校正標本の構成区分
- `screening_hints`：投票依頼・演説告知等の機械的な注意表示。最終判定ではない
- `retrieval_policy_ids`、`retrieval_policy_titles`、`retrieval_reasons`：既存検索が候補にした政策と理由。最終判定ではない

## 検証

```bash
python3 scripts/validate_post_review.py \
  --input data/private/post_review_working.csv
```
