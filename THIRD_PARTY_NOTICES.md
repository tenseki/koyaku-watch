# 第三者資料と公開データ

## 適用範囲

本リポジトリのMIT Licenseは、著者が作成したソースコードと文書に適用する。
第三者が作成した資料、X上のコンテンツ、外部モデル、外部ライブラリには適用しない。

## 自由民主党の資料

分析では、自由民主党公式サイトの2026年衆院選政権公約、候補者ページおよび
候補者一覧JSONを参照した。公開リポジトリにはこれらの複製を収録せず、
`sources/` 以下に公式URL、取得日時、ファイル名、SHA-256を記録する。

- 自由民主党「ご利用にあたって」：https://www.jimin.jp/term/

政策マスタと候補者表は分析用に構造化したデータである。出典を明示し、
第三者資料に対する権利を主張しない。

## Xのデータ

X APIで取得した投稿本文、APIレスポンス、取得ログ、AI・人手レビュー作業表は
`data/private/` に保存し、公開リポジトリには収録しない。

公開成果物は、公開時点のX Developer Agreement and Policyを再確認した上で、
必要最小限のPost ID、分析ラベル、集計値および再現用メタデータに限定する。
投稿本文を復元できる判断理由や根拠引用は非公開とする。

- X Developer Agreement：https://docs.x.com/developer-terms/agreement
- X Developer Policy：https://docs.x.com/developer-terms/policy
- Restricted use cases：https://docs.x.com/developer-terms/restricted-use-cases

## 外部モデルとライブラリ

Ruriなどの埋め込みモデルおよびPython依存ライブラリは本リポジトリへ同梱しない。
利用者は各提供元のライセンスと利用条件に従って取得する。
