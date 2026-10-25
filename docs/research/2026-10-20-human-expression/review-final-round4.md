# 第四轮独立静态验收

结果：通过。校验身份、终态、字段保留、文件与散列；不证明调研穷尽、原文真实性或编辑效果。

| 范围 | 检查结果 |
|---|---|
| 冻结身份 | 65项：中文24，其余41；基线散列锁定 |
| 调查终态 | 65/65；身份相符=True |
| 经典阅读 | 4本，41卡；按所读页及证据核对，非全书通读 |
| 新PDF | 13份；逐项回执、来源、大小、散列、magic |
| 完整正文HTML | 2包；另核目录/章节/前后附属材料及图像，不当原版PDF |
| 冻结文件缺口 | 仍在队列58项；调查终态不等于全部取得 |
| 运行时 | skills/commands/plugin/scripts/evals相对HEAD无改动，或错误列表明确列出 |

受限材料的公开目录检查只覆盖二进制原件/扫描图、会话查询键与长段精确复制。推论归属和版权边界仍需结合人工阅读记录。

## 错误

无。

## 独立原页抽审与已修问题

- `XU-318-attribution`（corrected_verified）：初稿把先代词后姓名直接归为作者对悬念的分析；318页只明确根节点后指。 报告、卡05及来源更新提案已把悬念/揭示体验归本项目推论；读回确认。
- `XU-322-zero-reference`（supported_verified）：核查零形也可指车辆是否为原书脚注明示。 脚注明确可看作汽车；卡07保留另解，未把人物还原当唯一答案。
- `XU-355-357-cultural-bridge`（supported_with_limits_verified）：核查跨层省略是否被泛化为必补全部常识。 原书以显著性解释打印机省墨盒，以西方村庄/教堂知识及缺关键层解释烛台例；卡13保留文化、受众与非直接试验限制。
- `ZF-006-topic-vs-subject`（corrected_verified）：初稿把a句句法主语中国人的婚姻误写为两句共同篇章话题。 6页明确篇章话题均为中国人；报告和卡03已改为句法首层主语不同、篇章话题同为中国人，读回确认。
- `ZF-edition-and-section-scope`（supported_verified）：核查1996版身份及§1.1/1.2完整边界。 版权图可见1996年4月第1版第1次印刷、ISBN7-5392-2683-8；4页起§1.1、5页起§1.2、7页后段起§1.3，截图覆盖全部相关正文。未据此声称读过2014版或全书。
- `XU-prior-page-24`（clarified_verified）：前阶段24页局部这一措辞可能误当24个页的阅读量。 来源更新提案已明写第24页的局部阅读。此项只核记录表述，未在本轮重新视觉阅读24页。
- `ZH012-received-vs-publication`（corrected_verified）：初稿把2005收稿/搜索日期当相关论文发表年。 原刊表格与官方作者表支持2006发表、2005收稿；中文报告/status已修并读回，不用论文替代2008专书。
- `ZH033-transcription-not-original-PDF`（supported_with_quality_limits_verified）：结构完整转录是否可能被误称原版PDF或精确金标准。 已核155原行连续、正文至附录A–F/参考尾；独立读方法/词汇指标/讨论。fi/ff连字丢失、断词、工具页脚标记、图表布局缺失已明列；只是完整正文转录，阅读partial。
- `ZH043-late-chapter-vs-full-book`（supported_with_limits_verified）：结语及参考可读是否被推为全书逐页权限或整书已取得。 独立读原UI结语6033字符（含重复）、参考开头及两张原阅读器截图，4文件大小/hash符。记录仅晚部章节可读，online_full_book_available=null，本地整书仍缺。
- `ZH034-ERIC-and-new-route-labels`（corrected_verified）：ERIC1965草稿及新核官方机构页等措辞超出本轮证据。 ERIC仅日期1965、Pages1和摘要，关系未核；中文已修。ZH056明确北大链接为既有入口、本轮实际公开检索；ZH074不据界面导航数断全书章节。
- `INTL-Hyland-methods-and-limits`（supported_verified）：检索词表、学科频率是否被当中文编辑准则或质量配额。 独立核177–178/187/189–190并视核两页：240篇8学科/逐例判功能、隐含评价难恢复、工程提问反例及章节定位限制均有据；不是中文重写因果实验。
- `INTL-Bazerman-two-volume-body-identity`（supported_with_metadata_conflicts_verified）：完整HTML正文、原版PDF、部分精读与出版社元数据是否混称。 核卷1title/copyright/原书Contents、卷2copyright及两manifest；又核WAC完整HTML目录有12/11章、两卷均明列2013-08-17。漏卷1第11章及2014只归Parlor短搜索缓存（作者书单也2014）；卷2无单独原书Contents叶，依据WAC目录/镜像索引与正文，不冒称取得。完整HTML不当原PDF。
- `INTL-Bazerman-revision-and-terminology`（supported_with_transfer_limits_verified）：作者修订及规范资源论是否被扩成受托编辑任意增写或专业词一律通俗化。 独立通读卷1Chapter11、卷2Chapter8；作者增资料/改意义不等于受托保义权限，化学术语与正式规范有实际约束，教育效果只是章节引用二手研究。
- `XU2005-original-exclusion-scope`（supported_verified）：书347与2005论文的否定范围是否可仅截取只讨论判反转。 独立视觉读2005印195–197及书346–347；原论文暂不讨论有M、书只讨论不带M均可排除M，孔亦承认可含原意。保留上位清单/措辞安排张力，不断理论范围完全反转。
- `LIAO-reprint-vs-critic-quotation`（source_conflicts_preserved_verified）：孔文原文校正能否直接替代所见引文，是否已经查到1987原刊。 独立视觉核1992版权及92–94/110–111/115六页。94未见胡萝卜素，制裁例有了也有的；111标题管界终止，115原载1987第4期，与1991自引同、与孔第6期冲突。原刊未见，重印不等于刊本逐字同；8补充卡及四来源提案保留此边界。
- `YUS-recovered-full-book-PDF`（structure_and_identity_verified）：验证恢复后的实际PDF是否为正确整书，而非再次书目/章节命中。 独立核370页、7264283字节及SHA；视觉版权p5证2011/KU/CC BY-NC-ND4.0、目录末叶p11和末封370。逐章标题锚点1–8、参考297–342、姓名/主题索引至353齐；只核结构与身份，未把文件完整当全书通读。
- `YUS-email-register-and-evidence`（selected_argument_supported_verified）：邮件是否统一口语化、表中无明显差异是否被当统计等效或中文验证。 独立读230/231/236/237：作者与引用者保留体裁分歧，约定语步仍可有个体差异；表6.1二手转述的连接成分无dramatic differences非等效、名词化例少无结论；任务和权力关系制约正式度。新卡保留2011/非中文迁移、未追原研究及未读第7章的限制。

## 保留事项

无额外静态告警。

本验收不编辑来源卡、生成目录、获取队列或运行时skill；结构化明细见[JSON](review-final-round4.json)。
