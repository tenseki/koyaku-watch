# 標準投稿データ形式

X APIのプランや取得エンドポイントと分析処理を分離するため、取得データは次の標準CSVへ変換してから前処理する。

| 列 | 必須 | 内容 |
| --- | --- | --- |
| `post_id` | 必須 | Xの投稿ID。テストデータでは仮IDも可 |
| `candidate_key` | 必須 | `mvp_candidates_2026.csv` と結合する候補者ID |
| `author_id` | 必須 | X内部のユーザーID。API未取得のテスト時は仮IDも可 |
| `x_handle` | 必須 | `@` を除いたXハンドル |
| `created_at` | 必須 | ISO 8601形式の投稿日時 |
| `post_type` | 必須 | `post`、`reply`、`quote`、`repost` のいずれか |
| `raw_text` | 必須 | 候補者本人が付した本文。長文投稿はX APIの `note_tweet.text` を優先し、引用元・返信先の本文を含めない |
| `post_url` | 必須 | 公開投稿URL |
| `has_media` | 必須 | 画像または動画付きなら `true` |
| `retrieved_at` | 必須 | 取得日時。テストデータでは作成日時 |

前処理後のCSVには次の列を追加する。

| 列 | 内容 |
| --- | --- |
| `analysis_text` | URL・メンション除去と空白正規化後の本文 |
| `is_analysis_target` | 分析対象なら `true` |
| `exclusion_reason` | 除外した場合の理由 |

`raw_text`を含む取得・前処理データは内部利用限定とし、Gitで公開しない。`tests/fixtures/` の人工データはこの制限の対象外とする。

X API取得時は `tweet.fields` に `note_tweet` を必ず含める。`note_tweet.text`
がある場合は通常の `text` ではなくそちらを保存し、長文投稿の省略を防ぐ。

前処理後の投稿と政策の比較結果に対する人手判定は `README_labeling.md` の5段階ラベルに従う。
