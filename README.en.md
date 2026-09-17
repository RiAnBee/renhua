# renhua (人话)

[中文](README.md) | English

**A Chinese-language "de-AI-flavor" skill that only subtracts.**

It deletes the specific things that make Chinese text read like a machine wrote it.

---

## What it does

Give it a passage of Chinese text. It applies six rules, each traceable to a specific location:

1. **Deletes zero-information sentences** — the closing elevation, restatement, moral
2. **Deletes preachy meta-commentary** — "this tells us a lesson" style stepping outside the content
3. **Breaks up adjacent-sentence isomorphism** — when several sentences in a row share one skeleton,
   reorder; when several are short fragments in a row, merge them (not delete information)
4. **Thins explicit cohesion** — over-dense adversatives (**formal register only**) and
   sentence-initial "同时/此外/另外" sequencing (**both registers**)
5. **Thins rhetorical density** — metaphor and parallelism spread across the piece, every section
   closing on a one-line aphorism
6. **Deletes opening declarations** — openings that use "not X, not Y, only Z" instead of stating
   plainly (**deleted only when** each negation is restated elsewhere in the piece; where the
   negation is the *only* such promise, it stays)

There are also 5 optional rules (zero-subject paragraph openers, empty colon lead-ins, pseudo-list
structure, dangling framing, reversal tone), off by default.

Then it hands you a **change ledger**: which rule each edit maps to, what the original was, what it
became, and why. Plus a **do-not-touch list**: places that look AI-ish but were deliberately left alone,
with reasons.

The rewrite is the deliverable. The diagnosis is a side effect.

---

## What it does NOT do

This section matters more than the one above.

### Sentences don't get shorter

**Chinese AI text has *shorter* sentences than human Chinese, and they are more uniform in length.**
Native Chinese median is ~50 characters per sentence; machine-generated Chinese is under 40. Our own
corpus (Cliff's δ, **both registers p<0.05**): mean sentence length −0.46/−0.53, sentence-length CV
−0.44/−0.38.

So it only **merges** runs of short fragments; it never splits long sentences — splitting moves in the
**wrong direction**. ("Sentence length should vary" is a popular recommendation that our measurements
retired; see `no-touch.zh.md`.)

### Metaphor, questions, and parallelism stay

Measured: **humans use metaphor 2.4× more than AI** (8× for standalone-paragraph metaphors),
**humans use questions in body text 17× more**, and **intra-sentence parallelism is used no less by humans**
(0.61×).
Deleting these makes writing look *more* like AI, not less.

### No added first person, slang, or paragraph breaks

No evidence supports any of this. Density is the author's choice, not a rule's obligation.

### Formally-regulated text is off-limits

Government notices, contracts, legal clauses, academic papers, technical docs, API references, SOPs —
these genres *require* uniform formatting and consistent wording. "De-AI-flavoring" them means breaking
the genre.

When such a register is detected, **the entire rule family is disabled**; only tool artifacts are cleaned.

### No promise of a lower detection rate

This is a mathematical constraint: `TPR ≤ FPR + TV`.
"Spare human writing" and "fool detectors" are **two ends of the same dial** — you cannot max both.

This skill serves **experienced human readers**, not detectors.

### Content problems stay

De-AI-flavoring changes *how* something is said. Opinions flattened by AI do not come back through
rewriting. Measured: content is preserved after rewriting (87% of text pairs above 0.95 cosine), but in
heavy-AI writing, **neutral-stance proportion is 66.7% vs 39.5% for humans** — a gap the author has to close.

---

## Why subtraction only

The evidence points here.

**Evidence 1**: The same AI-generated paragraphs were edited by 18 professional writers (MFA). Across
8,035 edits: replacement 74%, deletion 18%, insertion 8%. Asked which version was best, **65% chose the
writer-edited version** — and their three most frequent edit categories were Awkward Word Choice 28%,
Poor Sentence Structure 20%, Redundant Exposition 18%. **All word- and sentence-level.**

**Evidence 2**: When AI text was scrubbed of the seven flaw categories professional writers had
identified (cliches, redundant exposition, purple prose…), narrative-layer AI detection accuracy only
dropped from 95.5% to **93.9%**.

So: what readers notice, and what gets detected, both live at the word/sentence and redundancy-removal
layer. Structure-level rewriting has no supporting evidence and costs information.

Hence the closed action set: **delete / merge / move / restore**. No "add."

---

## Install

```bash
git clone https://github.com/RiAnBee/renhua.git
cp -r renhua/skills/renhua ~/.claude/skills/     # or your skills directory
```

**If you intend to edit this skill, symlink instead of copying** — otherwise the installed copy
**will not update** after a `git pull`, while you keep editing the repo version, and the two
silently diverge:

```bash
ln -s "$PWD/renhua/skills/renhua" ~/.claude/skills/renhua
```

As a Claude Code plugin:

```bash
/plugin marketplace add RiAnBee/renhua
/plugin install renhua
```

---

## Usage

Just state the need:

```
make this not read like AI
this sounds too much like AI, clean it up
```

You can scope it:

```
only clean up wording, don't touch structure
this is an academic paper, don't change the format
```

The skill infers register and length on its own. **You never declare a model or a genre.**

---

## Layout

```
skills/renhua/
├── SKILL.md                        # 3 hard limits + 4 gates + 6 always-on rules + output contract
└── references/
    ├── rules.zh.md                 # 5 optional rules (zero-subject paragraph openers, empty lead-ins…)
    ├── counterexamples.zh.md       # Counterexample gate: Chinese sentences that look triggered but aren't
    ├── no-touch.zh.md              # Do-not-touch list: 18 debunked popular recommendations
    └── evidence.md                 # Sources, figures, corpus setting, evidence grades
```

`SKILL.md` is around 350 lines (budget cap). References load on demand and don't occupy context.

---

## Our own Chinese corpus

**This is the project's only evidence source with a native Chinese human baseline** — every earlier
Chinese figure came from a Chinese-translated-from-English setting.

| Layer | Source | Docs | Chinese chars |
|---|---|---|---|
| Human · formal | People's Daily | 100 | 174,040 |
| Human · informal | cnblogs personal tech blogs | 82 | 179,425 |
| AI · formal | same model × 40 news topics | 40 | 33,490 |
| AI · informal | **same model** × 40 tech-blog topics | 40 | 74,270 |

**The split is deliberate; we don't pool.** Pooling lies — take adversative connectives:

| Formal register | Informal register | Pooled (the wrong move) |
|---|---|---|
| AI **6.43×** human | AI **0.08×** human (opposite direction) | **2.04×** |

**2.04× holds in neither real register.** So calibration corpus layers must **mirror the skill's
register gate**.

**Only 2 features are robust in both registers at p<0.05** (Cliff's δ): mean sentence length −0.46/−0.53,
sentence-length CV −0.44/−0.38. Two more share a direction but are weak (jump mean, questions).

**We retracted conclusions.** The first pass reported 6 robust features; review found two methodological
defects — the AI·informal layer had mixed three models (on questions, the inter-model gap was **105%**,
*larger than the human-vs-machine gap*), and sentence-length stats were polluted by code blocks and
tables (identifier lines glued into a fake 411-character "sentence"). After the fix, the robustness of
`paragraph-final sentence-length CV` and `jump CV` **was an artifact of the confound** and has been
downgraded to "formal register only."

**Limits**: one model family on the AI side; no contamination scrubbing on the human side; the
"informal" layer is really tech blogs; all features are regex-reproducible surface measures with no
syntactic annotation.

---

## On evidence: an honest note

This skill rests on reading **77 papers**, centered on a large-scale human-vs-machine writing study from
the narrative science field (arXiv:2604.03136, University of Maryland with Google DeepMind:
10,272 prompts, each written by a human author and five LLMs = 61,608 stories, 24 missing because
models refused), supported by a dozen directly relevant stylometry, computational linguistics, and
editing-behavior studies, **plus this project's own Chinese comparison corpus** (previous section).

**Before that corpus, clean Chinese-native human-vs-machine comparison evidence barely existed:**

- The only study with both a native Chinese human baseline (People's Daily, Xinhua) and machine-generated
  text is a **Chinese-translated-from-English setting**, and its authors acknowledge source-language interference.
- Another frequently-cited Chinese study has a table whose "low-translationese vs high-translationese"
  columns are **both machine translations**. It measures source-language interference intensity, not
  human-vs-machine difference.
- Chinese syntactic phenomena like "over-long prenominal modifiers", "当……时", "对于……来说" have
  **zero evidence** in the academic literature for Chinese specifically.

So the rules are graded by **evidence strength**:

| Grade | Meaning | Example |
|---|---|---|
| A | Measured on Chinese corpora with a native Chinese human baseline | All our own corpus entries; adversative connectives 6.43× (formal); inter-sentence isomorphism 2.0× |
| B | Cross-linguistic mechanism, independently replicated | Zero-information endings, preachy meta-commentary, alignment as the cause |
| C | Single source / narrow corpus / conflicting evidence | Em-dashes (English side runs the other way) |
| P | Practitioner methodology | Rhetorical budget, three-question ending test |

**Our own corpus has firm limits too**: one model family on the AI side, no contamination scrubbing on
the human side, the "informal" layer is really tech blogs, all features are surface measures.
**Cross-model claims still have to rest on the papers.**

---

## Three hard limits

No request breaks these:

1. **Information conservation** — invent no fact, number, proper noun, causal link or stance; and delete no
   hedge or concession the original had
2. **Closed action set** — delete / merge / move / restore only; "add" is prohibited
3. **Fixed priority** — `do-not-touch list > per-sentence counterexamples > gates > rules`; if register is
   unclear, default to no change

If a user explicitly asks to change something on the do-not-touch list, the user wins — but the skill states
the risk first and flags it in the ledger.

---

## On model specialization

You may have heard "different models have very different AI flavor." That claim is **directionally right
but wrongly explained**.

- **Chinese-made and foreign-made models are indistinguishable**: 66.63% classification accuracy,
  F1 0.519 — near random
- **Between models**, attributable variance is 68.4%; **between human and machine** it is 93.2%
- Model fingerprints **get erased by model updates**: one model family's em-dash rate went from
  "nearly every sentence" to almost never in under a year

The actual cause is **degree of alignment**, not vendor. Four independent studies corroborate:
**base models sit closer to humans than instruction-tuned ones.** Same-weight Llama 3 8B, base → instruct:
present-participle effect size jumps from −0.03 to 0.44, nominalization from −0.15 to 0.49, AI
classification accuracy from 73–78% to 90.7–92.4%.

**So this skill does not split rules by model.**

Instead: specialization moves from "rules per model" to "criteria hit per text." The criteria contain
**no model-dependent constants** — everything is within-document relative frequency. Different models hit
different items on the same checklist and automatically get different treatment. Zero user input; the word
"model" never appears.

---

## Verification: a three-minute self-check

1. **Run it on an old draft you wrote yourself.** Expect almost no changes — **three or more edits means
   it is misfiring on human text** (this applies only when *you* wrote the input; an AI-drafted piece
   should legitimately get multiple edits).
2. **Read only the deletion list, and ask "did I lose anything?"** Not "does it read like AI?"
3. **Revert any edit you cannot map to a rule number.**

Optional magnitude check: post-rewrite semantic similarity ≥0.85; word-level edit distance **≤0.35**
(there is no lower bound — few edits is not a failure).

**Do not use AI-detector scores as acceptance criteria.** Six of twelve detectors score heavily-rewritten
text as *less* AI — detection rate is not monotonic with AI involvement.

---

## Limitations

1. **It cannot reach the "humans do more of this" half.** Subplots, time jumps, allusive naming, moral
   ambiguity, direct address to the reader — humans clearly do more of these, but they all require
   **adding** content, which information conservation forbids. They go into the do-not-touch list only.
2. **It expires.** AI flavor is a moving target; multiple longitudinal studies agree the drift deepens over
   time, and wordlist-based judgments go stale.
3. **Gate decisions are subjective.** The line between "tech blog" and "product documentation" is not
   always clear. Current policy: **when unsure, prefer no change** — missing an edit costs far less than
   breaking something.
4. **Layout is out of scope.** Bold density, heading shape, and list nesting have no human-side baseline,
   so the skill leaves them alone. If that is where your "AI flavor" impression comes from, it will say so
   rather than manufacture edits.
5. **Coverage is incomplete.** The rule list is deliberately narrow, keeping only what can be pointed to and
   what is safe to delete.

---

## Credits

- Inspired by [lieflat-less-ai-tone](https://github.com/larashero3-dotcom/lieflat-less-ai-tone).
  Its methodology (paired-corpus per-feature human/machine frequency ratios) and its *negative* findings
  are both valuable — the latter helped this project discard a large number of reversed recommendations.
- Core evidence from the human-vs-machine writing study (arXiv:2604.03136).

Paper list and per-item sources: `skills/renhua/references/evidence.md`.

---

## Contributing

New evidence, counterexamples (real Chinese sentences that look triggered but shouldn't be edited), and
failure reports are all welcome.

**Counterexamples especially.** This project's number-one failure mode is not a missed edit — it is
**breaking normal human writing**. Humans use metaphor 2.4× more than AI, questions 17× more, and
intra-sentence parallelism 0.61×. A rule without counterexamples is a dangerous rule.

New rules must satisfy three conditions at once: **pointable to a specific location**, **has a
human-side baseline**, and **has ≥3 writeable counterexamples**. See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## License

[MIT](LICENSE)

---

## See also

- For finer-grained Chinese corpus statistics and ratio tables, see
  [lieflat-less-ai-tone](https://github.com/larashero3-dotcom/lieflat-less-ai-tone)
- This project handles Chinese only. English AI tells differ (some directions are reversed). Do not port
  the rules directly.
