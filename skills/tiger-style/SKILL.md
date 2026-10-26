---
name: tiger-style
description: TigerBeetle's Tiger Style for safe, performant Zig. Use when reviewing Zig for safety, assertions, bounded control flow, naming, or structure, or when asked about Tiger Style. Apply it while writing when the project already follows it.
license: MIT
---

# Tiger Style

Adapted from [TigerBeetle's Tiger Style](https://github.com/tigerbeetle/tigerbeetle/blob/main/docs/TIGER_STYLE.md). The doctrine is theirs. This file and the three
references beside it are a working restatement, MIT licensed like the rest of
this repo.

## Where this is stricter

This is an overlay for code where a bug is data loss or a remote exploit:
crypto, filesystems, wire-format parsers. A project adopts it on purpose, and
where the project's default style and this file disagree, this file wins.

Three disagreements, named, so nobody has to guess:

- `init` writes through an out-pointer, `fn init(target: *T) !void`, rather than
  returning the value. In-place initialization is viral, and that is the point.
- 70 lines per function is a hard limit, not a target.
- Branching is explicit and split into nested `if`/`else`, rather than a
  `switch` expression that returns.

Design goals in priority order: **safety > performance > developer experience**.

## Core Rules (Always Apply When Writing Code)

### Safety

- Simple, explicit control flow only. No recursion.
- **Hard limit: 70 lines per function.** Centralize control flow in parent functions; push pure logic to helpers.
- **Assertions should be useful, not ceremonial.** Assert preconditions, invariants, and postconditions that catch real bugs. Do NOT pad functions with fluff assertions just to hit a count. If a function is simple and correct without assertions, that's fine. Zig's type system already provides many implicit assertions — optionals assert non-null on unwrap, tagged unions assert the active tag on access, bounded integers assert on overflow. Using the right data structure IS an assertion strategy. The original Tiger Style guide says "2 per function on average" — treat that as a signal to _think about_ what to assert, not a quota to fill.
- **Pair assertions**: enforce the same property via two different code paths — but only when it adds real verification value.
- Assert positive space (what you expect) AND negative space (what you don't).
- Split compound assertions: `assert(a); assert(b);` not `assert(a and b);`.
- Minimize dynamic allocations. Favor static allocation, stack allocation, and arena allocators. When dynamic allocation is necessary, prefer deterministic patterns (arena per-request, pool pre-allocation) over ad-hoc heap usage.
- Put upper bounds on everything: loops, queues, allocations.
- Use explicitly-sized types (`u32`) — avoid `usize`.
- Declare variables at smallest possible scope.
- All errors must be handled explicitly.
- Split compound conditions into nested `if/else`. Don't use complex `else if` chains.
- State invariants positively: `if (index < length)` not `if (index >= length)`.
- Explicitly pass all options to library functions — never rely on defaults.

### Performance

- Think about performance in the design phase — that's where 1000x wins happen.
- Sketch against four resources (network, disk, memory, CPU) × two characteristics (bandwidth, latency).
- Optimize slowest resources first: network > disk > memory > CPU.
- Batch accesses. Separate control plane from data plane.
- Extract hot loops into standalone functions with primitive args (no `self`).
- **Tracy profiling zones**: every extracted function and meaningful code path should have a `tracy.traceNamed(@src(), ...)` zone. Zones are compiled out in release builds (zero cost), so add them wherever they provide even marginal observability value. Name zones to distinguish initial vs continuation paths (e.g., `"decrypt"` vs `"decrypt remaining"`).

### Naming & Formatting

**Note:** Casing and formatting are enforced by `zig fmt`, plus whatever linter the project runs. The rules below cover semantics that linters don't catch.

- No abbreviations unless primitive integer in sort/matrix context.
- Units/qualifiers go last, sorted by descending significance: `latency_ms_max` not `max_latency_ms`.
- Choose related names with equal character count for alignment: `source`/`target` not `src`/`dest`.
- Prefix helpers with calling function name: `readSector()` → `readSectorCallback()`.
- Struct order: fields, then types (conclude with `const T = @This();`), then methods.
- Comments are sentences: space after `//`, capital letter, full stop. End-of-line comments can be phrases.
- Always say **why** in comments and commit messages, not just what.

### Booleans Are a Code Smell

Every `bool` should trigger the question: "can this be modeled better?" Booleans are almost always a crutch for a richer type. Consider:

- **`enum`** — if it represents a state or mode, name the states: `.active` / `.inactive` not `true`/`false`
- **Tagged union** — if the boolean gates which fields are valid, a union encodes that invariant into the type system
- **Optional (`?T`)** — "present or absent" is clearer than a bool + separate value
- **Bitset / packed struct** — if you have multiple flags, pack them; individual bools waste space and lose the grouping

Booleans aren't forbidden, but every use should survive scrutiny. A function that takes two bools is a strong signal something should be an enum or options struct.

### Cache Invalidation & State

- Don't duplicate variables or create aliases.
- Pass args >16 bytes as `*const` if not meant to be copied.
- Construct larger structs in-place via out pointer (`fn init(target: *T) !void`). In-place init is viral.
- Calculate/check variables close to where they're used. Don't introduce early, don't leave around.
- Prefer simpler return types: `void` > `enum` > `u64` > `?u64` > `!u64`. Avoid `bool` returns — an enum with named variants is almost always clearer.
- Functions should run to completion without suspending.
- Guard against buffer bleeds — zero padding correctly.
- Group resource allocation with corresponding `defer` using newlines.

### Off-By-One

- `index` (0-based) vs `count` (1-based) vs `size` (count × unit) are distinct types.
- Use `@divExact()`, `@divFloor()`, or `div_ceil()` to show division intent.

## Detailed Review

For a thorough code review against Tiger Style, read the relevant reference files:

- **[references/safety.md](references/safety.md)**: Full safety rules — assertions, control flow, memory, bounds, error handling. Read when reviewing safety-critical code or assertion coverage.
- **[references/performance.md](references/performance.md)**: Performance philosophy, batching, mechanical sympathy, CPU optimization. Read when reviewing hot paths or system design.
- **[references/developer-experience.md](references/developer-experience.md)**: Naming conventions, cache invalidation patterns, off-by-one prevention, formatting rules, in-place initialization, documentation. Read when reviewing naming, structure, or style.

When performing a full Tiger Style review, read all three reference files and check the code against each section systematically.
