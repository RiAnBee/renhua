#!/usr/bin/env python3
"""根因实验：AI 味是否来自「助手人格」？

假说（由用户的两个实例引出）：
  例1「不X，不Y，只Z」——助手先排除误解，再给答案
  例2「这一节比上面那节重要」——助手/老师给读者导航
  两者同源：模型把自己放在**助手/老师**的位置，而不是**作者**的位置。

设计：同一话题 × 4 种框定，看「起手式」与「元文本导航」是否随框定改变。

  A 助手姿态  「帮我解释一下 X」
  B 作者姿态  「写一篇关于 X 的随笔，你就是作者，写给读者看」
  C 私人通信  「写封邮件给同事，说说 X 这事」
  D 助手姿态·带受众（对照，隔离「受众」这个因素）
              「给我讲讲 X，我要拿去给同事看」

若 B/C 显著低于 A → 假说成立（根因是姿态）
若四者无差 → 假说被推翻（是更深的东西）

用法：python3 persona_experiment.py
"""
import re
import sys
import json
import pathlib
import statistics as st

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / ".harness" / "persona-experiment"
sys.path.insert(0, str(ROOT / "scripts"))
from analyze_corpus import clean, sentences, paragraphs  # noqa: E402

TOPICS = [
    "为什么要给代码写注释", "怎么选一门第二外语", "城市里养猫的注意事项",
    "如何安排一周的锻炼", "怎样挑选一把办公椅", "为什么需要定期备份数据",
    "怎么和同事沟通需求变更", "为什么咖啡因会影响睡眠", "怎样规划一次长途旅行",
    "如何判断一份工作是否适合自己", "为什么要读纸质书", "怎么处理突发的线上故障",
]

FRAMES = {
    "A 助手姿态": "帮我解释一下「{t}」。",
    "B 作者姿态": "写一篇关于「{t}」的随笔，你就是作者，写给读者看。",
    "C 私人通信": "写封邮件给同事，说说「{t}」这件事。",
    "D 助手带受众": "给我讲讲「{t}」，我要拿去给同事看。",
}

# 用户指出的两个形态
OPENING_DECL = re.compile(r"^[^。！？]{0,20}?不[^，。]{1,14}[，、][^。]{0,20}?不[^，。；]{1,14}")
PARALLEL_NEG = re.compile(r"不[^，。；]{1,14}[，、][^。；]{0,20}?不[^，。；]{1,14}")
META_NAV = re.compile(r"这一节|这一段|本文|本节|上文|下文|接下来|下面(?:我们|来|将)|"
                      r"如前所述|前面提到|如上所述|需要注意的是|值得注意")
DECL_ASSERT = re.compile(r"[。；\n]\s*(?:只|而只|这才)[^。]{2,30}。")


def profile(t):
    t = clean(t)
    head = t[:200]
    ps = paragraphs(t)
    ss = sentences(t)
    out = {
        "开场平行否定": len(PARALLEL_NEG.findall(head)),
        "起手式(否定+断言)": 1 if (PARALLEL_NEG.search(head) and
                                   len(PARALLEL_NEG.findall(head)) >= 1) else 0,
        "元文本导航(全篇)": len(META_NAV.findall(t)),
        "元文本导航(开头200字)": len(META_NAV.findall(head)),
        "段首框架句": sum(1 for p in ps if META_NAV.match(p.strip())) / max(len(ps), 1),
        "序数结构词": len(re.findall(r"首先|其次|再次|最后|第一|第二", t)),
        "结论套话": len(re.findall(r"总而言之|总之|综上|由此可见", t)),
        "让步转折公式": len(re.findall(r"[。；\n]\s*不过[，,][^。]{0,30}?(?:仍|还|也)[^。]{0,20}?"
                                       r"(?:面临|存在|需要|有)", t)),
        "字数": len(t),
    }
    if ss:
        L = [len(s) for s in ss]
        out["句长CV"] = st.pstdev(L) / max(st.mean(L), 1e-9)
    if len(ps) > 2:
        ll = [len(sentences(p)[-1]) for p in ps if sentences(p)]
        if len(ll) > 2:
            out["段末句长CV"] = st.pstdev(ll) / max(st.mean(ll), 1e-9)
    # 第一人称
    out["第一人称"] = len(re.findall(r"我(?:们)?", t)) / max(len(t), 1) * 1000
    return out


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    existing = {}
    if (OUT / "results.jsonl").exists():
        for l in (OUT / "results.jsonl").read_text(encoding="utf-8").splitlines():
            if l.strip():
                r = json.loads(l)
                existing[(r["frame"], r["topic"])] = r
    print(f"已有 {len(existing)} 条，待补 {len(TOPICS)*len(FRAMES) - len(existing)} 条")
