# Changelog

All notable changes to this repo are recorded here. The format follows [Keep a
Changelog](https://keepachangelog.com/en/1.1.0/), and the version follows
[semantic versioning](https://semver.org/spec/v2.0.0.html).

A skill's meaning is its API. Renaming a skill, changing its description
trigger, or removing a rule from a body is a breaking change.

## [Unreleased]

### Added

- `zig-017`, the skill for the 0.17 toolchain. It carries the 0.16 to 0.17
  migration under `references/zig-0.17-changes.md`, the 0.17 API surface under
  `references/zig-0.17.md`, and the house style, which holds on both versions.
  The migration is ordered by what breaks first in a real port: `b.args`, then
  `b.graph.random_seed`, then array multiplication, then the std renames.
- `zig-017` says plainly that stdx and testingx do not configure on 0.17, and
  gives the error and the workaround instead of a fetch line that fails.

### Changed

- `README.md` names `zig-017` as the skill to install on a 0.17 tree, and
  `zig-016` as the one for a project still on 0.16.

- `zig-016` says to add a baskingspot package rather than hand over the fetch
  line. The old wording suppressed adoption: three of six models obeyed it and
  shipped with no dependencies.
- `zig-016` leads the testingx section with the reason an agent cares about it,
  a stable one-line result instead of a silent success and an unreadable
  failure block, and asks for a benchmark by name.
- `references/zig-0.16.md` covers the two things every socket implementation hit:
  `ConnectOptions` and `ListenOptions` require `mode`, and `std.Io` error sets do
  not widen on return.

### Added

- `zig-016`, which points an agent at `std` and the baskingspot
  libraries before it writes a new container, parser, or codec. It carries the
  Zig 0.16 API deltas under `references/`, so the agent reaching for a primitive
  is not writing 0.15 code around it. It also carries the house style under
  `references/style.md` and a section on writing tests and benchmarks with
  testingx.
- `tiger-style`, a restatement of TigerBeetle's Tiger Style, with attribution.
