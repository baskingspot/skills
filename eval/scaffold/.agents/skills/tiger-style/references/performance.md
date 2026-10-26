# Tiger Style — Performance

> "The lack of back-of-the-envelope performance sketches is the root of all evil." — Rivacindela Hudsoni

## Design-Phase Optimization

The best time to solve performance — the huge 1000x wins — is in the design phase, precisely when you can't measure or profile. It's harder to fix after implementation and the gains are less. Have mechanical sympathy. Like a carpenter, work with the grain.

## Back-of-Envelope Sketches

Sketch performance against four resources and two characteristics:

| Resource | Bandwidth | Latency |
| -------- | --------- | ------- |
| Network  | ?         | ?       |
| Disk     | ?         | ?       |
| Memory   | ?         | ?       |
| CPU      | ?         | ?       |

Sketches are cheap. Use them to be "roughly right" and land within 90% of the global maximum.

## Resource Prioritization

Optimize for the slowest resources first: **network > disk > memory > CPU**.

Compensate for frequency of usage — faster resources used many times more may cost as much. A memory cache miss happening 1,000 times may be as expensive as a disk fsync.

## Control Plane vs Data Plane

Clear delineation through batching enables a high level of assertion safety without losing performance. Control plane handles orchestration; data plane handles throughput.

## Batching & Amortization

Amortize network, disk, memory and CPU costs by batching accesses. This is the single most important performance technique.

## CPU Efficiency

- Let the CPU be a sprinter doing the 100m.
- Be predictable. Don't force the CPU to zig-zag and change lanes.
- Give the CPU large enough chunks of work.
- Be explicit. Minimize dependence on the compiler to do the right thing.
- **Extract hot loops into stand-alone functions with primitive arguments without `self`.** The compiler doesn't need to prove it can cache struct fields in registers, and humans can spot redundant computations easier.

## Tracy Profiling Zones

Tracy zones are compiled out in release builds — they are truly zero cost in production. This means the decision to add a zone should be based purely on observability value, never on overhead concerns.

- **Every extracted helper function** should have a `tracy.traceNamed(@src(), "descriptive name")` zone. When refactoring a large function into helpers, each helper gets its own zone so the profiling timeline reflects the new structure.
- **Name zones to distinguish code paths**: use different names for initial vs continuation paths (e.g., `"decrypt"` vs `"decrypt remaining"`). This makes it immediately visible in the Tracy timeline when rare/expensive paths fire.
- **Nest zones meaningfully**: helper zones nest inside their caller's zone. The hierarchy should mirror the logical structure: `"recv" → "decrypt"`, `"write" → "encrypt remaining"`.
- **Review checklist**: when reviewing code, check that new functions and significant branches have Tracy zones. Missing zones are a review finding, same as missing assertions.
