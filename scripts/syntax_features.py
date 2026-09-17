#!/usr/bin/env python3
"""句法复杂度特征：补齐 CCL23 里「需要解析器」的那一整类。

## 为什么单独一个脚本

本项目此前只有正则与分词，所以 CCL23（朱君辉等 2023，159 项特征）里的**依存句法类**
（句法树高、依存距离、短语长度、修饰语数）**整类未测**。§十六 为测并列短语装了
spaCy `zh_core_web_sm`，同一套依赖可把这一类一并补上。

## CCL23 报过的数值（该文表 2；人类 vs GPT）

| 特征 | 人类 | AI | 方向 |
|---|---|---|---|
| 句法树高 > 14 的句子**占比** | 16.0% | 12.9% | AI 更低 |
| 平均句法树高 | — | — | — |
| 名词短语平均长度（字） | 4.054 | **4.816** | **AI 更长** |
| 动词短语平均长度（字） | 人类更高 | | AI 更低 |
| 平均句子依存距离 | — | — | — |
| 主要动词前平均词数 | — | — | — |

⚠️ **名词短语长度是已知冲突项**：CCL23 说 AI 更长，而**吴继峰等 2025**（10,657 篇学术汉语）
说母语者更长；本项目此前用正则测「长定语」得 AI **更少**（δ=−0.32/−0.66），
与吴继峰一致、与 CCL23 相反（见 evidence.md §10.2）。本脚本用句法口径复测。

## 度量定义（都与 CCL23 同族）

- **句法树高**：依存树的最大深度（token 数计深度，root 为 0）
- **依存距离**：|head.i − tok.i|，对每个非标点 token 取；报均值与最大值
- **名词短语长度**：以 NOUN/PROPN 为根、整棵子树（nsubj/dobj/amod/compound:nn/nummod…）
  的 token 数
- **动词短语平均长度**：同上，以 VERB 为根
- **形容词修饰语数（amod）**：每句 `amod` 弧数
- **主要动词前词数**：root 之前（按字符序）的 token 数

用法：
```bash
.harness/venv/bin/python scripts/syntax_features.py          # 需 spaCy + zh_core_web_sm
```
若无 spaCy 则退出并提示（本脚本**必须**用解析器，没有降级路径）。
"""
import re
import sys
import statistics as st
import pathlib
import itertools

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from analyze_corpus import clean, read_docs, GROUPS  # noqa: E402

HAN = re.compile(r"[\u4e00-\u9fff]")
PUNCT = {"punct", "dep"}


def fixed_window(t, n=600, frac=0.125):
    """取 n 个汉字的连续窗口（与 §十二／§十三／§十五／§十六 同一函数）。"""
    idx = [i for i, c in enumerate(t) if HAN.match(c)]
    if len(idx) < n:
        return None
    s = min(int(len(idx) * frac), len(idx) - n)
    return t[idx[s]:(idx[s + n - 1] + 1)]


def sentences(t):
    return [s for s in re.split(r"[。！？；]", t) if len(HAN.findall(s)) >= 5]


def tree_height(doc):
    """依存树最大深度（root = 0）。"""
    depth = {}

    def d(tok):
        if tok.i in depth:
            return depth[tok.i]
        depth[tok.i] = 0 if tok.head.i == tok.i else d(tok.head) + 1
        return depth[tok.i]

    return max((d(t) for t in doc), default=0)


def subtree_size(tok):
    """以 tok 为根的子树 token 数。"""
    n = 0
    stack = [tok]
    while stack:
        cur = stack.pop()
        n += 1
        stack.extend(cur.children)
    return n


def syntax_metrics(nlp, t):
    c = clean(t)
    if len(HAN.findall(c)) < 100:
        return None
    ss = sentences(c)
    ns = max(len(ss), 1)
    heights, deps, max_deps, np_lens, vp_lens, amods, pre_verbs = [], [], [], [], [], [], []
    for doc in nlp.pipe(ss, batch_size=16):
        toks = [x for x in doc if x.dep_ not in PUNCT]
        if not toks:
            continue
        heights.append(tree_height(doc))
        for x in toks:
            deps.append(abs(x.head.i - x.i))
        max_deps.append(max(deps[-len(toks):]) if toks else 0)
        amods.append(sum(1 for x in doc if x.dep_ == "amod"))
        root = next((x for x in doc if x.head.i == x.i), None)
        if root is not None and root.pos_ == "VERB":
            pre_verbs.append(sum(1 for x in toks if x.i < root.i))
        for x in doc:
            # 名词短语：取**名词性中心语**（排除自身是修饰/并列成分的 token），
            # 其子树即该 NP 的全部成分（定语、量词、同位语…）。
            if x.pos_ in ("NOUN", "PROPN") and x.dep_ not in (
                    "conj", "compound:nn", "amod", "nummod", "clf", "det", "case", "punct"):
                np_lens.append(subtree_size(x))
            if x.dep_ == "ROOT" and x.pos_ == "VERB":
                vp_lens.append(subtree_size(x))
    if not heights:
        return None
    return {
        "平均句法树高": st.mean(heights),
        "句法树高>14占比": sum(1 for h in heights if h > 14) / len(heights),
        "平均依存距离": st.mean(deps) if deps else 0,
        "平均句最大依存距离": st.mean(max_deps) if max_deps else 0,
        "名词短语平均长度": st.mean(np_lens) if np_lens else 0,
        "动词短语平均长度": st.mean(vp_lens) if vp_lens else 0,
        "amod数/句": st.mean(amods) / 1 if amods else 0,
        "主要动词前平均词数": st.mean(pre_verbs) if pre_verbs else 0,
    }


def cliffs(a, b):
    gt = sum(1 for x in a for y in b if x < y)
    lt = sum(1 for x in a for y in b if x > y)
    return (gt - lt) / (len(a) * len(b))


def mw_z(a, b):
    n1, n2 = len(a), len(b)
    if n1 < 3 or n2 < 3:
        return 0.0
    comb = sorted([(v, 0) for v in a] + [(v, 1) for v in b])
    ranks = [0.0] * len(comb)
    i = 0
    while i < len(comb):
        k = i
        while k + 1 < len(comb) and comb[k + 1][0] == comb[i][0]:
            k += 1
        avg = (i + k) / 2 + 1
        for m in range(i, k + 1):
            ranks[m] = avg
        i = k + 1
    r1 = sum(ranks[m] for m in range(len(comb)) if comb[m][1] == 0)
    u1 = r1 - n1 * (n1 + 1) / 2
    tie = sum(t ** 3 - t for t in
              [len(list(g)) for _, g in itertools.groupby(v for v, _ in comb)])
    sd = ((n1 * n2 / 12) * ((n1 + n2 + 1) - tie / ((n1 + n2) * (n1 + n2 - 1)))) ** 0.5
    return (u1 - n1 * n2 / 2) / sd if sd > 0 else 0.0


def length_matched(nlp, docs_h, docs_a):
    """**必须做的对照**：按句长把人类与 AI 的句子配对后再比。

    ⚠️ **不做这一步会得出完全错误的结论。** 句法树高、依存距离、短语长度都是
    **句长的下游** —— AI 的句子更短（本项目稳健结论），短句的树自然更浅、
    依存距离自然更短。未控制时这一整类特征都显示「AI 句法更简单」（δ=−0.40~−0.77），
    按句长配对后差异**基本消失**（平均依存距离 z=+0.4，最大依存距离甚至反向）。
    详见 `evidence.md` §十七。
    """
    def collect(t):
        out = []
        for s in sentences(t):
            doc = nlp(s)
            toks = [x for x in doc if x.dep_ not in PUNCT]
            if len(toks) < 5:
                continue
            deps = [abs(x.head.i - x.i) for x in toks]
            np = [subtree_size(x) for x in doc
                  if x.pos_ in ("NOUN", "PROPN")
                  and x.dep_ not in ("conj", "compound:nn", "amod", "nummod",
                                     "clf", "det", "case", "punct")]
            out.append(dict(n=len(toks), h=tree_height(doc), dep=st.mean(deps),
                            maxdep=max(deps), np=st.mean(np) if np else 0))
        return out

    H = [x for t in docs_h for w in [fixed_window(clean(t))] if w for x in collect(w)]
    A = [x for t in docs_a for w in [fixed_window(clean(t))] if w for x in collect(w)]

    # 按**精确句长**分桶，桶内取均值，再按桶内较少的一边加权。
    # ⚠️ 早先的写法是「拿每个人类句去配对第一个同长 AI 句」，会**重复取用同一句**，
    # 把 AI 的均值偏向该长度的第一个样本（实测让树高差从 +0.34 缩到 +0.13）—— 已改为分桶。
    def by_len(rows):
        d = {}
        for x in rows:
            d.setdefault(x["n"], []).append(x)
        return d

    BH, BA = by_len(H), by_len(A)
    shared = sorted(n for n in BH if n in BA and min(len(BH[n]), len(BA[n])) >= 5)
    print(f"\n## 按句长分桶配对（{len(shared)} 个句长桶，"
          f"覆盖人类 {sum(len(BH[n]) for n in shared)} / AI {sum(len(BA[n]) for n in shared)} 句）"
          f"—— 这才是可信的比较\n")
    print(f"  {'指标':12s}{'人类':>9s}{'AI':>9s}{'差':>9s}{'z':>7s}   判定")
    print("  " + "-" * 58)
    for key, name in (("h", "句法树高"), ("dep", "平均依存距离"),
                      ("maxdep", "最大依存距离"), ("np", "名词短语长度")):
        diffs, ws, mh, ma = [], [], [], []
        for n in shared:
            hh = [x[key] for x in BH[n]]
            aa = [x[key] for x in BA[n]]
            w = min(len(hh), len(aa))
            diffs.append(st.mean(hh) - st.mean(aa))
            se_b = ((st.variance(hh) / len(hh) if len(hh) > 1 else 0)
                    + (st.variance(aa) / len(aa) if len(aa) > 1 else 0)) ** 0.5
            ws.append(w)
            mh.append(st.mean(hh))
            ma.append(st.mean(aa))
        W = sum(ws)
        d = sum(x * w for x, w in zip(diffs, ws)) / W
        # 加权合并标准误（桶内独立）
        var = sum((w / W) ** 2 * (((st.variance([x[key] for x in BH[n]]) / len(BH[n])
                                    if len(BH[n]) > 1 else 0)
                                   + (st.variance([x[key] for x in BA[n]]) / len(BA[n])
                                      if len(BA[n]) > 1 else 0)))
                  for n, w in zip(shared, ws))
        z = d / var ** 0.5 if var > 0 else 0
        weight = lambda v: sum(x * w for x, w in zip(v, ws)) / W
        verdict = ("无差异" if abs(z) < 2 else
                   "**AI 更高（与未控制时相反）**" if z < 0 else "人类更高")
        print(f"  {name:12s}{weight(mh):>9.3f}{weight(ma):>9.3f}{d:>+9.3f}{z:>+7.1f}   {verdict}")


def main():
    try:
        import spacy
    except ImportError:
        sys.exit("需要 spaCy：见 scripts/coord_phrases.py 顶部的安装说明")
    try:
        nlp = spacy.load("zh_core_web_sm")
    except OSError:
        sys.exit("需要中文模型 zh_core_web_sm：见 scripts/coord_phrases.py 顶部")

    print(f"句法复杂度特征（spaCy {nlp.meta['name']}，600 汉字等量窗口）\n")
    V = {}
    for g, folder in GROUPS.items():
        rows = []
        for t in read_docs(folder):
            w = fixed_window(clean(t))
            if w:
                m = syntax_metrics(nlp, w)
                if m:
                    rows.append(m)
        V[g] = rows
        print(f"  {g:12s} n={len(rows)}")

    keys = list(V["人类·正式"][0].keys())
    print(f"\n{'指标':22s}{'人类新闻':>10s}{'AI新闻':>10s}{'δ转述':>8s}{'z':>7s}"
          f"{'人类博客':>10s}{'AI博客':>10s}{'δ博客':>8s}{'z':>7s}   判定")
    print("-" * 106)
    for k in keys:
        v = {g: [r[k] for r in V[g]] for g in V}
        mu = {g: st.mean(v[g]) for g in v}
        dF, dI = cliffs(v["人类·正式"], v["AI·正式"]), cliffs(v["人类·口语"], v["AI·口语"])
        zF, zI = mw_z(v["人类·正式"], v["AI·正式"]), mw_z(v["人类·口语"], v["AI·口语"])
        if abs(dF) > .33 and abs(dI) > .33 and dF * dI < 0:
            verd = "**体裁依赖** ⚠️"
        elif abs(dF) > .33 and abs(dI) > .33:
            verd = "两体裁同向 ✅"
        elif abs(dF) > .33:
            verd = "仅转述体"
        elif abs(dI) > .33:
            verd = "仅作者在场体"
        else:
            verd = "无稳健信号"
        print(f"{k:22s}{mu['人类·正式']:>10.3f}{mu['AI·正式']:>10.3f}{dF:>+8.2f}{zF:>+7.1f}"
              f"{mu['人类·口语']:>10.3f}{mu['AI·口语']:>10.3f}{dI:>+8.2f}{zI:>+7.1f}   {verd}")

    length_matched(nlp, read_docs(GROUPS["人类·正式"]), read_docs(GROUPS["AI·正式"]))

    print("\n**与 CCL23 对照**（该文表 2）：")
    m = {k: st.mean([r[k] for r in V["人类·正式"]]) for k in keys}
    a = {k: st.mean([r[k] for r in V["AI·正式"]]) for k in keys}
    print(f"  句法树高>14占比  CCL23 人类 16.0% / AI 12.9%（AI 更低）"
          f"  ← 本项目 人类 {m['句法树高>14占比']*100:.1f}% / AI {a['句法树高>14占比']*100:.1f}%")
    print(f"  名词短语平均长度 CCL23 人类 4.054 / AI 4.816（AI 更长）"
          f"  ← 本项目 人类 {m['名词短语平均长度']:.3f} / AI {a['名词短语平均长度']:.3f}")


if __name__ == "__main__":
    main()
