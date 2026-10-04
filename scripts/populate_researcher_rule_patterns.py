#!/usr/bin/env python3
"""Write the agreed researcher rules to the rule ledger."""

from __future__ import annotations

import csv
import os
from pathlib import Path


DATE = "2026-10-04"
POLICY_ORDER = [
    "ECO-001", "ECO-002", "ECO-003", "ECO-004", "ECO-005", "ECO-006",
    "ECO-007", "ECO-008", "ECO-009", "ECO-010", "EDU-002", "WEL-001",
    "TAX-001", "INF-001", "CON-001", "POL-001", "FOR-001", "FOR-002",
    "FOR-003", "FOR-004", "FOR-005", "FOR-006", "FOR-007",
]


def build_rule(
    policy_id: str,
    policy_name: str,
    rule_id: str,
    priority: int,
    output: str,
    logic: str,
    required: str,
    excluded: str,
    description: str,
    rationale: str,
    in_scope: str,
    out_scope: str,
    notes: str = "",
) -> dict[str, str]:
    return {
        "政策ID": policy_id,
        "政策名": policy_name,
        "規則ID": rule_id,
        "規則の版": "1.0",
        "規則の状態": "有効",
        "優先順": str(priority),
        "適用段階": "人手判定",
        "処理内容": description,
        "出力ラベル": output,
        "判定式": logic,
        "必須語彙（いずれか）": required,
        "必須語彙群（すべて）": "",
        "除外語彙・条件": excluded,
        "文脈条件": "投稿本文だけで判断する",
        "規則の説明": description,
        "設定理由": rationale,
        "想定する誤検出パターン": "",
        "境界事例（該当）": in_scope,
        "境界事例（非該当）": out_scope,
        "例外時の処理": "否定・引用・皮肉などは目視判定",
        "目視確認の要否": "条件外のみ",
        "検証事例ID": "会話内確認事例",
        "検証状況": "合意済み・事例確認済み",
        "検証日": DATE,
        "規則の決定者": "研究者",
        "注記": notes,
    }


def main() -> int:
    path = Path("data/researcher_rule_patterns_2026.csv")
    with path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        fields = list(reader.fieldnames or [])
        source_rows = list(reader)
    base_rows = {}
    for row in source_rows:
        policy_id = row["政策ID"]
        if policy_id in POLICY_ORDER and policy_id not in base_rows:
            base_rows[policy_id] = row
    titles = {policy_id: base_rows[policy_id]["政策名"] for policy_id in POLICY_ORDER}

    def r(
        policy_id: str,
        rule_id: str,
        priority: int,
        output: str,
        logic: str,
        required: str,
        excluded: str,
        description: str,
        rationale: str,
        in_scope: str,
        out_scope: str,
        notes: str = "",
    ) -> dict[str, str]:
        return build_rule(
            policy_id, titles[policy_id], rule_id, priority, output, logic,
            required, excluded, description, rationale, in_scope, out_scope, notes,
        )

    common = [
        build_rule(
            "共通", "全政策共通", "COMMON-001", 1, "判定対象の限定",
            "投稿本文に明示された政策内容だけを判断する", "", "リンク先・画像・動画音声・返信元・引用元だけの内容",
            "本文外の情報を推測して補わない", "再現可能性と第三者検証可能性のため",
            "本文で制度・方針を述べる", "リンク先にだけ政策がある",
        ),
        build_rule(
            "共通", "全政策共通", "COMMON-002", 2, "ラベル階層",
            "具体的手段・方向・話題・非該当を区別する", "", "分野名だけで方向性以上にしない",
            "specific_measure は具体的実施内容、policy_direction は実現方向、topic_only は論点言及、none は個別政策と結び付かない",
            "同じ語でも投稿の発話の強さが異なるため",
            "制度導入を進める", "分野一般への称賛や訪問報告",
        ),
        build_rule(
            "共通", "全政策共通", "COMMON-003", 3, "policy_direction",
            "候補者自身が付与した個別政策目標のハッシュタグがある", "個別政策目標を表すハッシュタグ",
            "一般的分野タグのみ。否定・皮肉・第三者引用だけのタグ",
            "個別政策スローガンのハッシュタグは候補者が掲げる政策方向として扱う。本文で実施を述べなければ specific_measure にはしない",
            "候補者が自ら選んで付与した具体的スローガンは、単なる分野索引より強い支持を示すため",
            "#食品消費税ゼロ", "#物価高対策",
            "政策ごとの高精度タグを確認して適用する",
        ),
        build_rule(
            "共通", "全政策共通", "COMMON-004", 4, "適用範囲の明示",
            "本表に規則がある場合だけ補助的に適用する", "", "規則の不在を none の根拠にしない",
            "本表は完全な自動判定仕様ではない。反復的な境界事例と、研究者が説明可能な補助規則を記録する。表に規則がない投稿は共通原則に照らして個別に人手判定する",
            "明白な事例や一回限りの文脈判断まで無理に一般化しないため",
            "規則外の投稿を共通原則で人手判定する", "規則がないため政策非該当と扱う",
            "規則の不在は自動判定の根拠ではない",
        ),
    ]

    rules = {
        "ECO-001": [r("ECO-001", "ECO-001-001", 10, "none",
            "ガソリン価格の変化だけで税・暫定税率・減税の仕組みがない", "ガソリン|ガソリン価格",
            "ガソリン税|暫定税率|トリガー条項|ガソリン減税",
            "価格言及を暫定税率廃止と区別する", "価格水準だけでは税制変更の主張と扱わないため",
            "ガソリン税の廃止を進める", "ガソリン価格の引下げ実績")],
        "ECO-002": [r("ECO-002", "ECO-002-001", 10, "none",
            "軽油価格の変化だけで軽油引取税・暫定税率・減税の仕組みがない", "軽油|軽油価格",
            "軽油引取税|軽油税|暫定税率|軽油減税",
            "価格言及を軽油引取税廃止と区別する", "価格水準だけでは税制変更の主張と扱わないため",
            "軽油引取税の廃止を進める", "軽油価格の引下げ実績")],
        "ECO-003": [r("ECO-003", "ECO-003-001", 10, "条件別",
            "年収の壁・控除・178万円への言及がある", "年収の壁|基礎控除|給与所得控除|178万円",
            "手取り増・賃上げだけ",
            "壁の見直しは policy_direction、具体額・開始時期を示す実施内容は specific_measure", "一般的な所得向上と区別するため",
            "年収の壁を見直す", "強い経済で手取りを増やす")],
        "ECO-004": [
            r("ECO-004", "ECO-004-HT-001", 20, "policy_direction",
                "候補者自身の投稿に #食品消費税ゼロ 又は #食料品消費税ゼロ がある",
                "#食品消費税ゼロ|#食料品消費税ゼロ", "否定・第三者引用だけの場合",
                "個別政策目標のハッシュタグを方向性として付与する。タグのみでは specific_measure にしない",
                "候補者自身が掲げる個別政策スローガンのため",
                "選挙告知本文に #食品消費税ゼロ のみを付与", "#消費税 や #物価高対策",
                "AI none 限定監査で4件確認"),
            r("ECO-004", "ECO-004-001", 10, "条件別",
                "食料品又は飲食料品の消費税をゼロ・非課税にするとの本文上の表明",
                "食料品消費税|飲食料品消費税|消費税ゼロ|非課税", "食料品支援・商品券・食費支援だけ",
                "実現を表明すれば specific_measure、タグのみ又は論点提示なら policy_direction",
                "物価対策一般との混同を避けるため",
                "食料品の消費税をゼロにする", "食料品クーポンを配布する")],
        "ECO-005": [r("ECO-005", "ECO-005-001", 10, "条件別",
            "電気・ガス料金と支援・補助・値引き・負担軽減が結び付く", "電気代|電気料金|ガス代|ガス料金|電気・ガス",
            "水道料金、LPガスのみ、一般的な光熱費、電力価格の説明だけ",
            "支援方向は policy_direction、金額・期間・世帯額を示せば specific_measure",
            "政策対象を電気・ガス料金に限定するため",
            "電気・ガス代への支援", "水道基本料金の減免")],
        "ECO-006": [r("ECO-006", "ECO-006-001", 10, "条件別",
            "高校と授業料又は無償化が結び付く", "高校無償化|高校授業料|高校就学支援金",
            "教育一般、奨学金、大学授業料、学校環境",
            "無償化実現は policy_direction、年度等を伴う実施内容は specific_measure",
            "対象教育段階を固定するため",
            "高校授業料を無償化する", "大学奨学金を拡充する")],
        "ECO-007": [r("ECO-007", "ECO-007-001", 10, "条件別",
            "小学校給食費の無償化又は給食費ゼロ", "給食無償化|小学校給食費|給食費ゼロ",
            "子ども食堂・食料支援・教育一般",
            "無償化は policy_direction、年度等を伴う実施内容は specific_measure。食材費補助・質量維持・一時軽減は topic_only",
            "無償化と物価高対応を区別するため",
            "小学校給食費を無償化する", "給食の食材価格高騰分を補助する")],
        "ECO-008": [r("ECO-008", "ECO-008-001", 10, "条件別",
            "分娩又は出産費用の自己負担軽減に触れる", "出産費用|正常分娩|自己負担ゼロ|お財布がいらない出産",
            "妊婦健診のみ、妊娠中の個人的出来事、一般的な子育て支援",
            "出産費用の無償化を目指す表明は policy_direction、制度・法案等を示せば specific_measure",
            "妊婦健診制度と分娩費用制度を区別するため",
            "お財布がいらない出産を目指す", "妊婦との会話・無事の出産を祈る投稿")],
        "ECO-009": [r("ECO-009", "ECO-009-001", 10, "条件別",
            "従事者又は職員と処遇・賃上げ・給与・待遇が同じ主張にある", "処遇改善|賃上げ|給与|待遇",
            "医療機関・介護事業者への経営支援、施設訪問、分野一般の支援",
            "処遇改善は policy_direction、3％・月1万円などの数値を示せば specific_measure。要望を聞いたとの報告は topic_only",
            "事業者支援と働く人の処遇を区別するため",
            "介護職員の処遇を月1万円改善する", "医療施設の光熱費を支援する")],
        "ECO-010": [r("ECO-010", "ECO-010-001", 10, "条件別",
            "給付付き税額控除又は税額控除の導入・制度設計", "給付付き税額控除|給付付税額控除|税額控除",
            "手取り増、新たなセーフティネット、社会保障改革だけ",
            "導入・検討・制度設計は policy_direction、実装手順を具体化すれば specific_measure",
            "一般的な所得支援と区別するため",
            "給付付き税額控除の制度設計を進める", "新たなセーフティネットをつくる")],
        "EDU-002": [r("EDU-002", "EDU-002-001", 10, "条件別",
            "中学校35人学級、少人数学級、学校の学習・教育環境", "35人学級|少人数学級|学習環境|教育環境",
            "教育一般、奨学金、学校訪問だけ",
            "中学校35人学級と年度等は specific_measure、少人数学級を進めるは policy_direction、学校の学習環境改善のみは topic_only",
            "公約の中核と目指す結果を区別するため",
            "中学校で35人学級を実現する", "教育を大切にする")],
        "WEL-001": [r("WEL-001", "WEL-001-001", 20, "topic_only",
            "子ども・子育て支援又は保育への明示的言及があるが、通園制度の内容はない", "子育て支援|保育",
            "子どもとの出来事、行事参加、子ども一般への称賛",
            "こども誰でも通園の制度内容があれば policy_direction 以上。制度に達しない子育て支援は topic_only",
            "広い領域言及を集計する政策主張と混同しないため",
            "切れ目ない子育て支援を充実する", "保育園で子どもを応援した")],
        "INF-001": [r("INF-001", "INF-001-001", 10, "policy_direction",
            "首都機能のバックアップ拠点化・移転・分散を進める", "副首都|首都機能|バックアップ拠点|首都機能移転",
            "東京一極集中の是正、多極分散、地方創生だけ",
            "法案名や時期がなくても、首都機能をどこにどう配置するかを示せば policy_direction",
            "一般的な地域振興との混同を避けるため",
            "地域を首都機能のバックアップ拠点とする", "東京一極集中を是正する")],
        "POL-001": [r("POL-001", "POL-001-001", 10, "条件別",
            "議員定数・衆議院定数・議席数の削減", "議員定数|定数削減|議席数削減",
            "政治改革、政治資金改革、歳費削減、選挙で議席を増やす話",
            "定数削減は policy_direction、1割などの削減幅を示せば specific_measure。定数・議席の削減を主張しない投稿は none",
            "政治改革カテゴリを過度に広げないため",
            "議員定数の削減を実現する", "政治改革を進める")],
        "FOR-001": [r("FOR-001", "FOR-001-001", 10, "条件別",
            "違反者の在留・退去への対応を本文に示す", "不法滞在|不法残留|退去強制|強制送還|国費送還",
            "外国人政策一般、治安一般、単なる動画・行事告知",
            "対策・送還の実施方向は policy_direction、人数・期間・送還倍増等を示せば specific_measure",
            "外国人一般の話と制度対応を区別するため",
            "違法外国人を退去させる法整備を進める", "外国人政策について語る予定")],
        "FOR-005": [r("FOR-005", "FOR-005-001", 10, "条件別",
            "外国人又は海外投資家と土地・不動産の取得又は規制が同じ文脈にある",
            "外国人|海外投資家|土地|不動産|農地|水源地|森林|マンション",
            "外国投資一般、民泊一般、行事予定だけ",
            "取得規制・法整備は policy_direction、取得状況の報告だけは topic_only、土地不動産を伴わない外国投資は none",
            "対象財産を限定するため",
            "海外投資家の不動産購入を規制する", "外国資本への経済依存を問題にする")],
        "FOR-007": [
            r("FOR-007", "FOR-007-001", 5, "none",
                "投稿に外国人関係のアンカー語が一切ない", "",
                "外国人|外国人材|外国人労働者|在留外国人|在留資格|移民|移住労働者|技能実習|特定技能|育成就労|永住|帰化|JESTA",
                "人口減少、地域維持、共生社会だけではFOR-007に入れない",
                "共生という表層語による偽陽性を防ぐため",
                "外国人材との共生を進める", "地域共生社会を実現する"),
            r("FOR-007", "FOR-007-002", 10, "条件別",
                "外国人政策又は外国人住民への言及がある", "外国人|外国人材|多文化共生",
                "外国人関係のない人口減少・地域維持",
                "具体的な受入れ・共生・労働力確保の方針がなければ topic_only。方向が示されれば policy_direction",
                "FOR-007の公約は広く、表層語だけでは方向を特定できないため",
                "外国人政策の必要性を述べる", "人口減少対策を進める")],
    }

    output = list(common)
    for policy_id in POLICY_ORDER:
        base = base_rows[policy_id]
        if policy_id in rules:
            output.extend(rules[policy_id])
        else:
            output.append({field: base.get(field, "") for field in fields})

    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(output)
    temporary.chmod(0o644)
    os.replace(temporary, path)
    print(f"wrote {len(output)} rows; {sum(bool(row['規則ID']) for row in output)} rules")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
