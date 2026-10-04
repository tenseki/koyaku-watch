# 公約ウォッチ

[![Public reproducibility](https://github.com/tenseki/koyaku-watch/actions/workflows/public-reproducibility.yml/badge.svg)](https://github.com/tenseki/koyaku-watch/actions/workflows/public-reproducibility.yml)

公開CSVからのSVG再生成・テスト・公開前監査を自動確認します。[実行内容と確認方法](PUBLIC_REPRODUCIBILITY.md)。

選挙公約と、選挙期間中の候補者によるX上の発信との対応を検証し、政策ごとの言及状況を再現・検証可能な形で可視化するプロジェクトです。

13アカウント・487分析対象投稿によるMVPについて、取得、前処理、全件レビュー、
二次監査、検索モデル比較、政策別集計、図表、公開用の結果レポートまで完了して
います。X APIはPay Per UseのApp-only読み取り認証を使用しました。

MVPの結果は[「MVP分析結果」](MVP分析結果_2026.md)、全229候補を対象とした
集計は[「全候補者分析結果」](全候補者分析結果_2026.md)にまとめています。これは
全候補者・全公約・全SNSを扱う結論ではなく、事前に固定した対象と手続きで、
公約への言及をどのように観察・集計できるかを検証したものです。

本プロジェクトにおける「再現可能」は、同じ入力と設定から同じ集計結果を
再計算できることに加え、別の選挙・政党・候補者群へ同じ取得、ラベリング、
監査、集計手順を再適用できることを意味します。

## 長期ミッション

2026年衆院選の分析は、過去の一選挙について結論を出すことだけが目的では
ありません。次回以降の選挙期間中に、公式公約には記載されている一方で
候補者の公開発信では相対的に目立たない政策を投票日前に可視化し、有権者が
自分で確認できる材料を提供するための実地試験です。

2026年版では、取得、前処理、政策分割、候補抽出、人手確認、監査、集計、
公開までの手順を作り、実データで武器として使えるかを検証します。公開する
中心成果は一回限りの分析結果だけでなく、別の選挙へ再適用できるコード、設定、
データ形式、判定規則、検証手順、公開時の注意事項です。

次回選挙で実用になることは現時点では前提としません。精度、所要時間、費用、
公開上の制約を検証し、実用にならない場合は方式の変更または中止を判断し、
失敗した条件と理由も記録します。

次回選挙では、2026年版を基に著者自身が新しい実行環境をforkし、その選挙の
公約、候補者、期間に合わせて設定とデータを固定した上で、選挙期間中の分析を
行うことを目標とします。

## 現在の内容

- `MVP分析結果_2026.md`：MVPの対象、結果、図表、解釈と限界
- `全候補者分析結果_2026.md`：全229候補の匿名集計、図表、読み方と限界
- `全候補者分析設計書_2026.md`：全候補版の対象、判定、集計、公開範囲
- `assets/charts/`：Web用SVGとnote・SNS用PNGの政策別言及率グラフ
- `分析設計書_MVP.md`：目的、対象範囲、分析方法、公開方針
- `scripts/`：候補者・政策データ生成、投稿前処理、類似度計算、ラベリング候補生成
- `config/`：MVP対象、政策セット、モデル、ラベル、集計ビューの設定
- `data/`：比較用政策マスタ、匿名のMVP・全候補集計、入力データ形式の仕様
- `sources/`：一次資料の公式URL、取得日時、ファイル名、ハッシュの記録
- `RECOVERY.md`：現在地点、残作業、PCやChatGPT/Codexの再設定後の復旧手順
- `PUBLICATION_CHECKLIST.md`：GitHub公開前の分離・監査手順
- `THIRD_PARTY_NOTICES.md`：第三者資料と公開データの取扱い

## 公開範囲とデータの構成

公開版には、コード、設定、政策の定義、集計規則、匿名の政策別集計、図表、
分析結果を含めます。公開CSVは、欠損値として空欄の列を残すのではなく、
非公開の項目を列ごと削除した匿名集計です。

| 区分 | 非公開の処理用データ | 公開するデータ |
| --- | --- | --- |
| 投稿の識別・取得 | 投稿ID、アカウント識別子、URL、取得日時 | 含めない |
| 投稿内容 | 投稿本文、投稿種別、検索・抽出の補助情報 | 含めない |
| 判定過程 | 検索候補、AI判定、確認者メモ、確認日時 | 含めない |
| 集計に使う最終判定 | 投稿ごとの政策ラベル | 政策別の件数・割合・言及アカウント数のみ |
| 政策定義 | 政策ID、分類、政策名 | 公開する |

非公開データでは、投稿を識別して重複を除き、事前に定めた基準で政策項目ごとの
最終ラベルを集計します。公開データには、個人・アカウント・投稿を識別できる情報
および投稿本文を含めません。公開用の政策別集計と全体集計は、MVP版の
[`data/mvp_policy_summary_2026.csv`](data/mvp_policy_summary_2026.csv)、
[`data/mvp_analysis_summary_2026.json`](data/mvp_analysis_summary_2026.json)に加え、
全候補版の[`data/all_candidates_policy_summary_2026.csv`](data/all_candidates_policy_summary_2026.csv)、
[`data/all_candidates_analysis_summary_2026.json`](data/all_candidates_analysis_summary_2026.json)を含む。
列の意味は[全候補版集計データの説明](data/README_all_candidates_aggregate.md)を参照する。

自民党公式サイトから分析時に保存したPDF、HTML、JSONも公開版には収録せず、
公式URLとハッシュだけを残します。

現在の非公開Git履歴には第三者サイトの原資料が含まれるため、このリポジトリを
そのままPublicへ変更しません。公開時は
[`PUBLICATION_CHECKLIST.md`](PUBLICATION_CHECKLIST.md) に従い、
公開可能な最新版だけから新しい履歴を作成します。

## 着想と参考

公約と実際の政治活動・発信を照合し、市民が検証できる形にするという問題意識では、
[加古川市議会議員マップ](https://note.com/chinjou_ojisan)の実践から
着想を得ています。

大量の政治言説を機械処理と人間の読解の往復によって分析する方法、および
日本語埋め込みモデルRuriの利用については、下地理則氏の
[「政治家の『答弁拒否』の言語学：計量政治言語学のアプローチ」](https://note.com/lingfieldwork/n/n4f76fa8f52be)
を参考にしています。

## 必要環境

- 候補者・政策データの生成：Python 3（追加パッケージは不要）
- 埋め込み類似度の計算：`requirements-analysis.txt` のパッケージ

## 生成結果の確認

MVP候補者一覧は次のコマンドで再生成できます。

```bash
python3 scripts/build_mvp_candidate_list.py \
  --candidates data/candidates_2026.csv \
  --config config/mvp_candidates_2026_cabinet.json \
  --output /tmp/mvp_candidates_2026.csv
```

出力を保存済みデータと比較します。

```bash
cmp /tmp/mvp_candidates_2026.csv data/mvp_candidates_2026.csv
```

何も表示されなければ同一です。

## 比較する政策の選択

機械比較用の政策マスタは `data/policies_2026.csv`、名前付き政策セットは `config/policy_sets_2026.json` に保存しています。比較対象を変えるときは、プログラム本体ではなく設定ファイルの `policy_ids` を編集します。

```bash
python3 scripts/build_policy_set.py \
  --config config/policy_sets_2026.json \
  --set institution_and_foreign_policy \
  --output /tmp/policies_active.csv
```

`--set` を省略すると `default_set` が使われます。利用可能なセットは `--list-sets` で確認できます。比較プログラムは、ここで出力されたCSVまたは同じ設定ローダーを入力に使用します。

## X API取得前の分析基盤

X APIの取得処理と分析処理を分離するため、後段は [標準投稿データ形式](data/README_posts_schema.md) のCSVを入力とします。

人工サンプルを前処理するには次を実行します。

```bash
python3 scripts/preprocess_posts.py \
  --analysis-config config/analysis_mvp_2026.json \
  --input tests/fixtures/posts_sample.csv \
  --output /tmp/posts_processed.csv
```

## X APIの認証確認

X Developer Consoleで発行したApp-only Bearer Tokenは、Git管理外の`.env`にだけ保存します。`.env`の次の行で、等号の右側にトークンを貼り付けてください。引用符は不要です。

```dotenv
X_API_BEARER_TOKEN=
```

トークンそのものを画面に出さず、公式の`@XDevelopers`のユーザー情報1件だけを取得して認証を確認します。このAPI呼び出しは課金対象です。

```bash
python3 scripts/check_x_api.py
```

固定投稿があれば公開投稿1件も取得する場合は、次を実行します。ユーザー情報1件に加えて投稿1件が課金対象になります。

```bash
python3 scripts/check_x_api.py --fetch-pinned-post
```

`.env`は`.gitignore`の対象です。トークンをREADME、ソースコード、ターミナルのコマンド履歴、Issue、チャットへ貼り付けないでください。

## 限定期間の試験取得

Full-archive Searchを使い、MVP設定の対象期間から候補者1名の投稿を取得します。既定では高市早苗候補の最大10投稿について、費用上限を表示するだけでAPIは呼び出しません。

```bash
python3 scripts/fetch_x_posts.py
```

表示内容を確認後、`--execute`を付けると課金対象の取得を行い、標準投稿CSVと取得ログをGit管理外の`data/private/`へ保存します。

```bash
python3 scripts/fetch_x_posts.py --execute
```

取得件数を広げる場合は、試験結果と残高を確認してから`--page-size`と`--max-pages`を明示的に変更します。

複数候補者は少人数のバッチに分け、各候補者の取得後に標準前処理まで実行します。既定の第1バッチは4名、各最大100投稿で、費用上限を表示するだけです。

```bash
python3 scripts/fetch_x_batch.py
python3 scripts/fetch_x_batch.py --execute
```

全229候補の本文保全は、事前のCounts結果を費用見積もりと件数照合に使い、
ハッシュ検証済みの取得済みファイルを飛ばせる再開モードで行います。

```bash
python3 scripts/fetch_x_batch.py \
  --analysis-config config/analysis_all_candidates_2026.json \
  --all-candidates --resume --page-size 500 --max-pages 10 \
  --candidate-interval 5.2

python3 scripts/fetch_x_batch.py \
  --analysis-config config/analysis_all_candidates_2026.json \
  --all-candidates --resume --page-size 500 --max-pages 10 \
  --candidate-interval 5.2 --execute
```

候補者を変える場合は`--candidate-key`を人数分指定します。各バッチ後にDeveloper Consoleの残高と使用状況を確認してから次へ進みます。

13名の取得・前処理が揃ったら、パイロットファイルを除外して正式対象だけを集計します。この集計は投稿本文を画面へ出力しません。

```bash
python3 scripts/summarize_x_acquisition.py
```

分析前に、候補者ごとの前処理済みCSVを設定ファイルの候補者順で1つに統合します。投稿IDの重複、候補者キー、列構成も検証されます。出力は投稿本文を含むためGit管理外です。

```bash
python3 scripts/build_analysis_corpus.py
```

## 全候補者の投稿数調査

本文を取得する前に、Full-archive Countsで公式X掲載候補者の対象期間投稿数だけを調べます。途中結果を候補者ごとに保存するため、中断後も続きから再開できます。

```bash
python3 scripts/count_x_posts.py
python3 scripts/count_x_posts.py --execute
```

CountsとSearchではコンプライアンスフィルタの差により件数が完全一致しない場合があります。費用見積もり用の概数として使用します。

2026年8月30日の調査では、公式X掲載候補者229名の対象期間投稿は合計9,463件だった。中央値29件、平均41.3件、範囲0〜303件で、本文取得費用は現行単価で約47.32ドルと見積もられる。先行取得した13名ではCountsとSearchの件数が全件一致した。

類似度計算を行う場合は、仮想環境に分析用依存関係を導入します。X APIの契約や認証情報は不要です。

```bash
python3 -m venv .venv
.venv/bin/pip install \
  --index-url https://download.pytorch.org/whl/cpu \
  torch
.venv/bin/pip install -r requirements-analysis.txt
.venv/bin/python scripts/build_labeling_candidates.py \
  --analysis-config config/analysis_mvp_2026.json \
  --posts data/private/mvp_posts.processed.csv \
  --policy-set mvp_all \
  --output-dir data/private/analysis-mvp-all
```

比較用に設定ファイルの既定モデルを上書きする場合は、再現性のためモデル名と
固定リビジョンをセットで指定します。

```bash
.venv/bin/python scripts/build_labeling_candidates.py \
  --analysis-config config/analysis_mvp_2026.json \
  --posts data/private/mvp_posts.processed.csv \
  --policy-set mvp_all \
  --output-dir data/private/analysis-mvp-all-ruri310m \
  --model cl-nagoya/ruri-v3-310m \
  --revision 18b60fb8c2b9df296fb4212bb7d23ef94e579cd3
```

確定した投稿単位ラベルに対する複数の検索実行は、次のように同じ条件で
評価できます。

```bash
python3 scripts/evaluate_retrieval.py \
  --review data/private/post_review_working.csv \
  --analysis-config config/analysis_mvp_2026.json \
  --similarity ruri70m=data/private/analysis-mvp-all/similarity_all.csv \
  --similarity ruri310m=data/private/analysis-mvp-all-ruri310m/similarity_all.csv \
  --output data/private/retrieval_evaluation.json
```

試行では `foreign_policy_only`（7政策）、正式MVPでは `mvp_all`（23政策）を使う設定です。出力は全政策・投稿ペアの `similarity_all.csv`、人手確認用の `labeling_candidates.csv`、再現性情報を持つ `run_metadata.json` です。最初の2つのCSVは分析用投稿本文を含むため非公開とし、Git管理外の場所に出力します。人手判定は [5段階ラベリング形式](data/README_labeling.md) に従います。

全487投稿の確定ラベルによる検証の結果、主分析の `specific_measure` は
Ruri v3 70mの「キーワード一致または政策ごとの類似度上位3件」で31件中31件を回収した。
一次検索はこのルールに固定する。

実際の反復レビューは、政策・投稿ペアを一行ずつ読む方式ではなく、487投稿を一度ずつ確認する投稿単位の表を使います。

```bash
python3 scripts/build_post_review.py
python3 scripts/validate_post_review.py \
  --input data/private/post_review_working.csv
```

AI一次判定と人手確定は別列に保存し、AI結果を人手修正で上書きしません。書式と作業手順は [投稿単位レビュー形式](data/README_post_review.md) を参照してください。

Xの長文投稿は通常の `text` が省略されるため、取得処理は
`tweet.fields=note_tweet` を要求し、`note_tweet.text` を優先します。取得後に本文が
変わった場合は、その投稿の旧AI・人手判定を無効化し、未変更の判定とバッチ順だけを引き継ぎます。

```bash
python3 scripts/refresh_post_review.py \
  --generated /tmp/post_review_regenerated.csv \
  --current data/private/post_review_working.csv
```

## 注意

取得資料の出典、取得日時、ハッシュ値は各 `sources/*/README.md` に記録しています。生のX投稿本文は公開対象に含めない方針です。詳細は分析設計書と
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)を参照してください。

## ライセンス

著者が作成したコードと文書は[MIT License](LICENSE)で公開します。
第三者資料、X上のコンテンツ、外部モデル、外部ライブラリには適用しません。
