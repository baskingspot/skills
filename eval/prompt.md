# The eval prompt

The same text goes to every run. It states the protocol exactly and says
nothing about how to implement it, because the implementation is the variable.

Paste it in as a bracketed paste, then press Enter. A plain `rex send` submits
on the first newline.

```
Build a command-line tool in this project.

The binary is `minired`, with subcommands. `minired serve --bind 127.0.0.1 --port 6380` runs a server. `minired get KEY --port 6380`, `minired set KEY VALUE --port 6380`, and `minired del KEY --port 6380` run clients.

The wire protocol is line-oriented and CRLF terminated. Values are arbitrary bytes and may contain spaces. `SET key value` replies `+OK\r\n`. `GET key` replies `$<len>\r\n<value>\r\n`, or `$-1\r\n` when the key is absent. `DEL key` replies `:1\r\n` or `:0\r\n`. `KEYS` replies `*<n>\r\n`, then `$<len>\r\n<key>\r\n` for each key.

The server is single-threaded and handles one connection at a time, with no locks.

Three constraints. The store holds 100k keys and a lookup must not scan. Protocol encoding and decoding must be testable without opening a socket. A connection's buffers are allocated once, not per request.

The client prints the value and exits 0, exits 1 when the key is absent, and exits 2 on a connection failure. `--verbose` on the server logs each command it runs.

Write tests for the protocol and the store, and a benchmark for the protocol encoder and decoder. `zig build test` must pass.
```
