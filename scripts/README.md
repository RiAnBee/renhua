# 研究脚本

这些是维护者的论文与语料研究工具，**不是新版skill的运行依赖，也不是自动改稿或效果验收器**。脚本中的A1/A3等旧编号、触发阈值与“稳健／无差异”标签对应当时的探索协议，不恢复旧的编辑规则。

当前编辑合同见 [SKILL.md](../skills/renhua/SKILL.md)，当前评测见 [evals/README.md](../evals/README.md)，历史数据解释见 [研究存档](../docs/research/evidence-history.md)。

## 论文检索与下载

```bash
python3 scripts/fetch_papers.py sweep
python3 scripts/fetch_papers.py download
python3 scripts/fetch_papers.py download --id 2604.03136
```

下载依据候选池中的筛选状态；先确认记录再下载。`sweep`、筛选与合并工具在 `.harness/` 写候选与筛查记录。PDF与可用的TeX源码保存在 `papers/<id>/`，不入库；无源码的论文不能伪造源码。

论文检索脚本使用Python标准库及`curl`等外部命令；具体参数见脚本帮助。论文的数量不等于当前编辑方案的效果证据。

## 旧语料的采集与特征探索

```bash
python3 scripts/collect_corpus.py probe
python3 scripts/collect_corpus.py crawl <入口URL> <目标篇数>
python3 scripts/collect_corpus.py stats
python3 scripts/analyze_corpus.py
python3 scripts/stats_corpus.py
```

`analyze_corpus.py`读取已有语料并计算特征，**不会自动生成AI对照稿**。它和统计脚本会覆盖相应 `.harness/` 结果文件；需要保留历史时先另存输入与结果快照。

`corpus/formal`与`corpus/informal`是历史目录名，实际来源为新闻与技术博客，不等于所有正式／口语中文。抓取全文版权归原作者，`corpus/`不入库。

其他脚本：

| 文件 | 历史用途 |
|---|---|
| `false_positive.py` | 旧规则的机械形态触发代理；触发率不等于编辑损害率 |
| `ling_features.py` | 词汇与欧化表达候选特征探索 |
| `coord_phrases.py`、`syntax_features.py` | 并列、依存句法及句长分层比较 |
| `zh_pos_features.py`、`prosody_features.py` | 词性与韵律代理特征探索，部分需要本地jieba/spaCy资源 |
| `persona_experiment.py` | 历史姿态／文体实验的材料与结果处理 |

这些脚本不随skill安装，也没有因本轮重构新增依赖。需运行时先读相应入口与依赖；不要为了普通改稿安装NLP模型。

## 怎样解释输出

- 区分汉字数、Unicode字符数与分词后词数。现有部分指标使用`len()`，不能一概叫汉字。
- 对语体、来源、长度与测量算子做检查；完整文档编辑不使用硬截断窗口。
- 单项显著性、频率差异和语料分类能力不是改稿收益；多重比较、同文相关性和探索性筛选均影响解释。
- 未复现不等于证明不存在；自己的窄语料也不能否决其他任务的研究。
- 检测器命中、编辑动作、保真损害、读者偏好分别测量。需要评价新版时按完整文档协议运行，不把旧脚本改个名字当新评测。
