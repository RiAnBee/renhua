# renhua · 人话

[中文](README.md) | English

A Chinese prose-editing skill for empty, stiff, repetitive, or contextually awkward writing. It preserves facts, judgments, tone, and the author's voice.

This is an editor, not an AI-origin detector. It does not impose slang, short sentences, an internet-post persona, or a literary style, and promises no detector-score reduction.

## Usage

Give your agent the draft and, when relevant, its purpose:

```text
Use renhua to make this Chinese draft natural. Keep my voice and return only the edited text.
This email is for a client. Remove the template tone without turning a request into a demand.
Edit this technical explanation; keep code, parameters, and numbered steps intact.
```

The default deliverable is the complete edited draft, without a change ledger or a list of rules. Ask for key changes and reasons when you need them. An already effective passage can remain unchanged.

You do not need to name the generating model. The skill follows the supplied audience, purpose, and explicitly designated style samples; otherwise it retains the draft's register. It does not search private files for a style profile or build a permanent author model.

## What it edits

- Repetition, announcements, and self-evaluation that serve no useful function.
- Stiff wording, misplaced modifiers, unclear references, and unnecessarily indirect syntax.
- Awkward transitions or sentence boundaries, without changing the underlying relationships.
- Rhetorical gestures and redundant emphasis that obscure the actual point.

Questions, parallelism, metaphors, connectives, long sentences, and short sentences are not automatic editing targets. A repeated sentence can still answer a separate concern, preserve politeness, or establish rhythm.

**Changing wording is not permission to change meaning.** Facts, quantities, terms, quotations, sources, qualifications, stance, responsibility, and the force of a request must survive.

### A constructed boundary example

Before:

> 小组完成了对值班安排的调整。如果方便，请周三前告诉我；来不及也请说一声。

An acceptable edit:

> 小组调整了值班安排。如果方便，请周三前告诉我；来不及也请说一声。

The first sentence can be simplified. The flexibility in the second is meaningful; changing it to a firm Wednesday deadline would be a fidelity failure. This example illustrates the contract, not measured performance.

## Default scope

| Allowed when needed | Not automatic |
|---|---|
| Meaning-preserving rewording, syntax changes, sentence splitting or merging | Invented facts, data, experiences, motives, or opinions |
| Editing explanatory prose inside a README or mixed document | Changes to code, parameters, quotations, obligations, conditions, or attribution |
| Removing redundant emphasis that has no function | Changes to heading hierarchy, numbering, tables, or cross-references |
| Identifying organizational problems and briefly suggesting a remedy | Reordering, splitting, or merging body paragraphs, or changing argument/narrative order |

Explicitly request structural editing when needed; it still uses only the supplied material. Requests such as “typos only,” “review without rewriting,” and “preserve formatting” narrow the scope.

Chinese/English mixed documents are edited only within the authorized Chinese scope. Pure English does not receive Chinese style advice. Traditional/simplified script, regional vocabulary, person, and existing voice are retained.

## Install and update

Copy the whole skill directory:

```bash
git clone https://github.com/RiAnBee/renhua.git
mkdir -p ~/.claude/skills
cp -r renhua/skills/renhua ~/.claude/skills/
```

Use another skills directory if required by your agent. **For an existing installation, move the old `renhua` directory aside before copying the new one**, rather than merging files and leaving obsolete rules behind. An existing symlink to the repository follows repository updates directly.

The repository also includes a local plugin entrypoint. OMP supports:

```bash
omp --plugin-dir ./renhua
```

`commands/renhua.md` routes to the core rather than duplicating its policy. No marketplace manifest is configured, so this README does not provide an unverified marketplace-install command.

## Layout

```text
skills/renhua/
  SKILL.md                  # Complete default editing contract
  references/
    examples.zh.md          # On demand for difficult boundaries or structural work
    evidence.md             # On demand when the user asks for evidence
```

Research and evaluation are outside the installable skill:

- [Current evidence and limitations](skills/renhua/references/evidence.md)
- [Archived research and retractions](docs/research/evidence-history.md)
- [Reconstruction audit and design](docs/plans/2026-09-22-renhua-reconstruction.md)
- [Evaluation protocol](evals/README.md) and [implementation record](docs/plans/2026-09-22-renhua-reconstruction.report.md)

## Why it no longer only subtracts

The previous contract extended “do not invent facts” into a restriction on normal rewording, using sentence lengths, human/AI frequency differences, and rule hits as editing proxies. Those prescriptions have been withdrawn: **a feature that distinguishes sources does not necessarily improve writing when removed.**

[LAMP](https://arxiv.org/abs/2409.14509v5) includes substantial replacement editing, not just deletion. [StoryScope](https://arxiv.org/abs/2604.03136v6) studies narrative attribution signals; its classification results do not establish that structural editing is useless. Chinese question-answering, translated news, and register studies do not define one universal sentence-length target either.

The evidence summary separates observations from design decisions. Historical work remains available, but a non-replication is not a permanent editing prohibition, and a small historical error fraction is not a current error-rate guarantee.

## Validation and limitations

First check whether meaning, tone, or commitments changed. Then ask whether the edit is more useful for the intended audience. Edit counts, source labels, and detector scores answer neither question.

This reconstruction uses 36 original synthetic development documents and 120 separately sealed synthetic confirmation documents. They exercise engineering boundaries; **they are neither a human-writing baseline nor proof of real-world safety or best-in-class quality**. Direct-prompt runs, actual skill loading, model-assisted review, and human blind review are reported separately in the implementation record.

The skill still relies on the editor model's judgment. Authors or domain users should review distinctive voices, legal material, and technical content. Editing cannot recover facts or judgments absent from the input. Stable gains over a good simple editing prompt require complete-document comparisons and Chinese reader evaluation.

## Contributing and license

Report unnecessary edits, missed problems, meaning changes, or voice flattening with the full context, intended audience, and relevant boundaries. Prompt wording changes behavior and needs rechecking. See [CONTRIBUTING.md](CONTRIBUTING.md).

Inspired by [lieflat-less-ai-tone](https://github.com/larashero3-dotcom/lieflat-less-ai-tone), with additional practical lessons from [human-writing](https://github.com/KKKKhazix/human-writing). Stars and self-reported feature ratios are not performance validation.

[MIT](LICENSE). Third-party papers and collected texts retain their original copyrights; they are not uploaded with this repository or relicensed by it.
