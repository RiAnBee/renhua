# renhua (人话)

[中文](README.md) | English

**A Chinese-language "de-AI-flavor" skill that only subtracts.**

It adds no facts, changes no positions, restructures nothing. It deletes the specific things that make
Chinese text read like a machine wrote it.

---

## What it does

Give it a passage of Chinese text. It does four things:

1. **Deletes zero-information sentences** — the closing elevation, restatement, moral
2. **Deletes preachy meta-commentary** — "this tells us a lesson" style stepping outside the content
3. **Breaks up adjacent-sentence isomorphism** — when several sentences in a row share one skeleton,
   reorder (not delete information)
4. **Thins explicit cohesion and rhetorical density** — over-dense connectives, rhetoric spread across
   the whole piece

Then it hands you a **change ledger**: which rule each edit maps to, what the original was, what it
became, and why. Plus a **do-not-touch list**: places that look AI-ish but were deliberately left alone,
with reasons.

The rewrite is the deliverable. The diagnosis is a side effect.

---

## What it does NOT do

This section matters more than the one above.

### It will not shorten your sentences

**Chinese AI text has *shorter* sentences than human Chinese.** Native Chinese median is ~50 characters
per sentence; machine-generated Chinese is under 40. Shortening sentences moves in the **wrong direction**.

### It will not delete your metaphors, questions, or parallelism

Measured: **humans use metaphor 2.4× more than AI** (8× for standalone-paragraph metaphors),
**humans use questions in body text 17× more**, and **intra-sentence parallelism is used no less by humans**
(0.61×).

Deleting these makes writing look *more* like AI, not less.

### It will not add first person, slang, or break up long paragraphs

No evidence supports any of this. Density is the author's choice, not a rule's obligation.

### It will not touch formally-regulated text

Government notices, contracts, legal clauses, academic papers, technical docs, API references, SOPs —
these genres *require* uniform formatting and consistent wording. "De-AI-flavoring" them means breaking
the genre.

When such a register is detected, **the entire rule family is disabled**; only tool artifacts are cleaned.

### It does not promise a lower AI-detection rate

This is a mathematical constraint: `TPR ≤ FPR + TV`.
"Spare human writing" and "fool detectors" are **two ends of the same dial** — you cannot max both.

This skill serves **experienced human readers**, not detectors.

### It cannot fix content

De-AI-flavoring changes *how* something is said. Opinions flattened by AI do not come back through
rewriting. Measured: content is preserved after rewriting (87% of text pairs above 0.95 cosine), but in
heavy-AI writing, **neutral-stance proportion is 66.7% vs 39.5% for humans**. Stance is the author's to recover.

---

## Why subtraction only

Not caution — the evidence points here.

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
├── SKILL.md                        # 3 hard limits + 4 gates + 5 always-on rules + output contract
└── references/
    ├── rules.zh.md                 # 5 optional rules (zero-subject paragraph openers, empty lead-ins…)
    ├── counterexamples.zh.md       # Counterexample gate: Chinese sentences that look triggered but aren't
    ├── no-touch.zh.md              # Do-not-touch list: 18 debunked popular recommendations
    └── evidence.md                 # Sources, figures, corpus setting, evidence grades
```

`SKILL.md` is 316 lines. References load on demand and don't occupy context.

---

## On evidence: an honest note

This skill rests on reading **77 papers**, centered on a large-scale human-vs-machine writing study from
the narrative science field (arXiv:2604.03136, University of Maryland with Google DeepMind:
10,272 prompts × 6 generators = 61,608 texts), supported by a dozen directly relevant stylometry,
computational linguistics, and editing-behavior studies.

**But one thing has to be said plainly: clean Chinese-native human-vs-machine comparison evidence
barely exists.**

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
| A | Measured on Chinese corpora with a native Chinese human baseline | Adversative connectives >2×, inter-sentence isomorphism 2.0×, empty colon lead-ins 9.4× |
| B | Cross-linguistic mechanism, independently replicated | Zero-information endings, preachy meta-commentary, alignment as the cause |
| C | Single source / narrow corpus / conflicting evidence | Em-dashes (Chinese and English directions conflict; disabled by default) |
| P | Practitioner methodology | Rhetorical budget, three-question ending test |

**Chinese rules can only state direction, not claim a clean Chinese measurement ratio.** This is recorded
in `references/evidence.md`.

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

Measurements:

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

1. **Run it on an old draft you wrote yourself.** Expect almost no changes. **Three or more edits means it
   is misfiring on human text.**
2. **Read only the deletion list, and ask "did I lose anything?"** Not "does it read like AI?"
3. **Revert any edit you cannot map to a rule number.**

Optional magnitude check: post-rewrite semantic similarity ≥0.85; word-level edit distance in 0.15–0.35.

**Do not use AI-detector scores as acceptance criteria.** Six of twelve detectors score heavily-rewritten
text as *less* AI — detection rate is not monotonic with AI involvement.

---

## Limitations

1. **It cannot reach the "humans do more of this" half.** Subplots, time jumps, allusive naming, moral
   ambiguity, direct address to the reader — humans clearly do more of these, but they all require
   **adding** content, which information conservation forbids. They go into the do-not-touch list only.
2. **It expires.** AI flavor is a moving target. Multiple longitudinal studies agree the drift deepens over
   time. Wordlist-based judgments go stale.
3. **Gate decisions are subjective.** The line between "business commentary" and "technical report" is not
   always clear. Current policy: **when unsure, prefer no change** — missing an edit costs far less than
   breaking something.
4. **Coverage is incomplete.** The rule list is deliberately narrow, keeping only what can be pointed to and
   what is safe to delete.

---

## Credits

- Inspired by [lieflat-less-ai-tone](https://github.com/larashero3-dotcom/lieflat-less-ai-tone).
  Its methodology (paired-corpus per-feature human/machine frequency ratios) and its *negative* findings
  are both valuable — the latter helped this project discard a large number of reversed recommendations.
- Core evidence from the human-vs-machine writing study (arXiv:2604.03136).

Paper list and per-item sources: `skills/renhua/references/evidence.md`.

---

## License

[MIT](LICENSE)

---

## See also

- For finer-grained Chinese corpus statistics and ratio tables, see
  [lieflat-less-ai-tone](https://github.com/larashero3-dotcom/lieflat-less-ai-tone)
- This project handles Chinese only. English AI tells differ (some directions are reversed). Do not port
  the rules directly.
