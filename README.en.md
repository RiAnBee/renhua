# renhua · 人话

[中文](README.md) | English

Chinese drafts from models tend to come out vague, stiff, repetitive, or out of register. This skill edits those spots until a reader can move through the text in one go, and might even remark that the agent has finally started to sound like a person. Facts, judgments, tone, and the author's own voice stay as they are.

It does not guess which model wrote the draft, and it reports no detector score.

## Usage

Hand the draft to any agent that supports Agent Skills:

```text
Use renhua to make this Chinese draft natural. Keep my voice and return only the edited text.
This email is for a client. Remove the template tone without turning a request into a demand.
Edit this technical explanation; keep code, parameters, and numbered steps intact.
```

The default deliverable is the complete edited draft. Ask for "key changes and reasons" when you want them. A passage that already works comes back unchanged; there is no quota to fill.

You do not need to name the model that wrote the draft. A stated audience, purpose, or style sample governs the edit. Otherwise the draft's own register, person, and regional vocabulary carry over. The skill does not search private files or build an author profile.

## What it changes

- Repetition, announcements, and self-evaluation that do no work.
- Actions buried under noun phrases, misplaced modifiers, references the reader cannot resolve.
- Connectives piled up until the relation disappears; sentence breaks that turn a parallel into a cause.
- Rhetorical gestures that crowd out the point: stacked reversals, evenly spaced aphorisms, vague metaphors, repeated emphasis.

Long or short sentences, parallelism, questions, metaphors, and formal wording are not editing targets by themselves. No sentence-length, density, or change-count quota exists.

## Before you touch the draft

Start with who is writing, for whom, and what goes wrong if the text is wrong. What the reader already knows, which sentence would cost someone something if it were overstated — without that, there is no telling filler from content, and deletion turns into guesswork. Once it is clear, each sentence has grounds to stay or go; rewording alone will not get you there.

Then the genre. A notice, a news item, a theoretical essay, a technical post, a personal essay: each has its own normal form. The skill does not make official prose read unlike official prose. It fixes over-uniformity inside a genre: every sentence the same length, disyllabic words in a run, every paragraph opening the same way.

Finally, how many real facts you hold. That sets how concrete the text can be: one or two items for an essay, five or more for a notice, a news item, or a report. Models use whatever they are given and will not select.

Missing material or a missing purpose gets one sentence at delivery. It is not filled in for the author.

Words can change; meaning cannot. Numbers, terms, quotations, sources, qualifications, stance, responsibility, and the force of a request all survive. A sentence with no new fact can still work: it answers a worry, hands a decision back, or carries the rhythm.

### One boundary example

> 小组完成了对值班安排的调整。如果方便，请周三前告诉我；来不及也请说一声。

Edited:

> 小组调整了值班安排。如果方便，请周三前告诉我；来不及也请说一声。

The first sentence can be shortened. The leeway in the second cannot: "submit by Wednesday" turns a request into an order. This illustrates the contract, not measured performance.

## Default scope

| Allowed when needed | Not automatic |
|---|---|
| Meaning-preserving rewording; word order, syntax, sentence splitting and merging | Invented facts, data, experiences, motives, or opinions |
| Editing explanatory prose, including inside a README | Changes to code, parameters, quotations, obligations, conditions, or attribution |
| Removing emphasis that does no work | Changes to heading hierarchy, numbering, tables, or cross-references |
| Naming an organizational problem and suggesting a fix | Reordering, splitting, or merging body paragraphs; changing argument or narrative order |

Ask for structural editing when you want it; it still uses only the supplied material. "Typos only", "review without rewriting", and "preserve formatting" narrow the scope to that one job.

Mixed Chinese/English documents are edited only inside the authorized Chinese scope. Pure English gets no Chinese style advice. Traditional or simplified script, regional words, person, and voice follow the draft.

## Install and update

Copy the whole directory, `references/` included:

```bash
git clone https://github.com/RiAnBee/renhua.git
mkdir -p ~/.claude/skills
cp -r renhua/skills/renhua ~/.claude/skills/
```

Any skills directory your agent recognises works. If an older `renhua` is already installed, move it aside before copying, so two rule sets do not mix. A symlink into the repository updates whenever the repository files do.

Plugin entrypoint:

```bash
omp --plugin-dir ./renhua
```

`commands/renhua.md` routes to the core and holds no second copy of the rules. No marketplace manifest is configured; install from a local directory.

## Layout

```text
skills/renhua/
  SKILL.md                  # Editing contract; usable on its own
  references/
    examples.zh.md          # Difficult boundaries, structural work
    ai-flavor-cases.md      # Something reads wrong but you cannot name it
    situating.md            # Judging situation, genre, material dose
    evidence.md             # When someone asks for the evidence
```

The reasoning ships as the [evidence summary](skills/renhua/references/evidence.md) inside the skill directory. The research library, evaluation material and analysis scripts stay local and are not part of the repository.

## What the previous version withdrew

The old contract turned "invent no facts" into "replace nothing", and governed edits with sentence length, human/AI frequency gaps, and rule hits. Those prescriptions were withdrawn in 2026-09: **telling sources apart does not make the text better once those features are gone.**

[LAMP](https://arxiv.org/abs/2409.14509v5) records professional editors replacing far more than they delete, which does not support deletion-only editing. [StoryScope](https://arxiv.org/abs/2604.03136v6) studies narrative attribution signals; its classifier results say nothing about whether structural editing helps. Chinese question answering, translated news, and register studies do not add up to one sentence-length target.

The evidence summary keeps observation and design decision apart. Historical work remains available for review; a non-replication is not a permanent ban, and an old small-sample error fraction is not today's rate.

## Validation and limitations

Read an edit in this order: did meaning, tone, or commitment change; then, does this version suit the purpose at hand. Beyond those two questions, change counts, source labels, and detector scores are only circumstantial.

Development material is 36 synthetic drafts, with 120 differently themed synthetic drafts sealed separately. They exercise engineering boundaries. **They are not a human-writing baseline and they prove nothing about real-world safety or quality.** Direct-prompt runs, real skill loading, model-assisted review, and human blind review are counted separately in the implementation record.

Five pre-registered experiments (one model, 30 items, 5 genres x 6 topics) support the three layers: situation context cuts evaluative filler from 7.7 to 5.2 per 1,000 characters, while added material only reaches 5.9; material count lifts referential density 4 -> 20 -> 28 -> 40 with coverage at 1.00; genre labels drive form convergence (eta-squared 0.456 -> 0.342), material barely moves it. **No reader blind review was run this round**, so the release claims fewer predictable failures (dumping every supplied fact, inventing around a missing situation) and makes no claim that output reads more human. Protocols and raw reports stay local and are not published with the repository.

Editing still rests on the model's judgment; information preservation has no formal guarantee. Distinctive voices, legal text, and technical material should be reviewed by the author or a domain user. Missing material can only be flagged, never recovered. Answering whether this beats a good one-line prompt needs complete-document comparisons and Chinese reader evaluation; neither has been run.

## Contributing and license

Report edits that were unnecessary, problems that were missed, meaning that shifted, or voice that flattened, with the full context, intended audience, and boundaries. Changing prompt wording changes behaviour, so it has to be retested. See [CONTRIBUTING.md](CONTRIBUTING.md).

Inspired by [lieflat-less-ai-tone](https://github.com/larashero3-dotcom/lieflat-less-ai-tone), with practical lessons from [human-writing](https://github.com/KKKKhazix/human-writing) on material and function. Stars are not treated as validation.

[MIT](LICENSE). Third-party papers and collected texts keep their original copyright; they are not uploaded with this repository or relicensed by it.
