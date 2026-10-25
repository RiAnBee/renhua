# 语域内的离散度：AI 是否更集中

多变量离散度＝同一格内文档两两欧氏距离的均值（特征标准化，bootstrap 2000 次）。

| 格 | n | 离散度 | 95% CI |
|---|---|---|---|
| human_formal | 99 | 5.487 | 4.98–5.919 |
| human_informal | 79 | 6.273 | 5.651–6.874 |
| ai_formal | 40 | 3.979 | 3.552–4.199 |
| ai_informal | 40 | 4.398 | 3.932–4.637 |

## 稳健性：样本量不是原因

把人类按与 AI 相同的样本量（每格 40 篇）重复抽样 500 次：

| 语域 | AI 离散度 | 人类 n=40 子样本中位数 [95% 区间] | AI 是否低于区间下界 |
|---|---|---|---|
| formal | 3.979 | 5.459 [4.871, 6.094] | 是 |
| informal | 4.398 | 6.297 [5.675, 6.858] | 是 |

差异不是样本量造成的；**仍无法排除**的是「单一模型 vs 多作者」这一概念性混杂，这一点靠外部检查点研究补强（Kirk 2024；Sourati 2026）。

单变量 IQR 比值（AI/人类）中位数：正式 0.728、非正式 0.552。

| 特征 | 正式 | 非正式 |
|---|---|---|
| sent_len_mean | 0.459 | 0.321 |
| sent_len_cv | 0.76 | 0.481 |
| para_sents_mean | 0.622 | 0.666 |
| p_comma | 0.821 | 0.484 |
| p_period | 0.799 | 0.898 |
| connective_rate | 1.329 | 1.191 |
| sent_initial_connective_ratio | 2.72 | 0.537 |
| hedge_rate | 0.0 | 1.247 |
| booster_rate | 0.0 | 0.53 |
| pronoun_rate | 0.444 | 0.539 |
| de_rate | 1.093 | 0.534 |
| nominalization_rate | 0.858 | 1.104 |
| digit_rate | 0.299 | 0.935 |
| type_token_ratio | 0.687 | 0.563 |
| top50_share | 0.618 | 0.513 |
| unigram_entropy | 0.807 | 0.555 |
| self_repeat_5gram | 0.524 | 0.976 |
| disyllabic_ratio | 0.697 | 0.593 |
| monosyllabic_ratio | 0.87 | 0.521 |
| para_topic_overlap | 0.471 | 0.549 |
