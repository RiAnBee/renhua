#!/usr/bin/env python3
"""分词层的中文特征：补齐 CCL23 里依赖词性标注的那几条。

## 为什么单独一个脚本

CCL23（朱君辉等 2023，159 项特征）里有一批特征必须**词性标注**才能算，而本项目此前
只有正则与句长。§十六 装了 `jieba.posseg`（`.harness/vendor`），这里用它补上：

| CCL23 特征 | 该文数值（人类 / AI） | 方向 | 可否修 |
|---|---|---|---|
| 量词密度 | 0.027 / 0.019 | **人类 1.42×** | 否（AI 更少） |
| 第二人称比例 | 0.010 / 0.021 | AI **2.1×** | 可能 |
| 文言虚字「之」（文白比例） | 台湾 JCSA 2026：人类更多 | 人类更多 | 否 |
| 相邻句名词重复 | 0.263 / 0.631 | AI **2.4×** | 可能 |
| 全文名词重复 | 0.192 / 0.368 | AI **1.9×** | 可能 |

## 方法（两条长度对照都必须做）

- **等量窗口**：每篇 600 汉字（篇级长度污染，§十五）
- **按句长配对**：`相邻句名词重复` 是**按句**计算的量，必须控句长（§十七）

⚠️ 本项目的既有结论里，「相邻句实词重复」已记为**与文献口径相反**（§10.2）：
吴继峰 2025 测的是「词汇复现/同现」（语义网络丰富度）、CCL23 测的是「相邻句实词重复」
（重复率）—— 同一现象的两种度量。本脚本按 **CCL23 的重复率口径**测，并分开报
名词与全部实词两版。

用法：
```bash
python3 scripts/zh_pos_features.py     # 需 .harness/vendor 下的 jieba
```
"""
import re
import sys
import statistics as st
import pathlib
import itertools

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from analyze_corpus import clean, read_docs, GROUPS  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".harness" / "vendor"))
try:
    import jieba.posseg as pseg
except ImportError:
    sys.exit("需要 jieba：把 jieba 解包到 .harness/vendor/（见 prosody_features.py 顶部说明）")

HAN = re.compile(r"[\u4e00-\u9fff]")
# 量词 q；人名/地名归入名词；文言虚字单列
NOUN_POS = {"n", "ns", "nr", "nt", "nz", "ng"}
CONTENT_POS = {"n", "ns", "nr", "nt", "nz", "ng", "v", "vn", "a", "an", "vd", "ad", "i", "l"}
SECOND_PERSON = {"你", "您", "你们", "您们"}

# ⚠️ **jieba 不单独标量词**：它把「一个」「三次」「两只」整体标成 `m`（数词），
# `q` 标签实际从不出现（实测）。所以量词只能从 `m` 词的**词尾**识别 ——
# 汉语是「数词 + 量词」语序，量词在末尾。
MEASURE = set("个位名次回项条件张片块团群批种类款项笔宗桩件事物本册页篇章节段句字词句"
              "只匹头条尾峰峰羽角蹄对双副套串束把支根枝杆面颗粒滴阵场顿番遍趟遭轮"
              "层重级步岁年级期届班组队伍帮伙些点分秒时天年月日周旬季度米尺斤吨升"
              "平方米平方公里人次户家所座栋幢间层室处门台部辆船舶架列班位人次")


def fixed_window(t, n=600, frac=0.125):
    idx = [i for i, c in enumerate(t) if HAN.match(c)]
    if len(idx) < n:
        return None
    s = min(int(len(idx) * frac), len(idx) - n)
    return t[idx[s]:(idx[s + n - 1] + 1)]


def sentences(t):
    return [s for s in re.split(r"[。！？；]", t) if len(HAN.findall(s)) >= 5]


def doc_metrics(t):
    """篇级：量词、文言虚字、第二人称（都按每千字）。"""
    c = clean(t)
    hz = len(HAN.findall(c))
    if hz < 100:
        return None
    toks = list(pseg.cut(c))
    # 量词：`q` 标签（若分词器提供）+ 从 `m` 词尾识别的量词语素
    q = sum(1 for w, f in toks if f == "q")
    q += sum(1 for w, f in toks if f == "m" and w and w[-1] in MEASURE)
    zhi = sum(1 for w, f in toks if w == "之")          # 文言虚字「之」
    two = sum(1 for w, f in toks if w in SECOND_PERSON)
    n = sum(1 for w, f in toks if f in NOUN_POS)
    return {"量词/千字": q / hz * 1000, "文言虚字之/千字": zhi / hz * 1000,
            "第二人称/千字": two / hz * 1000, "名词/千字": n / hz * 1000}


def sent_metrics(t):
    """句级：相邻句名词重复率（CCL23 口径）、全文名词重复率。"""
    c = clean(t)
    if len(HAN.findall(c)) < 100:
        return None
    ss = sentences(c)
    if len(ss) < 3:
        return None
    seq = []
    for s in ss:
        toks = list(pseg.cut(s))
        seq.append({"n": len([1 for w, f in toks if f not in ("x", "w")]),
                    "noun": {w for w, f in toks if f in NOUN_POS},
                    "cont": {w for w, f in toks if f in CONTENT_POS}})
    for which in ("noun", "cont"):
        rs = []
        for a, b in zip(seq, seq[1:]):
            if b[which]:
                rs.append(len(a[which] & b[which]) / len(b[which]))
        allw = set().union(*(s[which] for s in seq))
        rep = (len(seq) and sum(len(s[which]) for s in seq) / max(len(allw), 1)) or 0
        seq[0][which + "_rep"] = st.mean(rs) if rs else 0
        seq[0][which + "_global"] = rep
    return {"句长(词)": st.mean([s["n"] for s in seq]),
            "相邻句名词重复": seq[0]["noun_rep"], "相邻句实词重复": seq[0]["cont_rep"],
            "全文名词重复": seq[0]["noun_global"], "全文实词重复": seq[0]["cont_global"]}


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


def table(title, V, keys, note=""):
    print(f"\n## {title}\n")
    if note:
        print(note + "\n")
    print(f"{'指标':18s}{'人类新闻':>10s}{'AI新闻':>10s}{'δ转述':>8s}{'z':>7s}"
          f"{'人类博客':>10s}{'AI博客':>10s}{'δ博客':>8s}{'z':>7s}   判定")
    print("-" * 100)
    for k in keys:
        v = {g: [r[k] for r in V[g]] for g in V}
        mu = {g: st.mean(v[g]) for g in v}
        dF, dI = cliffs(v["人类·正式"], v["AI·正式"]), cliffs(v["人类·口语"], v["AI·口语"])
        zF, zI = mw_z(v["人类·正式"], v["AI·正式"]), mw_z(v["人类·口语"], v["AI·口语"])
        verd = ("**体裁依赖** ⚠️" if abs(dF) > .33 and abs(dI) > .33 and dF * dI < 0
                else "两体裁同向 ✅" if abs(dF) > .33 and abs(dI) > .33
                else "仅转述体" if abs(dF) > .33
                else "仅作者在场体" if abs(dI) > .33 else "无稳健信号")
        print(f"{k:18s}{mu['人类·正式']:>10.3f}{mu['AI·正式']:>10.3f}{dF:>+8.2f}{zF:>+7.1f}"
              f"{mu['人类·口语']:>10.3f}{mu['AI·口语']:>10.3f}{dI:>+8.2f}{zI:>+7.1f}   {verd}")


def main():
    D, S = {}, {}
    for g, folder in GROUPS.items():
        d, s_ = [], []
        for t in read_docs(folder):
            w = fixed_window(clean(t))
            if not w:
                continue
            m = doc_metrics(w)
            if m:
                d.append(m)
            m2 = sent_metrics(w)
            if m2:
                s_.append(m2)
        D[g], S[g] = d, s_
        print(f"  {g:12s} 篇级 n={len(d)}  句级 n={len(s_)}")

    table("篇级（600 汉字等量窗口）", D,
          ["量词/千字", "文言虚字之/千字", "第二人称/千字", "名词/千字"])

    # 句级指标要控句长：按「句长(词)」分桶配对
    print("\n## 句级：按句长(词)分桶配对后的结果\n")
    print(f"  {'指标':18s}{'人类':>9s}{'AI':>9s}{'差':>9s}{'z':>7s}   判定")
    print("  " + "-" * 62)
    H, A = S["人类·正式"], S["AI·正式"]
    for k in ["相邻句名词重复", "相邻句实词重复", "全文名词重复", "全文实词重复"]:
        buckets = {}
        for x in A:
            buckets.setdefault(round(x["句长(词)"] / 5), []).append(x)
        shared = [(hn, [x for x in H if round(x["句长(词)"] / 5) == hn], buckets[hn])
                  for hn in sorted(buckets)
                  if min(len([x for x in H if round(x["句长(词)"] / 5) == hn]), len(buckets[hn])) >= 5]
        ws, ds, mh, ma = [], [], [], []
        for _, hh, aa in shared:
            w = min(len(hh), len(aa))
            ws.append(w)
            mh.append(st.mean([x[k] for x in hh]))
            ma.append(st.mean([x[k] for x in aa]))
            ds.append(st.mean([x[k] for x in hh]) - st.mean([x[k] for x in aa]))
        W = sum(ws)
        d = sum(a * w for a, w in zip(ds, ws)) / W
        wt = lambda v: sum(a * w for a, w in zip(v, ws)) / W
        var = sum((w / W) ** 2 * (st.variance([x[k] for x in hh]) / len(hh)
                                  + st.variance([x[k] for x in aa]) / len(aa))
                  for (_, hh, aa), w in zip(shared, ws))
        z = d / var ** 0.5 if var > 0 else 0
        print(f"  {k:18s}{wt(mh):>9.3f}{wt(ma):>9.3f}{d:>+9.3f}{z:>+7.1f}"
              f"   {'无差异' if abs(z) < 2 else '人类更高' if z > 0 else '**AI 更高**'}")

    print("\n**与 CCL23 对照**（该文数值）：")
    print("  量词密度       CCL23 人类 0.027 / AI 0.019（人类 1.42×）")
    print("  第二人称比例   CCL23 人类 0.010 / AI 0.021（AI 2.1×）")
    print("  相邻句名词重复 CCL23 人类 0.263 / AI 0.631（AI 2.4×）")
    print("  ⚠️ 前两行是「比例」，本项目是「每千字」，单位不同，只比方向。")


if __name__ == "__main__":
    main()
