# AGENTS.md

Working notes for AI coding agents in baskingspot/skills.

## What this is

Agent skills for Zig, in the [Agent Skills](https://agentskills.io) format: one
directory per skill under `skills/`, each with a `SKILL.md`. The repo is the
distribution unit and the install is per skill, so a skill someone takes alone
has to work alone.

The repo is also a claim about what a good Zig skill is, so the bar is higher
here than for the org's other docs. Design notes and the reasoning behind a
skill go in `docs/slop/`. A `SKILL.md` is written for the agent that loads it,
and the README for the person deciding whether to install it.

## Environment

The flake is the tool contract, from `baskingspot/nix`, plus `skills-ref` from
Matt's nixpkgs. `nix develop` provides the tools, `just` lists the recipes, and
`just ci` runs what CI runs.

## Rules

- A skill directory is `skills/<name>/`, and `name` in the frontmatter matches
  the directory. `skills-ref validate` enforces this; the CLI discovers it.
- The description is the whole routing mechanism. It states what the skill does
  and when it fires, and the wording decides whether the agent reaches for it.
  Keep it one sentence of content and one of trigger.
- The body is loaded only when the skill fires, and it still has a budget: 500
  lines or 4,000 words. Beyond that, move reference into `references/` and link
  it. `just check` enforces the numbers.
- Reference only what the skill can reach. A relative link that does not resolve
  is a dead end for the agent, so `just check` fails on one.
- Every symbol a skill names must exist in the version it names. Verify against
  the source or `https://baskingspot.dev/<name>/api/` before writing it down. A
  skill that describes an API from memory is worse than no skill.
- Steer toward the behaviour, not away from the other one. "Name the primitive
  first" beats "do not hand-roll", because the second puts hand-rolling in
  front of the model.
- Direct the reader at tools that ship with Zig, or name where the tool comes
  from. `zig env` and `zig fmt` are always there. `zigdoc` and `ziglint` are not,
  so a mention carries its source URL or it is an instruction the reader cannot
  follow.
- Skills are public prose. Read `.github/docs/VOICE.md` in the org repo before
  writing one, and the org's `baskingspot-voice` skill if it is installed.
- Do not create a bubble of org-internal process here. A skill that only makes
  sense inside baskingspot is a project skill, and those live in
  `baskingspot/internal`.

## Checks

`just lint` runs all of it: `skills-ref validate` per skill, then
`scripts/check_skills.py`, then `nix fmt -- --ci`, `oxfmt --check`,
`ruff`, `ty`, `actionlint`, `zizmor`, and `just --fmt --check`.

`just sizes` is not a check. It prints the description length and body size of
each skill, which is how the startup cost stays visible.

Format with `just fmt`. Markdown and YAML go through `oxfmt`, Python through
`ruff format`, and Nix files through `nix fmt`.
