open Alcotest

module Account = Market_simulator.Binance_account

let config () =
  Account.make_config ~leverage:10.0 ~maintenance_margin_rate:0.05
    ~maker_fee_bps:1.0 ~taker_fee_bps:5.0 ()

let unwrap = function Ok value -> value | Error error -> fail error

let test_lifecycle () =
  let config = config () in
  let state = Account.empty_state ~collateral:1_000.0 in
  let order =
    unwrap
      (Account.submit_order ~config ~state ~id:"o1" ~side:Account.Buy
         ~quantity:2.0 ~tif:Account.Ioc ())
  in
  let order, state =
    unwrap (Account.apply_fill ~config Account.Taker ~price:100.0 ~quantity:1.0 order state)
  in
  check bool "partial" true (order.status = Account.Partially_filled);
  let order = Account.finalize order in
  check bool "IOC canceled remainder" true (order.status = Account.Canceled);
  check (float 0.001) "position" 1.0 state.position;
  check (float 0.001) "fee" 0.05 state.fees;
  let state = Account.apply_funding ~mark:110.0 ~rate:0.001 state in
  check (float 0.001) "funding" 0.11 state.funding_paid;
  check (float 0.001) "equity" 1_009.84 (Account.equity ~mark:110.0 state)

let test_reduce_only () =
  let config = config () in
  let state = Account.empty_state ~collateral:1_000.0 in
  let state = { state with position = -2.0; entry_price = Some 100.0 } in
  let order =
    unwrap
      (Account.submit_order ~config ~state ~id:"o2" ~side:Account.Buy
         ~quantity:1.0 ~reduce_only:true ())
  in
  check bool "reduce only" true order.reduce_only;
  match
    Account.submit_order ~config ~state ~id:"o3" ~side:Account.Buy
      ~quantity:3.0 ~reduce_only:true ()
  with
  | Ok _ -> fail "expected oversized reduce-only rejection"
  | Error error -> check bool "error" true (String.length error > 0)

let test_leverage_margin () =
  let config =
    Account.make_config ~leverage:2.0 ~maintenance_margin_rate:0.05
      ~maker_fee_bps:0.0 ~taker_fee_bps:0.0 ()
  in
  let state = Account.empty_state ~collateral:10.0 in
  let order =
    unwrap
      (Account.submit_order ~config ~state ~id:"margin" ~side:Account.Buy
         ~quantity:1.0 ())
  in
  match
    Account.apply_fill ~config Account.Taker ~price:100.0 ~quantity:1.0 order state
  with
  | Ok _ -> fail "expected leverage margin rejection"
  | Error error -> check bool "margin error" true (String.length error > 0)

let test_liquidation () =
  let config = config () in
  let state = Account.empty_state ~collateral:10.0 in
  let state = { state with position = 1.0; entry_price = Some 100.0 } in
  check bool "liquidated" true (Account.is_liquidated ~mark:85.0 config state);
  check bool "liquidation price" true
    (Option.is_some (Account.liquidation_price config state));
  let liquidated =
    match Account.liquidate ~mark:85.0 config state with
    | Ok value -> value
    | Error error -> fail error
  in
  check (float 0.001) "closed position" 0.0 liquidated.position;
  check bool "liquidated state" true liquidated.liquidated

let test_liquidation_fee_does_not_create_negative_collateral () =
  let config =
    Account.make_config ~leverage:10.0 ~maintenance_margin_rate:0.05
      ~maker_fee_bps:0.0 ~taker_fee_bps:0.0 ~liquidation_fee_bps:20_000.0 ()
  in
  let state = Account.empty_state ~collateral:1.0 in
  let state = { state with position = 1.0; entry_price = Some 100.0 } in
  let liquidated =
    match Account.liquidate ~mark:80.0 config state with
    | Ok value -> value
    | Error error -> fail error
  in
  check bool "liquidation keeps collateral nonnegative" true
    (liquidated.collateral >= 0.0)

let () =
  run "binance_account"
    [ ( "account",
        [ test_case "lifecycle" `Quick test_lifecycle;
          test_case "reduce only" `Quick test_reduce_only;
          test_case "leverage margin" `Quick test_leverage_margin;
          test_case "liquidation" `Quick test_liquidation;
          test_case "liquidation fee" `Quick
            test_liquidation_fee_does_not_create_negative_collateral ] ) ]
