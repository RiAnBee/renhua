#!/usr/bin/env python3
"""验证「汉语欧化语法」清单在本项目 AI 语料上是否成立。

背景：中文语言学界（王力 1943 → 谢耀基 → 贺阳 2008 → 余光中 → 闫易乾 2019）
已有一份**操作性**的欧化特征清单，但从未有人把它放到「AI 中文 vs 人类中文」上测。
本脚本补这一步。

若某特征在**两个语域**都显著（同向且 p<0.05），它就有资格进入 skill；
若只在一个语域显著或方向相反，只能作为语域限定规则或不用。

用法：python3 scripts/ling_features.py
"""
import re
import sys
import pathlib
import statistics as st

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from analyze_corpus import read_docs, clean, sentences, GROUPS  # noqa: E402
from stats_corpus import mann_whitney, cliffs_delta            # noqa: E402

# ---- 欧化清单（附学界出处，见 papers/ling/）------------------------------
# 自称/对称代词。欧化表现：代词该省不省（闫易乾 2019「代词的增多」）
PRONOUN = r"我|你|您|他|她|它|咱|我们|你们|他们|她们|它们|咱们|自己"
# 指示代词（同上，指示代词高频是机译汉语的特征，孔德璐 2024）
DEMONSTR = r"这|那|此|该|这些|那些|这种|那种|上述|前者|后者"
# 助词「的」。欧化表现：「的」字堆叠、长定语（王力「句子的延长」；余光中「的的不休」）
DE = r"的"
# 复数「们」。欧化表现：使用范围扩大（贺阳 2008 第 6.5 节；王力「记号的欧化」）
MEN = r"们"
# 虚化动词/万能动词。「进行/作出+抽象名词」（余光中 1987；夏云 2022 实证）
LIGHT_VERB = r"进行|作出|做出|给予|加以|予以|开展|实现|发生|形成|成为|起到|能够|可以"
# 抽象后缀。「性」「化」「度」「力」抽象名词（余光中 1987）
ABSTR_SUFFIX = r"[\u4e00-\u9fff]{1,3}性|[\u4e00-\u9fff]{1,3}化"
# 显式连接的连词全集（王力「联结成分的欧化」三条办法；本项目 A4 只测了转折连词）
CONNECTIVES = (r"(?:^|[。！？；\n])\s*(?:然而|但是|可是|不过|因此|所以|由于|因为|如果|虽然|尽管|"
               r"即使|而且|并且|何况|或者|以及|同时|此外|另外|总之|首先|其次|最后)")
# 连词「和/与/及」（受英文 and 影响，闫易乾 2019 例 4）
AND_WORDS = r"和|与|及|以及"
# 判断句「是…的」（闫易乾 2019 第 6 类）
JUDGMENT = r"是[^，。；]{0,24}的[，。；]"


def per_k(t, n):
    """每千字频次"""
    han = max(len(re.findall(r"[\u4e00-\u9fff]", t)), 1)
    return n / han * 1000


def attrib_ratio(t):
    """长定语代理量：同一小句内「的」≥2 的比例。"""
    ss = [s for s in sentences(t) if s.strip()[-1:] in "。！？"]
    if not ss:
        return 0.0
    return sum(1 for s in ss if s.count("的") >= 2) / len(ss)


def pron_chain_ratio(t):
    """代词连用代理量：相邻两句都含代词的段落占比（该省不省）。"""
    ps = [p for p in re.split(r"\n\s*\n", t) if p.strip()]
    hit = tot = 0
    for p in ps:
        ss = [s for s in sentences(p) if s.strip()[-1:] in "。！？"]
        for a, b in zip(ss, ss[1:]):
            tot += 1
            if re.search(PRONOUN, a) and re.search(PRONOUN, b):
                hit += 1
    return hit / tot if tot >= 3 else 0.0


def feats_ling(t):
    t = clean(t)
    out = {}
    for name, pat in [
        ("人称代词", PRONOUN), ("指示代词", DEMONSTR), ("助词「的」", DE),
        ("复数「们」", MEN), ("虚化动词", LIGHT_VERB), ("抽象后缀(性/化)", ABSTR_SUFFIX),
        ("显式连词", CONNECTIVES), ("和/与/及", AND_WORDS), ("判断句是…的", JUDGMENT),
    ]:
        out[name] = per_k(t, len(re.findall(pat, t)))
    out["长定语比例"] = attrib_ratio(t)
    out["代词连用比例"] = pron_chain_ratio(t)
    return out


def collect(folder):
    per = {}
    for d in read_docs(folder):
        for k, v in feats_ling(d).items():
            per.setdefault(k, []).append(v)
    return per


def main():
    hp = {g: collect(f) for g, f in GROUPS.items()}
    keys = list(feats_ling(open(__file__, encoding="utf-8").read()[:0] + "测试。").keys())

    print(f"{'欧化特征':18s} {'正式':>26s} {'口语':>26s}  判定")
    print("-" * 92)
    robust, weak, dep, null = [], [], [], []
    for k in keys:
        cells, dirs, sigs = [], [], []
        for reg in ("正式", "口语"):
            h = hp[f"人类·{reg}"].get(k, [])
            a = hp[f"AI·{reg}"].get(k, [])
            if len(h) < 3 or len(a) < 3:
                cells.append("        n/a        "); dirs.append(0); sigs.append(False); continue
            _, z = mann_whitney(h, a)
            d = cliffs_delta(h, a)
            sig = "***" if abs(z) > 3.29 else ("**" if abs(z) > 2.58 else ("*" if abs(z) > 1.96 else " "))
            cells.append(f"Δ={d:+.2f} z={z:+5.1f}{sig:<3s}")
            dirs.append(1 if d > 0.15 else (-1 if d < -0.15 else 0))
            sigs.append(abs(z) > 1.96)
        if dirs[0] != 0 and dirs[0] == dirs[1] and all(sigs):
            verdict = "稳健 ✅"; robust.append(k)
        elif dirs[0] != 0 and dirs[0] == dirs[1]:
            verdict = "同向·弱"; weak.append(k)
        elif dirs[0] != 0 and dirs[1] != 0 and dirs[0] != dirs[1]:
            verdict = "**语域依赖** ⚠️"; dep.append(k)
        elif dirs[0] == 0 and dirs[1] == 0:
            verdict = "无差异"; null.append(k)
        else:
            verdict = "仅单语域显著"
        print(f"{k:18s} {cells[0]} {cells[1]}  {verdict}")

    print(f"\n稳健（两语域同向且均 p<0.05）：{len(robust)} 条 → {', '.join(robust) or '无'}")
    print(f"同向但弱：{len(weak)} 条 → {', '.join(weak) or '无'}")
    print(f"语域依赖：{len(dep)} 条 → {', '.join(dep) or '无'}")
    print(f"无差异：{len(null)} 条 → {', '.join(null) or '无'}")
    print("\n注：Δ>0 表示 AI 比人类**更多**。欧化假设预测全部为正。")


if __name__ == "__main__":
    main()
