# 可分性与跨语域迁移（来源=人/AI）

正式 140 篇、非正式 122 篇；5 折分层交叉验证 AUC。

| 特征族 | 正式内 | 非正式内 | 合并 | 正式→非正式 | 非正式→正式 |
|---|---|---|---|---|---|
| M5_rhythm | 0.92 | 0.952 | 0.852 | 0.698 | 0.525 |
| M4_stance | 0.709 | 0.589 | 0.596 | 0.52 | 0.376 |
| M3_reference | 0.846 | 0.841 | 0.788 | 0.736 | 0.547 |
| M2_infostructure | 0.785 | 0.539 | 0.664 | 0.535 | 0.744 |
| H1_typicality | 0.784 | 0.44 | 0.63 | 0.446 | 0.409 |
| M1_register_legit | 0.777 | 0.717 | 0.657 | 0.568 | 0.625 |
| ALL | 0.97 | 0.948 | 0.937 | 0.786 | 0.65 |

## 方向稳定性：19/28 个特征在两语域同向

| 特征 | 正式内差(ai-human) | 非正式内差 | 同向 |
|---|---|---|---|
| sent_len_mean | -9.47 | -44.611 | 是 |
| de_rate | -3.522 | -9.08 | 是 |
| nominalization_rate | -2.319 | -1.668 | 是 |
| connective_rate | 1.469 | 1.698 | 是 |
| pronoun_rate | -0.835 | -0.757 | 是 |
| booster_rate | -0.536 | 0.072 | **否** |
| p_comma | 0.464 | -0.275 | **否** |
| para_sents_mean | 0.436 | -0.049 | **否** |
| p_period | 0.379 | 1.117 | 是 |
| first_person_pl_rate | -0.355 | -0.149 | 是 |
| digit_rate | -0.247 | -0.03 | 是 |
| bei_rate | -0.206 | 0.247 | **否** |
| hedge_rate | -0.179 | 0.515 | **否** |
| unigram_entropy | 0.138 | 0.003 | 是 |
| p_dunhao | 0.132 | 0.195 | 是 |
| p_semicolon | 0.109 | 0.351 | 是 |
| sent_len_cv | -0.08 | 0.042 | **否** |
| top50_share | -0.071 | -0.001 | 是 |
| type_token_ratio | 0.061 | -0.008 | **否** |
| sent_initial_connective_ratio | 0.054 | 0.005 | 是 |
| second_person_rate | -0.046 | -1.65 | 是 |
| p_question | -0.041 | 0.112 | **否** |
| para_sents_cv | 0.027 | 0.004 | 是 |
| adjacent_topic_continuity | -0.021 | -0.008 | 是 |
| para_topic_overlap | -0.02 | -0.003 | 是 |
| disyllabic_ratio | 0.006 | -0.006 | **否** |
| monosyllabic_ratio | 0.004 | 0.027 | 是 |
| self_repeat_5gram | -0.004 | -0.002 | 是 |
