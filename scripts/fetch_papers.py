#!/usr/bin/env python3
"""renhua — 文献候选池构建与论文原文下载。

用法：
    python3 scripts/fetch_papers.py sweep            # arXiv 扫库 -> .harness/candidates.json
    python3 scripts/fetch_papers.py download         # 下载 screen=keep 的论文（PDF + TeX source）
    python3 scripts/fetch_papers.py download --id X  # 下载单篇（可重复）

论文原文按 .gitignore 排除，只保留在本地。见 scripts/README.md。
"""

from __future__ import annotations

import argparse
import json
import random
import re
import subprocess
import sys
import tarfile
import time
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HARNESS = ROOT / ".harness"
PAPERS = ROOT / "papers"
CANDIDATES = HARNESS / "candidates.json"

API = "https://export.arxiv.org/api/query"
ATOM = "{http://www.w3.org/2005/Atom}"
ARXIV_NS = "{http://arxiv.org/schemas/atom}"

# 扫库查询：按主题分组，覆盖「人机文本差异」的各个证据层次。
QUERIES: list[tuple[str, str]] = [
    # A. 旗舰主题：语篇 / 叙事 / 情节层
    ("narrative", 'all:"AI-generated" AND all:"fiction"'),
    ("narrative", 'all:"story generation" AND all:"narrative" AND all:"human"'),
    ("narrative", 'all:"plot" AND all:"diversity" AND all:"language models"'),
    ("narrative", 'all:"creative writing" AND all:"large language models" AND all:"evaluation"'),
    # B. 表层特征：词汇 / 句法 / 标点 / 语体
    ("surface", 'all:"AI-generated text" AND all:"human-written"'),
    ("surface", 'all:"stylometry" AND all:"LLM-generated"'),
    ("surface", 'all:"linguistic features" AND all:"machine-generated"'),
    ("surface", 'all:"register" AND all:"large language models" AND all:"variation"'),
    ("surface", 'all:"Biber" AND all:"language models"'),
    ("surface", 'all:"punctuation" AND all:"LLM-generated"'),
    ("surface", 'all:"lexical diversity" AND all:"ChatGPT" AND all:"human"'),
    ("surface", 'all:"style" AND all:"detection" AND all:"LLM-generated text"'),
    # C. 成因：训练目标 / 对齐 / 同质化
    ("cause", 'all:"homogenization" AND all:"language models"'),
    ("cause", 'all:"mode collapse" AND all:"language model" AND all:"diversity"'),
    ("cause", 'all:"instruction tuning" AND all:"style" AND all:"diversity"'),
    ("cause", 'all:"RLHF" AND all:"writing" AND all:"style"'),
    ("cause", 'all:"post-training" AND all:"stylistic" AND all:"LLM"'),
    # D. 补救：改写 / 风格迁移 / 编辑
    ("remedy", 'all:"style transfer" AND all:"AI-generated" AND all:"human"'),
    ("remedy", 'all:"idiosyncrasies" AND all:"LLM" AND all:"writing" AND all:"edit"'),
    ("remedy", 'all:"rewriting" AND all:"LLM-generated text" AND all:"human-like"'),
    ("remedy", 'all:"humanization" AND all:"AI text"'),
    # E. 中文 / 非英语特定
    ("chinese", 'all:"Chinese" AND all:"LLM-generated" AND all:"detection"'),
    ("chinese", 'all:"Chinese" AND all:"AI-generated text" AND all:"features"'),
    ("chinese", 'all:"translationese"'),
    ("chinese", 'all:"Chinese" AND all:"human-written" AND all:"machine"'),
    # F. 应用文体与人类基线
    ("genre", 'all:"academic writing" AND all:"LLM" AND all:"linguistic"'),
    ("genre", 'all:"news" AND all:"LLM-generated" AND all:"human"'),
    ("genre", 'all:"social media" AND all:"AI-generated" AND all:"human"'),
    ("genre", 'all:"authorship attribution" AND all:"large language models"'),
    # G. 已知必收（标题/主题精确锚定）
    ("pinned", 'ti:"Can AI writing be salvaged"'),
    ("pinned", 'ti:"Do LLMs write like humans"'),
    ("pinned", 'ti:"style and substance"'),
    ("pinned", 'all:"excess vocabulary" AND all:"LLM-assisted writing"'),
    ("pinned", 'ti:"Echoes in AI"'),
    ("pinned", 'all:"homogenization" AND all:"scientific writing" AND all:"LLM"'),
    ("pinned", 'ti:"SlopShape"'),
    ("pinned", 'all:"engagement markers" AND all:"ChatGPT" AND all:"essays"'),
    ("pinned", 'ti:"AI slop"'),
    ("pinned", 'all:"writing style" AND all:"convergence" AND all:"large language models"'),
    ("pinned", 'all:"human-AI collaboration" AND all:"writing" AND all:"voice" AND all:"homogenization"'),
    ("pinned", 'all:"em dash" OR ti:"em dash"'),
    ("pinned", 'all:"Chinese" AND all:"AI-generated text" AND all:"stylometric"'),
    ("pinned", 'all:"human writers" AND all:"LLM" AND all:"creativity" AND all:"diversity"'),
    ("pinned", 'ti:"How LLMs Distort"'),
    ("pinned", 'all:"homogenizing effect" AND all:"large language models" AND all:"expression"'),
    ("pinned", 'ti:"Artificial Hivemind"'),
    ("pinned", 'all:"homogenize writing" AND all:"western styles"'),
    ("pinned", 'all:"Western" AND all:"homogeniz" AND all:"cultural nuances" AND all:"language models"'),
    ("pinned", 'ti:"engagement markers" AND all:"ChatGPT"'),
]


def _get(url: str, retries: int = 6, timeout: int = 90) -> bytes:
    """用 curl 取数据。

    环境里 `ALL_PROXY=socks5h://...`，而 urllib 不支持 socks 代理，直连出口会被
    arXiv 以 HTTP 406 拒绝。curl 认这个变量，所以统一走 curl。

    命中限速时 arXiv 也会回 406（不是 503），所以退避要够长、重试要够多次。
    """
    last = ""
    for attempt in range(retries):
        proc = subprocess.run(
            ["curl", "-sS", "-L", "--max-time", str(timeout), "-A", "renhua/0.1 (research)", url],
            capture_output=True,
        )
        if proc.returncode == 0 and proc.stdout:
            return proc.stdout
        last = proc.stderr.decode("utf-8", "replace").strip() or f"exit {proc.returncode}"
        time.sleep(5 * (attempt + 1) + random.uniform(0, 2))
    raise RuntimeError(f"GET failed: {url}: {last}")


def _text(node, path: str) -> str:
    found = node.find(path)
    return " ".join(found.text.split()) if found is not None and found.text else ""


def arxiv_query(search_query: str, max_results: int = 100, start: int = 0) -> list[dict]:
    # arXiv 会以 HTTP 406 拒绝把空格编成 '+' 的查询串，必须用 %20。
    url = (
        f"{API}?search_query={urllib.parse.quote(search_query, safe='')}"
        f"&start={start}&max_results={max_results}&sortBy=relevance&sortOrder=descending"
    )
    raw = _get(url)
    root = ET.fromstring(raw)
    out = []
    for entry in root.findall(f"{ATOM}entry"):
        raw_id = _text(entry, f"{ATOM}id")
        m = re.search(r"abs/([^v]+)(v\d+)?$", raw_id)
        if not m:
            continue
        primary = entry.find(f"{ARXIV_NS}primary_category")
        authors = [_text(a, f"{ATOM}name") for a in entry.findall(f"{ATOM}author")]
        out.append(
            {
                "id": m.group(1),
                "title": _text(entry, f"{ATOM}title"),
                "abstract": _text(entry, f"{ATOM}summary"),
                "authors": authors,
                "published": _text(entry, f"{ATOM}published"),
                "updated": _text(entry, f"{ATOM}updated"),
                "category": primary.get("term") if primary is not None else "",
                "comment": _text(entry, f"{ARXIV_NS}comment"),
                "journal_ref": _text(entry, f"{ARXIV_NS}journal_ref"),
                "url": f"https://arxiv.org/abs/{m.group(1)}",
            }
        )
    return out


def cmd_sweep(args: argparse.Namespace) -> int:
    HARNESS.mkdir(parents=True, exist_ok=True)
    pool: dict[str, dict] = {}
    if CANDIDATES.exists():
        for item in json.loads(CANDIDATES.read_text(encoding="utf-8")):
            pool[item["id"]] = item

    def flush() -> None:
        items = sorted(pool.values(), key=lambda x: x["published"], reverse=True)
        CANDIDATES.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

    for group, query in QUERIES:
        try:
            hits = arxiv_query(query, max_results=args.per_query)
        except RuntimeError as exc:
            print(f"  !! {group}: {exc}", file=sys.stderr, flush=True)
            continue
        new = 0
        for hit in hits:
            existing = pool.get(hit["id"])
            if existing:
                if group not in existing["groups"]:
                    existing["groups"].append(group)
                continue
            hit["groups"] = [group]
            hit["query"] = query
            hit["screen"] = "pending"
            pool[hit["id"]] = hit
            new += 1
        flush()
        print(f"  {group:9s} {len(hits):3d} hits, +{new:3d} new, pool={len(pool):4d}   [{query[:58]}]", flush=True)
        time.sleep(args.sleep)

    flush()
    items = sorted(pool.values(), key=lambda x: x["published"], reverse=True)
    print(f"\n候选池: {len(items)} 篇 -> {CANDIDATES}")
    return 0


def download_pdf(arxiv_id: str, dest: Path) -> bool:
    try:
        dest.write_bytes(_get(f"https://arxiv.org/pdf/{arxiv_id}"))
    except RuntimeError as exc:
        print(f"    pdf 失败: {exc}", file=sys.stderr)
        return False
    return dest.stat().st_size > 20_000


def download_source(arxiv_id: str, dest_dir: Path) -> str | None:
    dest_dir.mkdir(parents=True, exist_ok=True)
    tmp = dest_dir.parent / "eprint.raw"
    try:
        tmp.write_bytes(_get(f"https://arxiv.org/e-print/{arxiv_id}"))
    except RuntimeError as exc:
        print(f"    source 失败: {exc}", file=sys.stderr)
        return None

    # arXiv e-print 可能是 tar.gz，也可能是单个 gz/xz 压缩的 tex。
    try:
        with tarfile.open(tmp, "r:*") as tar:
            members = [m for m in tar.getmembers() if m.isfile()]
            for m in members:
                m.name = m.name.lstrip("./")
                if m.name.startswith("/") or ".." in Path(m.name).parts:
                    raise RuntimeError(f"unsafe path in tar: {m.name}")
            tar.extractall(dest_dir)
        tmp.unlink()
        return "tar"
    except tarfile.ReadError:
        pass

    subprocess.run(
        ["sh", "-c", f'gzip -dc "{tmp}" > "{dest_dir}/main.tex" 2>/dev/null || xz -dc "{tmp}" > "{dest_dir}/main.tex"'],
        check=False,
    )
    tmp.unlink(missing_ok=True)
    main = dest_dir / "main.tex"
    if main.exists() and main.stat().st_size > 0:
        return "single-tex"
    main.unlink(missing_ok=True)
    return None


def download_one(item: dict, force: bool = False, sleep: float = 3.2) -> dict:
    arxiv_id = item["id"]
    out = PAPERS / arxiv_id.replace("/", "_")
    out.mkdir(parents=True, exist_ok=True)
    pdf = out / f"{arxiv_id.replace('/', '_')}.pdf"
    meta_path = out / "meta.json"

    if force or not pdf.exists() or pdf.stat().st_size < 20_000:
        ok = download_pdf(arxiv_id, pdf)
        print(f"  pdf    {'ok ' if ok else 'FAIL'} {arxiv_id}  {item['title'][:58]}", flush=True)
        time.sleep(sleep)
    src_dir = out / "source"
    if force or not src_dir.exists() or not any(src_dir.rglob("*")):
        kind = download_source(arxiv_id, src_dir)
        if kind is None:
            src_dir.mkdir(exist_ok=True)
            (src_dir / ".missing").write_text("no e-print source available\n", encoding="utf-8")
        print(f"  source {kind or 'missing':11s} {arxiv_id}", flush=True)
        time.sleep(sleep)

    files = sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file())
    meta = {
        "id": arxiv_id,
        "title": item["title"],
        "authors": item["authors"],
        "published": item["published"],
        "category": item["category"],
        "url": item["url"],
        "groups": item.get("groups", []),
        "value": item.get("value", ""),
        "screen": item.get("screen", "keep"),
        "downloaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "files": files,
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta


def cmd_download(args: argparse.Namespace) -> int:
    if not CANDIDATES.exists():
        print("候选池不存在，先跑 sweep。", file=sys.stderr)
        return 1
    pool = json.loads(CANDIDATES.read_text(encoding="utf-8"))
    if args.id:
        wanted = [i for i in pool if i["id"] in set(args.id)]
        missing = set(args.id) - {i["id"] for i in wanted}
        for mid in missing:
            wanted.append({"id": mid, "title": "(手动指定)", "authors": [], "published": "", "category": "", "url": f"https://arxiv.org/abs/{mid}", "groups": ["manual"]})
    else:
        wanted = [i for i in pool if i.get("screen") in {"keep", "flagship"}]

    PAPERS.mkdir(parents=True, exist_ok=True)
    print(f"下载 {len(wanted)} 篇 -> {PAPERS}")
    for item in wanted:
        try:
            download_one(item, force=args.force, sleep=args.sleep)
        except Exception as exc:  # noqa: BLE001 - 单篇失败不阻断批处理
            print(f"  !! {item['id']}: {exc}", file=sys.stderr)
    total = len(list(PAPERS.glob("*/meta.json")))
    print(f"\n本地已有 {total} 篇。")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_sweep = sub.add_parser("sweep", help="arXiv 扫库，写候选池")
    p_sweep.add_argument("--per-query", type=int, default=100)
    p_sweep.add_argument("--sleep", type=float, default=3.5, help="每次请求后休眠秒数（arXiv 限速）")
    p_sweep.set_defaults(func=cmd_sweep)
    p_dl = sub.add_parser("download", help="下载 PDF + TeX 源码")
    p_dl.add_argument("--id", action="append", help="指定 arXiv id，可重复")
    p_dl.add_argument("--force", action="store_true", help="已存在也重下")
    p_dl.add_argument("--sleep", type=float, default=3.2, help="每次请求后休眠秒数（arXiv 限速）")
    p_dl.set_defaults(func=cmd_download)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
