# Zig 0.17

Training data covers Zig 0.11 to 0.15 at best. 0.16 moved `main`, `Io`, the
filesystem API, and half of `std.mem`. 0.17 moved `std.builtin` to `std.lang`,
removed array multiplication and `@cImport`, and rebuilt the build system. Both
are breaking, and the second one breaks a build script that the first one
already fixed.

Rule zero: check the API against the pinned toolchain, not memory.

```sh
zig env                     # .std_dir is the std source for THIS zig
```

`zig env` prints ZON, not JSON. Grep `.std_dir` when a signature matters. It is
the source of truth, it is in the toolchain, and it is cheap. `zigdoc` reads the
same source more comfortably when you have it
([rockorager/zigdoc](https://github.com/rockorager/zigdoc)).

The 0.16 to 0.17 delta has its own file:
[zig-0.17-changes.md](zig-0.17-changes.md). Read that when a build fails. This
file is what 0.17 looks like once it builds.

## "Removed" usually means "moved" or "aliased"

Zig keeps a deprecated alias for a release before it removes the name. A build
that succeeds is not evidence that the name is current, and a name that is gone
is not evidence that the capability is:

- `std.mem.indexOf` is `pub const indexOf = find`, marked deprecated. It
  compiles. `std.mem.copyForwards` compiles and its doc comment says to use
  `@memmove`. Neither is a compile error in 0.17, so a grep is the only way to
  find stale call sites.
- `@cImport` is the opposite case: it is a hard error, not a warning.
- `std.builtin` is still there as `pub const builtin = lang`. Code that says
  `std.builtin.OptimizeMode` compiles.

A vtable grep takes ten seconds and beats a guess:

```sh
grep -n 'pub fn\|pub const' "$(zig env | sed -n 's/.*std_dir = "\(.*\)".*/\1/p')/Io.zig"
```

## `main` takes `std.process.Init`

```zig
pub fn main(init: std.process.Init) !void {
    const gpa = init.gpa;                        // general purpose, threadsafe
    const io = init.io;                          // the default Io implementation
    const arena = init.arena.allocator();        // process lifetime, threadsafe
    const args = try init.minimal.args.toSlice(arena);
    // init.environ_map is a *Environ.Map
}
```

- argv and environ exist only through this parameter. There is no global argv
  and no `getenv`.
- `init.environ.getPosix("HOME")` for one variable, `init.environ_map` for the
  map. Pass what a function needs down as a parameter.
- `std.process.Init.Minimal` is the smaller variant: argv and environ only.
- In tests, `std.testing.io` is the `Io` and `std.testing.environ` is the
  environment.

## I/O is an interface

Anything that can block or introduce nondeterminism takes an `Io` value. It is
passed by value. Implementations fill a vtable, so a custom `Io` is legal.

```zig
const buffer = try std.Io.Dir.cwd().readFileAlloc(io, "conf.toml", gpa, .limited(1 << 20));

var buf: [4096]u8 = undefined;
var writer: std.Io.File.Writer = .init(.stdout(), io, &buf);
defer writer.interface.flush() catch {};
try writer.interface.print("hello {s}\n", .{"world"});

var reader = file.reader(io, &.{});          // &.{} is an unbuffered read
const bytes = try reader.interface.allocRemaining(gpa, .limited(max));

try file.writeStreamingAll(io, "hello");     // one-shot, no buffer
try file.close(io);                          // close takes the io
```

- `std.Io.Writer = .fixed(buffer)` and `std.Io.Reader = .fixed(data)` replace
  the old `FixedBufferStream`. `Allocating` builds a slice.
- `std.fs.File` and `std.fs.Dir` do not exist. The filesystem is `std.Io.File`
  and `std.Io.Dir`, and every method takes `io`.
- No `Io` in scope: `var threaded: std.Io.Threaded = .init_single_threaded;`
  gives you one. Treat that as a workaround in a program that has not been
  threaded yet, not as a pattern.
- `Io.Threaded` is the complete implementation and the default. `Io.Evented`,
  `Io.Uring`, and `Io.Kqueue` are incomplete, and `Io.Evented` has no networking.
- Alias `const Io = std.Io;` per file and call the method form,
  `io.sleep(...)`, not `Io.sleep(io, ...)`.

## Time and randomness

`std.time` is unit constants and `std.time.epoch`. It has no clock.

```zig
const mono = std.Io.Timestamp.now(io, .awake);   // monotonic, no error union
const wall = std.Io.Timestamp.now(io, .real);
const d = mono.durationTo(wall);

var bytes: [32]u8 = undefined;
io.random(&bytes);                                // io.randomSecure for secrets
```

`Io.Timestamp` and `Io.Duration` are plain values. `.{ .nanoseconds = n }`
constructs one with no `io`. For a `std.Random` interface, seed a
`std.Random.DefaultPrng` once per thread from `io.random` and keep it. Do not
return a `Random` from a helper: `std.Random.IoSource` hands back a value that
borrows the source, and the borrow dangles.

In tests, `var prng: std.Random.DefaultPrng = .init(std.testing.random_seed);`
at the test site.

## The lazy-analysis landmine

Zig analyzes lazily. A `switch` on a comptime-known build option never analyzes
the dead arms, so a call to an API that no longer exists can hide in a pruned
arm and survive every green build.

Build the option matrix, not the default. Run `zig build test` and `zig build`,
because a green test build with a broken `main` is a real failure mode, and run
every `-D` combination the project documents.

## `std.posix` is thin

54 functions remain. The set has not moved between 0.16 and 0.17. Survivors
include `read`, `setsockopt`, `mmap`, `munmap`, `kill`, `raise`, `openat`,
`sched_getaffinity`, the signal-set helpers, and `sigaltstack`. There is no
`std.posix.write`.

When the wrapper you want is missing, go higher (`std.Io`) or lower
(`std.posix.system`, which is `std.os.linux` without libc and `std.c` with it).
The raw layer has its own reference: [linux-raw-layer.md](linux-raw-layer.md).

Two landmines that have not moved:

- `std.Io.net.IpAddress.ConnectOptions` and `ListenOptions` declare `mode` with
  no default, so `.{ .mode = .stream }` is mandatory. `protocol` and `timeout`
  have defaults.
- `std.posix.setsockopt` maps `EINVAL` to `unreachable`, which is undefined
  behaviour in `ReleaseFast`. For an option where `EINVAL` is a real failure,
  use the raw layer and decode errno.

## Io error sets are narrow

An `Io` call fails with its own small error set, and `try` does not widen it into
a broader one. Declare what the function returns and map into it:

```zig
fn readAll(r: *Io.Reader) error{ ReadFailed, OutOfMemory }!void {
    const bytes = r.allocRemaining(gpa, .limited(n)) catch |e| switch (e) {
        error.OutOfMemory => return error.OutOfMemory,
        error.ReadFailed => return error.ReadFailed,
        error.StreamTooLong => return error.ReadFailed,
    };
    defer gpa.free(bytes);
}
```

The compiler names both sets in the message. Read it as a list of errors you did
not handle.

## Containers, by 0.17 name

| About to write              | Use                                | Why                                                    |
| --------------------------- | ---------------------------------- | ------------------------------------------------------ |
| A list with no upper bound  | `std.ArrayList(T)`                 | Unmanaged. Init `.empty`, pass the allocator per call. |
| A bitset                    | `std.bit_set.Integer(n)`, `.Array` | `.empty` and `.full`, not `initEmpty`/`initFull`.      |
| A set of flags              | `std.enums.EnumSet(E)`             | `.empty` and `.full`.                                  |
| A map keyed by a dense enum | `std.EnumMap(E, V)`                | An array indexed by `@backingInt`.                     |
| One array per struct field  | `std.MultiArrayList(T)`            | Fixed length stays a plain `[N]T`.                     |
| Cursive-free string lookup  | `std.StaticStringMap(V)`           | Built at comptime.                                     |

The stdx containers in the 0.16 skill are named the same way in 0.17, but the
package does not build on 0.17 yet. See [Dependencies](#dependencies-on-a-017-toolchain).

## Dependencies on a 0.17 toolchain

stdx v0.2.1 and testingx v0.3.0 declare `minimum_zig_version = "0.16.0"`, and
both fail to configure under 0.17. The first error is in their own build
scripts:

```
error: no field named 'random_seed' in struct 'Build.Graph'
```

With that patched out, the next failure is in the source:

```
error: binary operator '*' has whitespace on one side, but not the other
```

So the order of operations in a 0.17 project is:

1. `zig fetch --save <url>` the package you want.
2. Run `zig build`. If it fails in `zig-pkg/<dep>/build.zig`, the package has
   not ported.
3. Read the package's own release notes, or pin a commit that has ported.
4. If there is no 0.17 release, write the std version and leave a comment
   naming the package you will swap in. Do not vendor a patched copy: the next
   `zig fetch` overwrites it.

## The build script

This is the shape `zig init` writes in 0.17. It builds and its `test` and `run`
steps work.

```zig
const std = @import("std");

pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});

    const mod = b.addModule("demo", .{
        .root_source_file = b.path("src/root.zig"),
        .target = target,
        .optimize = optimize,
    });

    const exe = b.addExecutable(.{
        .name = "demo",
        .root_module = b.createModule(.{
            .root_source_file = b.path("src/main.zig"),
            .target = target,
            .optimize = optimize,
            .imports = &.{.{ .name = "demo", .module = mod }},
        }),
    });
    b.installArtifact(exe);

    const run_step = b.step("run", "Run it");
    const run_cmd = b.addRunArtifact(exe);
    run_cmd.step.dependOn(b.getInstallStep());
    run_cmd.addPassthruArgs();          // 0.17: b.args is gone
    run_step.dependOn(&run_cmd.step);

    const tests = b.addTest(.{ .root_module = mod });
    const run_tests = b.addRunArtifact(tests);
    run_tests.addPassthruArgs();
    const test_step = b.step("test", "Run tests");
    test_step.dependOn(&run_tests.step);
}
```

Things that changed and will bite:

- `addPassthruArgs()` replaces `if (b.args) |args| run.addArgs(args)`. `b.args`
  is a compile error now.
- `b.graph.random_seed` is gone, with no replacement for a build script. A test
  runner that wants a seed gets it from its own flag.
- `b.build_root` is `b.root`.
- `b.addFmt(.{ .paths = b.pathList(&.{ "src" }) })`, because `paths` is
  `LazyPath` now.
- `findProgram` searches during configuration and poisons the config cache.
  `findProgramLazy` returns a `LazyPath` and does not. Prefer the lazy one.
- Reading a file or the environment at configure time is now visible to the
  build system as cache poisoning. Declare it with `b.dependOnFileContents` and
  friends, or pass `--cache-poison=disallowed` in CI to catch it.
- A hand-written `fingerprint` in `build.zig.zon` is rejected, and the error
  prints the value to use.

`zig build --print-configuration` writes the resolved graph as ZON. `zig build
--listen=-` serves the build server protocol.

## Formatting

`{f}` calls a type's `format` method. `{q}` escapes for a double-quoted string
literal and now passes UTF-8 through. `{qf}` quote-escapes the output of a
`format`. `{s}`, `{d}`, `{x}`, and `{t}` are unchanged. `{D}` does not exist;
print an `std.Io.Duration` with `{f}`.

A custom formatter is:

```zig
pub fn format(self: @This(), w: *std.Io.Writer) std.Io.Writer.Error!void
```

`std.fmt.allocPrint` compiles and is deprecated. `allocator.print` is the
replacement, and it exists on `ArenaAllocator`, so `arena.print` works.

## Cast builtins are inferred

`@ptrCast`, `@intCast`, `@alignCast`, `@bitCast`, and `@fromBackingInt` take one
argument and take the destination from context, so the left side has to be
typed:

```zig
const big: u64 = @intCast(small);
const p: *const Header = @ptrCast(@alignCast(bytes));
const tag: Tag = @fromBackingInt(@as(u8, 2));
```

`@backingInt` is the exception: it takes a value and returns the integer.
