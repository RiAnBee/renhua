# 语域轴投影：AI 有没有写错语域

轴由**人类**两语域的均值差定义；正值=更接近人类正式，负值=更接近人类非正式。

| 格 | n | 中位数 | 四分位 | 落在正式侧的比例 |
|---|---|---|---|---|
| human_formal | 100 | 1.461 | 0.681–1.925 | 0.95 |
| human_informal | 82 | -1.204 | -1.931–-0.592 | 0.073 |
| ai_formal | 40 | 0.9 | 0.48–1.137 | 0.925 |
| ai_informal | 40 | -1.601 | -2.12–-1.212 | 0.0 |

AI·非正式的中位数距人类正式 3.062，距人类非正式 0.397。

轴权重（越大越偏正式）：

- sent_len_mean: 0.488
- para_sents_mean: 0.453
- monosyllabic_ratio: -0.389
- second_person_rate: -0.378
- connective_rate: -0.305
- p_dash: -0.257
- de_rate: -0.212
- p_question: -0.182
- sent_initial_connective_ratio: -0.159
- disyllabic_ratio: -0.008
