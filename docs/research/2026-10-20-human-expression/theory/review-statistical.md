# Statistical adversarial review of C1–C3

**Scope.** I reran the analyses from the raw text files rather than trusting the saved feature table. The implementation imports `human_model.py` and reuses its 21 feature definitions (`feats`, `FEATURE_KEYS`), `clean`, and CJK-count `window`; the independent runner was `/tmp/adversarial.py` (results retained in `adversarial_results.json`). Human has 60 documents (12 per S1–S5), v1 60, v2 57 (S2 has 9), and v3 60. All reported AI–human comparisons use the same available documents per batch.

## 1. Feature-set dependence

Statistics are mean per-feature eta-squared, mean leave-one-out silhouette, and mean within-genre pairwise Euclidean distance after within-dataset feature standardization. Values below are `(human; v1, v2, v3)`.

| feature set | eta² mean | silhouette | within distance | verdict |
|---|---:|---:|---:|---|
| all 21 | 0.232; 0.315, 0.358, 0.617 | −0.014; 0.174, 0.170, 0.670 | 5.352; 3.950, 4.073, 1.414 | **pass** |
| syntactic/rhythm 8 (`sent_len`, `sent_cv`, `para_cv`, `connective`, `sent_initial_conn`, `formula`, `condition`, `negation`) | 0.240; 0.320, 0.504, 0.961 | −0.062; 0.065, 0.204, 0.760 | 3.189; 2.777, 2.684, 0.660 | **pass** |
| lexical/reference 8 (`eval`, `digit`, `year`, `time`, `quote`, `inst`, `ttr`, `entropy`) | 0.226; 0.301, 0.239, 0.418 | 0.002; 0.163, 0.084, 0.385 | 3.123; 1.902, 2.272, 1.070 | **weakened for v2 eta, but ordering survives** |
| five random 10-feature halves | eta human range 0.146–0.234; v1 0.163–0.338; v2 0.208–0.415; v3 0.360–0.819 | human −0.059–0.001; v1 0.026–0.136; v2 0.082–0.212; v3 0.428–0.680 | human 3.43–3.69; v1 2.17–2.82; v2 2.31–3.04; v3 0.72–0.87 | **pass in all 5 draws** |

The human < AI eta² ordering, human < AI silhouette ordering, and human > AI within-spread ordering survive every tested subset. The lexical subset exposes the narrowest margin: v2 eta² (0.239) is only 0.013 above human (0.226).

**C1–C3:** survive this check, with C1 substantially feature-dependent in magnitude. C2 and C3 ordering are more stable than the headline eta² values.

## 2. Window sensitivity and cleaning

`window(text, n)` in `human_model.py` increments only when `CJK` matches, and stops at the nth CJK character; punctuation and other characters before that character are retained. An independent check found zero truncation mismatches at 150/250/400. `clean()` removes the compiled `NOTICE` pattern before feature extraction. In the human corpus, 14 files matched a site notice and 16 changed under cleaning. Thus the first-window result is not silently driven by the browser notices documented in the function comment.

| window | eta² mean `(H; v1,v2,v3)` | silhouette `(H; v1,v2,v3)` | within `(H; v1,v2,v3)` | verdict |
|---|---:|---:|---:|---|
| first 150 CJK | 0.222; 0.261, 0.309, 0.571 | −0.026; 0.124, 0.106, 0.602 | 5.388; 4.012, 4.203, 1.900 | **pass** |
| first 250 CJK | 0.232; 0.315, 0.358, 0.617 | −0.014; 0.174, 0.170, 0.670 | 5.352; 3.950, 4.073, 1.414 | **pass** |
| first 400 CJK | 0.240; 0.352, 0.376, 0.641 | −0.020; 0.214, 0.170, 0.788 | 5.435; 3.795, 4.000, 1.010 | **pass** |
| last 250 CJK | 0.162; 0.357, 0.368, 0.660 | −0.028; 0.211, 0.172, 0.948 | 5.774; 4.017, 4.046, 0.218 | **pass, but v3 has a structural artifact** |

The last-window v3 within distance is nearly zero because five genre groups are constant/near-constant in this suffix extraction (S1/S2/S3/S5 have 0.0 mean pairwise distance); its silhouette is therefore inflated to 0.948. The ordering technically survives, but this is a warning against interpreting the last-window v3 geometry as ordinary document variation.

**C1–C3:** ordering survives all windows. C1 effect size is sensitive to window position; C3 is especially distorted for last-250 v3.

## 3. Label asymmetry

A 5-nearest-neighbor classifier was trained on each AI batch's prompt labels and tested on the 60 human documents, using all 21 features and AI-training-set standardization. Accuracies were v1 **0.55**, v2 **0.40**, and v3 **0.30**. Confusion matrices use rows = true human S1–S5 and columns = predicted S1–S5:

- v1: `[[2,0,8,1,1],[1,2,3,5,1],[0,1,11,0,0],[1,0,0,8,3],[0,0,1,1,10]]`
- v2: `[[5,4,3,0,0],[2,1,5,4,0],[0,4,8,0,0],[1,0,3,6,2],[1,0,1,6,4]]`
- v3: `[[0,11,0,1,0],[2,9,1,0,0],[1,10,1,0,0],[1,3,0,5,3],[0,1,0,8,3]]`

This is **weakened** evidence for treating human source/outlet genres and AI prompt genres as interchangeable labels: transfer is poor, especially v3. It does not by itself falsify the geometry claim.

As a label-free sensitivity analysis, I clustered each AI batch into five K-means groups and recomputed eta² against those cluster labels. Mean eta² was v1 **0.341**, v2 **0.372**, and v3 **0.617**, versus human's source-label eta² **0.232**. Thus AI's higher between-group structure is not solely a consequence of using the prompt labels, although K-means eta² is descriptive and not an independent causal validation.

**C1:** survives as a structural result but the interpretation “same genre variable across human and AI” is weakened. **C2–C3:** not directly tested by classifier transfer; their geometry still separates AI more strongly.

## 4. Resampling unit and sample size

I used a permutation test that shuffles human/AI batch labels *within each genre*, preserving genre counts, with 1,000 permutations. The statistic is AI-minus-human mean eta² and the within-spread ratio human/AI.

| batch, n/genre | eta difference | p(eta difference) | within ratio H/AI | p(ratio) | verdict |
|---|---:|---:|---:|---:|---|
| v1, 12 | 0.0836 | <0.001 (0/1000) | 1.355 | <0.001 (0/1000) | **pass** |
| v2, 12 available | 0.1262 | <0.001 | 1.314 | <0.001 | **pass** |
| v3, 12 | 0.3855 | <0.001 | 3.784 | <0.001 | **pass** |
| v1, 9 | 0.0768 | <0.001 | 1.305 | <0.001 | **pass** |
| v2, 9 | 0.1315 | <0.001 | 1.275 | <0.001 | **pass** |
| v3, 9 | 0.3754 | <0.001 | 3.540 | <0.001 | **pass** |

The exact Monte Carlo reporting should be read as `p < 1/1000`, not literal zero. Reducing every genre to nine documents does not change the ordering.

**C1 and C3:** survive permutation and n=9 sensitivity. **C2:** silhouette was not the permutation target, but feature/window/scaling checks below retain its ordering.

## 5. Scaling

The original geometry standardizes each batch separately in `zmatrix`. I recomputed rank/quantile geometry and an explicitly pooled-SD geometry, where means and SDs are estimated from the combined human+AI rows before evaluating each batch. Mean silhouettes:

| standardization | human | v1 | v2 | v3 | verdict |
|---|---:|---:|---:|---:|---|
| per-batch z (original) | −0.014 | 0.174 | 0.170 | 0.670 | **pass** |
| pooled SD (human + AI rows) | −0.010 | 0.221 | 0.166 | 0.753 | **pass** |
| rank/quantile then z | 0.043 | 0.174 | 0.163 | 0.669 | **pass** |

The silhouette ordering survives both alternatives. Pooled scaling does not remove the separation; rank transform reduces the apparent human–AI gap only slightly for human vs v2.

**C2:** survives. C1 eta² is invariant to feature-wise affine scaling, so scaling is not a C1 challenge; C3 distances change in units but the ordering remains in the reported geometries.

## 6. Leakage and length

The raw (unwindowed) `cjk` ranges are human 546–994, v1 528–882, v2 200–306, and v3 554–749. Several features correlate materially with length in the raw data. Examples: human `entropy` **0.486**, `sent_len` **−0.403**, `formula` **−0.406**, `para_cv` **0.334**; v1 `formula` **−0.600**, `sent_cv` **−0.501**, `inst` **−0.503**; v3 `para_cv` **−0.862**, `formula` **−0.961**, `condition` **0.954**, `ttr` **−0.725**, `entropy` **0.754**. These are mechanically length-sensitive or partly length-mediated features, especially sentence/paragraph statistics, entropy, and TTR.

At first 150/250/400 CJK, almost every batch has exactly the requested CJK count (v2 has only 200–306 total CJK, so its 400 window is not full). Consequently within-batch length correlations become undefined (`NaN`) or zero: the window equalizes the denominator by construction rather than proving length independence. At 250, v2's shorter texts remain a visible exception (200–250 CJK). The equalized window therefore removes gross length as a between-document covariate for most rows, but it also creates a fixed-length conditioning artifact.

**C1–C3:** not falsified, but the length-leakage check is **weakened/diagnostic rather than a pass**. A fixed window equalizes `cjk`; it does not establish that all 21 features are length-free.

## Overall judgment

1. **Most checks pass:** human remains less genre-separated and more internally dispersed than AI across feature subsets, windows, sample sizes, permutation tests, and scaling choices.
2. **The claims should be narrowed:** eta² magnitudes depend on feature subset/window, and human-vs-AI genre labels are not empirically interchangeable (AI-to-human classifier accuracy 0.30–0.55).
3. **The strongest caveat is last-window v3:** suffixes are nearly constant within four genres, making within distance and silhouette partly degenerate.

## Three most dangerous problems and smallest decisive analyses

1. **Label construct mismatch (source/outlet vs prompt).** The classifier transfer failure (0.30–0.55) means “genre” may not be the same construct in both corpora. Smallest decisive analysis: preregister a common, blind annotation of the same 60 texts per batch by independent human raters using one genre rubric, then recompute eta²/silhouette/within spread on those labels; report inter-rater agreement.
2. **Fixed-window and suffix degeneracy.** Last-250 v3 produces zero within distance for S1/S2/S3/S5, and every fixed window makes length correlation unidentifiable. Smallest decisive analysis: use length-matched full documents (or 250-CJK random interior windows, repeated per document) and report document-level aggregation plus the distribution of valid-window statistics, excluding windows with fewer than two sentences/paragraphs under a prespecified rule.
3. **Feature/length dependence and researcher degrees of freedom.** The all-21 eta² is not a feature-invariant quantity; raw features show correlations up to |r|=0.96 with CJK length. Smallest decisive analysis: preregister one feature set, report pooled residualization of each feature against CJK length (fit on the combined corpus), and repeat the same permutation test on residuals; retain the claim only if the AI–human eta² and within-spread order survives.
