open Alcotest

module A = Market_simulator.Exec_account
module E = Market_simulator.Exec_event
module U = Market_simulator.Exec_units

let ok = function
  | Ok value -> value
  | Error message -> failwith ("unexpected error: " ^ message)

let is_error = function Ok _ -> false | Error _ -> true

(* Golden units: price 100.0000 = 1_000_000 ticks, quantity 1.0 = 1_000_000
   units, money 1.0 = 100_000_000 units. Notional 100.0 = 10_000_000_000. *)
let price = 1_000_000L
let quantity = 1_000_000L
let money units = units
let config =
  A.make_config ~leverage:10 ~maintenance_margin_rate_bps:50 ~maker_fee_bps:2
    ~taker_fee_bps:4 ~liquidation_fee_bps:125 ()

let aggressive =
  A.make_config ~leverage:20 ~maintenance_margin_rate_bps:50 ~maker_fee_bps:2
    ~taker_fee_bps:4 ~liquidation_fee_bps:125 ()

let make_order ?price_ticks ~side ?(tif = E.Gtc) ?(reduce_only = false)
    ?(post_only = false) quantity_units =
  {
    A.id = "ord-1";
    side;
    price_ticks;
    quantity_units;
    remaining_units = quantity_units;
    tif;
    reduce_only;
    post_only;
    status = A.New;
  }

let state ?(collateral = 5_000_000_000L) () = A.empty ~collateral

let test_notional_and_required_margin () =
  check int64 "notional" 10_000_000_000L
    (ok (U.notional ~price_ticks:price ~quantity_units:quantity));
  check int64 "required margin" 1_000_000_000L
    (ok (A.required_margin config ~price_ticks:price ~quantity_units:quantity));
  check int64 "margin rounds up" 3_333_333_334L
    (ok
       (A.required_margin
          (A.make_config ~leverage:3 ~maintenance_margin_rate_bps:50
             ~maker_fee_bps:2 ~taker_fee_bps:4 ())
          ~price_ticks:price ~quantity_units:quantity))

let test_submit_reserves_margin () =
  let order, state = ok (A.submit config (state ()) (make_order ~price_ticks:price ~side:E.Buy quantity)) in
  check int64 "reserved" 1_000_000_000L state.A.reserved_margin;
  check int64 "available" 4_000_000_000L
    (ok (A.available_margin state ~mark_ticks:price));
  check bool "accepted" true (order.A.status = A.New)

let test_submit_rejects_insufficient_margin () =
  let poor = state ~collateral:500_000_000L () in
  check bool "rejected" true
    (is_error (A.submit config poor (make_order ~price_ticks:price ~side:E.Buy quantity)))

let test_cancel_releases_reservation () =
  let order, state = ok (A.submit config (state ()) (make_order ~price_ticks:price ~side:E.Buy quantity)) in
  let cancelled, state = ok (A.cancel config state order) in
  check bool "canceled" true (cancelled.A.status = A.Canceled);
  check int64 "released" 0L state.A.reserved_margin

let test_taker_fill_charges_fee_and_opens_position () =
  let order, state = ok (A.submit config (state ()) (make_order ~price_ticks:price ~side:E.Buy quantity)) in
  let filled, state =
    ok (A.apply_fill config state order ~price_ticks:price ~quantity_units:quantity
          ~liquidity:E.Taker)
  in
  check bool "filled" true (filled.A.status = A.Filled);
  check int64 "position" 1_000_000L state.A.position;
  check (option int64) "entry" (Some 1_000_000L) state.A.entry_ticks;
  check int64 "collateral after taker fee" 4_996_000_000L state.A.collateral;
  check int64 "fees" 4_000_000L state.A.fees;
  check int64 "released" 0L state.A.reserved_margin

let test_maker_fill_uses_maker_fee () =
  let order = make_order ~price_ticks:price ~side:E.Buy quantity in
  let _, state =
    ok
      (A.apply_fill config (state ()) order ~price_ticks:price
         ~quantity_units:quantity ~liquidity:E.Maker)
  in
  check int64 "maker fee" 2_000_000L state.A.fees;
  check int64 "collateral" 4_998_000_000L state.A.collateral

let test_partial_fill_releases_part_of_the_reservation () =
  let order, state = ok (A.submit config (state ()) (make_order ~price_ticks:price ~side:E.Buy quantity)) in
  let filled, state =
    ok (A.apply_fill config state order ~price_ticks:price
          ~quantity_units:400_000L ~liquidity:E.Maker)
  in
  check bool "partially filled" true (filled.A.status = A.Partially_filled);
  check int64 "remaining" 600_000L filled.A.remaining_units;
  check int64 "reservation released for 0.4" 600_000_000L state.A.reserved_margin

let test_reduce_only_rules () =
  let order, state = ok (A.submit config (state ()) (make_order ~price_ticks:price ~side:E.Buy quantity)) in
  let _, state = ok (A.apply_fill config state order ~price_ticks:price ~quantity_units:quantity ~liquidity:E.Taker) in
  check bool "exceeds position" true
    (is_error (A.submit config state (make_order ~price_ticks:price ~side:E.Sell ~reduce_only:true 1_100_000L)));
  let closing, state =
    ok (A.submit config state (make_order ~price_ticks:price ~side:E.Sell ~reduce_only:true 600_000L))
  in
  check int64 "reduce-only reserves nothing" 0L state.A.reserved_margin;
  check int64 "reduce-only accepted" 600_000L closing.A.quantity_units;
  let state_only = A.empty ~collateral:5_000_000_000L in
  check bool "reduce-only without position" true
    (is_error (A.submit config state_only (make_order ~price_ticks:price ~side:E.Sell ~reduce_only:true 1_000_000L)))

let test_closing_fill_realizes_profit () =
  let order, state = ok (A.submit config (state ()) (make_order ~price_ticks:1_000_000L ~side:E.Buy quantity)) in
  let _, state = ok (A.apply_fill config state order ~price_ticks:1_000_000L ~quantity_units:quantity ~liquidity:E.Taker) in
  let close = { (make_order ~price_ticks:1_100_000L ~side:E.Sell quantity) with A.reduce_only = true } in
  let _, state = ok (A.apply_fill config state close ~price_ticks:1_100_000L ~quantity_units:quantity ~liquidity:E.Maker) in
  check int64 "position closed" 0L state.A.position;
  check (option int64) "entry cleared" None state.A.entry_ticks;
  check int64 "realized PnL" 1_000_000_000L state.A.realized_pnl

let test_funding_payment () =
  let order, state = ok (A.submit config (state ()) (make_order ~price_ticks:price ~side:E.Buy quantity)) in
  let _, state = ok (A.apply_fill config state order ~price_ticks:price ~quantity_units:quantity ~liquidity:E.Taker) in
  let state = ok (A.apply_funding state ~mark_ticks:price ~rate:10_000L) in
  check int64 "funding paid" 1_000_000L state.A.funding_paid;
  check int64 "collateral" 4_995_000_000L state.A.collateral;
  let short =
    {
      (A.empty ~collateral:5_000_000_000L) with
      A.position = -1_000_000L;
      A.entry_ticks = Some 1_000_000L;
    }
  in
  let short = ok (A.apply_funding short ~mark_ticks:price ~rate:10_000L) in
  check int64 "short receives funding" (-1_000_000L) short.A.funding_paid;
  check int64 "short collateral" 5_001_000_000L short.A.collateral

let test_equity_and_maintenance_margin () =
  let order, state = ok (A.submit config (state ()) (make_order ~price_ticks:1_000_000L ~side:E.Buy 100_000L)) in
  let _, state = ok (A.apply_fill config state order ~price_ticks:1_000_000L ~quantity_units:100_000L ~liquidity:E.Taker) in
  check int64 "equity at entry" 4_999_600_000L
    (ok (A.equity state ~mark_ticks:1_000_000L));
  check int64 "equity when up" 5_099_600_000L
    (ok (A.equity state ~mark_ticks:1_100_000L));
  check int64 "maintenance margin" 4_500_000L
    (ok (A.maintenance_margin config state ~mark_ticks:900_000L));
  check bool "not liquidated" false
    (ok (A.should_liquidate config state ~mark_ticks:900_000L))

let test_liquidation_closes_and_clamps_collateral () =
  (* 1 BTC at 100.0 with 20x leverage needs 5.0 margin, and 5.05 also covers
     the 0.04 taker fee, because the fill check uses equity after the fee. *)
  let tight = A.empty ~collateral:505_000_000L in
  let order, state =
    ok (A.submit aggressive tight (make_order ~price_ticks:1_000_000L ~side:E.Buy quantity))
  in
  check int64 "reserves 5.0" 500_000_000L state.A.reserved_margin;
  let _, state =
    ok
      (A.apply_fill aggressive state order ~price_ticks:1_000_000L
         ~quantity_units:quantity ~liquidity:E.Taker)
  in
  check int64 "collateral after the fee" 501_000_000L state.A.collateral;
  let full = A.empty ~collateral:500_000_000L in
  let order_at_limit, limit_state =
    ok (A.submit aggressive full (make_order ~price_ticks:1_000_000L ~side:E.Buy quantity))
  in
  check int64 "reserves the whole collateral" 0L
    (ok (A.available_margin limit_state ~mark_ticks:1_000_000L));
  check bool "a fee with no headroom fails at fill" true
    (is_error
       (A.apply_fill aggressive limit_state order_at_limit ~price_ticks:1_000_000L
          ~quantity_units:quantity ~liquidity:E.Taker));
  check bool "liquidated at a deep drop" true
    (ok (A.should_liquidate aggressive state ~mark_ticks:950_000L));
  let state = ok (A.liquidate aggressive state ~mark_ticks:950_000L) in
  check bool "flagged" true state.A.liquidated;
  check int64 "flat" 0L state.A.position;
  check int64 "collateral clamped" 0L state.A.collateral;
  check bool "cannot trade again" true
    (is_error
       (A.submit aggressive state (make_order ~price_ticks:price ~side:E.Buy quantity)))

let () =
  run "exec_account"
    [
      ( "margin",
        [ test_case "notional and required margin" `Quick test_notional_and_required_margin;
          test_case "submit reserves" `Quick test_submit_reserves_margin;
          test_case "insufficient margin" `Quick test_submit_rejects_insufficient_margin;
          test_case "cancel releases" `Quick test_cancel_releases_reservation ] );
      ( "fills",
        [ test_case "taker fill" `Quick test_taker_fill_charges_fee_and_opens_position;
          test_case "maker fee" `Quick test_maker_fill_uses_maker_fee;
          test_case "partial release" `Quick test_partial_fill_releases_part_of_the_reservation;
          test_case "reduce-only" `Quick test_reduce_only_rules;
          test_case "closing profit" `Quick test_closing_fill_realizes_profit ] );
      ( "risk",
        [ test_case "funding" `Quick test_funding_payment;
          test_case "equity" `Quick test_equity_and_maintenance_margin;
          test_case "liquidation" `Quick test_liquidation_closes_and_clamps_collateral ] );
    ]
