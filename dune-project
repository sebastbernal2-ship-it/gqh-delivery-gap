(lang dune 3.24)
(name market_simulator)
(version 0.2.0)
(generate_opam_files true)

(package
 (name market_simulator)
 (synopsis "Incremental Market-Simulator: A Bitemporal Order Book in OCaml")
 (maintainers "sebastbernal2-ship-it")
 (description
   "An incremental-computation-driven market simulator with a fully \
    bitemporal order book. Supports CSV and generated market data, \
    an Lwt event loop, a WebSocket API for real-time streams, \
    and full temporal queries (as-of, between, sequenced, non-sequenced).")
 (depends
   (ocaml (>= 5.2.0))
   dune
   incr
   alcotest
   cmdliner
   lwt
   csv
   fmt
   logs
   ptime
   websocket
   yojson
   sexplib0
   base
   ppx_deriving
   qcheck
   ppx_expect))

(package
 (name incr)
 (version 0.2.0)
 (synopsis "A minimal incremental computation engine (DAG-based, wave propagation)")
 (maintainers "sebastbernal2-ship-it")
 (description
   "A self-contained incremental computation library inspired by Jane Street's \
    Incremental library. Nodes form a DAG; when an input Var changes, only \
    affected downstream nodes recompute in topological order via wave-based \
    stabilization. Supports map, map2, map3, bind, cutoff, if_, and on_change. \
    No external dependencies beyond the OCaml stdlib.")
 (depends
   (ocaml (>= 5.2.0))
   dune))