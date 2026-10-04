# Contributing

## Coding standards

- **Formatting**: All OCaml source files must be formatted with `ocamlformat`.
  Run `ocamlformat --inplace src/*.ml src/*.mli test/*.ml examples/*.ml`
  before committing.
- **Tests**: Every new function needs at least one test. Prefer `ppx_expect`
  tests for output-heavy operations and `QCheck` for property-based invariants.
- **Module interfaces**: Every `.ml` file has a corresponding `.mli` that
  defines the public API. Internal types and functions are not exposed.
- **Error handling**: Use `Serror.t` for all fallible operations. Functions
  that can fail return `'a Serror.t`; callers handle both `Ok` and `Error`.
- **Data structures**: Prefer immutable data structures (Map, Set) over
  mutable ones (Hashtbl). Immutability enables incremental cut-off and
  simplifies reasoning about state.
- **Documentation**: Architecture decisions are recorded in `docs/adr/`.
  Module headers (ocamldoc `(** ... *)`) explain the module's purpose and
  invariants.

## Build and test

```bash
dune build
dune runtest
```

## Before submitting a PR

1. `ocamlformat --inplace src/*.ml src/*.mli test/*.ml examples/*.ml`
2. `dune build`
3. `dune runtest` — all tests must pass