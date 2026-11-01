# Zig 0.17 changes, 0.16 to 0.17

Checked against zig 0.17.0 on aarch64-linux, and against the std tree that
`zig env` prints. Every error message quoted here came out of that compiler.

Where the release notes and the compiler disagree, this file follows the
compiler. The disagreements are listed at the end.

## Table of contents

1. [Port order](#port-order)
2. [build.zig.zon](#buildzigzon)
3. [build.zig](#buildzig-1)
4. [Language](#language)
5. [Standard library](#standard-library)
6. [Toolchain](#toolchain)
7. [Where the notes are wrong](#where-the-notes-are-wrong)

## Port order

Fix the build script before the source. A broken `build.zig` reports one error
at a time and hides every source error behind it.

1. Bump `minimum_zig_version` in `build.zig.zon`.
2. Fix `build.zig`. Expect `b.args` and `b.graph.random_seed`.
3. Replace array multiplication. It is the largest source-level count in a
   real tree.
4. Fix the rest of `std`, then the language changes.

A dependency that has not ported blocks the build at step 2, because its own
`build.zig` runs first. Check the dependency before timing the port.

## build.zig.zon

`minimum_zig_version` becomes `"0.17.0"`.

A hand-written `fingerprint` fails:

```
error: invalid fingerprint: 0x1; if this is a new or forked package, use this value: 0xd642dfa087b3dd34
```

Take the value the compiler prints. Do not invent one.

## build.zig

### `b.args` is gone

```
error: no field named 'args' in struct 'Build'
```

Run arguments are no longer visible while the build graph is configured. They
attach to a `Run` step instead:

```zig
- if (b.args) |args| run_cmd.addArgs(args);
+ run_cmd.addPassthruArgs();
```

This breaks every build script that forwards `--`. It also breaks each of a
dependency's build scripts, which is why a 0.16 package fails to configure on
0.17.

### `b.graph.random_seed` is gone

Not in the release notes. A truncated seed still exists as the `--seed` build
flag, and the build script cannot read it. `std.Build.Graph` has no seed field
and `std.Build` exposes no accessor.

```
error: no field named 'random_seed' in struct 'Build.Graph'
```

testingx and stdx v0.3.0 both pass `--seed=0x{x}` from this field, so both
fail to configure on 0.17. A test runner that takes a seed gets it from the
runner instead: `--seed` is again a CLI flag, this time on the build.

### Renamed and split

| 0.16                                                                                | 0.17                                                       |
| ----------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| `b.build_root` (Directory)                                                          | `b.root` (`Cache.Path`)                                    |
| `b.findProgram(names, paths)`                                                       | `b.findProgram(.{ .names, .search_paths })`, `?[]const u8` |
| no equivalent                                                                       | `b.findProgramLazy(.{ ... })`, returns `LazyPath`          |
| `ConfigHeader.Options.include_guard_override`                                       | `include_guard`                                            |
| `LazyPath.getDisplayName`                                                           | `LazyPath.format`, printed with `{f}`                      |
| `LazyPath.basename`                                                                 | removed, the value is unknown until make phase             |
| `addArtifactArg`, `addPrefixedArtifactArg`                                          | `addArtifactArg2`                                          |
| `addOutputFileArg`, `addPrefixedOutputFileArg`                                      | `addOutputFileArg2`                                        |
| `addDirectoryArg`, `addDecoratedDirectoryArg`                                       | `addDirectoryArg2`                                         |
| `addFileArg`, `addFileContentArg`, `addDepFileOutputArg` and their `Prefixed` forms | the same name with `2`                                     |

`findProgram` searches during configuration, so calling it poisons the
configuration cache. `findProgramLazy` returns a `LazyPath`, searches only if a
step uses the path, and leaves the cache valid. Prefer it. Use `findProgram`
only when the configure logic must see the result, for example to pick a
default value.

### Cache purity

A `build.zig` that reads the filesystem or the environment at configure time
makes the configuration uncacheable. The build system calls this poisoning.
Declare the dependency instead:

```zig
b.dependOnFileContents(lazy_path);
b.dependOnFileMetadata(lazy_path);
b.dependOnDirectoryContents(lazy_path);
b.dependOnDirectoryMetadata(lazy_path);
```

Override the behaviour with `--cache-poison=pure|poisoned|disallowed|ignored`.
`pure` is the default. Use `disallowed` in CI to fail a build script that reads
something it did not declare.

### `AddFmt` takes `LazyPath`

`paths` and `exclude_paths` are `LazyPath` lists now. `b.pathList` builds one:

```zig
const fmt = b.addFmt(.{
    .paths = b.pathList(&.{ "src", "build.zig", "build.zig.zon" }),
    .check = true,
});
```

### Option paths

`addOptionPath` now means "must be a file". A directory is a separate call. The
old behaviour is not available under the old name:

- `addOptionPath` for a file
- `addOptionPathDirectory` for a directory
- `addOptionPathUntracked` to opt out of dependency tracking

### `@cImport` is removed

```
error: invalid builtin function: '@cImport'
```

`std.Build.Step.TranslateC` is deprecated in favour of the ZSF package:

```sh
zig fetch --save git+https://codeberg.org/ziglang/translate-c#zig-0.17.x
```

```zig
const Translator = @import("translate_c").Translator;

const translate_c = b.dependency("translate_c", .{});
const translator: Translator = .init(translate_c, .{
    .c_source_file = b.path("src/c.h"),
    .target = target,
    .optimize = optimize,
    .link_system_libs = &.{.{ .name = "glfw" }},
});
// then .module = translator.mod
```

`addWin32ResourceFile` and the other resource functions are deprecated in the
same way; that package is <https://codeberg.org/ziglang/rc>.

## Language

### Array multiplication is removed

`a ** b` no longer parses and no longer builds an array. The replacement is
`@splat`, which needs the result type from context:

```zig
- var buf = [1]u8{0} ** 4096;
+ var buf: [4096]u8 = @splat(0);
```

The error does not say "removed". It says:

```
error: binary operator '*' has whitespace on one side, but not the other
```

Treat that message as "array multiplication". `grep -n '\*\*'` finds every site,
and the count is high in a real tree: five in stdx alone.

### `@bitCast` reinterprets the logical bits

The new definition is endian-agnostic and is built from each field's logical
bits, not from memory. Integers, floats, bools, void, and enums with an explicit
backing integer still work. Arrays and vectors of those types still work, and
now agree on big-endian targets.

`extern struct` and `extern union` do not:

```
error: cannot @bitCast from 'bitcast.TwoBytes'
```

For type punning, cast a pointer:

```zig
const int_ptr: *align(1) const u16 = @ptrCast(&bytes);
```

A cast into an `enum` now checks the tag. A comptime-known invalid tag is a
compile error:

```
error: enum 'E' has no tag with value '3'
```

A runtime invalid tag is safety-checked Illegal Behavior.

### `@intFromEnum` and `@enumFromInt` are deprecated

The replacements are `@backingInt` and `@fromBackingInt`. `@backingInt` also
works on tagged unions, returning the backing integer of the active tag.

```zig
- return @enumFromInt(graph.generated_files.items.len - 1);
+ return @fromBackingInt(@intCast(graph.generated_files.items.len - 1));
- graph.generated_files.items[@intFromEnum(gen.index)];
+ graph.generated_files.items[@backingInt(gen.index)];
```

`@fromBackingInt` infers its result type, so the left side of the assignment
must be typed. `std.meta.BackingInt(T)` gives the integer type.

An empty enum must be backed by `noreturn`:

```
error: empty exhaustive enums must be backed by 'noreturn'
```

### `errdefer` takes no capture

```zig
- errdefer |err| std.debug.panic("panic: {s}", .{@errorName(err)});
+ f() catch |err| std.debug.panic("panic: {s}", .{@errorName(err)});
```

The block cannot change the returned error, so the binding bought nothing. Move
the function into an inner one that returns the error, and handle it at the
call.

### `void{}` is removed

Use `{}`. The old form fails with `type 'void' does not support array
initialization syntax`.

### `@hasDecl` sees public declarations only

The same file no longer counts as privileged. A private `const` in the current
file is invisible:

```zig
const Foo = struct {
    bar: i32,
    const baz = 1;
    pub var quux: u8 = 0;
};
// @hasDecl(Foo, "bar") is false, so is "baz"; "quux" is true
```

A reflection helper that checked for a private decl now returns false without a
compile error. Audit those call sites.

### Smaller language changes

- `i0` is removed: `error: signed integer cannot have bit width 0`. Use `u0`.
- `std.lang.GlobalLinkage` is `enum(u1) { strong, weak }`. `internal` and
  `link_once` are gone. Use `weak` for `link_once`, and stop exporting the
  symbol for `internal`.
- A slice of comptime-known length now converts to an array and to an array
  pointer: `const array: [3]u16 = slice.*;` and `const p: *const [3]u16 = slice;`.
- `@divCeil` exists. `std.math.divCeil(a, b) catch unreachable` becomes
  `@divCeil(a, b)`. It rounds toward positive infinity: `@divCeil(-5, 3) == -1`.
- `@SpirvType` creates SPIR-V sampler, image, sampled-image, and runtime-array
  types. Outside a SPIR-V target it is a compile error.

## Standard library

### Names

| 0.16                                           | 0.17                                                |
| ---------------------------------------------- | --------------------------------------------------- |
| `std.builtin`                                  | `std.lang` (alias kept)                             |
| `std.gpu`                                      | `std.spirv`                                         |
| `std.bit_set.IntegerBitSet`                    | `std.bit_set.Integer`                               |
| `std.bit_set.ArrayBitSet`                      | `std.bit_set.Array`                                 |
| `std.bit_set.StaticBitSet`                     | `std.bit_set.Static`                                |
| `std.bit_set.DynamicBitSetUnmanaged`           | `std.bit_set.Dynamic`                               |
| `std.bit_set.DynamicBitSet`                    | `std.bit_set.DynamicManaged`, deprecated            |
| `std.enums.EnumSet.initEmpty`/`initFull`       | `.empty` / `.full`                                  |
| `std.meta.fieldInfo`/`fieldNames`/`fieldTypes` | `@typeInfo`                                         |
| `std.ascii.indexOfIgnoreCase`                  | `std.ascii.findIgnoreCase` (and `Pos`, `PosLinear`) |
| `std.mem.readPackedIntNative`/`Foreign`        | `std.mem.readPackedInt`, which takes the endian     |
| `std.mem.writePackedIntNative`/`Foreign`       | `std.mem.writePackedInt`                            |
| `std.DoublyLinkedList.pop`                     | `std.DoublyLinkedList.popLast`                      |
| `std.heap.memory_pool.AlignedManaged`          | `std.heap.memory_pool.Aligned`                      |
| `std.heap.memory_pool.ExtraManaged`            | `std.heap.memory_pool.Extra`                        |

`std.lang.Optimize` replaces `OptimizeMode` and drops "release" from the tags:

```zig
// 0.16
std.builtin.OptimizeMode.ReleaseSafe
// 0.17
std.lang.Optimize.safe
```

The tags are `debug`, `safe`, `fast`, `small`. `Optimize.runtimeSafety` is
preferred over `std.debug.runtime_safety`, because a call site gets knowledge of
its own module. The old tag names are declared as values of the same enum, so a
comparison against `Optimize.ReleaseFast` still compiles. Use the new tags; do
not spend time rewriting call sites that work.

`std.DoublyLinkedList` is not generic and has not been since before 0.16. The
node holds `prev` and `next` and no payload, so `@fieldParentPtr` recovers the
containing struct. If a `pop` call site fails to build, the rename to `popLast`
is the whole fix.

### `@typeInfo` is struct-of-arrays

Structs, unions, and enums report parallel arrays instead of an array of field
structs:

```zig
- inline for (@typeInfo(S).@"struct".fields) |field| {
-     try s.fieldPrefix(field.name);
-     try printValue(field.type, @field(v, field.name));
- }
+ const info = @typeInfo(S).@"struct";
+ inline for (info.field_names, info.field_types) |field_name, field_type| {
+     try s.fieldPrefix(field_name);
+     try printValue(field_type, @field(v, field_name));
+ }
```

`Struct` and `Union` carry `field_names`, `field_types`, `field_attrs`, and
`decl_names`. `Enum` carries `field_names`, `field_values`, and `decl_names`.
`field_attrs` is where a default value, a comptime marker, and an alignment now
live.

### Allocators

`std.heap.SafeAllocator` replaces `std.heap.DebugAllocator`. It is thread-safe,
it does not hand back memory it has freed, it reports every leak from `deinit`,
and it crashes on a double free, on a resize of a bad pointer, and on a size
mismatch. It does this by trailing each allocation with a checksummed footer.
The no-reuse guarantee holds as long as the backing allocator does not reuse.

```zig
var safe: std.heap.SafeAllocator = .init(backing, .{});
defer _ = safe.deinit(); // returns the leak count
const allocator = safe.allocator();
```

`deinit` returns a count, so it needs `_ =` at a `defer`. `DebugAllocator` and
`std.heap.Check` are deprecated.

`BufferFirstAllocator` replaces `StackFallbackAllocator`, and the buffer is now
an argument:

```zig
var stack_buf: [1]Item = undefined;
var stack: std.heap.BufferFirstAllocator = .init(@ptrCast(&stack_buf), gpa);
const allocator = stack.allocator();
```

`std.heap.stackFallback` is removed.

### `ArrayList`

`getLastOrNull` and `getLast` are deprecated. Use `last`, which returns `?T`,
and `lastPtr`, which returns `?*T`.

```zig
- if (list.getLastOrNull()) |foo| { ... }
+ if (list.last()) |foo| { ... }
- const foo = list.getLast();
+ const foo = list.last().?;
```

### Printing

`std.fmt.allocPrint` still compiles and is deprecated. The allocator prints
directly:

```zig
- try std.fmt.allocPrint(arena, "{s}={d}", .{ x, y });
+ try arena.print("{s}={d}", .{ x, y });
```

`Allocator.print` and `Allocator.printSentinel` are the replacements.

`{q}` now passes UTF-8 through, so `café` is escaped without mangling the é.
`{qf}` is new, and quote-escapes the output of a `format`:

```zig
try writer.print("{qf}", .{value}); // "a\"b"
```

### `std.zon.parse` takes struct arguments

Results and diagnostics come from an arena now, and the caller owns neither.

```zig
var diag: std.zon.parse.Diagnostics = undefined;
const result = std.zon.parse.fromSlice(MyType, .{
    .gpa = gpa,
    .arena = arena,
    .source = source,
    .diagnostics = &diag,
}) catch |err| switch (err) {
    error.ParseZon => diag.fatal("input.zon"),
    error.OutOfMemory => return err,
};
```

Renames:

- `fromSliceAlloc` became `fromSlice`.
- `fromSlice` became `fromSliceNoAlloc`.
- Every other `from*` follows the same split.
- `updateFromSlice` and its siblings are new, and overwrite the named fields of
  an existing value.

`fromSliceNoAlloc` asserts at comptime that the type holds no pointers, so a
struct with a `[]const u8` field belongs in `fromSlice`.

### `@import("builtin")` deprecations

`cpu`, `os`, `abi`, and `object_format` are deprecated and go in 0.18.0. The
`target` field has all four:

```zig
- @import("builtin").os.tag
+ @import("builtin").target.os.tag
```

`target.ofmt` is the new name for `object_format`.

### Floats in `mem.eql`

`std.mem.eql` and `std.mem.findDiff` no longer short-circuit on identical
slices when the element type is a float, because `nan != nan`:

```zig
const x: [3]f64 = .{ 42.0, std.math.nan(f64), 3.1415 };
try std.testing.expect(!std.mem.eql(f64, &x, &x));
```

Code that relied on the short-circuit to call two NaN slices equal changes
answer. That is the point.

### `Uri` and `HostName` are separate again

`Uri` no longer validates a host as an RFC1123 host name, because RFC3986 and
RFC1123 disagree. `Uri.getHost` moved and became stricter:

```zig
- const host = try uri.getHost(&host_buf);
+ const host = try std.Io.net.HostName.fromUri(uri, &host_buf);
```

The error set differs, since `fromUri` validates. `Uri.getHostAlloc` is removed
with no replacement.

### Smaller std changes

- `std.mem.containsAtLeastScalar` takes `(T, haystack, element, minimum)`. The
  old `(T, haystack, minimum, element)` order was the previous function's, and
  0.17 reuses the name for the new order. A call site that compiles can now be
  wrong. Grep every call.
- `std.debug.SafetyLock.lock` and `unlock` take no argument. `lockShared` and
  `unlockShared` are new, with `assertLockedShared` to match.
- `std.Io.Semaphore.waitTimeout` is new.
- `std.fs.path` gains `relativeAppend` and `resolveAppend`.
- `std.Target.parseCpuModel` is `Arch.parseCpuModel(name)` and returns
  `?*const Cpu.Model`. It is a method on the arch, not on `Target`.
- `std.hash.crc` had a namespace audit.

## Toolchain

- `-Doptimize` prints `debug`, `safe`, `fast`, `small`. The old names still
  parse on the command line and map onto the new ones, so a script that passes
  `ReleaseSafe` keeps working. The enum tags are the lowercase form only.
- `--print-configuration` writes the resolved graph as ZON on stdout.
- `--listen=-` serves the build server protocol. ZLS is the first consumer and
  is broken on 0.17 in the meantime.
- `zig build -fincremental --watch` is usable for most `x86_64-linux` projects.
  It also runs on aarch64, where the incremental path is less exercised.
- `zig objdump` is new, for object and archive inspection. `--snapshot` redacts
  the values that move between runs.
- `zig fmt --complexity` prints token and AST-node counts, which is a better
  review signal than line count.
- `zig cache-cat` reads the new binary cache format.
- `zig fetch --save` writes the package into the local path as well as the
  global one. `--pkg-path` and `ZIG_LOCAL_PKG_DIR` apply to fetch and build.
- In `libc.txt`, `gcc_dir` became `cc_dir`. The old name is still accepted.
  `cc_dir` is required for Linux, Haiku, and Serenity targets, and a missing one
  is `error.LibCInstallationMissingCcDir`.
- glibc 2.44, musl 1.2.5, Linux 7.2 headers, macOS 27.0 headers,
  LLVM 22.1.8.

## Where the notes are wrong

Two claims in the 0.17.0 release notes do not match the compiler, and one
removal is missing from them. Check all three again on a later patch release.

**`std.lang.Optimize` is not a breaking rename.** The notes say `==` and `!=`
stop working with the old names. `Debug`, `ReleaseSafe`, `ReleaseFast`, and
`ReleaseSmall` are declared as `Optimize` values, so comparison, switch prongs,
and `fromString("ReleaseFast")` all still work:

```zig
pub const ReleaseFast: @This() = .fast;
```

Use the new tags in new code. Old code that compiles is not wrong.

**`std.fmt.allocPrint` is deprecated, not moved.** It still exists and forwards
to `Allocator.print`. The notes' "moved" heading reads as a removal.

**`b.graph.random_seed` is gone and the notes never say so.** The section on
passthru arguments covers `b.args`, and nothing covers the seed. The `--seed`
build flag survives for shuffling dependency traversal, and a build script
cannot read it. Every package that passes a seed to its test runner fails to
configure, which is the first error most ports hit.
