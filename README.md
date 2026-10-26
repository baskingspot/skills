<h1>
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/static/logo-dark.svg">
    <img src="docs/static/logo.svg" alt="baskingspot" height="48">
  </picture>
</h1>

Agent skills for Zig. A skill is a folder of instructions that an agent loads
when a task matches its description, and nothing until then. These carry the
parts of writing Zig that a model does not do on its own.

Written cold, Zig drifts toward C: a struct holding a slice and a length, a
`while` over `split` that parses as it scans, tests through the built-in runner,
a hand-rolled flag loop. `zig-016` names the primitive behind each of those,
wires up `testingx`, and applies the house style. `tiger-style` is the stricter
overlay, for code where a bug is data loss.

## Install

Any agent that reads the [Agent Skills](https://agentskills.io) format, which is
most of them:

```sh
npx skills add baskingspot/skills
```

It asks which skills and which agents, then writes each one into that agent's own
directory. Add `-g` to install for every project.

In [pi](https://pi.dev):

```sh
pi install git:github.com/baskingspot/skills
```

Both read `skills/` from this repo, so nothing is written twice.

## What is here

| Skill         | When an agent loads it                                                                                                                                                |
| ------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `zig-016`     | Writing or reviewing Zig 0.16. The 0.16 API deltas, the primitive behind whatever is about to be hand-written, testingx for tests and benchmarks, and the house style |
| `tiger-style` | Reviewing Zig for safety, assertions, bounded flow, naming, or structure, or when a project already follows it                                                        |

`zig-016` is the one to install by default. `tiger-style` is a choice: it is
TigerBeetle's doctrine, restated, and it puts safety over performance over
developer experience in a way not every project wants.

Both carry reference files under `references/`. The description and the body are
what an agent loads; a reference is read only when the body points at one.

## How we know it works

`eval/` holds the harness. `eval/scaffold/` is a vanilla Zig project with the
skills vendored under `.agents/skills/`, `eval/prompt.md` is the task, and
`eval/results/` holds what came back.

Three rounds so far, six models, with a no-skills control in the first two.
The results changed the skills more than once: a line telling the agent to hand
over a fetch line instead of adding a dependency suppressed adoption in three of
six runs, and removing it took stdx from none of six to five of six. The write-up
is in `eval/results/`.

## Working here

`nix develop` provides every tool, and `direnv allow` loads it on entry. `just`
lists the recipes. `just ci` runs what CI runs: `skills-ref validate` for the
specification, `scripts/check_skills.py` for this repo's rules, and the usual
formatters and linters.

`just sizes` prints what each skill costs. A description sits in every session
that has the skill installed; the body loads only when the skill fires.

`just vendor` copies the skills into `eval/scaffold/.agents/skills/`, and
`just check` fails when that copy drifts from the source.

## License

MIT. See `LICENSE`. The files in `docs/static/` are the exception: the
baskingspot name, mark, and logos are all rights reserved. See
`docs/static/LICENSE`.
