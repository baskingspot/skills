# Tiger Style — Developer Experience

## Naming

### Core Principles

Get the nouns and verbs just right. Great names capture what a thing is or does and provide a crisp, intuitive mental model. Take time to find the perfect name.

### Conventions

- **Casing and formatting are enforced by `zig fmt`, plus the project's linter.** Follow the Zig style guide (camelCase for functions, snake_case for variables/files).
- No abbreviations unless primitive integer in sort/matrix context. Scripts use long-form flags: `--force` not `-f`.

### Units & Qualifiers

Add units/qualifiers last, sorted by descending significance:

```
latency_ms_max   // not max_latency_ms
latency_ms_min   // groups with latency_ms_max
```

Variable starts with most significant word, ends with least significant.

### Meaningful Names

- Infuse with meaning: `gpa: Allocator` and `arena: Allocator` over `allocator: Allocator`.
- Choose related names with equal character count for alignment: `source`/`target` not `src`/`dest`.
  - Second-order effect: `source_offset` and `target_offset` line up in calculations.

### Helper Naming

Prefix helpers with calling function name: `readSector()` → `readSectorCallback()`.

### Parameter Order

- Callbacks go last (mirrors control flow — invoked last).
- Thread dependencies (allocator, tracer) positionally through constructors, most general to most specific.
- Use Zig's `options: struct` pattern when arguments can be mixed up. Two `u64` args must use options struct.
- If an argument can be `null`, name it so the meaning of `null` at the call site is clear.

### Struct & File Order

- `main` function first in files. Top-down reading flow.
- Structs: fields → types → methods.
- Conclude types section with `const TypeName = @This();`.
- If a nested type is complex, make it top-level.
- When order is ambiguous, consider alphabetical (taking advantage of big-endian naming).

### Name Clarity

- Don't overload names with multiple context-dependent meanings.
- Think of how names will be used outside code (docs, communication). Nouns work better than adjectives or participles.
  - `replica.pipeline` (noun, usable as section header) over `replica.preparing` (participle, needs clarification).

## Cache Invalidation & State

### No Duplication

Don't duplicate variables or take aliases. Reduces probability of state going out of sync.

### Pointer Arguments

Pass arguments >16 bytes as `*const` if not meant to be copied by value. Catches bugs where caller makes accidental stack copy.

### In-Place Initialization

Construct larger structs in-place via out pointer:

```zig
// Prefer:
fn init(target: *LargeStruct) !void {
    target.* = .{
        // in-place initialization
    };
}

fn main() !void {
    var target: LargeStruct = undefined;
    try target.init();
}

// Avoid:
fn init() !LargeStruct {
    return LargeStruct{
        // moving the initialized object
    };
}
```

In-place init assumes pointer stability and immovable types, eliminates intermediate copy-move allocations. **Viral**: if any field is in-place, the entire container should be.

### Variable Proximity

- Calculate/check variables close to where they are used.
- Don't introduce before needed. Don't leave around after.
- Reduces POCPOU (place-of-check to place-of-use) bugs.

### Return Type Simplicity

Prefer simpler return types to reduce dimensionality at call sites (viral through call chains):

`void` > `bool` > `u64` > `?u64` > `!u64`

### Function Completion

Functions should run to completion without suspending. Precondition assertions remain valid throughout.

### Buffer Bleeds

Guard against buffer underflows where padding isn't zeroed. Can leak sensitive information and violate deterministic guarantees.

### Resource Grouping

Use newlines to group allocation with corresponding `defer`:

```zig
const resource = try allocate();
defer release(resource);

// use resource...
```

Makes leaks easier to spot.

## Off-By-One Errors

### Index vs Count vs Size

These are distinct despite being primitive integers:

- **Index**: 0-based
- **Count**: 1-based (index + 1)
- **Size**: count × unit size

Include units and qualifiers in variable names to prevent confusion.

### Division Intent

Use `@divExact()`, `@divFloor()`, or `div_ceil()` to show intent. Communicates that rounding scenarios have been considered.

## Formatting

Formatting is enforced by `zig fmt`, plus whatever linter the project runs. Line length comes from the project's own lint config.

## Documentation & Comments

- **Always say why**, not just what.
- Commit messages inform and delight — they're permanent in git history (PR descriptions are not).
- Comments are sentences: space after `//`, capital letter, full stop or colon.
- End-of-line comments can be phrases without punctuation.
- For tests, include description explaining goal and methodology.

## Dependencies

Zero dependencies beyond the Zig toolchain. Dependencies introduce supply chain risks, safety/performance concerns, and installation overhead.

## Tooling

Standardize on Zig. Write scripts as `scripts/*.zig` rather than shell scripts — cross-platform, type-safe, and consistent across the team.
