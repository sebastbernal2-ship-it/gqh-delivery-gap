open Market_simulator

module Account = Binance_account

let arb_of_gen gen = QCheck.make gen

let finite value = not (Float.is_nan value || Float.is_infinite value)

let config ~leverage ~liquidation_fee_bps () =
  Account.make_config ~leverage ~maintenance_margin_rate:0.05
    ~maker_fee_bps:1.0 ~taker_fee_bps:5.0 ~liquidation_fee_bps ()

let gen_trade =
  QCheck.Gen.map3
    (fun leverage quantity price -> leverage, quantity, price)
    QCheck.Gen.(map (fun value -> float_of_int value /. 10.0) (int_range 1 1_000))
    QCheck.Gen.(map float_of_int (int_range 1 1_000))
    QCheck.Gen.(map float_of_int (int_range 1 100_000))

let prop_accepted_fills_respect_leverage () =
  QCheck.Test.make ~name:"accepted fills respect leverage"
    (arb_of_gen gen_trade) (fun (leverage, quantity, price) ->
      let config = config ~leverage ~liquidation_fee_bps:0.0 () in
      let state = Account.empty_state ~collateral:1_000_000_000.0 in
      match
        Account.submit_order ~config ~state ~id:"leverage" ~side:Account.Buy
          ~quantity ()
      with
      | Error _ -> true
      | Ok order -> (
          match Account.apply_fill ~config Account.Taker ~price ~quantity order state with
          | Error _ -> true
          | Ok (_, state) ->
              let margin = abs_float state.position *. price /. leverage in
              finite margin && finite (Account.equity ~mark:price state)
              && margin <= Account.equity ~mark:price state +. 1e-7))

let gen_position_and_quantity =
  QCheck.Gen.map2
    (fun position quantity -> position, quantity)
    QCheck.Gen.(map (fun value -> if value mod 2 = 0 then value else -value) (int_range 1 100))
    QCheck.Gen.(int_range 1 150)

let prop_reduce_only_never_increases_position () =
  QCheck.Test.make ~name:"reduce-only orders never increase position"
    (arb_of_gen gen_position_and_quantity) (fun (position, quantity) ->
      let state =
        { (Account.empty_state ~collateral:1_000_000.0) with
          position = float_of_int position; entry_price = Some 100.0 }
      in
      let side = if position > 0 then Account.Sell else Account.Buy in
      let quantity_float = float_of_int quantity in
      match
        Account.submit_order ~config:(config ~leverage:10.0 ~liquidation_fee_bps:0.0 ())
          ~state ~id:"reduce-only" ~side ~quantity:quantity_float ~reduce_only:true ()
      with
      | Error _ -> quantity > abs position
      | Ok order -> (
          match
            Account.apply_fill
              ~config:(config ~leverage:10.0 ~liquidation_fee_bps:0.0 ())
              Account.Taker ~price:100.0 ~quantity:quantity_float order state
          with
          | Error _ -> false
          | Ok (_, next) ->
              abs_float next.position <= float_of_int (abs position) +. 1e-9))

let prop_liquidation_closes_position () =
  QCheck.Test.make ~name:"liquidation closes and preserves finite account state"
    (arb_of_gen (QCheck.Gen.int_range 1 100)) (fun collateral_units ->
      let collateral = float_of_int collateral_units /. 10.0 in
      let state =
        { (Account.empty_state ~collateral) with
          position = 1.0; entry_price = Some 100.0 }
      in
      let config = config ~leverage:10.0 ~liquidation_fee_bps:100.0 () in
      match Account.liquidate ~mark:80.0 config state with
      | Error _ -> false
      | Ok liquidated ->
          liquidated.position = 0.0
          && liquidated.entry_price = None
          && liquidated.liquidated
          && liquidated.collateral >= 0.0
          && finite liquidated.collateral
          && finite liquidated.realized_pnl
          && finite liquidated.fees)

let prop_fees_and_funding_stay_finite () =
  QCheck.Test.make ~name:"fees and funding preserve possible balances"
    (arb_of_gen
       (QCheck.Gen.map2
          (fun quantity rate -> quantity, rate)
          QCheck.Gen.(map float_of_int (int_range 1 100))
          QCheck.Gen.(map (fun value -> float_of_int value /. 100_000.0) (int_range (-100) 100))))
    (fun (quantity, rate) ->
      let config = config ~leverage:10.0 ~liquidation_fee_bps:0.0 () in
      let state = Account.empty_state ~collateral:1_000_000.0 in
      match
        Account.submit_order ~config ~state ~id:"fees" ~side:Account.Buy ~quantity ()
      with
      | Error _ -> false
      | Ok order -> (
          match Account.apply_fill ~config Account.Taker ~price:100.0 ~quantity order state with
          | Error _ -> false
          | Ok (_, filled) ->
              let funded = Account.apply_funding ~mark:100.0 ~rate filled in
              finite funded.collateral && finite funded.fees
              && finite funded.funding_paid
              && finite (Account.equity ~mark:100.0 funded)
              && funded.collateral >= 0.0
              && funded.fees >= 0.0))

let () =
  QCheck_runner.run_tests_main
    [ prop_accepted_fills_respect_leverage ();
      prop_reduce_only_never_increases_position ();
      prop_liquidation_closes_position ();
      prop_fees_and_funding_stay_finite () ]
