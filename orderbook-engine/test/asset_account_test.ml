open Alcotest
module S = Market_simulator.Instrument_spec
module A = Market_simulator.Asset_account
module R = Market_simulator.Asset_replay
module E = Market_simulator.Exec_event
module T = Market_simulator.Timestamp

let ok = function
  | Ok value -> value
  | Error message -> failwith ("unexpected error: " ^ message)

let is_error = function Ok _ -> false | Error _ -> true
let time value = ok (T.of_string value)
let first = time "2024-01-01T00:00:00Z"
let trade_day = time "2024-01-02T15:00:00Z"
let settlement_day = time "2024-01-03T15:00:00Z"
let expiry = time "2024-01-19T21:00:00Z"
let price dollars = Int64.mul dollars 10_000L
let money dollars = Int64.mul dollars 100_000_000L
let unit = 1_000_000L

let spec kind multiplier =
  {
    S.venue = "test-venue";
    symbol = "TEST";
    currency = "USD";
    effective_from = first;
    effective_until = None;
    price_increment_ticks = 100L;
    quantity_increment_units = unit;
    multiplier;
    kind;
  }

let equity = spec S.Equity 1L

let future =
  spec
    (S.Future
       { expiry; initial_margin_bps = 1_000; maintenance_margin_bps = 500 })
    50L

let perpetual =
  spec
    (S.Perpetual { initial_margin_bps = 1_000; maintenance_margin_bps = 500 })
    1L

let option ?(settlement = S.Cash) () =
  spec
    (S.Option
       {
         underlying = "STOCK";
         strike_ticks = price 100L;
         expiry;
         right = S.Call;
         settlement;
         deliverable_units = 100_000_000L;
         exercise_multiplier = 100L;
       })
    100L

let fill state side dollars quantity ?(settle_at = None) () =
  ok
    (A.fill state ~at:trade_day ~side ~price_ticks:(price dollars)
       ~quantity_units:quantity ~fee_bps:0 ~settle_at)

let test_cash_equity_and_settlement () =
  let account = ok (A.create equity ~cash:(money 2_000L)) in
  let account = fill account E.Buy 10L (Int64.mul 100L unit) () in
  check int64 "buy debits cash" (money 1_000L) account.A.cash;
  check int64 "buy keeps equity" (money 2_000L)
    (ok (A.equity account ~mark_ticks:(price 10L)));
  let account =
    fill account E.Sell 12L (Int64.mul 40L unit)
      ~settle_at:(Some settlement_day) ()
  in
  check int64 "sale proceeds await settlement" (money 1_000L) account.A.cash;
  check int64 "sale gain" (money 80L) account.A.realized_pnl;
  check int64 "equity includes receivable" (money 2_200L)
    (ok (A.equity account ~mark_ticks:(price 12L)));
  let early = ok (A.settle_receivables account ~at:trade_day) in
  check int64 "early settlement does nothing" (money 1_000L) early.A.cash;
  let settled = ok (A.settle_receivables account ~at:settlement_day) in
  check int64 "settled proceeds" (money 1_480L) settled.A.cash

let test_equity_actions_and_short_rejection () =
  let account = ok (A.create equity ~cash:(money 2_000L)) in
  check bool "unlocated short rejected" true
    (is_error
       (A.fill account ~at:trade_day ~side:E.Sell ~price_ticks:(price 10L)
          ~quantity_units:unit ~fee_bps:0 ~settle_at:(Some settlement_day)));
  let account = fill account E.Buy 10L (Int64.mul 10L unit) () in
  let account = ok (A.split_equity account ~numerator:2L ~denominator:1L) in
  check int64 "split doubles shares" (Int64.mul 20L unit)
    account.A.position_units;
  check (Alcotest.option int64) "split halves basis"
    (Some (price 5L))
    account.A.entry_ticks;
  let account =
    ok
      (A.equity_dividend account ~amount_per_share:(money 1L)
         ~payable_at:settlement_day)
  in
  check int64 "dividend is a receivable" (money 2_020L)
    (ok (A.equity account ~mark_ticks:(price 5L)))

let test_futures_variation_and_expiry () =
  let account = ok (A.create future ~cash:(money 1_000L)) in
  let account = fill account E.Buy 100L (Int64.mul 2L unit) () in
  check int64 "futures do not debit principal" (money 1_000L) account.A.cash;
  let account =
    ok
      (A.future_settlement account ~at:settlement_day
         ~settlement_ticks:(price 101L))
  in
  check int64 "two contracts times fifty times one point" (money 1_100L)
    account.A.cash;
  check (Alcotest.option int64) "basis resets at settlement"
    (Some (price 101L))
    account.A.entry_ticks;
  let account =
    ok (A.future_expiry account ~at:expiry ~final_ticks:(price 102L))
  in
  check int64 "final variation credited" (money 1_200L) account.A.cash;
  check int64 "expired position closed" 0L account.A.position_units;
  check bool "expired contract rejects new fill" true
    (is_error
       (A.fill account ~at:expiry ~side:E.Buy ~price_ticks:(price 102L)
          ~quantity_units:unit ~fee_bps:0 ~settle_at:None))

let test_perpetual_funding () =
  let account = ok (A.create perpetual ~cash:(money 100L)) in
  let long = fill account E.Buy 100L unit () in
  let long =
    ok
      (A.perpetual_funding long ~mark_ticks:(price 100L) ~rate_units:1_000_000L)
  in
  check int64 "long pays one percent" (money 99L) long.A.cash;
  let short = fill account E.Sell 100L unit () in
  let short =
    ok
      (A.perpetual_funding short ~mark_ticks:(price 100L) ~rate_units:1_000_000L)
  in
  check int64 "short receives one percent" (money 101L) short.A.cash

let test_cash_option_and_physical_guard () =
  let account = ok (A.create (option ()) ~cash:(money 1_000L)) in
  let account = fill account E.Buy 2L unit () in
  check int64 "premium costs two hundred" (money 800L) account.A.cash;
  let account =
    ok (A.option_expiry account ~at:expiry ~underlying_ticks:(price 110L))
  in
  check int64 "cash call pays ten times one hundred" (money 1_800L)
    account.A.cash;
  check int64 "option realized gain" (money 800L) account.A.realized_pnl;
  let physical =
    ok (A.create (option ~settlement:S.Physical ()) ~cash:(money 1_000L))
  in
  let physical = fill physical E.Buy 2L unit () in
  check bool "physical exercise requires underlying ledger" true
    (is_error
       (A.option_expiry physical ~at:expiry ~underlying_ticks:(price 110L)))

let test_adjusted_cash_option_multiplier () =
  let base = option () in
  let terms =
    match base.S.kind with
    | S.Option terms -> terms
    | _ -> failwith "expected option"
  in
  let adjusted =
    { base with S.kind = S.Option { terms with exercise_multiplier = 50L } }
  in
  let account = ok (A.create adjusted ~cash:(money 1_000L)) in
  let account = fill account E.Buy 2L unit () in
  let account =
    ok (A.option_expiry account ~at:expiry ~underlying_ticks:(price 110L))
  in
  check int64 "exercise uses exercise multiplier" (money 1_300L) account.A.cash

let test_spec_validation () =
  check bool "tick violation" true
    (is_error
       (S.validate_fill equity ~at:trade_day ~price_ticks:100_001L
          ~quantity_units:unit));
  check bool "lot violation" true
    (is_error
       (S.validate_fill equity ~at:trade_day ~price_ticks:(price 10L)
          ~quantity_units:1L));
  check bool "missing identity" true
    (is_error (S.validate { equity with symbol = "" }));
  check bool "expired future" true
    (is_error
       (S.validate_fill future ~at:expiry ~price_ticks:(price 100L)
          ~quantity_units:unit));
  let underfunded = ok (A.create future ~cash:(money 999L)) in
  check bool "initial margin enforced" true
    (is_error
       (A.fill underfunded ~at:trade_day ~side:E.Buy ~price_ticks:(price 100L)
          ~quantity_units:(Int64.mul 2L unit) ~fee_bps:0 ~settle_at:None));
  let unowned_option = ok (A.create (option ()) ~cash:(money 1_000L)) in
  check bool "short option lacks declared margin" true
    (is_error
       (A.fill unowned_option ~at:trade_day ~side:E.Sell ~price_ticks:(price 2L)
          ~quantity_units:unit ~fee_bps:0 ~settle_at:None));
  check bool "premature exercise rejected" true
    (is_error
       (A.option_expiry unowned_option ~at:trade_day
          ~underlying_ticks:(price 110L)))

let event ?(at = trade_day) payload =
  {
    E.venue = equity.S.venue;
    symbol = equity.S.symbol;
    event_time = at;
    receive_time = at;
    sequence = None;
    source_id = "golden-fixture";
    source_path = "test/asset_account_test.ml";
    source_sha256 = String.make 64 'a';
    quality = E.Healthy;
    payload;
  }

let test_canonical_account_replay () =
  let buy =
    event
      (E.Fill
         {
           order_id = "buy";
           side = E.Buy;
           price_ticks = price 10L;
           quantity_units = unit;
           fee = 0L;
           liquidity = E.Taker;
         })
  in
  let sale_time = T.add_ns trade_day 1_000_000_000L in
  let sell =
    event ~at:sale_time
      (E.Fill
         {
           order_id = "sell";
           side = E.Sell;
           price_ticks = price 12L;
           quantity_units = unit;
           fee = 0L;
           liquidity = E.Maker;
         })
  in
  let settlement =
    event ~at:settlement_day
      (E.Observation { data_type = "equity_cash_settlement"; payload = "{}" })
  in
  let run events =
    R.run equity ~initial_cash:(money 2_000L)
      ~equity_settlement:(fun _ -> settlement_day)
      events
  in
  let replay = ok (run [ buy; sell; settlement ]) in
  check int "processed" 3 replay.R.processed;
  check int64 "replayed cash" (money 2_002L) replay.R.account.A.cash;
  check int64 "replayed realized gain" (money 2L)
    replay.R.account.A.realized_pnl;
  check bool "mixed instrument fails" true
    (is_error (run [ { buy with symbol = "OTHER" } ]));
  check bool "suspect fill fails" true
    (is_error (run [ { buy with quality = E.Suspect "bad capture" } ]));
  check bool "malformed provenance fails" true
    (is_error (run [ { buy with source_sha256 = "bad" } ]));
  check bool "out-of-order receive time fails" true
    (is_error (run [ sell; buy ]))

let () =
  Alcotest.run "asset accounting"
    [
      ( "economic lifecycles",
        [
          test_case "cash equity and settlement" `Quick
            test_cash_equity_and_settlement;
          test_case "equity actions and short guard" `Quick
            test_equity_actions_and_short_rejection;
          test_case "future variation and expiry" `Quick
            test_futures_variation_and_expiry;
          test_case "perpetual funding" `Quick test_perpetual_funding;
          test_case "cash option and physical guard" `Quick
            test_cash_option_and_physical_guard;
          test_case "adjusted cash option multiplier" `Quick
            test_adjusted_cash_option_multiplier;
          test_case "instrument spec validation" `Quick test_spec_validation;
          test_case "canonical account replay" `Quick
            test_canonical_account_replay;
        ] );
    ]
