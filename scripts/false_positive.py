#!/usr/bin/env python3
"""误伤率实测：规则在**人类原创文本**上会触发多少次？

## 为什么必须单独测这个

前面所有测量都是**聚合**的（AI 组 vs 人类组的均值差）。但聚合显著**不等于**单篇安全：
一条规则可以在均值上成立，却在 40% 的人类文本上触发 —— 那在实践中就是灾难。
「改动 ≥3 处的那次，如果输入是人写的，就是误伤」（CONTRIBUTING）。

## 两个必须守住的口径

**1. 尊重语域闸门。** A4a 在口语语域**本就停用**。对口语语料计 A4a 触发，
是把「设计如此」算成「误伤」。所以 A4a 只对 formal 语料统计。

**2. 必须消除长度污染。** 本语料里 AI 正式篇均 837 汉字、人类正式 1178 汉字 ——
篇级触发率会被长度直接带偏（长的篇更容易触发）。所以主分析用**定长窗口**：
每篇取 600 汉字的连续窗口，各组的窗口长度完全一致，可以直接比。

**3. 触发 ≠ 改动。** 触发是误伤率的**上界**；闸门 4（单句反例门）还会挡掉一部分。
那一层需要判断，由 LLM 端到端实测，不在本脚本内。

## 未纳入的规则

- **A1 零信息句**：判据是语义的（「删掉后读者是否失去信息」），正则无法表达，**不纳入**。
  实测 A1 恰是误伤的主要来源（约 75%），需要端到端测 —— 见下。
- **A6 起手式宣言**：受文体门（仅「原则/取舍陈述」）保护，无法机械判定文体，
  只报**形态命中率**，并标注它受门保护。
- **A5 的「段内修辞密集」触发**：需要判断「比喻/排比/设问是否同时出现」，未机械化；
  本脚本只测它的另一条触发（段末句长均匀）。

## 端到端协议（测真正的误伤率，本脚本测不了）

代码代理给的是**很松的上界**——实测 A3b 代码级触发 23.8%，端到端 72 次运行里**一次都没触发**
（反例门全部吸收）。真正的误伤率必须让 LLM 跑：

1. 取**人类原创**样本（本记录用 12 篇人民网 + 12 篇博客园，汉字 600–1500，`seed=42`）
2. system = 完整 `SKILL.md` + `counterexamples.zh.md`；user = 该篇原文
3. 要求输出标准契约（改写稿 + 改动台帐 + 不动清单 + 未触发）
4. 数改动台帐条目数

**结果（池化 48 次运行）**：≥3 处（项目定义的误伤）= **4.2%**，均值 **0.73 处/篇**，中位 **0**。

⚠️ **运行方差大**：同一篇同一版本两次重复，平均绝对差 0.62，24 篇里只有 14 篇完全一致。
SD=0.74 → 检出 0.5 处差异需每组 ≈34 篇。**单次运行的 A/B 在 n=24 下没有判别力。**

完整记录见 `skills/renhua/references/evidence.md` §十二。

用法：python3 scripts/false_positive.py
"""
import re
import sys
import pathlib
import statistics as st

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from analyze_corpus import (  # noqa: E402
    read_docs, clean, sentences, paragraphs, GROUPS, ADVERSATIVE, ADDITIVE,
)

HAN = re.compile(r"[\u4e00-\u9fff]")

META_PREACH = (r"这告诉我们|这说明|由此可见|不难看出|值得注意的是|换言之|换句话说|"
               r"从本质上(?:讲|说)|可以说")
A6_OPEN = r"不[^，。；]{1,8}[，,]\s*[^，。；]{0,6}?不[^，。；]{1,8}[，,]\s*(?:只|仅|而)"

WINDOW = 600          # 定长窗口（汉字数）
FRAC = 0.125          # 从 12.5% 处开始，避开标题/导语


def han_window(t, n=WINDOW, frac=FRAC):
    """取恰好 n 个汉字的连续窗口；不足则返回 None。各组窗口长度一致 → 可比。"""
    idx = [i for i, c in enumerate(t) if HAN.match(c)]
    if len(idx) < n:
        return None
    start = min(int(len(idx) * frac), len(idx) - n)
    return t[idx[start]:(idx[start + n - 1] + 1)]


def frame(s):
    """「逗号位置一样、收尾方式一样」的机械代理：(分句块数, 末字)。"""
    s = s.strip().rstrip("。！？")
    chunks = [c for c in re.split(r"[，,、]", s) if c.strip()]
    return (len(chunks), s[-1:] if s else "")


# ---- 触发点收集：返回列表，长度 = 改动机会数 -------------------------------
def s_A2(t):
    return re.findall(META_PREACH, t)


def s_A3a(t):
    out = []
    for p in paragraphs(t):
        ss = sentences(p)
        for a, b in zip(ss, ss[1:]):
            fa = frame(a)
            if fa == frame(b) and fa[0] >= 1:
                out.append(1)
    return out


def s_A3b(t, run_min=3, cap=30):
    out = []
    for p in paragraphs(t):
        run = 0
        for s in sentences(p):
            run = run + 1 if len(s) <= cap else 0
            if run >= run_min:
                out.append(1)
                run = 0
    return out


def s_A4a(t, per_para=2):
    """转折连词：段内 ≥per_para 次，或连续段落都用它开头。**仅正式语域**。"""
    out = []
    for p in paragraphs(t):
        if len(re.findall(ADVERSATIVE, p)) >= per_para:
            out.append(1)
    run = 0
    for p in paragraphs(t):
        ss = sentences(p)
        if ss and re.match(r"\s*(?:然而|但是|可是|不过|尽管如此|反之)", ss[0]):
            run += 1
            if run >= 2:
                out.append(1)
        else:
            run = 0
    return out


def s_A4b(t, per_para=2):
    """并列补充连词：段内**句首** ≥per_para 次。两语域通用。"""
    pat = r"\s*(?:同时|此外|另外|与此同时|除此之外|与此相关)"
    out = []
    for p in paragraphs(t):
        if sum(1 for s in sentences(p) if re.match(pat, s)) >= per_para:
            out.append(1)
    return out


def s_A5(t, cv_thr=0.35, mean_cap=22):
    """段末句长均匀且偏短。需 ≥4 段，否则不判。"""
    lens = [len(sentences(p)[-1]) for p in paragraphs(t) if sentences(p)]
    if len(lens) < 4:
        return []
    cv = st.pstdev(lens) / max(st.mean(lens), 1e-9)
    return [1] if (cv < cv_thr and st.mean(lens) <= mean_cap) else []


def s_A6(t):
    ps = paragraphs(t)
    return re.findall(A6_OPEN, "\n".join(ps[:2]) if ps else t[:400])


GROUPS_REG = {
    "人类·正式": ("formal", "formal"),
    "AI·正式": ("ai_formal", "formal"),
    "人类·口语": ("informal", "informal"),
    "AI·口语": ("ai_informal", "informal"),
}

RULES = [
    ("A2 说教元评论", lambda t: s_A2(t)),
    ("A3a 相邻句同构", lambda t: s_A3a(t)),
    ("A3b 连续短句", lambda t: s_A3b(t)),
    ("A4b 并列补充", lambda t: s_A4b(t)),
    ("A5 段末句均匀", lambda t: s_A5(t)),
    ("A6 起手式形态", lambda t: s_A6(t)),
]


def collect(folder, register):
    """返回 (每篇各规则触发点数, 合格篇数)"""
    per = {r: [] for r, _ in RULES}
    per["A4a 转折连词"] = []
    ok = 0
    for d in read_docs(folder):
        w = han_window(clean(d))
        if w is None:
            continue
        ok += 1
        for r, fn in RULES:
            per[r].append(len(fn(w)))
        # 语域闸门：A4a 只在正式语域启用
        per["A4a 转折连词"].append(len(s_A4a(w)) if register == "formal" else 0)
    return per, ok


ALL = ["A2 说教元评论", "A3a 相邻句同构", "A3b 连续短句", "A4a 转折连词",
       "A4b 并列补充", "A5 段末句均匀", "A6 起手式形态"]


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / den
    return (max(0.0, c - h), min(1.0, c + h))


def main():
    data, ns = {}, {}
    for g, (f, reg) in GROUPS_REG.items():
        data[g], ns[g] = collect(f, reg)

    print(f"## 定长窗口分析（每篇取 {WINDOW} 汉字，各组窗口等长 → 可直接比）\n")
    print(f"{'组':12s}{'合格篇数':>10s}")
    for g in GROUPS_REG:
        print(f"{g:12s}{ns[g]:>10d}")

    print("\n### 1. 单规则触发率（窗口内至少 1 次）\n")
    print(f"{'规则':18s}{'人类·正式':>12s}{'AI·正式':>11s}{'人类·口语':>12s}{'AI·口语':>11s}   判定")
    print("-" * 84)
    risk = []
    for r in ALL:
        cells = []
        rates = {}
        for g in GROUPS_REG:
            v = data[g][r]
            k, n = sum(1 for x in v if x > 0), len(v)
            rates[g] = k / n if n else 0
            cells.append(f"{k/n*100:5.1f}%" if n else "  n/a")
        h = max(rates["人类·正式"], rates["人类·口语"])
        a = max(rates["AI·正式"], rates["AI·口语"])
        if h >= 0.20:
            verd = "⚠️ **人类侧过高**"; risk.append(r)
        elif h > a:
            verd = "⚠️ 人类 > AI（反向）"
        elif a - h >= 0.05:
            verd = "✅ 有效"
        else:
            verd = "· 区分力弱"
        print(f"{r:18s}{cells[0]:>12s}{cells[1]:>11s}{cells[2]:>12s}{cells[3]:>11s}   {verd}")

    print(f"\n### 2. 窗口内触发点合计（误伤率上界）\n")
    print(f"{'组':12s}{'≥1 处':>9s}{'≥3 处':>10s}{'≥3 的 95%CI':>18s}{'均值':>8s}")
    print("-" * 62)
    for g in GROUPS_REG:
        tot = [sum(data[g][r][i] for r in ALL) for i in range(ns[g])]
        n = len(tot)
        k3 = sum(1 for x in tot if x >= 3)
        lo, hi = wilson(k3, n)
        print(f"{g:12s}{sum(1 for x in tot if x>=1)/n*100:8.1f}%{k3/n*100:9.1f}%"
              f"{f'  [{lo*100:.1f}–{hi*100:.1f}]':>18s}{st.mean(tot):8.2f}")

    print("\n### 3. 人类侧触发率的 95% 置信区间\n")
    print(f"{'规则':18s}{'人类·正式':>26s}{'人类·口语':>26s}")
    print("-" * 72)
    for r in ALL:
        cells = []
        for g in ("人类·正式", "人类·口语"):
            v = data[g][r]
            k, n = sum(1 for x in v if x > 0), len(v)
            lo, hi = wilson(k, n)
            cells.append(f"{k/n*100:5.1f}%  [{lo*100:4.1f}–{hi*100:4.1f}]")
        print(f"{r:18s}{cells[0]:>26s}{cells[1]:>26s}")

    print("\n### 4. 触发阈值敏感性（改阈值会不会减少误伤）\n")
    for label, fn in [
        ("A4a 段内转折词 ≥k", lambda w, k: len(s_A4a(w, per_para=k)) > 0),
        ("A4b 段内句首补充 ≥k", lambda w, k: len(s_A4b(w, per_para=k)) > 0),
        ("A3b 连续短句 ≥k 句", lambda w, k: len(s_A3b(w, run_min=k)) > 0),
    ]:
        print(f"**{label}**")
        print(f"  {'k':>3s}{'人类·正式':>11s}{'AI·正式':>10s}{'人类·口语':>11s}{'AI·口语':>10s}")
        for k in (1, 2, 3, 4):
            cells = []
            for g, (f, reg) in GROUPS_REG.items():
                docs = [han_window(clean(d)) for d in read_docs(f)]
                docs = [d for d in docs if d]
                hits = sum(1 for d in docs if fn(d, k))
                cells.append(f"{hits/len(docs)*100:5.1f}%" if docs else "  n/a")
            print(f"  {k:>3d}{cells[0]:>11s}{cells[1]:>10s}{cells[2]:>11s}{cells[3]:>10s}")
        print()

    print("""---

**读法**：
- **人类侧高 = 会误伤**。阈值敏感性表用来看「调严阈值」能不能把人类侧压下来。
- 两边都高 = 规则无区分力；人类侧低 + AI 侧高 = 规则有效。
- 本表的触发率是**上界** —— 闸门 4 的反例门还会挡掉一部分，需 LLM 端到端实测。""")


if __name__ == "__main__":
    main()
