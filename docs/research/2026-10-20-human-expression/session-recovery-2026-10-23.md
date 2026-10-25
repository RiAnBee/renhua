# Codex 会话成果收口（2026-10-23）

本次工作接手 Codex 桌面端的同名会话，核实它到底做出了什么、哪些内容真的落到了本机，然后把缺口接着做下去。本文只记录**已实测**的状态；研究结论本身在[总报告](总报告.md)和各分支卡片里，这里不重复。

## 一句话结论

论文确实下载到了本机：`papers/` 下 108 份 PDF 全部存在，逐份 SHA-256 与登记清单一致，共计 5,950 物理页、248,157,652 字节（2026-10-23 复验）。研究产出也已落盘成 186 条来源、107 张阅读卡、14 类 GitHub 项目判定。**没做完的是获取侧**：59 条待获取记录（48 本书的准确版本 + 11 篇文章/章节），以及 RC006/RC007 两篇 ScienceDirect 原文的出版社 PDF 域验证。

## 会话身份与跨度

| 项 | 值 |
|---|---|
| 标题 | renhua 补充调研外部资料 |
| 线程 ID | `01a158cf-8176-70d2-91bc-765ee1d434d5` |
| 会话文件 | `~/.codex/sessions/2026/10/20/rollout-2026-10-20T18-15-56-01a158cf-…jsonl`（136 MB） |
| 派生分支 | `01a158d0-b7cb`、`01a158d0-ec00`、`01a158d1-1ed4`（中文、国际、GitHub 三条并行研究线） |
| 实际内容跨度 | 2026-10-20 18:16 — 2026-10-21 04:19（北京时间），约 10 小时连续运行 |
| 结构 | 15,600 条事件；45 条用户消息；399 条助手结论；11,532 次工具调用 |

会话内用户提出的两条原始目标（后续所有轮次都在这两条下推进）：

1. 深度调研中文与国外语言学、书籍、博客与研究文献，**先把资料全部下载到本地**，之后统一分析；
2. GitHub 上的同类去 AI 味项目**不下载**，但要写一份逐项目分类分析的调研报告，供后续无上下文 agent 使用。

会话末端没有改 `skills/renhua/`，也没有 commit/push。这一点在后续轮次里一直保持。

## 已经核实落盘的东西

| 资产 | 位置 | 实测状态 |
|---|---|---|
| 论文/书籍 PDF | `papers/`（298 MB） | 108 份，清单登记 108 份，缺失 0，SHA-256 不一致 0，5,950 页 |
| 私有原件与原件证据 | `.harness/research-20261020/`（511 MB） | 含第六轮原页截图、冻结基线、独立审查组件 |
| 研究正文与索引 | `docs/research/2026-10-20-human-expression/`（22 MB） | 186 条来源、107 张阅读卡、7 个分支报告、6 份轮次验收 |
| GitHub 项目库 | `github/` | 2,438 项入选、14 主类、112 条查询、3,861 个搜索身份全部有判定；`github/validation.json` 通过 |
| 获取与阅读队列 | `acquisition/` | 待获取 59、已有材料待读 91（互斥） |
| 知网 PDF | `papers/human-expression/cnki/` | 20 份，另有平台回执 |

其中 `papers/` 与 `.harness/` 被 `.gitignore` 排除，只在本机。`docs/research/` 尚未被 git 跟踪；这是会话结束时的实际状态，不是遗漏。

## 从 `/tmp` 收拢的临时证据

会话在 `/tmp` 下留了 358 个文件、6.8 MB 的中间证据（各轮国际分支抓取、GitHub 研究缓存、中间脚本、审计输出）。`/tmp` 会被系统清理，已整体复制到：

`.harness/research-20261020/tmp-evidence-20261023/`

包括 `renhua-round4-international/`、`renhua-round5-international/`、`renhua-round6-international/`、`renhua-continuation-a-international/`、`renhua-github-research/` 与零散脚本/审计 JSON。原件未删除，路径可回溯。

## 会话结束时仍未完成的部分

| 缺口 | 现状 | 为什么没关掉 |
|---|---|---|
| 59 条待获取 | 48 本书的准确版本 + 11 篇文章/章节；45 条仍在"要拿到整书"这一档 | 出版社付费墙、学校阅读器只给试读、知网需登录态；自动路线已穷尽 |
| RC006/RC007 出版社 PDF | 正文 HTML/TXT、图表、补充材料已存；原版 PDF 卡在 `pdf.sciencedirectassets.com` 的独立真人验证 | 验证码必须由用户当次操作，会话中途用户已休息 |
| 第六轮 final 交付 | 只有 `is_final:false` 的检查点 | 上两项未关，不生成假通过 |
| 整书通读 | 12 本完整书，均为 partial | 研究范围就是"读指定小节 + 记条件与反例"，不冒充全书 |

## 接手顺序

1. 本文 → [HANDOFF.md](HANDOFF.md)（零上下文交接，含所有既有修正）
2. [第六轮入口](fulltext-round6/README.md) → [13 项分歧与边界](fulltext-round6/disagreements-and-boundaries.md)
3. [catalog.jsonl](catalog.jsonl) / [acquisition/pending-access.jsonl](acquisition/pending-access.jsonl) 取机器可读状态
4. 本轮新增获取结果见 `acquisition/round7/`

## 本轮（2026-10-23）新增

- 新建可复用获取工具：`tools/oa_acquire.py`（逐条 OA 探测 + 下载 + 回执）、`tools/doaj_sweep.py`
  （DOAJ 期刊扫库，含 OJS/MDPI/PLoS 链接推断）、`tools/literature_sweep.py`（OpenAlex 路线，
  当前因限流停用）、`tools/register_round7.py`（只从文件本身复算页数与散列再登记）。
- 62 条待获取记录逐条探测：**0 条**拿到目标正文；2 份同类文献被判不是该书并隔离。
- DOAJ 扫库新增 39 条来源（全部 `read_status: metadata`，未读），剔除 7 份不可核读件；
  逐条主题索引见 `acquisition/round7/index.md`。
- 校验后当前清单：225 条来源、147 份 PDF、6,607 物理页、284,734,757 字节，
  `validate_delivery` 通过；待获取 59、待读 130。
- 中文线卡在知网滑块验证，按规则不绕过；解锁后的批次清单在 `acquisition/round7/README.md`。

后续轮次的数字以 `acquisition/pdf-files.jsonl`、`catalog-summary.json` 与 `acquisition/round7/`
回执为准，不以本文快照为准。
