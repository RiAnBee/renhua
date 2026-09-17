---
description: 清理中文文本里的 AI 味（只做减法：删零信息句、说教式评论、修辞超载）
argument-hint: [文件路径或直接粘贴文本]
---

清理下面这段中文的 AI 味。

**执行前必做**：

1. 先读 `skills/renhua/SKILL.md`（三条硬边界 + 四道闸门 + 六条规则 + 输出契约）
2. 再读 `skills/renhua/references/counterexamples.zh.md`（反例门，改写前必读）
3. 只有在不确定该不该改某处时，才读 `references/no-touch.zh.md`
4. 只有在用户追问依据时，才读 `references/evidence.md`

**不要一次读完所有 references。**

**必须遵守**：

- 动作只有 **删 / 合并 / 移 / 还原**，禁止「添加」
- 每条改动都要能指到规则号
- 语域没判定清楚时默认不改
- 不要输出 AI 味评分，不要调用检测器

**必须输出**：改写稿 + 改动台帐 + 不动清单 + 需要用户补的 + 未触发。

---

待处理内容：

$ARGUMENTS
