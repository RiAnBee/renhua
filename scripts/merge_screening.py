#!/usr/bin/env python3
"""合并各 shard 的粗审结果，写回候选池的 screen 字段，并生成下载清单。

用法：
    python3 scripts/merge_screening.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HARNESS = ROOT / ".harness"
CANDIDATES = HARNESS / "candidates.json"
RESULT_DIR = HARNESS / "screen-results"
SHARD_DIR = HARNESS / "screen-shards"
DOWNLOAD_LIST = HARNESS / "download-list.json"

TIER_TO_SCREEN = {"A": "keep", "B": "keep", "C": "maybe", "D": "drop"}


def main() -> int:
    pool = {i["id"]: i for i in json.loads(CANDIDATES.read_text(encoding="utf-8"))}
    results: dict[str, dict] = {}
    problems: list[str] = []

    for shard in sorted(SHARD_DIR.glob("shard-*.json")):
        result = RESULT_DIR / shard.name
        if not result.exists():
            problems.append(f"{shard.name}: 无结果文件")
            continue
        inputs = json.loads(shard.read_text(encoding="utf-8"))
        verdicts = json.loads(result.read_text(encoding="utf-8"))
        if len(inputs) != len(verdicts):
            problems.append(f"{shard.name}: 条数不匹配 in={len(inputs)} out={len(verdicts)}")
            continue
        for src, verdict in zip(inputs, verdicts):
            if src["id"] != verdict["id"]:
                problems.append(f"{shard.name}: id 顺序不匹配 {src['id']} vs {verdict['id']}")
                continue
            results[verdict["id"]] = verdict

    for arxiv_id, verdict in results.items():
        item = pool.get(arxiv_id)
        if item is None:
            problems.append(f"{arxiv_id}: 不在候选池中")
            continue
        item["screen"] = TIER_TO_SCREEN.get(verdict["tier"], "pending")
        item["tier"] = verdict["tier"]
        item["value"] = verdict.get("value", "")
        item["chinese_fit"] = verdict.get("chinese_fit", "")
        item["key_findings"] = verdict.get("key_findings", [])

    CANDIDATES.write_text(
        json.dumps(sorted(pool.values(), key=lambda x: x["published"], reverse=True), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    keep = [i for i in pool.values() if i.get("screen") == "keep"]
    keep.sort(key=lambda x: (x.get("tier", "Z"), x.get("chinese_fit") != "high", x["id"]))
    DOWNLOAD_LIST.write_text(json.dumps(keep, ensure_ascii=False, indent=2), encoding="utf-8")

    tiers: dict[str, int] = {}
    for i in pool.values():
        tiers[i.get("tier", "-")] = tiers.get(i.get("tier", "-"), 0) + 1
    chinese_high = [i for i in keep if i.get("chinese_fit") == "high"]

    print(f"合并 {len(results)} 条判定")
    print(f"分档统计: {tiers}")
    print(f"待下载 (keep): {len(keep)} 篇 -> {DOWNLOAD_LIST}")
    print(f"其中 chinese_fit=high: {len(chinese_high)} 篇")
    for i in chinese_high:
        print(f"   {i['id']:12s} [{i.get('tier')}] {i['title'][:66]}")
    if problems:
        print(f"\n⚠️ 问题 {len(problems)} 条:")
        for p in problems[:20]:
            print("  -", p)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
