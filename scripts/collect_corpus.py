#!/usr/bin/env python3
"""采集中文人类语料，按语域分层存放（不混池）。

用法：
    python3 collect_corpus.py probe
    python3 collect_corpus.py crawl formal 120
    python3 collect_corpus.py crawl informal 120
    python3 collect_corpus.py stats

分层：
    corpus/formal/    权威、精雕细琢（人民网、gov.cn 等）
    corpus/informal/  口语、个人写作（博客园个人博客等）
"""
import re
import sys
import json
import time
import hashlib
import pathlib
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
CORPUS = ROOT.parent / "corpus"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

# 每个分层可用的索引页（按顺序翻页取文章链接）
INDEXES = {
    "formal": [
        "https://www.people.com.cn/",
        "http://politics.people.com.cn/",
        "http://society.people.com.cn/",
        "http://culture.people.com.cn/",
        "http://edu.people.com.cn/",
        "http://finance.people.com.cn/",
    ],
    "informal": [
        "https://www.cnblogs.com/",
        "https://www.cnblogs.com/cate/108703/",
        *[f"https://www.cnblogs.com/cate/python/{p}/" for p in range(1, 5)],
        *[f"https://www.cnblogs.com/cate/java/{p}/" for p in range(1, 5)],
        *[f"https://www.cnblogs.com/cate/web/{p}/" for p in range(1, 5)],
        *[f"https://www.cnblogs.com/cate/2/{p}/" for p in range(1, 4)],
        "https://www.cnblogs.com/aggsite/TopViews",
        "https://www.cnblogs.com/aggsite/headline",
    ],
}

# 文章链接模式（按分层）
PATTERNS = {
    "formal": r'https?://[a-z]+\.people\.com\.cn/n\d/\d{4}/\d{4}/c\d+-\d+\.html',
    "informal": r'https://www\.cnblogs\.com/[A-Za-z0-9_\-]+/p/\d+',
}


def get(url, timeout=20):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
    for enc in ("utf-8", "gb18030", "gbk"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "ignore")


def strip_tags(html):
    html = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", html)
    html = re.sub(r"(?is)<br\s*/?>", "\n", html)
    html = re.sub(r"(?is)</(p|div|h\d|li|td|tr)>", "\n", html)
    txt = re.sub(r"(?s)<[^>]+>", "", html)
    for a, b in (("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
                 ("&quot;", '"'), ("&#39;", "'"), ("&ldquo;", "“"), ("&rdquo;", "”"),
                 ("&mdash;", "—"), ("&hellip;", "…")):
        txt = txt.replace(a, b)
    txt = re.sub(r"[ \t\u3000]+", " ", txt)
    txt = re.sub(r"\n{3,}", "\n\n", txt)
    return "\n".join(l.strip() for l in txt.split("\n")).strip()


def han_ratio(text):
    return len(re.findall(r"[\u4e00-\u9fff]", text)) / max(len(text), 1)


def extract_title(html):
    m = re.search(r"(?is)<title[^>]*>(.*?)</title>", html)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""


def main_body(html, tier):
    """抽出正文。两类站点结构不同，分别处理。"""
    if tier == "formal":
        # 人民网：正文常在 <div class="rm_txt_con"> 或 id="rwb_zw"
        for pat in (r'(?is)<div[^>]+class="rm_txt_con[^"]*"[^>]*>(.*?)</div>\s*</div>',
                    r'(?is)<div[^>]+id="rwb_zw"[^>]*>(.*?)</div>'):
            m = re.search(pat, html)
            if m:
                return strip_tags(m.group(1))
        return ""
    else:
        # 博客园：<div id="cnblogs_post_body">...</div>
        m = re.search(r'(?is)<div[^>]+id="cnblogs_post_body"[^>]*>(.*?)</div>\s*<div', html)
        if not m:
            m = re.search(r'(?is)<div[^>]+id="cnblogs_post_body"[^>]*>(.*)', html)
        if m:
            t = strip_tags(m.group(1))
            # 截掉评论区
            for marker in ("posted @", "分类:", "标签:", "刷新页面", "登录后才能查看"):
                i = t.find(marker)
                if i > 200:
                    t = t[:i]
            return t.strip()
        return ""


def save(tier, url, title, text, source):
    d = CORPUS / tier
    d.mkdir(parents=True, exist_ok=True)
    h = hashlib.sha1(url.encode()).hexdigest()[:12]
    (d / f"{h}.txt").write_text(text, encoding="utf-8")
    with (d / "meta.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "id": h, "url": url, "title": title, "source": source,
            "chars": len(text), "han": len(re.findall(r"[\u4e00-\u9fff]", text)),
        }, ensure_ascii=False) + "\n")
    return h


def already(tier):
    meta = CORPUS / tier / "meta.jsonl"
    if not meta.exists():
        return set()
    return {json.loads(l)["url"] for l in meta.read_text(encoding="utf-8").splitlines() if l.strip()}


def crawl(tier, target):
    seen = already(tier)
    got = 0
    pat = PATTERNS[tier]
    for idx in INDEXES[tier]:
        if got >= target:
            break
        try:
            html = get(idx)
        except Exception as e:
            print(f"  [索引失败] {idx} {type(e).__name__}")
            continue
        links = []
        for l in re.findall(pat, html):
            if l not in links:
                links.append(l)
        print(f"  [索引] {idx} → {len(links)} 条链接")
        for url in links:
            if got >= target:
                break
            if url in seen:
                continue
            try:
                page = get(url)
            except Exception:
                continue
            body = main_body(page, tier)
            if not body or len(body) < 400 or han_ratio(body) < 0.5:
                continue
            h = save(tier, url, extract_title(page), body, idx)
            seen.add(url)
            got += 1
            if got % 10 == 0:
                print(f"     ...已采 {got}/{target}")
            time.sleep(0.3)
    print(f"[{tier}] 本次新增 {got} 篇，累计 {len(seen)}")
    return got


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "probe"
    if cmd == "probe":
        for u in ["https://www.people.com.cn/", "https://www.cnblogs.com/"]:
            try:
                print(f"OK {len(get(u)):7d}  {u}")
            except Exception as e:
                print(f"ERR {type(e).__name__}: {e}  {u}")
    elif cmd == "crawl":
        crawl(sys.argv[2], int(sys.argv[3]))
    elif cmd == "stats":
        for t in ("formal", "informal"):
            m = CORPUS / t / "meta.jsonl"
            if not m.exists():
                print(f"{t}: 0 篇")
                continue
            rows = [json.loads(l) for l in m.read_text(encoding="utf-8").splitlines() if l.strip()]
            print(f"{t}: {len(rows)} 篇，汉字 {sum(r['han'] for r in rows):,}，"
                  f"篇均 {sum(r['han'] for r in rows)//max(len(rows),1)} 字")
