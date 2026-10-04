open Alcotest

module A = Market_simulator.Exec_account
module E = Market_simulator.Exec_event
module F = Market_simulator.Exec_fills
module L = Market_simulator.Exec_loop
module T = Market_simulator.Timestamp

let time text =
  match T.of_string text with
  | Ok value -> value
  | Error message -> failwith ("bad time: " ^ message)

let envelope seconds payload =
  {
    E.venue = "binance-futures";
    symbol = "BTCUSDT";
    event_time = time (Printf.sprintf "2026-10-03T23:42:%02d.000000000Z" seconds);
    receive_time = time (Printf.sprintf "2026-10-03T23:42:%02d.000000000Z" seconds);
    sequence = None;
    source_id = "test";
    source_path = "test.jsonl";
    source_sha256 = String.make 64 'a';
    quality = E.Healthy;
    payload;
  }

let level price_ticks quantity_units = { E.price_ticks; quantity_units }

let snapshot ?(second = 0) () =
  envelope second
    (E.Depth_snapshot
       {
         E.last_update_id = Some 100L;
         bids = [ level 1_000_000L 1_000_000L ];
         asks = [ level 1_000_100L 1_000_000L ];
       })

let update ?(second = 3) first last previous bids asks =
  envelope second
    (E.Depth_update
       {
         E.first_update_id = first;
         E.last_update_id = last;
         E.previous_update_id = Some previous;
         bids;
         asks;
       })

let trade ?(second = 10) quantity_units =
  envelope second
    (E.Trade
       {
         E.trade_id = 1L;
         price_ticks = 1_000_000L;
         quantity_units;
         buyer_is_maker = false;
       })

let config =
  A.make_config ~leverage:10 ~maintenance_margin_rate_bps:50 ~maker_fee_bps:2
    ~taker_fee_bps:4 ~liquidation_fee_bps:125 ()

let order ?(id = "quote-1") ?price_ticks ?(reduce_only = false)
    ?(tif = E.Gtc) ?(post_only = false) quantity_units =
  {
    A.id;
    side = E.Buy;
    price_ticks;
    quantity_units;
    remaining_units = quantity_units;
    tif;
    reduce_only;
    post_only;
    status = A.New;
  }

let run_loop ?(latency = L.default_latency) ~strategy events =
  L.run ~mode:F.Conservative ~latency ~config ~strategy
    ~initial_collateral:100_000_000_000L ~events

let once action =
  let fired = ref false in
  fun _ ->
    if !fired then [] else begin
      fired := true;
      [ action ]
    end

let submit_then_cancel ~latency events =
  let step = ref 0 in
  let strategy _ =
    incr step;
    match !step with
    | 1 -> [ L.Submit (order ~price_ticks:1_000_000L 500_000L) ]
    | 2 -> [ L.Cancel "quote-1" ]
    | _ -> []
  in
  run_loop ~latency ~strategy events

let test_submit_waits_for_decision_latency () =
  let events =
    [
      snapshot ();
      trade ~second:1 2_000_000L;
      update ~second:5 101L 110L 100L [] [];
    ]
  in
  let fast = run_loop ~strategy:(once (L.Submit (order ~price_ticks:1_000_000L 500_000L))) events in
  check int "fast submit" 1 fast.L.submitted;
  check int "fast fill" 1 fast.L.fills;
  check int64 "filled units" 500_000L fast.L.filled_units;
  let slow =
    run_loop
      ~latency:{ decision_ns = 2_000_000_000L; cancel_ns = 0L }
      ~strategy:(once (L.Submit (order ~price_ticks:1_000_000L 500_000L))) events
  in
  check int "slow submit" 1 slow.L.submitted;
  check int "no fill before the order is live" 0 slow.L.fills;
  check int64 "no units" 0L slow.L.filled_units

let test_cancel_latency_keeps_the_order_exposed () =
  let events =
    [
      snapshot ();
      trade ~second:1 2_000_000L;
      update ~second:6 101L 110L 100L [] [];
    ]
  in
  (* The cancel is decided at t=1 and takes 5 s, so the fill at t=1 lands. *)
  let exposed =
    submit_then_cancel ~latency:{ decision_ns = 0L; cancel_ns = 5_000_000_000L } events
  in
  check int "filled while exposed" 1 exposed.L.fills;
  check int "cancel applied later" 1 exposed.L.cancelled;
  let fast = submit_then_cancel ~latency:L.default_latency events in
  check int "canceled immediately" 1 fast.L.cancelled

let test_market_intent_takes_liquidity () =
  let strategy = once (L.Submit (order 500_000L)) in
  let report = run_loop ~strategy [ snapshot (); update ~second:5 101L 110L 100L [] [] ] in
  check int64 "position" 500_000L report.L.account.A.position;
  check int64 "taker units" 500_000L report.L.taker_units;
  check int64 "taker fee" 2_000_200L report.L.account.A.fees

let test_crossing_limit_takes_immediately () =
  let strategy = once (L.Submit (order ~price_ticks:1_000_200L 400_000L)) in
  let report = run_loop ~strategy [ snapshot (); update ~second:5 101L 110L 100L [] [] ] in
  check int64 "taker units" 400_000L report.L.taker_units;
  check int64 "position" 400_000L report.L.account.A.position

let test_visible_liquidity_is_consumed_across_orders () =
  let second_order = ref false in
  let strategy (context : L.context) =
    match context.L.event.E.payload with
    | E.Depth_snapshot _ when not !second_order ->
        [ L.Submit (order ~id:"first" 750_000L) ]
    | E.Trade _ when not !second_order ->
        second_order := true;
        [ L.Submit (order ~id:"second" 750_000L) ]
    | _ -> []
  in
  let report = run_loop ~strategy [ snapshot (); trade ~second:1 1L ] in
  check int64 "only displayed liquidity can fill twice" 1_000_000L
    report.L.filled_units;
  check int64 "position is bounded by visible liquidity" 1_000_000L
    report.L.account.A.position

let test_multilevel_fill_uses_current_order_remainder_and_timestamp () =
  let two_levels =
    envelope 0
      (E.Depth_snapshot
         { E.last_update_id = None;
           bids = [ level 1_000_000L 1_000_000L ];
           asks = [ level 1_000_100L 1_000_000L; level 1_000_200L 1_000_000L ] })
  in
  let report =
    run_loop ~strategy:(once (L.Submit (order ~tif:E.Fok 1_500_000L))) [ two_levels ]
  in
  check int "two price-level fills" 2 report.L.fills;
  check int64 "whole order filled" 1_500_000L report.L.filled_units;
  check int64 "account position matches fills" 1_500_000L
    report.L.account.A.position;
  check bool "fill timestamps are replay time" true
    (List.for_all
       (fun fill -> T.compare fill.L.at two_levels.E.receive_time = 0)
       report.L.fills_log)

let test_fok_is_atomic_when_visible_depth_is_insufficient () =
  let report =
    run_loop
      ~strategy:(once (L.Submit (order ~tif:E.Fok 1_500_000L)))
      [ snapshot () ]
  in
  check int "FOK rejected" 1 report.L.rejected;
  check int "no partial FOK fills" 0 report.L.fills;
  check int64 "account unchanged" 0L report.L.account.A.position

let test_post_only_crossing_order_is_rejected () =
  let report =
    run_loop
      ~strategy:(once
                   (L.Submit
                      (order ~price_ticks:1_000_200L ~post_only:true 500_000L)))
      [ snapshot () ]
  in
  check int "crossing post-only rejected" 1 report.L.rejected;
  check int "not submitted" 0 report.L.submitted;
  check int "not filled" 0 report.L.fills

let test_post_only_market_order_is_rejected () =
  let report =
    run_loop
      ~strategy:(once (L.Submit (order ~post_only:true 100_000L)))
      [ snapshot () ]
  in
  check int "market post-only rejected" 1 report.L.rejected;
  check int "no take" 0 report.L.fills

let test_sequence_gap_invalidates_book_until_snapshot () =
  let gap = update ~second:1 102L 103L 99L [] [] in
  let later_trade = trade ~second:2 2_000_000L in
  let strategy (context : L.context) =
    match context.L.event.E.payload with
    | E.Trade _ -> [ L.Submit (order 100_000L) ]
    | _ -> []
  in
  let report = run_loop ~strategy [ snapshot (); gap; later_trade ] in
  check int "one chain gap" 1 report.L.chain_gaps;
  check int "stale book cannot submit" 0 report.L.submitted;
  check bool "book cleared while untrusted" true
    (L.mid_ticks report.L.book = None)

let test_rejects_invalid_provenance_and_unsorted_input () =
  let raises f =
    try f (); false with Invalid_argument _ -> true
  in
  check bool "reject malformed source digest" true
    (raises (fun () ->
         ignore
           (run_loop ~strategy:(fun _ -> [])
              [ { (snapshot ()) with E.source_sha256 = "abc" } ])));
  check bool "reject receive-time regression" true
    (raises (fun () ->
         ignore
           (run_loop ~strategy:(fun _ -> [])
              [ trade ~second:2 1L; snapshot ~second:1 () ])))

let test_rejects_are_counted () =
  let strategy = once (L.Submit (order ~price_ticks:1_000_000L 100_000_000_000L)) in
  let report = run_loop ~strategy [ snapshot (); update ~second:5 101L 110L 100L [] [] ] in
  check int "rejected" 1 report.L.rejected;
  check int "not submitted" 0 report.L.submitted;
  check int64 "flat" 0L report.L.account.A.position

let test_liquidation_stops_the_loop () =
  (* A 1.0 long at 100 with 5.05 collateral and 20x leverage liquidates when the
     bid falls far enough, and the loop then rejects new orders. *)
  let aggressive =
    A.make_config ~leverage:20 ~maintenance_margin_rate_bps:50
      ~maker_fee_bps:2 ~taker_fee_bps:4 ~liquidation_fee_bps:125 ()
  in
  let events =
    [
      snapshot ();
      update ~second:5 101L 110L 100L
        [ level 1_000_000L 1_000_000L ]
        [ level 1_000_100L 1_000_000L ];
      (* Removing the touch level needs an explicit zero size. *)
      update ~second:6 111L 120L 110L
        [ level 1_000_000L 0L; level 500_000L 1_000_000L ]
        [];
    ]
  in
  let placed = ref false in
  let strategy (context : L.context) =
    if
      (not !placed)
      && L.mid_ticks context.L.book = Some 1_000_050L
    then begin
      placed := true;
      [ L.Submit (order ~price_ticks:1_000_100L 1_000_000L) ]
    end
    else []
  in
  let report =
    L.run ~mode:F.Optimistic ~latency:L.default_latency ~config:aggressive
      ~strategy ~initial_collateral:505_000_000L ~events
  in
  check int64 "took the offer" 1_000_000L report.L.taker_units;
  check int "taker fills" 1 report.L.fills;
  check int "liquidations" 1 report.L.liquidations;
  check bool "flat after liquidation" true (report.L.account.A.liquidated)

let test_merge_keeps_chronological_order () =
  let events =
    [
      snapshot ~second:0 ();
      trade ~second:1 2_000_000L;
      update ~second:6 101L 110L 100L [] [];
    ]
  in
  let merged =
    L.merge_events [ List.nth events 0; List.nth events 2 ] [ List.nth events 1 ]
  in
  check int "all events kept" 3 (List.length merged);
  List.iteri
    (fun index event ->
      if index > 0 then
        let previous = List.nth merged (index - 1) in
        check bool "ordered" true
          (T.compare previous.E.receive_time event.E.receive_time <= 0))
    merged;
  check int "second event is the trade" 1
    (if (List.nth merged 1).E.payload = (List.nth events 1).E.payload then 1 else 0)

let () =
  run "exec_loop"
    [
      ("merge", [ test_case "merge order" `Quick test_merge_keeps_chronological_order ]);
      ( "latency",
        [ test_case "submit latency" `Quick test_submit_waits_for_decision_latency;
          test_case "cancel latency" `Quick test_cancel_latency_keeps_the_order_exposed ] );
      ( "fills",
        [ test_case "market takes" `Quick test_market_intent_takes_liquidity;
          test_case "crossing limit" `Quick test_crossing_limit_takes_immediately;
          test_case "visible liquidity consumed" `Quick test_visible_liquidity_is_consumed_across_orders;
          test_case "multi-level fill timestamp" `Quick test_multilevel_fill_uses_current_order_remainder_and_timestamp;
          test_case "FOK atomic" `Quick test_fok_is_atomic_when_visible_depth_is_insufficient;
          test_case "post-only crossing" `Quick test_post_only_crossing_order_is_rejected;
          test_case "post-only market" `Quick test_post_only_market_order_is_rejected;
          test_case "rejects counted" `Quick test_rejects_are_counted ] );
      ("sequence", [ test_case "gap fail-closed" `Quick test_sequence_gap_invalidates_book_until_snapshot ]);
      ("input", [ test_case "provenance and order" `Quick test_rejects_invalid_provenance_and_unsorted_input ]);
      ("risk", [ test_case "liquidation" `Quick test_liquidation_stops_the_loop ]);
    ]
