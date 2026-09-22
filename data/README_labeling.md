# 人手ラベリング形式

`labeling_candidates.csv` は、機械が投稿の意味を確定した結果ではなく、人が確認する候補の一覧である。機械出力と人手判定を次の列で分ける。

23政策を暗記する必要はない。各行で隣り合う `policy_title` と `analysis_text` を直接比較し、その投稿がその政策に触れているかだけを判定する。

## 機械出力の列

- `similarity`：Ruriが計算したコサイン類似度
- `rank`：同じ政策内の類似度順位
- `keyword_matches`：政策マスタのキーワードに一致した語
- `selection_reason`：上位、キーワード一致、中位抽出、低位抽出のどれで候補に入ったか

これらは「言及あり」の判定ではない。

## 人が入力する列

| 列 | 内容 |
| --- | --- |
| `mention_level` | 下記の5段階ラベル |
| `evidence_text` | 判断根拠になった投稿内の短い語句 |
| `annotator` | 判定者 |
| `labeled_at` | 判定日時 |
| `judgment_reason_code` | 下記の定型理由コード |
| `judgment_reason` | 判断理由、保留理由 |

### `mention_level`

- `specific_measure`：制度名、対象、手段、数値等から個別の公約を特定できる
- `policy_direction`：具体制度まではないが、対象と政策方向が分かる
- `topic_only`：分野には触れているが、個別公約を特定できない
- `none`：該当政策や分野への言及がない
- `uncertain`：本文だけでは判断できない、または判定が分かれる

`topic_only` は個別 `policy_id` の言及数には足さない。`uncertain` も他のラベルに無理に統合しない。

## 判定手順

判定は投稿単位ではなく、`policy_id × post_id` の組ごとに行う。同じ投稿でも、ある政策には `specific_measure`、別の政策には `none` となり得る。

1. `analysis_text` に残った候補者本人の本文だけを読む。リンク先、返信先、引用元、画像、動画の内容を推測して補わない。
2. 対象の個別政策またはその政策分野に、本文が実質的に触れているか確認する。触れていなければ `none`。
3. 分野名だけなら `topic_only`、対象と政策の方向が分かれば `policy_direction`、制度・手段・対象・数値等から個別公約を特定できれば `specific_measure`。
4. 指示語や外部文脈に依存し、本文だけでは2または3を決められない場合だけ `uncertain` とする。単に迷った場合の退避先にはしない。

### 選挙運動上の定型投稿

次の内容だけからなる投稿は、投稿自体を分析対象から除外せず、分母に残した上で、すべての個別政策について `none` とする。

- 投票、期日前投票、候補者名の記入を呼びかけるだけの投稿
- 街頭演説、個人演説会、集会、ライブ配信等の日時・場所・開催を告知するだけの投稿
- 演説の開始・終了、到着、移動、握手、挨拶、応援への感謝等を報告するだけの投稿
- 「お願いします」「最後まで頑張る」等、支持を求めるだけの投稿

同じ本文に政策内容が書かれている場合は、この定型規則で一括して `none` にせず、政策について書かれた部分だけを通常の判定手順で評価する。例えば「本日18時に街頭演説」は `none` だが、「本日18時の街頭演説でガソリン税を下げると訴える」は、日時告知を無視し「ガソリン税を下げる」の具体性を対象政策に照らして判定する。

演説テーマとして政策分野名だけが明記され、立場・方向・具体策がない場合は `topic_only` とする。単なる「政策を訴える」「未来を語る」のように分野も特定できない表現は `none` とする。

## 定型理由コード

`judgment_reason_code` は次から一つを選ぶ。自由記述だけに依存しないことで、判定の一貫性と再集計可能性を保つ。

| コード | 通常対応するラベル | 用途 |
| --- | --- | --- |
| `target_specific_measure` | `specific_measure` | 対象政策の制度・手段・対象・数値等を確認できる |
| `target_policy_direction` | `policy_direction` | 対象と政策方向を確認できる |
| `target_topic_only` | `topic_only` | 政策分野だけを確認できる |
| `election_call_only` | `none` | 投票・支持・候補者名記入の呼びかけだけ |
| `campaign_event_notice_only` | `none` | 演説・集会等の告知や活動報告だけ |
| `unrelated_topic` | `none` | 対象政策・分野とは別の話題 |
| `insufficient_context` | `uncertain` | 本文だけでは外部文脈が不足する |
| `ambiguous_policy_mapping` | `uncertain` | 複数政策にまたがり個別政策への対応が決められない |
| `other` | 任意 | 上記にない理由。`judgment_reason` に説明を必須とする |

`specific_measure`、`policy_direction`、`topic_only` では `evidence_text` を必須とする。`none` でも機械上位やキーワード一致など誤検出理由の検証に役立つ場合は短い説明を残す。

作業中のCSVは次で検証する。未入力行は許容される。

```bash
python3 scripts/validate_labeling.py \
  --input data/private/analysis-mvp-all/labeling_candidates.csv
```

全件の入力完了時は `--require-complete` を追加し、空欄もエラーにする。

## 集計ビュー

`config/analysis_mvp_2026.json` に、少なくとも次の集計方法を名前付きで保存する。

- `specific_measure_only`：具体策だけを数える主ビュー
- `policy_direction_or_more`：具体策と政策方向を数える補足ビュー
- `topic_context_only`：分野だけの言及を個別政策と分けて確認するビュー

別の集計規則を使うときは元の結果を上書きせず、設定名と実行履歴を残す。
