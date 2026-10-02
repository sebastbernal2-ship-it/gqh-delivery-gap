open Alcotest

module L2 = Market_simulator.Binance_l2
module Trades = Market_simulator.Binance_trades
module Model = Market_simulator.Binance_maker_model

let timestamp seconds =
  match Ptime.of_float_s seconds with
  | Some value -> Market_simulator.Timestamp.of_ptime value
  | None -> failwith "invalid timestamp"

let state seconds bid_size =
  {
    L2.raw_line = "capture.gz";
    received_time = timestamp seconds;
    event_time = timestamp seconds;
    last_update_id = Int64.of_int (int_of_float seconds);
    bids = [ { L2.price = "100"; size = string_of_float bid_size } ];
    asks = [ { L2.price = "101"; size = "1" } ];
  }

let trade seconds quantity =
  {
    Trades.raw_line = "trades.gz";
    received_time = timestamp seconds;
    event_time = timestamp seconds;
    trade_time = timestamp seconds;
    symbol = "BTCUSDT";
    trade_id = Int64.of_int (int_of_float (seconds *. 10.0));
    price = 100.0;
    quantity;
    buyer_is_maker = true;
  }

let test_bounds () =
  let estimate =
    Model.estimate ~side:Model.Buy ~price:100.0 ~size:1.0
      ~placed_at:(timestamp 0.0)
      ~states:[ state 0.0 1.0; state 1.0 0.5; state 2.0 0.5 ]
      ~trades:[ trade 1.5 1.0 ]
  in
  check (float 0.001) "queue ahead" 1.0 estimate.initial_queue_ahead;
  check (float 0.001) "pessimistic fill" 0.0 estimate.pessimistic_filled;
  check (float 0.001) "optimistic fill" 0.5 estimate.optimistic_filled

let () = run "binance_maker_model" [ ("bounds", [ test_case "bounds" `Quick test_bounds ]) ]
