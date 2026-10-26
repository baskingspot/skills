# The Linux raw layer in Zig 0.16

Checked against the std tree that `zig env` prints for 0.16.0 on aarch64-linux.
The numbers and the disappeared functions move with the release, so grep before
relying on any of this.

## The layers

| Layer                  | What it is                                      | Reach for it when                       |
| ---------------------- | ----------------------------------------------- | --------------------------------------- |
| `std.Io`               | the interface; functions take an `Io`           | always first                            |
| `std.posix`            | 54 functions left; the medium layer is gone     | `setsockopt`, `mmap`, signals, `openat` |
| `std.posix.system`     | `std.os.linux` without libc, `std.c` with       | one call the layer above does not wrap  |
| `std.os.linux`         | one wrapper per syscall, each returning `usize` | a syscall that has no portable wrapper  |
| `std.os.linux.IoUring` | the raw ring wrapper                            | io_uring                                |

`syscall0` through `syscall6` live in `std/os/linux/<arch>.zig` and take a
`SYS` value. `SYS` is an arch-switched enum, in `std/os/linux/syscalls.zig`.

## `linux.E` is an enum, not an error set

`linux.E` is a plain enum of errno values. It is not an error set, so
`linux.E!T` is not a type and an errno value is not an error. Declare the error
set the code actually needs and map onto it:

```zig
const SysError = error{ WouldBlock, ConnectionReset, BrokenPipe, Interrupted, Unexpected };

fn toError(e: linux.E) SysError {
    return switch (e) {
        .AGAIN => error.WouldBlock,
        .CONNRESET => error.ConnectionReset,
        .PIPE => error.BrokenPipe,
        .INTR => error.Interrupted,
        else => error.Unexpected,
    };
}

fn check(raw: usize) SysError!u32 {
    const errno = linux.errno(raw);
    return if (errno == .SUCCESS) @intCast(raw) else toError(errno);
}
```

## What `std.posix` still has

54 functions. The ones worth naming: `read`, `setsockopt`, `getpeername`,
`mmap`, `munmap`, `mremap`, `msync`, `kill`, `raise`, `openat`, `getppid`,
`sched_getaffinity`, the signal-set helpers, `sigaltstack`, `sysctl`,
`dl_iterate_phdr`, `reboot`.

Gone: `socket`, `bind`, `listen`, `accept`, `epoll_*`, `pipe2`, `sendmsg`,
`recvmsg`, `splice`, and `fcntl` as a `posix` function. Each lives in
`std.os.linux` under its own name.

## `std.os.linux` wrappers

`socket`, `setsockopt`, `bind`, `listen`, `accept4`, `connect`, `shutdown`,
`sendmsg`, `recvmsg`, `sendto`, `recvfrom`, `epoll_create1`, `epoll_ctl`,
`epoll_wait`, `pipe2`, `fcntl`, `ioctl`, `getsockname`, `getpeername`, and the
`io_uring_*` calls. Each returns a raw `usize`, decoded with the pattern above.

There is no bare `send` or `recv`. Use `sendto`/`recvfrom`, or the `msg` forms.
`iovec` comes from `std.posix`; `linux.iovec_const` is private.

## Two landmines

`std.posix.setsockopt` maps `.INVAL => unreachable`, which is UB in
ReleaseFast and a process kill in Debug. Use it for options where `EINVAL` is a
programming bug, such as `TCP_NODELAY` or `SO_REUSEADDR`. For any option whose
`EINVAL` is a legitimate runtime failure, call `linux.setsockopt` and decode
errno. It also type-checks `SO_RCVTIMEO` and `SO_SNDTIMEO`, so a `timeval` takes
microseconds, not nanoseconds, and an oversized value returns
`error.TimeoutTooBig`.

There is no `linux.splice` function, only `SYS.splice`. Six arguments through
`syscall6`:

```zig
fn splice(fd_in: i32, off_in: ?*const u64, fd_out: i32, off_out: ?*const u64, len: usize, flags: u32) SysError!usize {
    const raw = linux.syscall6(.splice,
        @as(u64, @bitCast(@as(i64, fd_in))), @intFromPtr(off_in),
        @as(u64, @bitCast(@as(i64, fd_out))), @intFromPtr(off_out),
        len, flags);
    return check(raw);
}
```

## `IoUring` vs `Io.Uring`

`std.os.linux.IoUring` is the wrapper to use. `std.Io.Uring` is the unfinished
`Io.Evented` implementation, and its functions take `*Evented`. They are
different files.

`IoUring` gives you `init`, `get_sqe`, `submit`, `cq_ready`, `copy_cqes`, and
builder methods that return `*io_uring_sqe` (`read`, `write`, `splice`,
`accept_multishot`, `timeout`, and more). `user_data` is left to the caller.
Grep `pub fn` in `std/os/linux/IoUring.zig` before assuming a builder exists.

## What is not here

`Io.Evented` has no networking yet. `Io.Threaded` maps the surface onto blocking
syscalls, so it is the one to use when portability matters more than the last
microsecond.
