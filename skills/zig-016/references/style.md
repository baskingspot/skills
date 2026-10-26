# The shape of the Zig

The default Zig an agent writes is not wrong. It is just not this. These are the
rules that change what the code looks like, not what it does, and they are the
ones an agent will not arrive at on its own.

A project may adopt a stricter doctrine, such as TigerBeetle's Tiger Style. That
doctrine is opt-in, it is applied on purpose, and where it disagrees with this
file it wins.

## Expression shape

- Type on the left, anonymous literal on the right: `var x: Foo = .init(a, b);`,
  `const opts: Options = .{ .field = value };`. Never name the type twice. The
  exception is a `return`, where the signature already carries it: `return .{ .field = value };`.
- Control flow as an expression: `return switch (...)`, `return if (...)`. One
  return, not a return in every branch. Collapse `if (cond) return a; return b;`.
- `try` at the call, a centralized `catch` where the error is handled. Drop
  `try` where nothing can fail.
- `@branchHint(.cold)` on the rare error return.
- Alias a subexpression used twice in one function.
- 70 lines per function. Keep control flow in the parent and push
  pure computation into helpers.

## File structure

1. `//!` module doc. Never `///` at the top of a file.
2. Imports, with short aliases.
3. `const X = @This();` named for the type.
4. A scoped logger, when the project has one.

Hoist `const testing = std.testing;` and keep tests at the bottom of the file
they cover. Method order is `init`, `deinit`, public API, private helpers. The
allocator is the first argument. A `const` becomes `pub const` only when it
leaves the module. Free functions that take an enum become methods on it with a
`comptime self`.

Comments explain why. A threshold, a protocol detail, or a non-obvious ordering
gets a sentence. Document the reason, never the syntax.

A magic number with meaning becomes a named constant or an enum tag. Loop
counters and bytes quoted from a spec can stay bare. A `[N]u8` or a slice with
domain meaning gets a named type alias.

## The file is the type

A stateful type is its own file, named for the type. `Server.zig` holds
`const Server = @This();`, and a consumer imports the file and uses it as the
type. There is no inner `pub const Server = struct { ... }` wrapper.

```zig
// src/Server.zig
const Server = @This();

pub const Config = struct { ... };
const Phase = enum { ... };

config: Config,
ring: Ring,

pub fn init(gpa: Allocator, config: Config) !Server {
    return .{ ... };
}
pub fn deinit(self: *Server) void { ... }
fn dispatch(self: *Server, cqe: linux.io_uring_cqe) !void { ... }

// consumer
const Server = @import("Server.zig");
var server: Server = try .init(gpa, .{});
```

Every file-scope declaration is a member, the tests at the bottom exercise the
real type, and a helper type nests inside the one that owns it.

A file of standalone functions stays lowercase, `sys.zig` or `mem.zig`, and
earns its existence only with real content. One function is not a file.

## Imports: alias densely, never qualify in a body

The import block is the table of contents, so bodies stay short.

```zig
const std = @import("std");
const assert = std.debug.assert;
const mem = std.mem;
const testing = std.testing;
const Io = std.Io;
const Allocator = std.mem.Allocator;
const print = std.debug.print;
const linux = std.os.linux;
const Ring = linux.IoUring;
```

Every std path a body uses gets an alias, including single-use ones. A body
never says `std.mem.eql` or `std.debug.assert`. A deep type path lifts to a
PascalCase alias.

The exception is kernel types in snake_case, `linux.io_uring_cqe` and
`linux.cmsghdr`. They stay qualified, because a PascalCase alias claims it is a
Zig type, and [ziglint](https://github.com/rockorager/ziglint) flags the
mismatch.

## A bool is a smell

`true` and `false` at a call site carry no meaning. A two-variant enum names the
state: `CloseMode = enum { graceful, abortive }`, and `conn.close(.graceful)`
reads. `std.EnumSet(Flag)` holds the flags that can be set at once. A `phase`
enum replaces a pile of booleans and grows into a state machine.

A bool is fine where it is the data: a packed-struct bit, an
`atomic.Value(bool)`, presence that is really `?T != null`, generated code.

The test for a latch: does the bit change behaviour in more than one place? If
yes it is a flag, and it belongs in an `EnumSet`. If it only says something
exists, it is presence. When in doubt, name the state.

## No `usize` in state

Use an explicit width for a struct field or local state: `u64`, `u32`, `u16`.
Sizes stay deterministic instead of tracking the pointer width. `usize` appears
only where a std API demands it, cast at the boundary.

A bit tag is a `packed struct(uN)`, not shift arithmetic. `op: 8, slot: 16,
gen: 16, spare: 24` becomes a `packed struct(u64)` with those fields, and
`@bitCast` converts both directions. The type system does the packing, so there
is no `packTag` and no `unpackTag`.

The first declared field sits at bit 0, so declare least-significant first to
keep a most-significant-first wire layout. Explicit bit alignment on a field is
rejected by the compiler. Nested packed structs and bools are legal fields;
plain structs such as `EnumSet` are not.

## Buffers

A hand-rolled `buf: [N]T` plus `len` is the container the language already
ships. Use `stdx.buffer.Array(T, capacity)` for storage inside the value, and
`stdx.buffer.Slice(T)` for a read cursor over memory you own.

Append when capacity is known good with `appendAssumeCapacity`, not `append`
plus `catch unreachable`. Call `deinit` in teardown.

A list that grows with no known bound is `std.ArrayList(T)`. Never `gpa.alloc`
for a list the type owns.

## Arithmetic and safety

ReleaseFast wraps `+` and `-` silently, truncates `@intCast`, and erases
`std.debug.assert`. Pick the tool by where the operands come from:

- A length, count, or offset from input or the wire is validated in every build
  mode, and returns an error when the failure is recoverable. Check before
  mutating, and order the check so it cannot wrap itself.
- A value the kernel or an ABI reports is checked in every mode.
- A programmer invariant, such as a capacity contract or a refcount, is a
  `std.debug.assert`, paired with an `assumeCapacity`-style sibling.
- Wraparound that is the semantics, such as a generation or an epoch, is written
  with `+%` and `-%` on purpose.

`@panic` is for corruption already in hand, never for input you caught. A
bounds check that fires before damage is recoverable: return the error, unwind
the scope, log loudly. Aborting on something you detected is pure cost, and an
abort reachable from the network is a denial of service.

## Zeroing

`std.crypto.secureZero` for a buffer that can hold secret material. `@memset`
only for hygiene on a buffer that never holds a secret, with a comment saying
so.

The difference is dead-store elimination: the optimizer may drop a `@memset` to
a buffer it can see is dead, and it cannot drop `secureZero`. Classify by what
the buffer can hold, not what it holds where the zeroing happens.

## Logging

Scope the logger per module with `std.log.scoped(.fetch)` rather than reaching
for one global. Pick the level by the consequence, not by how interesting the
line is.
