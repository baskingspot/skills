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
a hand-rolled flag loop. `zig-017` names the primitive behind each of those and
carries the 0.16 to 0.17 migration. `zig-016` is the same skill for the previous
toolchain. `tiger-style` is the stricter overlay, for code where a bug is data
loss.

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

| Skill         | When an agent loads it                                                                                                                                      |
| ------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `zig-017`     | Writing new Zig 0.17, or porting a 0.16 tree to it. The 0.16 to 0.17 deltas, the primitive behind whatever is about to be hand-written, and the house style |
| `zig-016`     | The same for a project still on 0.16: the 0.15 to 0.16 deltas, testingx, and the house style                                                                |
| `tiger-style` | Reviewing Zig for safety, assertions, bounded flow, naming, or structure, or when a project already follows it                                              |

Install the one that matches the project's `build.zig.zon`. `zig-017` covers
everything `zig-016` does, so a project that ports does not need both.

What `zig-017` cannot tell you yet: stdx and testingx declare
`minimum_zig_version = "0.16.0"` and fail to configure on 0.17, on
`b.graph.random_seed` in their own build scripts. The skill says so, and says
what to write instead until they port.

`tiger-style` is a choice, not a version match: it is TigerBeetle's doctrine,
restated, and it puts safety over performance over developer experience in a way
not every project wants.

Each skill carries reference files under `references/`. The description and the
body are what an agent loads, and a reference is read only when the body points
at one.

## How we know it works

`eval/` holds the harness. `eval/scaffold/` is a vanilla Zig project with the
skills vendored under `.agents/skills/`, `eval/prompt.md` is the task, and
`eval/results/` holds what came back.

Three rounds so far, six models, with a no-skills control in the first two.
The results changed the skills more than once: a line telling the agent to hand
over a fetch line instead of adding a dependency left half the runs with no
dependency at all, and removing it took stdx from none of six to five of six.
The write-up for all three rounds is in `eval/results/`, with each round's
skills pinned to a commit or marked as an uncommitted draft.

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
