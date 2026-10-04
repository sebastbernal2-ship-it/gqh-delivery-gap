open Alcotest

module A = Market_simulator.Exec_account
module E = Market_simulator.Exec_event
module F = Market_simulator.Exec_fills
module L = Market_simulator.Exec_loop
module N = Market_simulator.Naive_backtest
module S = Market_simulator.Exec_strategy
module T = Market_simulator.Timestamp

let time text =
  match T.of_string text with
  | Ok value -> value
  | Error message -> failwith ("bad time: " ^ message)

let envelope seconds payload =
  {
    E.venue = "binance-futures";
    symbol = "BTCUSDT";
    event_time = time (Printf.sprintf "2026-10-04T00:00:%02d.000000000Z" seconds);
    receive_time = time (Printf.sprintf "2026-10-04T00:00:%02d.000000000Z" seconds);
    sequence = None;
    source_id = "test";
    source_path = "test.jsonl";
    source_sha256 = String.make 64 'a';
    quality = E.Healthy;
    payload;
  }

let level price_ticks quantity_units = { E.price_ticks; quantity_units }

(* A thin book: 0.5 visible on the bid, so a 2.0 order cannot fill in full. *)
let snapshot () =
  envelope 0
    (E.Depth_snapshot
       {
         E.last_update_id = Some 100L;
         bids = [ level 1_000_000L 500_000L ];
         asks = [ level 1_000_100L 500_000L ];
       })

let config =
  A.make_config ~leverage:10 ~maintenance_margin_rate_bps:50 ~maker_fee_bps:2
    ~taker_fee_bps:4 ()

(* The same intent on both paths: buy 2.0 units at market. The naive baseline
   fills all of it at the mid; the realistic loop can only take the 0.5 that is
   visible on the ask. *)
let strategy _ =
  [
    L.Submit
      {
        A.id = "gap-1";
        side = E.Buy;
        price_ticks = None;
        quantity_units = 2_000_000L;
        remaining_units = 2_000_000L;
        tif = E.Gtc;
        reduce_only = false;
        post_only = false;
        status = A.New;
      };
  ]

let events = [ snapshot () ]

let test_naive_fills_in_full_at_the_mid () =
  let report =
    N.run ~config ~strategy ~initial_collateral:100_000_000_000L ~events
  in
  check int "one order" 1 report.N.orders;
  check int64 "filled in full" 2_000_000L report.N.filled_units;
  (* Mid is 1_000_050, so the notional is 1_000_050 * 2_000_000 / 100 and the
     taker fee is four basis points of it. *)
  let expected_fee =
    Int64.div (Int64.mul (Int64.div (Int64.mul 1_000_050L 2_000_000L) 100L) 4L) 10_000L
  in
  check int64 "naive fee" expected_fee report.N.fees

let test_realistic_fills_only_visible_depth () =
  let report =
    L.run ~mode:F.Conservative ~latency:L.default_latency ~config ~strategy
      ~initial_collateral:100_000_000_000L ~events
  in
  check int64 "only the visible ask filled" 500_000L report.L.filled_units;
  check int "one fill" 1 report.L.fills

let test_gap_is_measurable () =
  let naive =
    N.run ~config ~strategy ~initial_collateral:100_000_000_000L ~events
  in
  let realistic =
    L.run ~mode:F.Conservative ~latency:L.default_latency ~config ~strategy
      ~initial_collateral:100_000_000_000L ~events
  in
  let shortfall =
    Int64.sub naive.N.filled_units realistic.L.filled_units
  in
  check int64 "naive overstates fills" 1_500_000L shortfall;
  check bool "and equities differ" true
    (not (Int64.equal naive.N.equity realistic.L.account.A.collateral))

let test_capital_blocked_is_flagged () =
  let poor = A.empty ~collateral:1_000_000L in
  check bool "blocked" true
    (N.capital_blocked config poor 1_000_000L 2_000_000L);
  let rich = A.empty ~collateral:100_000_000_000L in
  check bool "not blocked" false
    (N.capital_blocked config rich 1_000_000L 2_000_000L)

let () =
  run "naive_backtest"
    [
      ( "gap",
        [ test_case "naive fills in full" `Quick test_naive_fills_in_full_at_the_mid;
          test_case "realistic fills visible only" `Quick
            test_realistic_fills_only_visible_depth;
          test_case "gap is measurable" `Quick test_gap_is_measurable;
          test_case "capital blocked" `Quick test_capital_blocked_is_flagged ] );
    ]
