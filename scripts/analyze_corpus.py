#!/usr/bin/env python3
"""分层测量人机风格差异。

核心设计：2×2 —— {人类, AI} × {正式, 口语}。
**按语域分别算倍率，再对比混池算出的倍率**，用以验证「混池会扭曲结论」。

用法：python3 analyze_corpus.py
"""
import re
import json
import pathlib
import statistics as st

ROOT = pathlib.Path(__file__).resolve().parent.parent
CORPUS = ROOT / "corpus"

SENT_SPLIT = re.compile(r"(?<=[。！？])")


def read_docs(folder):
    d = CORPUS / folder
    if not d.exists():
        return []
    docs = []
    for f in sorted(d.glob("*.txt")):
        t = f.read_text(encoding="utf-8")
        if len(t) > 200:
            docs.append(t)
    return docs


def sentences(t):
    return [s.strip() for s in SENT_SPLIT.split(t) if len(s.strip()) > 2]


def paragraphs(t):
    ps = [p.strip() for p in re.split(r"\n\s*\n", t) if len(p.strip()) > 20]
    if len(ps) < 3:                      # 有些源用单换行分段
        ps = [p.strip() for p in t.split("\n") if len(p.strip()) > 20]
    return ps


def per_k(t, n):
    """每千字频次"""
    return n / max(len(t), 1) * 1000


# ---- 特征定义（全部正则可复现）------------------------------------------
# `不过`/`可是` 在中文里兼作副词（"干不过""只不过是"）与转折连词。
# 只用位置可判定的形式：句首、或紧随意群边界。
ADVERSATIVE = (r"(?:^|[。！？；\n])\s*(?:然而|但是|可是|不过|尽管如此|反之)|"
               r"然而|但是|，不过|。不过")
ORDINAL = r"首先|其次|再次|最后|第一|第二|其一|其二|再者"
CONTRAST_PAIR = r"不是[^，。；]{0,20}?而是|并非[^，。；]{0,20}?而是|不在于[^，。；]{0,20}?而在于|与其说"
REVERSED_PAIR = r"是[^，。；]{0,14}?，(?:而)?不是|，不是[^，。；]{0,14}$"
PARALLEL_NEG = r"不[^，。；]{0,12}?[，、][^。]{0,12}?不[^，。；]{0,12}?[，、]"   # 不X，不Y，
META_TEXT = r"这一节|这一段|本文|本节|上文|下文|接下来|下面(?:我们|来)|如前所述|前面提到|如上所述"
CONCLUSION = r"总而言之|总之|综上|由此可见|可见|说到底|归根结底"
HEDGE = r"可能|也许|大概|或许|似乎|往往|通常|一般来说|在一定程度上"
VAGUE_ATTR = r"研究表明|数据显示|专家(?:表示|指出|认为)|业内人士|有分析认为|报告显示"
DASH = r"——"
QUESTION = r"[？?]"
METAPHOR = r"像[^，。]{2,}|如同|仿佛|好似|宛如|犹如"
COLON_LEAD = r"[:：]\s*(?:\n|$)"

FEATS = {
    "转折连词": ADVERSATIVE,
    "序数结构词": ORDINAL,
    "对举(不是..而是)": CONTRAST_PAIR,
    "反向对举(是X不是Y)": REVERSED_PAIR,
    "平行否定(不X,不Y)": PARALLEL_NEG,
    "元文本导航": META_TEXT,
    "结论套话": CONCLUSION,
    "缓和语": HEDGE,
    "模糊归因": VAGUE_ATTR,
    "破折号": DASH,
    "问句": QUESTION,
    "比喻标记": METAPHOR,
    "空转冒号引列表": COLON_LEAD,
}


CONCESSION_TURN = r"[。；\n]\s*不过[，,][^。]{0,30}?(?:仍|还|也|依然)[^。]{0,20}?(?:面临|存在|需要|有)"  # 让步转折公式


def drop_label_lines(t):
    """去掉标签行、表格行、标识符行。

    这些行短、且不含任何句内标点，是代码块/表格/字段清单的残留。
    不清理它们，句长统计会把「策略文件 / breakthrough_platform.py / 突破平台」
    这类无标点的连续行粘成一个几百字的假"句子"——实测污染过 411 字。
    """
    out = []
    for line in t.split("\n"):
        s = line.strip()
        if not s:
            out.append(line)
            continue
        if len(s) < 40 and not re.search(r"[。，、；：！？\u201c\u201d]", s):
            continue
        out.append(line)
    return "\n".join(out)


def clean(t):
    """去掉代码块、行内代码、URL、列表项——它们不是散文，会污染句长与虚词统计。"""
    t = re.sub(r"```.*?```", " ", t, flags=re.S)
    t = re.sub(r"`[^`\n]+`", " ", t)
    t = re.sub(r"https?://\S+", " ", t)
    t = re.sub(r"^\s*\|.*$", " ", t, flags=re.M)          # Markdown 表格行
    t = drop_label_lines(t)                                  # 标签/标识符行
    t = re.sub(r"^\s*(?:[-*+>]|\d+[.)])\s+.*$", " ", t, flags=re.M)
    t = re.sub(r"^\s*(?:def |class |import |from |function |const |var |let |#include|\$ |> )\S.*$",
               " ", t, flags=re.M)
    t = re.sub(r"[ \t\u3000]+", " ", t)
    return t


def feats(t):
    t = clean(t)
    out = {}
    for name, pat in FEATS.items():
        out[name] = per_k(t, len(re.findall(pat, t)))
    out["让步转折公式"] = per_k(t, len(re.findall(CONCESSION_TURN, t)))
    # 句长
    ss = [s for s in sentences(t) if s.strip()[-1:] in "。！？"]
    if ss:
        L = [len(s) for s in ss]
        out["平均句长"] = st.mean(L)
        out["句长CV"] = st.pstdev(L) / max(st.mean(L), 1e-9)
    # 段末句长度 CV（节奏均匀度）
    ps = paragraphs(t)
    lastlens = [len(ss[-1]) for p in ps
                if (ss := [s for s in sentences(p) if s.strip()[-1:] in "。！？"])]
    if len(lastlens) > 2:
        out["段末句长CV"] = st.pstdev(lastlens) / max(st.mean(lastlens), 1e-9)
    # 段首句是否为评论/元文本框架
    if ps:
        framed = sum(1 for p in ps if re.match(r"\s*(值得注意|更重要的是|关键在于|问题在于|"
                                                r"说白了|不难看出|总的来说|需要注意的是|"
                                                r"事实上|客观来说|毫无疑问)", p))
        out["段首框架句占比"] = framed / len(ps)
    # 信息推进：相邻句字符级 Jaccard（越低=跳步越大）
    jumps = []
    for p in ps:
        ss2 = [s for s in sentences(p) if s.strip()[-1:] in "。！？"]
        for a, b in zip(ss2, ss2[1:]):
            A, B = set(a), set(b)
            if A and B:
                jumps.append(1 - len(A & B) / len(A | B))
    if len(jumps) > 3:
        out["跳步均值"] = st.mean(jumps)
        out["跳步CV"] = st.pstdev(jumps) / max(st.mean(jumps), 1e-9)
    return out


def agg(docs):
    """返回每个特征的均值"""
    acc = {}
    for d in docs:
        for k, v in feats(d).items():
            acc.setdefault(k, []).append(v)
    return {k: st.mean(v) for k, v in acc.items()}, len(docs)


def fmt(v):
    return f"{v:.3f}" if abs(v) < 10 else f"{v:.1f}"


GROUPS = {
    "人类·正式": "formal",
    "AI·正式": "ai_formal",
    "人类·口语": "informal",
    "AI·口语": "ai_informal",
}

if __name__ == "__main__":
    data, n = {}, {}
    for label, folder in GROUPS.items():
        docs = read_docs(folder)
        data[label], n[label] = agg(docs)
        han = sum(len(re.findall(r"[\u4e00-\u9fff]", d)) for d in docs)
        print(f"{label:10s} {n[label]:3d} 篇  {han:>8,} 汉字")

    keys = sorted(set().union(*[set(v) for v in data.values()]))

    def ratio(a, b):
        """b 相对 a 的倍数（AI ÷ 人类）"""
        va, vb = data[a].get(keys[0]), data[b].get(keys[0])
        return None

    print("\n## 分层 vs 混池\n")
    hdr = ("特征", "人·正式", "AI·正式", "正式倍率", "人·口语", "AI·口语", "口语倍率", "混池倍率")
    print("| " + " | ".join(hdr) + " |")
    print("|" + "---|" * len(hdr))

    rows = []
    for k in keys:
        hf, af = data["人类·正式"].get(k), data["AI·正式"].get(k)
        hi, ai = data["人类·口语"].get(k), data["AI·口语"].get(k)
        if hf is None or af is None or hi is None or ai is None:
            continue
        rf = af / hf if hf else float("inf")
        ri = ai / hi if hi else float("inf")
        # 混池：把两语域合并后的比值
        pooled_h = (hf * n["人类·正式"] + hi * n["人类·口语"]) / (n["人类·正式"] + n["人类·口语"])
        pooled_a = (af * n["AI·正式"] + ai * n["AI·口语"]) / (n["AI·正式"] + n["AI·口语"])
        rp = pooled_a / pooled_h if pooled_h else float("inf")
        rows.append((k, hf, af, rf, hi, ai, ri, rp))
        print(f"| {k} | {fmt(hf)} | {fmt(af)} | {rf:.2f}× | {fmt(hi)} | {fmt(ai)} | {ri:.2f}× | {rp:.2f}× |")

    print("\n## 结论：倍率是否随语域改变\n")
    flip = 0
    for k, hf, af, rf, hi, ai, ri, rp in rows:
        if (rf > 1.3 and ri < 0.77) or (rf < 0.77 and ri > 1.3):
            print(f"- **{k}**：正式 {rf:.2f}× vs 口语 {ri:.2f}× —— **方向相反**")
            flip += 1
        elif abs(rf - ri) / max(rf, ri, 1e-9) > 0.4:
            print(f"- {k}：正式 {rf:.2f}× vs 口语 {ri:.2f}× —— 幅度差 {abs(rf-ri)/max(rf,ri)*100:.0f}%")
    print(f"\n方向相反的 {flip} 条")

    pathlib.Path(ROOT / ".harness" / "corpus-analysis.json").write_text(
        json.dumps({"n": n, "groups": data}, ensure_ascii=False, indent=2), encoding="utf-8")
