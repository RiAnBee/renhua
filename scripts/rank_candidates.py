#!/usr/bin/env python3
"""从候选池里筛出「需要人审」的子集，并按分数分片输出给 sub agent。

人工/agent 粗审成本有限，所以先用确定性规则把明显无关的（纯检测器刷分、纯数据集、
纯水印、纯安全）降到低位，把真正在讲「人机写作差异」的抬上来。

用法：
    python3 scripts/rank_candidates.py                 # 写 .harness/screen-queue.json + 分片
    python3 scripts/rank_candidates.py --shards 8      # 分成 8 片
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HARNESS = ROOT / ".harness"
CANDIDATES = HARNESS / "candidates.json"
QUEUE = HARNESS / "screen-queue.json"
SHARD_DIR = HARNESS / "screen-shards"

# 强正信号：标题/摘要里直接表明在做「人 vs 机器」对比或给出差异特征
STRONG = [
    r"human[- ]?(?:written|authored)",
    r"human vs\.? ?(?:ai|llm|machine)",
    r"(?:ai|llm|machine)[- ](?:generated|written|authored).{0,40}(?:vs|versus|compared|differ)",
    r"distinguish(?:ing)? (?:between )?human",
    r"stylometric",
    r"linguistic (?:features|characteristics|differences)",
    r"writing style",
    r"stylistic (?:variation|differences|features|markers)",
    r"register variation|multidimensional analysis|Biber",
    r"idiosyncras",
    r"homogeniz|homogenis|monocultur",
    r"diversity of (?:llm|machine|ai)",
    r"excess vocab",
    r"formulaic",
    r"anthropomorph|human-?like (?:writing|text|prose)",
]

# 中等正信号
MEDIUM = [
    r"creativity|creative writing|story generation|narrative",
    r"authorship attribution",
    r"clich|purple prose|exposition",
    r"em[- ]?dash|punctuation",
    r"lexical diversity|vocabulary",
    r"syntactic complexity|nominali[sz]ation",
    r"translationese|machine translationese",
    r"chinese|mandarin",
    r"post-?training|instruction tun|rlhf|alignment",
    r"rewrit|revis|edit",
    r"watermark",
]

# 负信号：纯工程技术，没有差异特征的讨论
NEGATIVE = [
    r"\bdetector\b.{0,30}(?:ensemble|deberta|roberta|benchmark|robust)",
    r"adversarial (?:attack|evasion)",
    r"watermark(?:ing)? (?:scheme|robust|detection)",
    r"quantization|distillation|pruning|inference (?:speed|latency)",
    r"federated|differential privacy",
    r"database|query|sql",
    r"recommendation|click-?through",
    r"medical imaging|segmentation|drug discovery",
    r"robot|autonomous driving",
    r"code generation|software (?:bug|repair)",
    r"jailbreak|safety (?:guard|filter)|harmful",
    r"sentiment analysis of product",
    r"fake news detection using",
]

FLAGSHIP = "2604.03136"


def score(item: dict) -> tuple[float, list[str]]:
    text = f"{item['title']}\n{item.get('abstract', '')}".lower()
    reasons: list[str] = []
    value = 0.0

    for pat in STRONG:
        if re.search(pat, text):
            value += 3.0
            reasons.append(f"+strong:{pat}")

    hits = sum(1 for pat in MEDIUM if re.search(pat, text))
    if hits:
        value += min(hits, 4) * 1.0
        reasons.append(f"+medium×{hits}")

    for pat in NEGATIVE:
        if re.search(pat, text):
            value -= 1.5
            reasons.append(f"-neg:{pat}")

    # 组别加权：chinese / remedy / narrative 更贴目标
    groups = set(item.get("groups", []))
    if "chinese" in groups:
        value += 2.0
        reasons.append("+chinese")
    if "remedy" in groups:
        value += 1.5
        reasons.append("+remedy")
    if "narrative" in groups:
        value += 1.0
        reasons.append("+narrative")
    if "cause" in groups:
        value += 0.5
        reasons.append("+cause")
    if "genre" in groups:
        value -= 0.5

    # 顶会/顶刊信号
    comment = (item.get("comment") or "").lower()
    journal = (item.get("journal_ref") or "").lower()
    if re.search(r"acl|emnlp|naacl|coling|iclr|neurips|icml|chi|cscw|eacl|tacl", f"{comment} {journal}"):
        value += 1.5
        reasons.append("+venue")
    if journal:
        value += 0.5
        reasons.append("+journal")

    # 新近性微调
    year = int(item["published"][:4]) if item.get("published") else 2024
    if year >= 2026:
        value += 0.5
    elif year <= 2022:
        value -= 0.5

    return value, reasons


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shards", type=int, default=8)
    parser.add_argument("--min-score", type=float, default=4.0)
    args = parser.parse_args()

    pool = json.loads(CANDIDATES.read_text(encoding="utf-8"))
    scored = []
    for item in pool:
        if item["id"] == FLAGSHIP:
            continue
        if item.get("screen") in {"keep", "flagship", "drop"}:
            continue
        s, reasons = score(item)
        item["score"] = round(s, 2)
        item["score_reasons"] = reasons
        scored.append(item)

    scored.sort(key=lambda x: (-x["score"], x["id"]))
    queue = [i for i in scored if i["score"] >= args.min_score]

    QUEUE.write_text(json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8")

    SHARD_DIR.mkdir(parents=True, exist_ok=True)
    for old in SHARD_DIR.glob("*.json"):
        old.unlink()
    size = (len(queue) + args.shards - 1) // args.shards
    for n in range(args.shards):
        chunk = queue[n * size : (n + 1) * size]
        if not chunk:
            continue
        (SHARD_DIR / f"shard-{n + 1:02d}.json").write_text(
            json.dumps(chunk, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    print(f"候选池 {len(scored)} 篇，入队 {len(queue)} 篇（score >= {args.min_score}）")
    print(f"分 {args.shards} 片 -> {SHARD_DIR}")
    print("\n最高分 15 篇：")
    for i in queue[:15]:
        print(f"  {i['score']:5.1f}  {i['id']:12s} {i['title'][:70]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
