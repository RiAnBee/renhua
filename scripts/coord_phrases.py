#!/usr/bin/env python3
"""并列短语密度：检验 CCL23 的「句均并列短语数」能否复现？

## 来源（本项目目前唯一还没测的外部候选）

朱君辉等 2023（CCL 2023 /《中文信息学报》2024, 38(4):17-27）用 159 项特征对比中文人机
问答，报告「并列短语」相关 3 项是分类模型中贡献度最高的特征之一，且
**ChatGPT 在这三项上都远高于人类**（该文表 2／表 5，**依存句法**度量）：

| 指标 | 人类 | AI | 倍率 |
|---|---|---|---|
| 句均并列短语数*（两种算法均高贡献） | 0.251 | **0.729** | **2.9×** |
| 单句平均并列短语数 | 0.095 | — | — |
| 并列短语数 | 0.813 | — | — |

该文的示意例子是**顿号枚举**：
> AI：「……这些市场都提供各种服装产品，**包括男装、女装、童装等**。」
> 人类：「……有很多服装批发大楼，其中的天雅是专门的品牌批发，购物环境不错……」
作者的解释是「AI 经常使用多个并列成分，这些并列成分处于同一语义场之中」。

## 两种口径，都要报

1. **正则代理**（总是可用）：顿号枚举组、顿号／并列连词的每千字与每句频次。
   优点：可复现、无依赖。缺点：**顿号枚举 ≠ 依存句法上的并列短语**——
   枚举只是并列的一种显性实现，「A 和 B」这种不用顿号的并列会漏掉。
2. **依存句法**（需要 spaCy + 中文模型，见下）：统计 `conj` 依存关系。
   这是与 CCL23 同口径的度量。

## 方法学（同 §十二／§十五，必须一起报）

- **等量窗口**：每篇取 600 汉字（`fixed_window`）。AI·正式 篇均 837 汉字 vs 人类 2230，
  不做等量窗口的话，任何「数出来」的量都会被长度直接带偏。
- **分体裁**：按 §十四 的转述体／作者在场体两层各测一次，再看方向是否一致。
- **这一条撞不了禁改清单**：并列短语是**句内**形态，删它属「删」，不在禁改项里 ——
  所以它是「可修」候选里最后一个没测的。

## 怎么跑

```bash
# 只用正则 + POS 口径（任何环境都能跑）
python3 scripts/coord_phrases.py

# 带依存句法（与 CCL23 同口径；约 300MB）
python3 -m venv .harness/venv
.harness/venv/bin/pip install -i https://pypi.tuna.tsinghua.edu.cn/simple spacy
.harness/venv/bin/pip install pysocks        # 让 pip 能走 SOCKS 代理
.harness/venv/bin/pip install \
  https://github.com/explosion/spacy-models/releases/download/zh_core_web_sm-3.8.0/zh_core_web_sm-3.8.0-py3-none-any.whl
.harness/venv/bin/python scripts/coord_phrases.py
```

⚠️ **本环境的网络坑（已实测）**：
- 系统 python 是 externally-managed（PEP 668）→ 用 venv，`--user` 会被拒。
- `ALL_PROXY` 指向 `socks5h://127.0.0.1:10808`，而 pip 默认**没有 PySocks** →
  装任何包前先 `pip install pysocks`，否则报 `Missing dependencies for SOCKS support`。
- **pypi.org 直连超时，GitHub 直连也超时**；改用清华镜像装 PyPI 包、
  **经代理**取 GitHub 上的模型 wheel（PySocks 装好后 pip 会自动走 `ALL_PROXY`）。
- PyPI 上有个同名的 `zh-core-web-sm` 是**抢注的占位包**（pip 会警告 dependency confusion），
  真模型只在 GitHub releases。
"""
import re
import sys
import statistics as st
import pathlib
from collections import Counter

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from analyze_corpus import clean, read_docs, GROUPS  # noqa: E402

HAN = re.compile(r"[\u4e00-\u9fff]")

# 并列连词。`和/与/及/跟/同` 兼作介词（"与去年相比"），`或/还是` 兼作疑问语气，
# 所以这是**上界**——真实并列关系要句法才判得准。
COORD_CONJ = r"和|与|以及|及|跟|同|或|或者|还是"

# 顿号枚举：X、Y、Z（至少两个顿号项）
ENUM_RUN = r"[^，。；！？：\s（(）)]{1,20}、(?:[^，。；！？：\s（(）)]{1,20}、)*[^，。；！？：\s（(）)]{1,20}"


def fixed_window(t, n=600, frac=0.125):
    """取 n 个汉字的连续窗口（与 §十二／§十三／§十五 同一函数）。"""
    idx = [i for i, c in enumerate(t) if HAN.match(c)]
    if len(idx) < n:
        return None
    s = min(int(len(idx) * frac), len(idx) - n)
    return t[idx[s]:(idx[s + n - 1] + 1)]


def sentences(t):
    return [s for s in re.split(r"[。！？；]", t) if len(HAN.findall(s)) >= 5]


# ---- 口径 1：正则代理 ----------------------------------------------------
def regex_metrics(t):
    c = clean(t)
    hz = len(HAN.findall(c))
    if hz < 100:
        return None
    ss = sentences(c)
    ns = max(len(ss), 1)
    d = len(re.findall(r"、", c))
    j = len(re.findall(COORD_CONJ, c))
    g = len(re.findall(ENUM_RUN, c))
    return {
        "句数": ns,
        "顿号枚举组/句": g / ns,
        "顿号/句": d / ns,
        "并列连词/句": j / ns,
        "并列连接合计/句": (d + j) / ns,
    }


# ---- 口径 1b：POS 感知（jieba，比裸顿号更接近「并列短语」）--------------
# 真实的并列短语要求**同一范畴**的成分并列（名词与名词、动词与动词）。
# 裸数顿号会把「、」的所有用法都算进来，所以这里要求两侧都是同类实词。
CONTENT_POS = {"n", "v", "vn", "a", "an", "m", "q", "ns", "nr", "nt", "nz",
               "vd", "ad", "eng", "j", "i", "l"}
COORD_SEP = {"、", "和", "与", "以及", "及", "跟", "同", "或", "或者", "还是"}


def _load_pseg():
    try:
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent
                               / ".harness" / "vendor"))
        import jieba.posseg as pseg
        return pseg
    except ImportError:
        return None


def pos_coord_metrics(pseg, t):
    """返回三个口径的并列计数。

    **并列组** = 被顿号／并列连词串起来的连续成分段（≥2 个成分）。
    两档严格度：
      - `strict`：要求相邻成分**同类**（POS 首字母相同）—— 最保守
      - `loose` ：只要求两侧都是实词 —— 上界

    分组方法：找出所有「合法的分隔符位置」，把**相隔 2 个 token**（即共享中间成分）
    的位置并成一组。⚠️ 早先的写法在遇到「成分」token 时就 flush，会把
    「男装、女装、童装」错算成 2 组 4 成分（应为 1 组 3 成分）—— 已修。
    """
    c = clean(t)
    if len(HAN.findall(c)) < 100:
        return None
    ss = sentences(c)
    ns = max(len(ss), 1)
    out = {}
    for label, strict in (("strict", True), ("loose", False)):
        groups = items = 0
        for s in ss:
            toks = [(w.word, w.flag) for w in pseg.cut(s)]
            n = len(toks)

            def is_sep(i):
                if not (0 < i < n - 1):
                    return False
                w, a, b = toks[i][0], toks[i - 1], toks[i + 1]
                if w not in COORD_SEP:
                    return False
                if a[1] not in CONTENT_POS or b[1] not in CONTENT_POS:
                    return False
                return (a[1][:1] == b[1][:1]) if strict else True

            seps = [i for i in range(1, n - 1) if is_sep(i)]
            k = 0
            while k < len(seps):
                m = k
                while m + 1 < len(seps) and seps[m + 1] == seps[m] + 2:
                    m += 1
                groups += 1
                items += (m - k + 1) + 1          # 分隔符数 + 1 = 成分数
                k = m + 1
        out[f"并列组/句({label})"] = groups / ns
        out[f"并列成分/句({label})"] = items / ns
    out["句数"] = ns
    return out


# ---- 口径 2：依存句法 ----------------------------------------------------
def load_nlp():
    """有 spaCy + 中文模型就返回 pipeline，否则 None。"""
    try:
        import spacy
    except ImportError:
        return None
    for name in ("zh_core_web_sm", "zh_core_web_md", "zh_core_web_trf"):
        try:
            return spacy.load(name)
        except OSError:
            continue
    return None


def dep_metrics(nlp, t, batch_sents=None):
    """统计 `conj` 依存关系。

    `conj` = 并列关系，直接对应 CCL23 的「并列短语」。两种计数：
      - conj_arcs      ：并列弧数（每个被并列的成分算一条）
      - conj_groups    ：并列组数（每个「中心语 + 其并列成分」算一组）
    报**每句**与**每千字**两版；CCL23 报的是每句。
    """
    c = clean(t)
    hz = len(HAN.findall(c))
    if hz < 100:
        return None
    ss = sentences(c)
    ns = max(len(ss), 1)
    arcs = 0
    heads = set()
    for doc in nlp.pipe(ss, batch_size=16):
        for tok in doc:
            if tok.dep_ == "conj":
                arcs += 1
                heads.add((tok.head.idx, tok.head.text))
    return {
        "句数": ns,
        "conj弧/句": arcs / ns,
        "conj组/句": len(heads) / ns,
        "conj弧/千字": arcs / hz * 1000,
    }


# ---- 统计（与 stats_corpus.py 同口径：Mann-Whitney + Cliff's δ）----------
def cliffs_delta(a, b):
    gt = sum(1 for x in a for y in b if x < y)
    lt = sum(1 for x in a for y in b if x > y)
    return (gt - lt) / (len(a) * len(b))


def mann_whitney_z(a, b):
    import itertools
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


def report(title, per_group, keys):
    print(f"\n## {title}\n")
    print(f"{'指标':20s}{'人类新闻':>10s}{'AI新闻':>10s}{'δ转述':>9s}{'z':>7s}"
          f"{'人类博客':>10s}{'AI博客':>10s}{'δ博客':>9s}{'z':>7s}   判定")
    print("-" * 104)
    for k in keys:
        v = {g: [r[k] for r in rows] for g, rows in per_group.items()}
        mu = {g: st.mean(v[g]) for g in v}
        dF, dI = cliffs_delta(v["人类·正式"], v["AI·正式"]), cliffs_delta(v["人类·口语"], v["AI·口语"])
        zF, zI = mann_whitney_z(v["人类·正式"], v["AI·正式"]), mann_whitney_z(v["人类·口语"], v["AI·口语"])
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
        print(f"{k:20s}{mu['人类·正式']:>10.3f}{mu['AI·正式']:>10.3f}{dF:>+9.2f}{zF:>+7.1f}"
              f"{mu['人类·口语']:>10.3f}{mu['AI·口语']:>10.3f}{dI:>+9.2f}{zI:>+7.1f}   {verd}")


def main():
    nlp = load_nlp()
    pseg = _load_pseg()
    print("=" * 104)
    print("并列短语密度 —— 复现 CCL23 的「句均并列短语数」？")
    print("=" * 104)
    print(f"依赖解析：{'spaCy ' + nlp.meta['name'] if nlp else '**不可用**（只跑正则代理口径）'}")
    print(f"POS 感知：{'jieba.posseg 可用' if pseg else '**不可用**'}")

    wins, dep_wins, pos_wins = {}, {}, {}
    for g, folder in GROUPS.items():
        docs = read_docs(folder)
        rw, dw, pw = [], [], []
        for t in docs:
            w = fixed_window(clean(t))
            if not w:
                continue
            m = regex_metrics(w)
            if m:
                rw.append(m)
                if pseg:
                    pm = pos_coord_metrics(pseg, w)
                    if pm:
                        pw.append(pm)
                if nlp:
                    dm = dep_metrics(nlp, w)
                    if dm:
                        dw.append(dm)
        wins[g], dep_wins[g], pos_wins[g] = rw, dw, pw
        extra = (f"  POS n={len(pw)}" if pseg else "") + (f"  句法 n={len(dw)}" if nlp else "")
        print(f"  {g:12s} n={len(rw)}{extra}")

    rkeys = ["顿号枚举组/句", "顿号/句", "并列连词/句", "并列连接合计/句"]
    report("口径 1：正则代理（600 汉字等量窗口）", wins, rkeys)

    if pseg and all(pos_wins[g] for g in pos_wins):
        report("口径 1b：POS 感知（同类实词 + 顿号／并列连词）", pos_wins,
               ["并列组/句(strict)", "并列成分/句(strict)",
                "并列组/句(loose)", "并列成分/句(loose)"])

    if nlp and all(dep_wins[g] for g in dep_wins):
        dkeys = ["conj弧/句", "conj组/句", "conj弧/千字"]
        report("口径 2：依存句法 conj 关系（与 CCL23 同口径）", dep_wins, dkeys)
        hf, af = dep_wins["人类·正式"], dep_wins["AI·正式"]
        mu_h = st.mean([r["conj弧/句"] for r in hf])
        mu_a = st.mean([r["conj弧/句"] for r in af])
        print(f"\n**与 CCL23 对照**：CCL23 人类 0.251 / AI 0.729 → **2.9×**；"
              f"本项目转述体 人类 {mu_h:.3f} / AI {mu_a:.3f} → "
              f"**{(mu_a / mu_h if mu_h else float('nan')):.2f}×**")
    else:
        print("\n（未跑依存句法口径；正则代理只是**上界**，见 docstring）")


if __name__ == "__main__":
    main()
