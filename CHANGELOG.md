# Changelog

All notable changes to this repo are recorded here. The format follows [Keep a
Changelog](https://keepachangelog.com/en/1.1.0/), and the version follows
[semantic versioning](https://semver.org/spec/v2.0.0.html).

A skill's meaning is its API. Renaming a skill, changing its description
trigger, or removing a rule from a body is a breaking change.

## [Unreleased]

### Changed

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
