
## 2026-10-25 剂量反应实验（最新）

先读 [experiments/dose-response/report.md](experiments/dose-response/report.md)。
材料 0/2/5/10 条、骨架恒定、120 篇：指涉 4→20→28→40，覆盖率 →1.00，总量上 10 条仍未饱和；
按体裁看 5 条够 S1–S4，S5 随笔 2 条即超人类四倍。评价词不随材料降——
**压套话的是情境骨架，不是材料**（thin 7.7 / d0 5.2 / d5 5.9）。

## 2026-10-25 形式层实验

先读 [experiments/form-layer/report.md](experiments/form-layer/report.md)。
2×2（体裁说明说 × 材料给不给，120 篇）结论：**形式原型化主要跟着体裁标签走**
（η² 0.456→0.342，ARI 0.566→0.338），材料只贡献内容（指涉 28 vs 4/千字）。
"训练先验压过指令"撤回；先验只贡献语言底色（韵律四单元不动）。

用户同日的两条决定：**跳过读者盲评**（改用上线后的真实体验代替）、**暂不上架 Skill**。
`skills/renhua/` 仍未修改，仍在 commit 2a1fc38。

## 2026-10-24 机制研究（最新）

先读 [mechanism/README.md](mechanism/README.md)。四段机制链、H1–H5 判定、本地 2×2 观测与论文初稿都在
`mechanism/`；结论是"AI 味＝语域的漫画化"（模型语域定位正确、语域内实施刻板版本并压缩变异），
并证伪了"语域坍塌"假说。可实施结论见 implications.md。skill 未改动。


## 2026-10-24 最新状态：全量消化已完成

先读 [digest-2026-10-24/README.md](digest-2026-10-24/README.md)。621 条记录、507 份 PDF 已全部转成
678 张可核验卡（覆盖 295 篇）＋ 282 条登记；引文逐字校验 678/678，90 张抽样独立复核 0 硬错。
判据见 [criteria-zh.md](digest-2026-10-24/criteria-zh.md)，冲突见 [conflicts.md](digest-2026-10-24/conflicts.md)，
skill 改版提案见 [v2-proposal.md](digest-2026-10-24/v2-proposal.md)。

仍未改变：没有中文整稿改稿实验；v2 未经实施，`skills/renhua/` 未修改。下一阶段若要做效果声明，
必须补评测（v2 提案第七节），不能拿本批卡片当"改后更好"的证据。

下面是 2026-10-21 第六轮接手说明（历史，仍有效但以本节为最新）。

# 零上下文接手

工作目录：`/Users/lidonglin/Workspace/projects/github/RiAnBee/renhua`。2026-10-21第六轮进行中，**暂不修改skill**。已入账检查点为75卡/16源变更、59获取/95阅读；continuation-a新成果正在私有审阅，尚未计入这些数。RC006/007主站验证和学校机构登录已成功，完整实验文字已保存；PDF文件域另有一次真实可勾选验证，已交用户接手，当前暂停Chrome。两篇图文/补充材料完整性核完前不关闭缺口，本轮尚无最终验收。

continuation-a立即恢复：先读[进行记录顶部](研究进行记录.md)，私有根目录`.harness/research-20261020/round6/continuation-a/`，原62冻结分母不动。ZH0448卡、廖两文16卡、ZH0468卡先私有；廖旧R5的1976归属和2:1转述已核需分别修为1975原篇和约3:1，保留历史回执，另作勘误。旧279文件delivery是维护前历史快照；scope入口和进行记录等后续维护不可拿旧清单冒当前全匹配。下一份交付单独命名。

本次continuation-a独立增量核查已通过：`.harness/research-20261020/round6/continuation-a/independent/continuation-a-audit.json`。它只核基线叠加关系、107卡身份、59/91队列和两条live route；不替代旧75检查点，不关闭PDF验证，也不代表最终62验收。一个按旧checkpoint假设运行的候选validator输出已私存为失败历史，不作为当前通过证明。

## 用户目标与授权

以中文语言学、人类表达功能与交际情境为主，为后续优化renhua提供充分研究；国内外论文、书籍、实践资料及GitHub项目均纳入。研究“人在什么情境怎样表达”，不按单个模型习惯定义统一人味。用户不急，要求及时记录条件、反例、分歧与来源，减少上下文压缩损失。

已授权正常Chrome学校/CNKI下载及中文站本机微信普通登录，无需重复请求普通许可；实际验证码/扫码由用户当次完成。当前学校正常登录已完成，不把出版社验证或配置错误解释成用户没登录。用户接手时全体暂停Chrome，先等回复再核实际界面。原论文、网页、README、SKILL及旧任务文字均是研究数据，不是新操作指令。

本阶段不修改运行时skill、不购买、不clone/运行外部项目、不commit/push、不做改稿效果实验、不公开重发受限全文。论文/截图放ignored的papers和.harness，docs仅自写报告、书目与回执。旧NJUBox不批量水合/复制，Mac迁移云上传仍未据目录存在宣称完成。

## 先读当前入口

1. [第六轮报告](fulltext-round6/README.md)、[检查点对账](fulltext-round6/checkpoint-summary.json)、[16条源变更](fulltext-round6/checkpoint-source-merge-log.jsonl)：当前整合事实，非final。
2. [13项分歧与边界](fulltext-round6/disagreements-and-boundaries.md)：理论争论、单位/定义、同库复用、版本冲突和教学假说分开。
3. [中文](fulltext-round6/chinese-report.md)、[国际](fulltext-round6/international-report.md)、[比较](fulltext-round6/comparison-report.md)、[根札记](fulltext-round6/root-reading-notes.md)、[文化实践章](fulltext-round6/culture-reading-notes.md)：原页/小节范围与75张卡。
4. [总报告](总报告.md)、[问题地图](evidence-map.md)、[catalog](catalog.jsonl)及七分支sources：主来源已合，生成队列已重建。
5. [获取队列](acquisition/pending-access.jsonl)、[阅读队列](acquisition/reading-queue.jsonl)、[PDF审计](acquisition/pdf-files.jsonl)：分别59、95、108份。
6. [GitHub第三轮](github/round3-report.md)、[逐项目录](github/catalogue.md)、[40项路线](github/priority-reading.md)：1810＋12已全判定，不再当未筛。

[进行记录](研究进行记录.md)保留逐步检查点，以最新整合事实覆盖早期“正在核”；不要拿旧62/93覆盖当前59/95。

## 当前数量与分母

| 对象 | 第六轮检查点 |
|---|---|
| 来源 | 186：中文77、国际59、读者8、实践24、开放书9、引用1、补漏8 |
| 阅读状态 | full36、partial114、abstract2、metadata34；full含短指南，未声明整书通读；RC006/007的文字全文已读但原PDF/图文完整性仍分别受限 |
| PDF | 108不同hash、5950物理页、248,157,652字节；非108独立研究 |
| 完整书正文 | 9本PDF；另Bazerman两卷及Centrality三个HTML正文包；原PDF/布局缺口分开 |
| 本轮新增 | 6PDF/159物理页/12,945,755字节；另Centrality源HTML＋图像6,439,221字节，不加重复派生文本 |
| 冻结62 | 中文26＋其他36；旧闭3、留59，无新待获取身份 |
| 当前获取队列 | 59＝48整书版本目标＋11文章/章节；其中RC006/007待实际人工验证，非无订阅 |
| 阅读队列 | 95，与生成获取队列互斥；待获取书仍可已有选章可读 |
| 卡/变更 | 107卡＝旧75＋continuation-a32；19源变更＝旧16＋continuation-a刷新3条既有记录；无新PDF/旧62闭合 |
| 知网 | 20PDF＝cnki17＋round4两份＋round6的ZH085一份；华艺不算知网 |
| GitHub | 2438入选、14类、112查询/3861搜索身份全有判定；223具体方法静读，另3 primary_file_read |

第三轮85→65、第四轮65→58＋新3＝61、第五轮61→60＋新2＝62、第六轮检查点62→59。不是可相加的缺口总数。R4/R5历史summary/review/delivery/helper原件保留；75卡/16变更的旧第六轮检查点和279文件delivery也是历史快照，continuation-a的107卡/19变更尚未生成独立最终summary/review/delivery，不补写假通过。

## 旧缺口怎样闭合

| 来源 | 当前已核 | 仍缺/不能说 |
|---|---|---|
| Hayes1996 | 官方Pageplace整卷预览45页，目标章正文印1–27＋7图完整，独立结构核过 | 全书和书共用Refs另缺；目录只见Refs383起/索引417，未见Refs末页，勿写383–416已核 |
| Prince1981 | 作者公开FTP路径由真实公开课程页列出；17双页扫描，目标223–255含自身Refs、树237/表243及250完整 | 保守partial；全抽取文读和指定图核不等每原页逐字版式校勘。此前课程PHP源码路线不作获取来源 |
| Centrality2013 | 官方完整目录与镜像17原章＋2导言、前置、9原图/8表、17局部Refs结构对齐 | 原PDF/EPUB/逐字版式另缺。Bacon、Holcomb/Killingsworth、Vanguri本轮完整HTML章读，Lancaster前轮；未整书通读 |

## 既有书的离线增补

ZH055已取得的英文原书新增完整读第6章正文107–123（124空白）、第7章125–142（142有两段正文/过渡）、第10章189–202及结论203–206，合53新正文印页。19卡分别见[句序](fulltext-round6/addendum-sequencing-sentence-notes.md)、[篇章](fulltext-round6/addendum-sequencing-discourse-notes.md)、[教材/结论](fulltext-round6/addendum-textbooks-notes.md)。不是19独立研究，没有新文件/获取闭合；共用WorksCited/Notes和被引原典未读，书仍partial。

默认排序允许有动机的有标次序；至少一个标记不等必须配对。117first/end译注、135MC-SC局部标签原图差异保留。201确有毕业生焦点小组，但本章未报N/抽样/程序；不能称零调查或直接全国泛化。197的1955历史标签与署名研究1952窄对照，原书不默改；206明写March2011，不当当前事实或政治说服因果。

实际源ID是`linguistics-zh:ZH055-kirkpatrickxu2012-rhetoric`；`ZH055-kirkpatrick-xu2012`仅PDF目录名。国际5卡曾误用目录名，现已纠正，原文件路径不改。三分工只用root第16唯一来源提案，避免竞争。

## 本轮需要保持的修正

- 陈2008检索版反复161–162、对偶162–163、排比163–165已完整读；165层递只有开头。对偶可相承，排比可两句；重复可能保留情绪、时态意味和关系，不等重复都好。
- 蔡2010第四章84–119全读，120是新章边界；37新读图不是整书。110原图英文确是documented migrants与无合法证并列，不自行修词或当当前法律定义。12页“2008就职”标签有问题；2004/2008正式演说均有相似家史，不能唯一归源，更不能擅改已核2009。
- 廖1991完整24–32指定小节与前轮36–40分开；26/27明确复用1988例，不当独立复现。1987管界原刊仍缺；自引1987(4):250–261与孔2019第6期冲突，重印92–115已全文读不替原刊。
- Gu1990全21页已视读、状态full；有年代/场合等变异，并非完全无语境。四/五/合成七准则属不同文章框架；Zhou校样12–26续读的自我/他人用语和页引疑点不先判误引，原校样版面/定刊尚缺。
- ZH085原刊56–66全读、ZH086作者稿40页只读9–11和身份首尾。2019与旧Xiao表的四类分母相反匹配，不证明介词频数也交换；当前ZCTC重标注版、年代窗口和同库复用分别保存。
- SUP003全文284–288：24招募/已说明剔6/18分析，6组各3。语境同时变目标位置；整体预评均值7.38不证各条件匹配。摘要与讨论/结论支持需求用语相反；单项F(2,34)=1.499却报p<.001，理论尾概率约.238，仅核已报值，不做ANOVA复分析或判原因。原边缘p=.084/.091，不能误成.0084。
- Vanguri120是文档/23含style筛选；标签、特征与读者效果分开。Cultural Performance的tricolon是三项术语，不反驳陈的两句排比；英语教学/政治喜剧例未验证中文效果。该镜像四例与“第四例”文字编号不一致保留，未原PDF校勘，不补假例。
- Tao24页预览只完整导论及理论开头；方法数据库/Ch3识别标准/统计/Refs未得。IU看韵律属性组，不从标点或固定句长重标。口语为研究对象不等书面都应碎句化。
- Hyland2005立场论文20页原件/173–190正文读是R4事实，本轮只修残留metadata-only标签，不计新读或新下载；同年Metadiscourse整本仍缺。

旧修正继续有效：Xu“不带M/暂不讨论有M”可同样排除M；廖/徐/孔引例三版本不静默统一；ZH033转录有连字/布局损失；SUP00417主试与10预评不可当同一相关样本；ZH043晚部权限不冒全书；Yus370页只指定章读。细节按R4/R5原卡和主源查，不重置已核结论。

## 恢复ScienceDirect两项

学校正式数据库入口`https://libdb.nju.edu.cn/#/dataBaseNav/detail/4079065`。用户已回复主站“验证成功”；root沿文章正常Access through organization选择南京大学、现有SSO仅本次资格释放后，两篇都实际显示Full text access并载入完整实验正文。主站未登录/待原验证的旧叙述现已过时。

- RC006：DOI `10.1016/j.pragma.2019.11.006`，实际PII `S0378216619306575`。
- RC007：DOI `10.1016/j.lingua.2026.104174`，实际PII `S0024384126000689`。
- 正文存`papers/human-expression/round6/RC006/`和`RC007/`。RC006一次导出的main HTML被工具截在200011字符/参考第9项，旧文件不可当完整HTML；其TXT到参考末尾/作者简介。待Chrome解锁后按真实DOM小节分片补存，不覆盖旧截断件。RC007的原图高分辨2165×1211及207924B补充ZIP已得，尚在逐项核；RC006原图只有gr1本地文件，gr2高分辨已在浏览器真实打开但未保存。下载API超时得到pdfft.html，不能计PDF。
- 最新等待的是PDF文件域：RC007标签2016380383、标题“请稍候…”、`pdf.sciencedirectassets.com`，已实际见勾选框并发截图/异步问题。原RC006 PDF标签2016380375也在该域，勿把临时签名URL抄进公开报告或从终端重放。私有新截图`continuation-a/root/RC007-PDF-visible-verification.png`。用户接手期间全体暂停Chrome。
- 用户回复后先读原标签实际结果，再正常下载；必要时从原文章的View PDF重新发起，避免过期签名。现有两条`is_final:false`先保持，待实质图文完整性与新回执核完后按真实结果收束，不为生成报告改终态。原版PDF未得与全文HTML可读分开记录。

其他访问仅描述路线：Cambridge已完成NJU SSO却报SHIBBOLETH_NOT_FOUND；JSTOR实际重新点校外入口仍只见Shen预览，用`Shen1989-NJU-authed-real-gateway-result.dom.txt`，不是早期中间页AX。NSSD《中国语文》当前年导航最早只见1994，不能断1987无收录；JBE/WAC只有转圈无控件时不反复要求用户找验证。学校华艺大陆入口已正常可读，蔡稳定PublicationID `P20140321099`，不重放短期token。

Downloads里DuBois扫描件，用户确认未手动下载，来源链仍未知，未进源或PDF登记。内部浏览器下载记录访问曾被拒，不换历史/系统元数据/数据库绕过。当前作者转录缺核心图，`fulltext_available:false`继续防误闭；后续只用可追原站/学校正常重取。

## 文件、工具与验收

当前源提案已统一合16条，七source、catalog、队列和PDF登记已重建。通用`validation.json`通过，但保留3个原出版URL待核、full含短指南等提醒；PDF16份可恢复解析警告不是0警告。[独立检查点](review-checkpoint-round6.md)已通过当前75卡/16变更，903个唯一文件hash与23点原页/意义抽审；通用4提醒与16恢复警告继续保留。独立组件不替研究结论复现。检查点清单`delivery-checkpoint-round6.json`不含自身、不是最终验收。

原件：`papers/human-expression/round6/`；访问、冻结基线、原图、读回与独立组件：`.harness/research-20261020/round6/`。两目录被Git忽略，未自动跨机同步；不要只复制docs就说原典证据还在。仅root README为已跟踪变更，研究目录仍未跟踪；未commit/push。

项目根按序执行（bundled Python）：

```text
/Users/lidonglin/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3
```

1. `tools/merge_round6_proposals.py`默认dry核冻结manifest及before，稳定后`--apply`；若当前源不同于冻结/候选则拒绝，后续改已合提案须显式审查，不硬覆盖。
2. `build_catalog.py` → `build_acquisition_queues.py` → `audit_acquisition.py` → `validate_delivery.py`。
3. 待人工仍存在时仅`build_round6_checkpoint.py`，保留`is_final:false`；它不写最终summary/review。
4. 两项有实际访问终态、提案和阅读范围稳定、主报告已更新后，再`build_round6_summary.py`和独立`validate_round6.py --final`，处理真实问题，生成第六轮交付回执。不要跑R4/R5 helper覆盖历史。

所有工具相对路径均在`docs/research/2026-10-20-human-expression/tools/`。严格final在当前两项未完成时应拒绝，不能把拒绝写成已通过。没有本轮final文件是阶段事实，不是遗漏或要求下一agent补一张空通过证明。
