#!/usr/bin/env python3
"""Build a reproducible limited audit sample from AI-none post reviews."""

from __future__ import annotations

import argparse
import csv
import random
import re
from pathlib import Path


# Conservative policy anchors for a false-negative audit.  Broad category words
# (for example, "education", "coexistence", and "take-home pay") are excluded.
CORE_PATTERNS = {
    "ECO-001": r"ガソリン税|暫定税率|トリガー条項|ガソリン減税",
    "ECO-002": r"軽油引取税|軽油税|軽油減税",
    "ECO-003": r"年収の壁|178万円|基礎控除|給与所得控除",
    "ECO-004": r"食料品.{0,12}消費税|消費税.{0,12}食料品|消費税ゼロ|食料品.{0,12}非課税",
    "ECO-005": r"電気.{0,8}(ガス|料金|代)|ガス.{0,8}(電気|料金|代)|7300円",
    "ECO-006": r"高校.{0,12}(授業料|無償化|就学支援金)|(授業料|無償化|就学支援金).{0,12}高校",
    "ECO-007": r"給食無償|給食費|学校給食",
    "ECO-008": r"正常分娩|出産費用|お財布.{0,8}出産|出産.{0,8}自己負担",
    "ECO-009": r"(医療|介護|障害福祉).{0,24}(処遇|賃上げ|給与|待遇)|(処遇|賃上げ|給与|待遇).{0,24}(医療|介護|障害福祉)",
    "ECO-010": r"給付付き税額控除|給付付税額控除|税額控除",
    "EDU-002": r"35.{0,3}人学級|少人数学級|学級編制",
    "WEL-001": r"誰でも通園|乳幼児.{0,12}保育所|保育所.{0,12}就労要件",
    "TAX-001": r"環境性能割|車体課税|自動車取得",
    "INF-001": r"副首都|首都機能.{0,16}(バックアップ|分散|移転)|多極分散.{0,16}首都",
    "CON-001": r"皇室典範|皇位継承|男系男子|養子縁組",
    "POL-001": r"議員定数|定数削減|議員.{0,12}(削減|減ら|半減)",
    "FOR-001": r"不法滞在|不法残留|退去強制|強制送還|国費送還",
    "FOR-002": r"JESTA|電子渡航認証|出入国在留DX",
    "FOR-003": r"在留資格|経営.{0,4}管理|技人国|永住|帰化",
    "FOR-004": r"(外国人.{0,24}(税未納|医療費未払い|保険料未納)|税未納.{0,24}外国人|医療費未払い.{0,24}外国人)",
    "FOR-005": r"(外国人|海外投資家).{0,32}(土地|不動産|農地|水源地|マンション|森林)|(土地|不動産|農地|水源地|マンション|森林).{0,32}(外国人|海外投資家)",
    "FOR-006": r"(日本語|制度|ルール).{0,24}(在留審査|在留資格)|在留審査.{0,24}(日本語|制度|ルール)",
    "FOR-007": r"外国人材|多文化共生|外国人.{0,20}共生|共生.{0,20}外国人",
}


def is_ai_human_none(row: dict[str, str]) -> bool:
    return (
        row["ai_policy_labels"].strip() == "none"
        and row["human_policy_labels"].strip() == "none"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20261004)
    parser.add_argument("--sample-per-stratum", type=int, default=15)
    args = parser.parse_args()

    with args.input.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
        fields = list(file.seek(0) or csv.DictReader(file).fieldnames or [])
    # Reopen for the field names: seek plus DictReader above is deliberately
    # avoided because rows have already been read.
    with args.input.open(encoding="utf-8", newline="") as file:
        fieldnames = list(csv.DictReader(file).fieldnames or [])

    compiled = {policy_id: re.compile(pattern) for policy_id, pattern in CORE_PATTERNS.items()}
    ai_none = [row for row in rows if row["ai_policy_labels"].strip() == "none"]
    selected: list[dict[str, str]] = []
    selected_urls: set[str] = set()

    for row in ai_none:
        matched = [policy_id for policy_id, pattern in compiled.items() if pattern.search(row["analysis_text"])]
        if not matched:
            continue
        copied = dict(row)
        copied["audit_stratum"] = "core_term_ai_none"
        copied["matched_policy_ids"] = "|".join(matched)
        copied["selection_method"] = "policy-specific conservative anchor"
        selected.append(copied)
        selected_urls.add(row["post_url"])

    structural = {
        "mechanical_event_notice": lambda row: (
            is_ai_human_none(row)
            and not row["retrieval_policy_ids"].strip()
            and row["screening_hints"].strip() in {"campaign_event", "election_call", "election_call|campaign_event"}
        ),
        "mechanical_short_reply": lambda row: (
            is_ai_human_none(row)
            and not row["retrieval_policy_ids"].strip()
            and row["post_type"] == "reply"
            and len(row["analysis_text"].strip()) <= 30
        ),
        "mechanical_retrieval_blank": lambda row: (
            is_ai_human_none(row)
            and not row["retrieval_policy_ids"].strip()
            and not row["screening_hints"].strip()
            and not (row["post_type"] == "reply" and len(row["analysis_text"].strip()) <= 30)
        ),
    }
    randomizer = random.Random(args.seed)
    for stratum, predicate in structural.items():
        population = sorted(
            [row for row in ai_none if row["post_url"] not in selected_urls and predicate(row)],
            key=lambda row: row["post_url"],
        )
        sample_size = min(args.sample_per_stratum, len(population))
        for row in randomizer.sample(population, sample_size):
            copied = dict(row)
            copied["audit_stratum"] = stratum
            copied["matched_policy_ids"] = ""
            copied["selection_method"] = f"random sample; seed={args.seed}; n={sample_size}/{len(population)}"
            selected.append(copied)

    output_fields = fieldnames + ["audit_stratum", "matched_policy_ids", "selection_method"]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=output_fields)
        writer.writeheader()
        writer.writerows(selected)
    args.output.chmod(0o600)

    print(f"AI none rows: {len(ai_none)}")
    print(f"core-term candidates: {sum(row['audit_stratum'] == 'core_term_ai_none' for row in selected)}")
    for stratum in structural:
        count = sum(row["audit_stratum"] == stratum for row in selected)
        print(f"{stratum}: {count}")
    print(f"audit rows written: {len(selected)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
