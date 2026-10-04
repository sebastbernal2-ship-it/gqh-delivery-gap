open Alcotest

module Hf_l2 = Market_simulator.Hf_l2
module L2_backtest = Market_simulator.L2_backtest
module L2_execution = Market_simulator.L2_execution

let timestamp seconds =
  match Ptime.of_float_s seconds with
  | Some value -> Market_simulator.Timestamp.of_ptime value
  | None -> failwith "invalid timestamp"

let snapshot seconds =
  {
    Hf_l2.timestamp = timestamp seconds;
    symbol = "BTCUSDT";
    bids = [ { Hf_l2.price = 99.0; cumulative_size = 1.0; distance_bps = 0.0 } ];
    asks = [ { Hf_l2.price = 101.0; cumulative_size = 1.0; distance_bps = 0.0 } ];
    mid_price = 100.0;
    traded_volume = 0.0;
  }

let test_time_latency () =
  let snapshots = [ snapshot 0.0; snapshot 1.0; snapshot 2.0 ] in
  let strategy _ _ =
    [ { L2_backtest.side = L2_execution.Buy; size = 0.5; limit_price = None } ]
  in
  let result =
    L2_backtest.run ~initial_cash:1_000.0 ~latency_ms:1_500L strategy snapshots
  in
  check int "one delayed fill" 1 result.final_portfolio.trade_count;
  check (float 0.001) "fill at second snapshot" 101.0
    (List.hd result.trades).price

let test_conflicting_latency () =
  let strategy _ _ = [] in
  check_raises "latency options conflict" (Invalid_argument "latency options conflict")
    (fun () ->
      ignore
        (L2_backtest.run ~initial_cash:1_000.0 ~latency_snapshots:1
           ~latency_ms:1_000L strategy [ snapshot 0.0 ]))

let () =
  run "l2_backtest_latency"
    [ ( "latency",
        [ test_case "time latency" `Quick test_time_latency;
          test_case "conflicting latency" `Quick test_conflicting_latency ] ) ]
