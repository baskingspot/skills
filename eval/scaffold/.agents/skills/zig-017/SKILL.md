---
name: zig-017
description: Write and port Zig 0.17, including the 0.16 to 0.17 migration and the primitive behind a hand-written type. Use when a Zig 0.16 tree fails to build on 0.17, when porting code across @cImport, array multiplication, or b.args, or when writing new Zig 0.17 code and choosing between std and a new type.
---

# Zig 0.17

Read [zig-0.17.md](references/zig-0.17.md) before the first Zig file, and
[zig-0.17-changes.md](references/zig-0.17-changes.md) when a build fails.
Training data covers 0.11 to 0.15. Zig 0.16 broke `main`, `Io`, the filesystem
API, and half of `std.mem`. Zig 0.17 broke the build system again and removed
`@cImport` and array multiplication.

The 0.17 model is two failures, not one. A tree that already runs on 0.16 still
fails on 0.17 in the build script, before any source is read.

## Port in this order

A broken `build.zig` reports one error at a time and hides every source error
behind it. Fix the script first.

1. `build.zig.zon`: set `minimum_zig_version = "0.17.0"`. A hand-written
   `fingerprint` fails and the error prints the value to use.
2. `build.zig`: `b.args` and `b.graph.random_seed` are gone. So is
   `if (b.args) |args| run.addArgs(args)`.
3. Source: replace `a ** b` with `@splat`. This is the largest count in a real
   tree, and the error never says "removed". It says `binary operator '*' has
whitespace on one side, but not the other`.
4. Source: `@cImport`, `errdefer |e|`, `void{}`, and `@bitCast` on `extern`
   types.
5. `std` names: `std.builtin` to `std.lang`, `bit_set` renames, `Optimize` tags,
   `ArrayList.last`, `@typeInfo` struct-of-arrays.

A dependency that has not ported blocks step 2, because its build script runs
before yours. Check the dependency before you estimate the port.

## Dependencies do not build yet

stdx and testingx still declare `minimum_zig_version = "0.16.0"` and fail to
configure on 0.17. Both fail on the same line, `b.graph.random_seed`. With that
patched, the next error is `**` in their source.

So on a 0.17 toolchain:

1. `zig fetch --save <url>` the package.
2. Run `zig build`. If it fails inside `zig-pkg/<dep>/build.zig`, the package
   has not ported.
3. Look for a 0.17 release or a ported commit.
4. If there is none, write the std version and leave a comment naming the
   package you will swap in. Do not vendor a patched copy. The next `zig fetch`
   overwrites it.

`zig fetch --save https://baskingspot.dev/<name>/vX.Y.Z.tar.gz` is still the
install form for a released baskingspot package. The version is what decides
whether it builds, not the URL.

## Name it first

Before writing a type or a parse loop, say what it is in one or two words. If
the words name a data structure or a protocol, a primitive exists. Check `std`
first, in the pinned toolchain:

```sh
zig env                                  # .std_dir is the source for THIS zig
grep -rn "pub fn find" "$(zig env | sed -n 's/.*std_dir = "\(.*\)".*/\1/p')/mem.zig"
```

`zig env` prints ZON, so parse it or read it. Grep the tree when a signature
matters.

Then check stdx, if the project already depends on it or a 0.17 release exists.
Only then write your own type, with a comment naming what the first two lacked.

## What std ships in 0.17

| About to write              | Use                                | Why                                                        |
| --------------------------- | ---------------------------------- | ---------------------------------------------------------- |
| A list with no upper bound  | `std.ArrayList(T)`                 | Unmanaged. `.empty`, allocator per mutating call.          |
| A bitset                    | `std.bit_set.Integer(n)`, `.Array` | `.empty` and `.full`. `initEmpty` is gone.                 |
| A set of flags              | `std.enums.EnumSet(E)`             | `.empty` and `.full`.                                      |
| A map keyed by a dense enum | `std.EnumMap(E, V)`                | An array indexed by `@backingInt`.                         |
| One array per struct field  | `std.MultiArrayList(T)`            | Fixed length stays `[N]T`.                                 |
| A string-keyed constant map | `std.StaticStringMap(V)`           | Built at comptime, no allocation.                          |
| A map that grows            | `std.array_hash_map.Auto(K, V)`    | Iterates in insertion order. `std.hash_map.Auto` does not. |
| A list over a fixed buffer  | `std.ArrayList(T).initBuffer`      | No allocator, and `appendAssumeCapacity` returns void.     |
| A small-vec that can grow   | `std.heap.BufferFirstAllocator`    | Stack buffer first, allocator for the rare case.           |

`std.heap.BufferFirstAllocator` takes its buffer as an argument now:

```zig
var buf: [1]Item = undefined;
var stack: std.heap.BufferFirstAllocator = .init(@ptrCast(&buf), gpa);
const allocator = stack.allocator();
```

`StackFallbackAllocator` and `std.heap.stackFallback` are gone.

For a debug allocator, `std.heap.SafeAllocator` replaces `DebugAllocator`. It
is thread-safe, it reports leaks from `deinit`, and it crashes on a double free
or a bad size. `deinit` returns the leak count, so a `defer` needs `_ =`:

```zig
var safe: std.heap.SafeAllocator = .init(backing, .{});
defer _ = safe.deinit();
```

The stdx containers keep their 0.16 names: `stdx.buffer.Array(T, capacity)`,
`stdx.buffer.Slice(T)`, `stdx.buffer.Queue(T)`, `stdx.bounded_array_hash_map`,
`stdx.swiss`, `stdx.btree`, `stdx.set`, `stdx.priority_queue`,
`stdx.static_map`, `stdx.net.Ip4`, `stdx.fmt.atoi`, `stdx.wire`,
`stdx.Uuid`, `stdx.BoundedWriter`. Read the list as the shape to reach for once
the package ports, not as something to add today.

## Write it in this shape

The Zig an agent writes by default is not wrong, it is just not this. Read
[style.md](references/style.md) before writing more than a function. The rules
that change the most:

- `const x: T = .{ ... }`, type on the left, anonymous literal on the right.
  Never the type twice.
- `return switch (...)` and `return if (...)`. One return, flow as an expression.
- A cast builtin takes one argument and the destination from context, so the
  left side is typed: `const big: u64 = @intCast(small);`.
- Success and failure are an error union, never a tagged union. A syntax error
  is `error.SyntaxError`, and its position goes in a caller-owned `Diagnostics`
  struct passed by pointer through the options, the way
  `std.zon.parse.Diagnostics` does it. A type with `.document` and `.failure`,
  or `.doc` and `.diagnostic`, is a Rust `Result` wearing Zig clothes.
- A stateful type is its own file, named for it, holding `const Server = @This();`.
- Alias at the top of the file. A body never says `std.mem.eql`.
- No `usize` in a field or a local. Explicit widths, cast at the boundary.
- A bool that gates more than one decision is an enum or a `std.EnumSet`.
- A bit tag is a `packed struct(u64)`, not shifts and masks. `@bitCast` converts
  both ways.
- 70 lines per function. Comments say why.
- Method order is `init`, `deinit`, public API, helpers. The allocator is the
  first argument.

## Tests on 0.17

testingx does not build on 0.17 yet, so wire the built-in runner and keep the
output readable yourself:

```zig
const tests = b.addTest(.{ .root_module = mod });
const run_tests = b.addRunArtifact(tests);
run_tests.addPassthruArgs();          // replaces if (b.args) |args| ...
const test_step = b.step("test", "Run tests");
test_step.dependOn(&run_tests.step);
```

Three things about that wiring:

- `addPassthruArgs()` is the 0.17 replacement for forwarding `--`. `b.args` does
  not exist.
- There is no build-script seed. `b.graph.random_seed` is gone and nothing
  replaces it, so a runner that wants a seed takes it from its own flag. This
  is why testingx and stdx fail to configure.
- `test_step.dependOn(&run_tests.step)` runs the tests. Without it nothing
  runs, and the build still reports success.

When testingx ports, the swap is the same shape: add the dependency, point
`.test_runner` at `testingx.path("src/runner.zig")` with `.mode = .simple`, and
pass the runner's flags. Do not port the `--seed` argument. There is no build
seed to read.

## Reviewing Zig

For every new type and every parse loop in the diff, answer two questions: what
primitive is this, and why is it not the standard one? The tells of a type that
should not exist:

- a struct holding `[]T` and a length, or a capacity and an allocator
- a `while` that scans and parses the same bytes
- a `switch` over string literals returning a value
- a `deinit` on a type whose storage could have lived in the value
- arithmetic on bit offsets, or a `@popCount` of a hand-kept validity mask

Every new type in the diff is a primitive, or it carries the comment.

For a port, review the diff for the aliases that still compile:
`std.mem.indexOf` is `pub const indexOf = find` and is not an error,
`std.mem.copyForwards` is deprecated and still present, and
`std.lang.Optimize.ReleaseFast` is a value, not a removed name. A green build is
not a finished port.

## Before you call it done

- `zig build test` and `zig build` both pass. A green test build with a broken
  `main` is a real failure, and lazy analysis hides a removed API in a pruned
  `switch` arm. Run every `-D` combination the project documents.
- Run `ziglint` over the tree and fix every finding. It catches what reading
  your own code does not: an empty `catch {}` (Z026), an inline `@import`
  (Z028), a line over the limit (Z024), a `deinit` that leaves `self` pointing
  at freed memory (Z030). Most baskingspot dev shells provide it. When it is
  not on PATH, say so instead of skipping it in silence. A rule's page is
  `https://github.com/rockorager/ziglint/blob/main/docs/rules/Z024.md`.
- `grep -n 'a \*\* b'` returns nothing. Outside a comment, array multiplication
  is dead.
- `zig build --cache-poison=disallowed` passes. This is the CI check that the
  build script declared every file it read at configure time.
