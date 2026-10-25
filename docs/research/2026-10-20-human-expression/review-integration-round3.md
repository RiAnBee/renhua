# 第三轮获取与整合工具独立复核

复核快照：2026-10-20 21:00 左右；此后新增资料由主任务重建。没有修改中文来源卡、主报告、HANDOFF 或 skill。

## 当前文件与范围核对

- `build_catalog.py`：176 卡，full 26 / partial 80 / abstract 12 / metadata 58；7 分支，无重复ID或无效URL错误。只保留 ZH036 原刊URL未确认的既有警告。
- `build_acquisition_queues.py`：74 个记录待取全文，其中国际37、中文33、开放书1、阅读加工2、补充1；完整书待取48。RC007虽已读公开引言与片段、状态partial，仍正确留在全文缺口中。
- `audit_acquisition.py`：73 PDF、73唯一哈希、4,819物理页、187,059,009字节；无未关联文件/解析失败。11文件有可恢复解析警告，记录不删除。
- 完整开放整书8个记录：open-books分支7本与中文ZH055。以明确 `full_book_obtained=true` 且实际PDF关联的source ID计，不按标题或所有book类型计。当前8个ID也对应8个不同文件；样章没有混入。
- ZH021为一篇完整EPUB论文，881,103字节；不是第9本书，不增加PDF页数。ZIP mimetype、OPF题名、3项spine和源卡哈希一致。

逐项复算 ZH003/021/029/032/055/060/075-cui 的文件哈希及字节，均与源卡一致。PDF物理页分别11、112、35、231、18、33；ZH021为EPUB。ZH029的112页是整期，已视觉核查物理34页题名作者与物理42页参考文献/英文摘要，目标文章只占34–42的9页，源卡已正确区分。ZH003提取乱码按原卡保留视觉阅读边界。旧ZH075-liao与新ZH075-cui的完整ID不同，未混为一条。

## 修正的两个工具问题

1. **EPUB关联崩溃，已修。** `validate_delivery.py` 直接对 `files` 每项调用 `.get()`，遇到旧卡的字符串路径时实际触发 `AttributeError`。增加统一迭代器，兼容路径字符串和结构化记录；在当前完整数据上重跑不再崩溃，EPUB哈希/类型核验通过。裸字符串若用于EPUB仍须补哈希，不能因兼容解析而跳过文件验证。
2. **上一轮GitHub绿色不能代表本轮完成，已补门槛。** 旧GitHub validation还只有1440索引与旧核心队列绿色。总验证现按GitHub owner约定，另查本轮1810及12的expected/reviewed、两个disposition_complete、剩余0及identity_errors空。合并前总passed为false，错误全部是GitHub本轮字段尚未交付；文献计数/关联/139条本地Markdown链接在该快照无误。最终须由主任务在GitHub合并后重跑，不能引用修复前的总绿色。

原始复核数据在 `.harness/research-20261020/round3-integration-audit/`，含 `new-document-checks.json`、两张ZH029定位图及修复前验证脚本。总检查只验证已保存结构与一致性，不证明全网搜尽、全文通读、来源结论真实或编辑有效。
