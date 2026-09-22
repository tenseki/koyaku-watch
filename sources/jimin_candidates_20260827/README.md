# 取得記録：自由民主党 2026年衆院選 公認候補者

このディレクトリは取得記録のみを公開する。公式HTML・JSONの複製は公開リポジトリへ
収録せず、Git管理外の
`data/private/source_archive/jimin_candidates_20260827/` にローカル保存する。

| 項目 | 内容 |
| --- | --- |
| 取得日時 | 2026-08-27T05:16:41+09:00 |
| 一覧の公式URL | https://www.jimin.jp/election/results/sen_shu51/candidate/ |
| 公式JSON URL | https://www.jimin.jp/election/results/sen_shu51/candidate/data/list/index.json |
| 取得件数 | 337候補者 |
| 党が公式ページでXリンクを掲載した候補者数 | 229候補者 |

## ローカル保存ファイル

| ファイル | 内容 | SHA-256 |
| --- | --- | --- |
| `candidate_list.json` | 候補者一覧表示に使われる公式JSON | `60adc29363bc799b78bc77cd38cdef691498ecc01b51433a9bf4a62a11659071` |
| `candidate_index.html` | 公認候補者の入口ページ | `c8dec7dc914616e7fddb712c9a6352be528d1ea0f6ba8b38504027eca980f017` |
| `candidate_constituency.html` | 選挙区候補者ページ | `056544825e74320f79bb24509e6cf0a8761af0df5ec013c9c8bd6c9f60434e3d` |
| `candidate_proportion.html` | 比例代表候補者ページ | `4f887809a25f699a2f6800973f155d41666dde6700a8fb39b0764ec8be0d2715` |

このJSONの `sns` 配列で `type` が `site_x` のURLのみを、党が掲載した候補者のXリンクとして抽出した。Xリンクがないことは、候補者にXアカウントが存在しないことを意味しない。「この公式候補者ページにはXリンクが掲載されていない」ことを意味する。

生成物は `data/candidates_2026.csv`（337件）および `data/candidate_x_accounts_2026.csv`（229件）である。`candidate_key` は候補者詳細ページのスラッグであり一意キーとして用いる。党内管理ID `candidate_id` は一部候補者で未付与（元データが `0`）のため、主キーには用いない。

自民党ウェブサイトのコンテンツは自民党または各権利者に帰属する。
本リポジトリのライセンスは原資料へ適用されない。
