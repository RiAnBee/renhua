#!/usr/bin/env python3
"""Render the blind-review forms as standalone HTML (no scripts, no network)."""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKT = HERE / "packet"

TEMPLATE = """<!doctype html>
<html lang="zh"><head><meta charset="utf-8"><title>盲评表 {form}</title>
<style>
body{{font-family:-apple-system,"PingFang SC",serif;max-width:760px;margin:40px auto;line-height:1.9;color:#222}}
.item{{border-top:1px solid #ddd;padding:22px 0}}
.text{{white-space:pre-wrap;background:#fafafa;padding:14px;border-radius:6px}}
.q{{margin:10px 0}}
label{{margin-right:14px}}
input[type=number]{{width:64px}}
textarea{{width:100%;height:38px}}
.hint{{color:#666;font-size:13px}}
</style></head><body>
<h2>阅读判断（第 {form} 份，共 12 份）</h2>
<p class="hint">请逐条读完再看问题。本表只问"这段文字像不像有人在具体场合写的"，不问写得好不好。
每条约 1 分钟，共 20 条。做完请把本页另存或截图回传，或把答案填进同名 CSV。</p>
{body}
</body></html>"""

ITEM = """<div class="item" id="{bid}">
<div class="hint">{bid}</div>
<div class="text">{text}</div>
<div class="q">1. 情境感（0=完全像范文，100=像真有其事）：
  <input type="number" min="0" max="100" name="{bid}_score"></div>
<div class="q">2. 如果必须选：
  <label><input type="radio" name="{bid}_choice" value="a"> (a) 有人真的为这件事写的</label>
  <label><input type="radio" name="{bid}_choice" value="b"> (b) 按体裁写出来的范文</label></div>
<div class="q">3. 指出一处（选一个）：
  <label><input type="radio" name="{bid}_pick" value="concrete"> 最具体的一处</label>
  <label><input type="radio" name="{bid}_pick" value="empty"> 最空的一处</label>
  <textarea name="{bid}_quote" placeholder="把那一处的原文抄 4 字以上"></textarea></div>
</div>"""


def esc(t: str) -> str:
    return (t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def main() -> int:
    items = {i["blind_id"]: i for i in json.loads((PKT / "items.json").read_text())}
    forms = json.loads((PKT / "forms.json").read_text())
    for f in forms:
        body = "\n".join(ITEM.format(bid=bid, text=esc(items[bid]["text"])) for bid in f["items"])
        (PKT / f"form-{f['form']:02d}.html").write_text(TEMPLATE.format(form=f["form"], body=body))
    print("wrote", len(forms), "forms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
