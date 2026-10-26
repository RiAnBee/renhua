# renhua · 人话

[中文](README.md) | English

Model-written Chinese is often not wrong at the word level; the sentence is complete but does not land on the matter at hand. renhua first checks who is saying what to whom and what the reader must do, then edits only what blocks that exchange. It does not rewrite the author's claims or manner of speaking.

It does not guess the source model or use detector scores as an outcome.

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

Ask what each passage is doing for this writer, this reader, and this occasion: what it points to, what it claims, what relation it has to the surrounding sentences, and what the reader must be able to decide or do. Missing material is flagged, not invented.

Do not start with a blacklist. Words such as `满`, `而`, `不是……而是……`, headings, and summaries can be useful. Edit only when a form could fit almost any topic, has no commitment to an object or proposition, and does no work for relation, stance, politeness, scope, or genre. Paragraph openings and endings are sampling points, not bans.

Fix propositions, relations, commitments, and reader state before adjusting wording, syntax, punctuation, or rhythm. A notice, news item, theoretical essay, technical post, and personal essay each has its own normal form.

Missing purpose, material, or responsibility boundaries get one sentence at delivery. They are not filled with adjectives.

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

## What the previous version withdrew

The old contract turned "invent no facts" into "replace nothing", and governed edits with sentence length, human/AI frequency gaps, and rule hits. Those prescriptions were withdrawn in 2026-09: **telling sources apart does not make the text better once those features are gone.**

[LAMP](https://arxiv.org/abs/2409.14509v5) records professional editors replacing far more than they delete, which does not support deletion-only editing. [StoryScope](https://arxiv.org/abs/2604.03136v6) studies narrative attribution signals; its classifier results say nothing about whether structural editing helps. Chinese question answering, translated news, and register studies do not add up to one sentence-length target.

The evidence summary keeps observation and design decision apart. Historical work remains available for review; a non-replication is not a permanent ban, and an old small-sample error fraction is not today's rate.

## Validation and limitations

Read an edit in this order: did meaning, tone, or commitment change; then, does this version suit the purpose at hand. Beyond those two questions, change counts, source labels, and detector scores are only circumstantial.

Development material includes synthetic drafts used only to stress-test editing boundaries. **It is not a human-writing baseline and proves nothing about real-world quality.** Direct prompts, real skill loading, model-assisted review, and human evaluation must be reported separately.

Local experiments support a narrow claim: situation context and real material change what models select, while genre prompts change formal prototypes. They do not establish a fixed “AI vocabulary” or guarantee that an edit will read as human. The current working hypothesis is a **break in situated commitments**: check objects, propositions, relations, reader tasks, and consequences before touching form.

No Chinese full-document intervention with human readers has been run. Authors or domain users should review distinctive voices, legal text, and technical material. Missing material can only be flagged. Change counts, source labels, and detector scores cannot replace that review.

## Contributing and license

Report edits that were unnecessary, problems that were missed, meaning that shifted, or voice that flattened, with the full context, intended audience, and boundaries. Changing prompt wording changes behaviour, so it has to be retested. See [CONTRIBUTING.md](CONTRIBUTING.md).

Inspired by [lieflat-less-ai-tone](https://github.com/larashero3-dotcom/lieflat-less-ai-tone), with practical lessons from [human-writing](https://github.com/KKKKhazix/human-writing) on material and function. Stars are not treated as validation.

[MIT](LICENSE). Third-party papers and collected texts keep their original copyright; they are not uploaded with this repository or relicensed by it.
