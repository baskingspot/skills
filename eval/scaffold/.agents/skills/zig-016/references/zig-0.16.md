# Zig 0.16

LLM training data covers Zig 0.11-0.15 at best. Zig 0.16 has massive breaking changes.

Rule zero: verify APIs against the pinned toolchain, not memory.

```bash
zig env                     # .std_dir = the std source for THIS zig
```

`zig env` prints `.std_dir`. Grep that tree when a signature matters. It is the
source of truth, it is in the toolchain, and it is cheap. `zigdoc` is a nicer way
to read the same source when you have it
([rockorager/zigdoc](https://github.com/rockorager/zigdoc)).

## "Removed" usually means "moved" — grep before you hand-roll

0.16 relocated huge API surfaces without renaming the capability. When the
release notes say a type or function was removed, ask where it went before
writing your own:

- `std.posix.ucontext_t` removed → signal-frame parsing lives in `std.debug.cpu_context.fromPosixSignalContext` (gives `getPc`/`getFp` per arch).
- `std.net` DNS "gone" → `std.Io.net.HostName.lookup` / `HostName.connect` is the resolver; `Io.Threaded` implements it. `IpAddress.parse` being literal-only is about parsing, not resolution.
- `std.time.Timer`/`Instant`/`*Timestamp` removed → `std.Io.Timestamp` (below).

All three were relearned the hard way by hand-rolling something std already had. A vtable grep (`grep -n 'netLookup\|pub fn' std/Io.zig`) takes ten seconds.

## Juicy Main — `main` takes `std.process.Init`

```zig
pub fn main(init: std.process.Init) !void {
    const gpa = init.gpa;                          // general purpose allocator, threadsafe
    const io = init.io;                            // default Io implementation
    const arena = init.arena.allocator();          // process-lifetime, threadsafe
    const args = try init.minimal.args.toSlice(init.arena.allocator());
    // init.environ_map: *Environ.Map — env vars are NOT global anymore
}
```

- argv and environ exist **only** through this parameter. Global argv/env access is gone.
- `std.process.Init.Minimal` is the smaller variant (argv + environ only, no gpa/io).
- Use `std.testing.io` in tests, like `std.testing.allocator`. `std.testing.environ` for env.

## I/O as an interface — everything takes `Io`

`std.fs.File` → `std.Io.File`. `std.fs.Dir` → `std.Io.Dir`. `std.fs.cwd()` → `std.Io.Dir.cwd()`. `file.close()` → `file.close(io)`.

```zig
// stdout, buffered:
var buf: [4096]u8 = undefined;
var writer: std.Io.File.Writer = .init(.stdout(), io, &buf);
defer writer.interface.flush() catch {};
try writer.interface.print("hello {s}\n", .{"world"});

// one-shot:
try std.Io.File.stdout().writeStreamingAll(io, "Hello, world!\n");

// reading:
var file_reader = file.reader(io, &.{});          // &.{} = empty buffer, unbuffered
const contents = try file_reader.interface.allocRemaining(allocator, .limited(max));

// FixedBufferStream is gone:
var writer: std.Io.Writer = .fixed(buffer);
var reader: std.Io.Reader = .fixed(data);
```

- No `Io` at hand: `var threaded: std.Io.Threaded = .init_single_threaded; const io = threaded.io();` — a workaround, not a pattern; thread `Io` through instead.
- `Io.Threaded` is complete (the default `init.io`). `Io.Evented`/`Io.Uring`/`Io.Kqueue` are WIP.
- Style: alias `const Io = std.Io;` per file, and use the method form (`io.random(&buf)`, `io.sleep(...)`, `futex.futexWake(io)`), never `Io.random(io, ...)`.

## Clock and randomness in 0.16

`std.time` is unit constants plus `std.time.epoch` — **no clock functions at all**. A `std.time.microTimestamp()` call compiles only when lazy analysis never reaches it (see the landmine section).

- Time reads: `std.Io.Timestamp.now(io, .awake)` (monotonic) or `.now(io, .real)` (wall). `Io.Timestamp` is a plain value type: `.{ .nanoseconds = n }` constructs one with no io, and `durationTo`/`addDuration`/`toSeconds`/`toMilliseconds` are pure value math. Many projects wrap a `timex` module around the raw clock syscall instead of threading io just for time — that is a legitimate pattern.
- Randomness: `io.random(&buf)` for bytes (`io.randomSecure` for secrets). For a `std.Random` interface, seed a `std.Random.DefaultPrng` once per thread from `io.random` and keep it — preferred over `std.Random.IoSource`, whose returned `Random` borrows the IoSource struct: return it from a helper and the borrow dangles. `std.Random.DefaultCsprng` (ChaCha) when the stream should stay unpredictable.
- Tests: `var prng: Random.DefaultPrng = .init(testing.random_seed);` inline at the test site, then `prng.random()`. No helper that vends a `Random` — it needs a fn-local static to keep the borrow alive, which is machinery for a two-line problem.

## The lazy-analysis landmine

Zig analyzes lazily. A `switch` on a comptime-known build option never analyzes dead arms, so a call to a removed API can sit in a pruned arm and survive every green build — until someone builds the other flag combination. Same for code paths only reachable under a different `-D` option.

Defense: build the option matrix, not just the default. Run BOTH `zig build test` AND `zig build` (a green test build with a broken `run()` is a real observed failure mode), and any non-default build flags the project ships.

## `std.posix` was gutted

The medium layer is gone. Survivors include `read`, `setsockopt`, `mmap`/`munmap`, `kill`/`raise`, `openat`, `sched_getaffinity`, signal-set helpers, `sigaltstack`. There is no `std.posix.write` — write through `Io`, or `linux.write` at the raw layer. Everything else: go **higher** (`std.Io`) or **lower** (`std.posix.system` — `std.os.linux` without libc, `std.c` with libc).

**Connecting and listening need `.mode`.** `std.Io.net.ConnectOptions` and
`ListenOptions` declare `mode: Socket.Mode` with no default, so `.{ .mode = .stream }`
is mandatory and `addr.connect(io, .{})` does not compile. `protocol` and
`timeout` do have defaults.

**setsockopt landmine:** `std.posix.setsockopt` maps `EINVAL` to `unreachable` — UB in ReleaseFast. For any option where EINVAL is a legitimate runtime failure, use the raw layer and decode errno yourself. It also type-checks `SO_RCVTIMEO`/`SO_SNDTIMEO`: the `timeval` is validated and a too-large value returns `error.TimeoutTooBig`, so pass microseconds (`std.time.us_per_ms`), not nanoseconds. See [linux-raw-layer.md](linux-raw-layer.md).

## `std.Io` error sets are narrow

An `Io` call fails with its own small error set, and `try` or `catch |e| return e`
will not widen it into a function whose error union is broader. Declare the
error set you actually return and map into it:

```zig
fn readAll(reader: *Io.Reader) Error!void {
    reader.readAlloc(gpa, n) catch |e| switch (e) {
        error.OutOfMemory => return error.OutOfMemory,
        error.ReadFailed => return error.ReadFailed,
        error.StreamTooLong => return error.Truncated,
    };
}
```

The compiler's message names the two sets: `expected type 'error{ReadFailed,
StreamTooLong}', found 'error{EndOfStream}'`. Read it as "these are the errors
you did not account for".

## `std.mem` renames — "index of" is now "find"

`indexOf` → `find`, `indexOfScalar` → `findScalar`, `indexOfAny` → `findAny`, `lastIndexOf` → `findLast`, `indexOfPos` → `findPosLinear` family. Emitting `std.mem.indexOf*` is a compile error now.

## Other 0.16 breaks, one line each

- `@Type` removed → `@Int`, `@Struct`, `@Union`, `@Enum`, `@Pointer`, `@Fn`, `@Tuple`, `@EnumLiteral()`.
- `@cImport` deprecated (still compiles, no warning) → `b.addTranslateC` in build.zig + `const c = @import("c")`. Recipe: [Migrating off @cImport](zig-0.16-changes.md#migrating-off-cimport).
- Sync primitives moved: `Thread.ResetEvent`→`Io.Event`, `WaitGroup`→`Io.Group`, `Futex`→`Io.Futex`, `Mutex`→`Io.Mutex`, `Condition`→`Io.Condition`, `Semaphore`→`Io.Semaphore`. `std.once` and `Thread.Pool` removed. `ArenaAllocator` is threadsafe/lock-free; `ThreadSafeAllocator` removed.
- `std.crypto.random` gone → `io.random(&buf)` / `io.randomSecure(&buf)`.
- `{D}` format specifier removed → `{f}` with `std.Io.Duration`.
- `std.ArrayList` is unmanaged: init `.empty`, allocator per mutating call. `ArrayListUnmanaged` is a deprecated alias.
- Managed containers removed (`AutoArrayHashMap` → `array_hash_map.Auto`, etc.); `PriorityQueue`/`PriorityDequeue` lost their allocator field.
- Cast builtins are single-argument, return type inferred: `const x: DestType = @ptrCast(ptr);`
- Type reflection tags lowercase: `.int`, `.float`, `.@"struct"`, `.@"enum"`.
- Structs/arrays have no `==`; use `std.meta.eql` / `std.mem.eql`.
- Returning the address of a local is a compile error ("expired local variable").
- Pointers are forbidden in `packed struct`/`packed union`. `extern` enums/packed types need explicit backing ints.
- Runtime vector indexing is forbidden — coerce to array first.
- Error renames: `RenameAcrossMountPoints`/`NotSameFileSystem`→`CrossDevice`, `SharingViolation`→`FileBusy`, `EnvironmentVariableNotFound`→`EnvironmentVariableMissing`.
- Child processes: `std.process.spawn(io, .{ ... })`, `std.process.run(allocator, io, .{...})`.
- `std.meta.intToEnum` → `std.enums.fromInt` (returns `?Enum`, not an error union — `orelse`, not `catch`).
- `std.mem.copyForwards`/`copyBackwards` → the `@memmove` builtin.

Build system: `b.addExecutable(.{ .name, .root_module = b.createModule(.{ .root_source_file = b.path("src/main.zig"), .target, .optimize }) })`; `addStaticLibrary()` → `addLibrary(.{ .linkage = .static })`; path strings → `b.path(...)` LazyPaths.

## Security footgun: narrow-type arithmetic in bounds checks

Zig evaluates `narrow_type + comptime_int` in the narrow type **before** widening for the comparison:

```zig
const len = r.assumeRead(u16);           // attacker-controlled length
if (remaining < len + 5) return error.UnexpectedEof;   // BUG: len + 5 overflows u16
```

panics (Debug/ReleaseSafe) or is UB (ReleaseFast) before the comparison rejects the oversized input. Remote DoS class. No linter catches it. Always widen first:

```zig
if (remaining < @as(usize, len) + 5) return error.UnexpectedEof;
```

## Style

- `camelCase` functions, `snake_case` variables/constants, `PascalCase` types.
- Prefer `const foo: Type = .{ .field = value };` over `const foo = Type{...};`.
- File order: `//!` doc, `const Self = @This();`, imports, `const log = std.log.scoped(...)`.
- Allocators explicit; `errdefer` for cleanup on error paths.
- Use `@splat` for uniform array/vector init: `const mask: [4]u8 = @splat(0);`
- Extract type aliases for repeated semantic types (`const RecordLen = u16;`, not bare `u16` in every signature).
- Tests inline with the code they cover.
- Comments explain why, not what.

## Before writing Zig code

1. `zig env` and a grep for any std API you are not certain of. 0.16 renamed too much to guess.
2. If a capability seems missing, grep `.std_dir` for where it moved before hand-rolling it.
3. Read existing code in the project first; match established patterns.
4. After writing, run `zig build test`, `zig build`, and every non-default build-flag combination the project documents.

## Running one module's tests standalone (with dependency modules)

To run one module's tests outside `zig build`, for a faster loop and direct
stderr, pass the dependency modules on the command line. Each `--dep NAME` comes
before the `-MNAME=...` that uses it:

```sh
zig test src/root.zig \
  --dep dep --Mroot=src/root.zig \
  --dep dep_options --Mdep=zig-pkg/dep-*/src/root.zig
```

- `error: module 'X' declared but not used` means the root source file never
  references `@import("X")`. Wire only the dependencies the root imports.
- A dependency whose module needs a generated companion module, such as a
  `build_options` module, needs that companion named here too. Its `build.zig`
  says which.
- A test runner that prints per suite can hide which vector failed inside a
  table test. A temporary print in the table runner is faster than a binary
  search.
