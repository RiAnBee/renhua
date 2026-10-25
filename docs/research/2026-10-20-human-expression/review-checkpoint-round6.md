# 第六轮检查点独立核验

本检查点静态检查：通过。本轮尚未最终验收，不能据此称62项全终态或全部全文已取得。

冻结62项（中文26、其余36）；当前终态60/62；待人工记录：reading-cognition:RC006、reading-cognition:RC007。

当前核75卡、186来源；新注册PDF6份/159页；原62闭3、留59。这是实际当前文件口径，非预定数量。

检查点摘要33个字段、16条来源变更的字段与前后散列逐项相符；核903个不同文件散列、415条本地Markdown文件链接。补充路线7条，仅作实际访问证据，不增调查目标或取得数。

独立人工抽审23点；全部当前闭合身份已有原件结构核。原页修正与范围见[JSON](review-checkpoint-round6.json)。

通用文件校验另保留4条范围/书目提醒；PDF登记中16份有解析器可恢复警告。本工具的静态错误数不抹去这些上游提醒。

## 人工发现与已修问题

- 完整镜像书体是否齐TOC/前置/图表/本地参考，不能用自报complete或末句索引代替实际结构。 实际核WAC19条与镜像17署名章+2导言、25原书组件、前置身份/版权、全部9原图和8表、本地17章References及实际源字节6439221。完整镜像正文可闭，未获PDF/EPUB、未原PDF逐字版式对照、未全书语义读；镜像18末搜索摘只辅证。曾发现主receipt引用旧manifesthash/size，国际已修60277B/6a653...，123内容hash重核通过。
- Centrality图片获取的十条短期签名重定向URL进入公开状态记录。 首次静态检查实际识别international-status的attempts41–50 final_url有Expires/Signature/Key-Pair-Id；国际分支获root批准后仅公开去query并说明，完整请求与响应保留private，未改已核图片/HTML/PDF、manifest、来源提案或获取计数。复验按当前字节检查，不将旧失败记录覆盖为从未有问题。
- 审查者误把PDF目录名ZH055-kirkpatrick-xu2012当来源ID，曾把正确中文/root卡误报为错误。 root指出后直接重核冻结sources、当前sources及catalog三原行：真实来源ID都是linguistics-zh:ZH055-kirkpatrickxu2012-rhetoric，目录名仅文件定位。本agent明确撤回错误建议并通知中文保持原14卡；国际5卡原使用目录式ID，现由作者改为真实来源ID且回执/manifest同步。未改原PDF、未制造新书目、未把人工判断作为身份校验例外。

Hayes仅闭目标章正文，书共用参考另缺；Prince闭包含自身参考的目标章，均不计整本书。Centrality闭实质HTML书正文，原PDF/EPUB和版式仍缺。ZH055新增指定三章及结论的阅读保留partial，不因53正文页或19卡称整书通读。

## 当前错误

无当前静态错误。

## 最终验收仍待

- investigation_still_pending：reading-cognition:RC006: in_progress
- investigation_still_pending：reading-cognition:RC007: in_progress
- strict_round6_final_summary_not_accepted_at_checkpoint：Final62-terminal summary and strict merge log are not substituted by checkpoint counts.
- two_live_routes_then_formal_final_integration_and_readback：Current checkpoint entries are integrated. Await the two actual access outcomes, then update any resulting proposals/files/queues and formal summary before an explicitly requested final audit; no review-final-round6 pass is emitted.

本工具未修改主来源、获取/阅读队列、运行时或第四/五轮历史；也未运行或写入最终验收。
