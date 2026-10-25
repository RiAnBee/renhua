# 可分性与跨语域迁移（来源=人/AI）

正式 140 篇、非正式 122 篇；5 折分层交叉验证 AUC。

| 特征族 | 正式内 | 非正式内 | 合并 | 正式→非正式 | 非正式→正式 |
|---|---|---|---|---|---|
| M5_rhythm | 0.922 | 0.961 | 0.911 | 0.782 | 0.788 |
| M4_stance | 0.721 | 0.622 | 0.612 | 0.514 | 0.34 |
| M3_reference | 0.846 | 0.807 | 0.81 | 0.724 | 0.713 |
| M2_infostructure | 0.752 | 0.443 | 0.613 | 0.493 | 0.734 |
| H1_typicality | 0.784 | 0.468 | 0.627 | 0.443 | 0.438 |
| M1_register_legit | 0.777 | 0.725 | 0.66 | 0.575 | 0.633 |
| ALL | 0.978 | 0.953 | 0.949 | 0.852 | 0.835 |

## 方向稳定性：18/28 个特征在两语域同向

| 特征 | 正式内差(ai-human) | 非正式内差 | 同向 |
|---|---|---|---|
| sent_len_mean | -8.749 | -9.912 | 是 |
| de_rate | -3.681 | -9.488 | 是 |
| connective_rate | 2.583 | 1.403 | 是 |
| nominalization_rate | -2.319 | -1.601 | 是 |
| pronoun_rate | -1.772 | -1.636 | 是 |
| booster_rate | -0.667 | 0.096 | **否** |
| p_comma | 0.464 | -0.334 | **否** |
| para_sents_mean | 0.436 | -0.057 | **否** |
| p_period | 0.379 | 1.048 | 是 |
| first_person_pl_rate | -0.355 | -0.148 | 是 |
| bei_rate | -0.281 | 0.203 | **否** |
| digit_rate | -0.247 | -0.038 | 是 |
| hedge_rate | -0.223 | 0.554 | **否** |
| unigram_entropy | 0.138 | -0.012 | **否** |
| p_dunhao | 0.132 | 0.181 | 是 |
| p_semicolon | 0.109 | 0.343 | 是 |
| sent_len_cv | -0.075 | -0.074 | 是 |
| top50_share | -0.071 | 0.002 | **否** |
| type_token_ratio | 0.061 | -0.006 | **否** |
| sent_initial_connective_ratio | 0.052 | 0.006 | 是 |
| second_person_rate | -0.046 | -1.679 | 是 |
| p_question | -0.041 | 0.1 | **否** |
| para_sents_cv | 0.027 | 0.006 | 是 |
| para_topic_overlap | -0.02 | -0.003 | 是 |
| adjacent_topic_continuity | -0.014 | -0.001 | 是 |
| disyllabic_ratio | 0.006 | -0.006 | **否** |
| monosyllabic_ratio | 0.004 | 0.027 | 是 |
| self_repeat_5gram | -0.004 | -0.002 | 是 |
