open Alcotest

module L2 = Market_simulator.Binance_l2
module Trades = Market_simulator.Binance_trades
module Account = Market_simulator.Binance_account
module Backtest = Market_simulator.Binance_backtest

let timestamp seconds =
  match Ptime.of_float_s seconds with
  | Some value -> Market_simulator.Timestamp.of_ptime value
  | None -> failwith "invalid timestamp"

let state seconds bid_size ask_size =
  {
    L2.raw_line = "capture.gz";
    received_time = timestamp seconds;
    event_time = timestamp seconds;
    last_update_id = Int64.of_int (int_of_float seconds);
    bids = [ { L2.price = "100"; size = Printf.sprintf "%.17g" bid_size } ];
    asks = [ { L2.price = "101"; size = Printf.sprintf "%.17g" ask_size } ];
  }

let instrument () =
  match
    Market_simulator.Binance_units.instrument ~symbol:"BTCUSDT"
      ~price_step:"0.10" ~quantity_step:"0.001"
  with
  | Ok value -> value
  | Error error -> failwith error

let config () =
  Account.make_config ~leverage:10.0 ~maintenance_margin_rate:0.05
    ~maker_fee_bps:1.0 ~taker_fee_bps:5.0 ()

let test_taker () =
  let order =
    {
      Backtest.id = "taker";
      side = Account.Buy;
      quantity = 0.5;
      price = None;
      placed_at = timestamp 0.0;
      execution = Backtest.Taker;
    }
  in
  let result =
    match
      Backtest.run ~collateral:1_000.0 ~config:(config ()) ~symbol:"BTCUSDT"
        ~instrument:(instrument ()) ~maker_policy:Backtest.Pessimistic
        ~states:[ state 0.0 1.0 1.0 ] ~trades:[] ~orders:[ order ]
    with
    | Ok result -> result
    | Error error -> fail error
  in
  let fill = List.hd result.orders in
  check (float 0.001) "taker fill" 0.5 fill.filled;
  check bool "filled status" true (fill.status = Account.Filled)

let test_maker_policy () =
  let order =
    {
      Backtest.id = "maker";
      side = Account.Buy;
      quantity = 1.0;
      price = Some 100.0;
      placed_at = timestamp 0.0;
      execution = Backtest.Maker;
    }
  in
  let states = [ state 0.0 1.0 1.0; state 1.0 0.5 1.0; state 2.0 0.5 1.0 ] in
  let trades =
    [
      {
        Trades.raw_line = "trades.gz";
        received_time = timestamp 1.5;
        event_time = timestamp 1.5;
        trade_time = timestamp 1.5;
        symbol = "BTCUSDT";
        trade_id = 1L;
        price = 100.0;
        quantity = 1.0;
        buyer_is_maker = true;
      };
    ]
  in
  let result =
    match
      Backtest.run ~collateral:1_000.0 ~config:(config ()) ~symbol:"BTCUSDT"
        ~instrument:(instrument ()) ~maker_policy:Backtest.Optimistic ~states ~trades ~orders:[ order ]
    with
    | Ok result -> result
    | Error error -> fail error
  in
  check (float 0.001) "maker fill" 0.5 (List.hd result.orders).filled

let () =
  run "binance_backtest"
    [ ( "execution",
        [ test_case "taker" `Quick test_taker;
          test_case "maker policy" `Quick test_maker_policy ] ) ]
