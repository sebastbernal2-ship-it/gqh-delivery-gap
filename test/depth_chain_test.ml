open Alcotest

module D = Market_simulator.Depth_chain

let apply chain first_id last_id previous_id =
  D.apply chain ~first_update_id:first_id ~last_update_id:last_id
    ~previous_update_id:previous_id

let test_accepts_chain_continuing_updates () =
  let chain = D.create () in
  D.reset chain 100L;
  check bool "bridging accept" true (apply chain 101L 110L 100L = D.Accept);
  check bool "chained accept" true (apply chain 130L 140L 110L = D.Accept);
  check (option int64) "trailing id" (Some 140L) (D.current chain)

let test_accepts_an_update_spanning_the_snapshot () =
  let chain = D.create () in
  D.reset chain 100L;
  check bool "spanning accept" true (apply chain 95L 105L 94L = D.Accept);
  check (option int64) "trailing id" (Some 105L) (D.current chain)

let test_supersedes_updates_before_the_snapshot () =
  let chain = D.create () in
  D.reset chain 100L;
  check bool "superseded" true (apply chain 60L 90L 59L = D.Superseded);
  check (option int64) "trailing id unchanged" (Some 100L) (D.current chain)

let test_rejects_a_bootstrap_gap () =
  let chain = D.create () in
  D.reset chain 100L;
  check bool "gap" true (apply chain 150L 160L 149L = D.Gap)

let test_rejects_a_live_gap () =
  let chain = D.create () in
  D.reset chain 100L;
  ignore (apply chain 101L 110L 100L);
  check bool "gap" true (apply chain 150L 160L 149L = D.Gap)

let test_reset_starts_a_new_chain () =
  let chain = D.create () in
  D.reset chain 100L;
  ignore (apply chain 101L 110L 100L);
  D.reset chain 5000L;
  check bool "superseded after reset" true (apply chain 4000L 4500L 3999L = D.Superseded);
  check bool "accept after reset" true (apply chain 5001L 5010L 5000L = D.Accept);
  check bool "no baseline before reset" true (D.create () |> fun empty -> apply empty 1L 2L 0L = D.Gap)

let () =
  run "depth_chain"
    [
      ( "rule",
        [ test_case "chain continuing" `Quick test_accepts_chain_continuing_updates;
          test_case "spanning snapshot" `Quick test_accepts_an_update_spanning_the_snapshot;
          test_case "superseded" `Quick test_supersedes_updates_before_the_snapshot;
          test_case "bootstrap gap" `Quick test_rejects_a_bootstrap_gap;
          test_case "live gap" `Quick test_rejects_a_live_gap;
          test_case "reset" `Quick test_reset_starts_a_new_chain ] );
    ]
