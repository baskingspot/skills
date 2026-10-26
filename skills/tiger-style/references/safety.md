# Tiger Style — Safety

> "The rules act like the seat-belt in your car: initially they are perhaps a little uncomfortable, but after a while their use becomes second-nature and not using them becomes unimaginable." — Gerard J. Holzmann

Based on [NASA's Power of Ten — Rules for Developing Safety Critical Code](https://spinroot.com/gerard/pdf/P10.pdf).

## Control Flow & Structure

- Use only very simple, explicit control flow. No recursion — ensures all executions that should be bounded are bounded.
- Use only a minimum of excellent abstractions. Every abstraction introduces the risk of a leaky abstraction. Abstractions are never zero cost.
- **Hard limit: 70 lines per function.**
  - Good function shape: few parameters, simple return type, meaty logic between braces.
  - Centralize control flow: keep `switch`/`if` in parent function, push non-branchy logic to helpers.
  - Centralize state manipulation: parent keeps state in locals, helpers compute what needs to change.
  - Keep leaf functions pure. ["Push `if`s up and `for`s down."](https://matklad.github.io/2023/11/15/push-ifs-up-and-fors-down.html)

## Bounds & Limits

- Put a limit on everything. All loops and queues must have a fixed upper bound.
- Follows "fail-fast" principle: violations detected sooner rather than later.
- Where a loop cannot terminate (e.g. event loop), this must be asserted.
- Use explicitly-sized types like `u32` — avoid architecture-specific `usize`.

## Assertions

Assertions detect programmer errors. Unlike operating errors, assertion failures are unexpected. The only correct way to handle corrupt code is to crash. Assertions downgrade catastrophic correctness bugs into liveness bugs and are a force multiplier for fuzzing.

### Density & Coverage

- **Minimum two assertions per function** on average.
- Assert all function arguments, return values, pre/postconditions, and invariants.
- A function must not operate blindly on data it has not checked.

### Pair Assertions

For every property, find at least two different code paths where an assertion can be added. Example: assert data validity before writing to disk AND immediately after reading from disk.

### Assertion Techniques

- May use a blatantly true assertion instead of a comment as stronger documentation where the condition is critical and surprising.
- Split compound assertions: `assert(a); assert(b);` over `assert(a and b);` — simpler to read, more precise on failure.
- Use single-line `if` for implications: `if (a) assert(b);`.
- Assert compile-time constant relationships as sanity checks and to document/enforce subtle invariants or type sizes.

### Positive & Negative Space

The golden rule: assert the positive space you expect AND the negative space you don't expect. Interesting bugs are found where data moves across the valid/invalid boundary. Tests must test exhaustively with valid and invalid data, and as valid data becomes invalid.

### Assertions Are Not a Substitute

- Build a precise mental model of the code first.
- Encode understanding as assertions.
- Write code and comments to explain and justify the model to reviewers.
- Use fuzzing as the final line of defense.

## Memory Management

- **Minimize dynamic allocations.** Favor static allocation, stack allocation, and arena allocators over ad-hoc heap usage.
- When dynamic allocation is necessary, prefer deterministic patterns: arena-per-request, pre-allocated pools, or bounded caches.
- Avoid unbounded allocations that grow with input size without explicit limits.
- The goal is predictable performance and reduced risk of use-after-free — not zero allocation at all costs.
- Consider all memory usage patterns upfront as part of the design, even when dynamic allocation is used.

## Variable Scope

- Declare at the smallest possible scope.
- Minimize number of variables in scope.
- Reduces probability of misuse.

## Compound Conditions

- Split into nested `if/else` branches — makes branches and cases clear.
- Split complex `else if` chains into `else { if { } }` trees.
- Consider whether a single `if` also needs a matching `else` to handle both spaces.

## Positive Invariants

State invariants positively:

```zig
// Prefer:
if (index < length) {
    // The invariant holds.
} else {
    // The invariant doesn't hold.
}

// Avoid:
if (index >= length) {
    // It's not true that the invariant holds.
}
```

## Error Handling

All errors must be handled. 92% of catastrophic system failures result from incorrect handling of non-fatal errors explicitly signaled in software.

## External Interactions

Don't react directly to external events. Run your program at its own pace:

- Keeps control flow under your control.
- Enables batching instead of context switching on every event.
- Maintains bounds on work per time period.

## Compiler Warnings

Appreciate all compiler warnings at the compiler's strictest setting from day one.

## Library Defaults

Explicitly pass all options to library functions at the call site. Never rely on defaults. Example:

```zig
// Prefer:
@prefetch(a, .{ .cache = .data, .rw = .read, .locality = 3 });

// Avoid:
@prefetch(a, .{});
```

## Documentation

Always motivate, always say why. Explaining rationale increases understanding, compliance, and shares criteria for evaluating decisions.
