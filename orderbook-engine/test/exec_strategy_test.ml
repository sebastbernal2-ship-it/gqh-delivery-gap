open Alcotest

module A = Market_simulator.Exec_account
module E = Market_simulator.Exec_event
module L = Market_simulator.Exec_loop
module S = Market_simulator.Exec_strategy
module T = Market_simulator.Timestamp

let time seconds =
  match T.of_string (Printf.sprintf "2026-10-03T23:42:%02d.000000000Z" seconds) with
  | Ok value -> value
  | Error message -> failwith message

let envelope seconds payload =
  {
    E.venue = "binance-futures";
    symbol = "BTCUSDT";
    event_time = time seconds;
    receive_time = time seconds;
    sequence = None;
    source_id = "test";
    source_path = "test.jsonl";
    source_sha256 = String.make 64 'a';
    quality = E.Healthy;
    payload;
  }

let level price_ticks quantity_units = { E.price_ticks; quantity_units }

let snapshot ?(second = 0) ?(bids = [ level 1_000_000L 1_000_000L ])
    ?(asks = [ level 1_000_100L 1_000_000L ]) () =
  envelope second
    (E.Depth_snapshot { E.last_update_id = Some 100L; bids; asks })

let update ?(second = 5) ?(previous = 100L) ?(first = 101L) ?(last = 110L) bids asks =
  envelope second
    (E.Depth_update
       {
         E.first_update_id = first;
         E.last_update_id = last;
         E.previous_update_id = Some previous;
         bids;
         asks;
       })

let trade ?(second = 1) ~buyer_is_maker ~quantity_units () =
  envelope second
    (E.Trade
       {
         E.trade_id = 1L;
         price_ticks = 1_000_050L;
         quantity_units;
         buyer_is_maker;
       })

let test_prefetch_counts_and_imbalance () =
  let events =
    [
      snapshot ();
      trade ~second:1 ~buyer_is_maker:false ~quantity_units:1_000_000L ();
      trade ~second:2 ~buyer_is_maker:true ~quantity_units:500_000L ();
      update ~second:5 [ level 1_000_000L 3_000_000L ] [ level 1_000_100L 1_000_000L ];
    ]
  in
  let features = S.prefetch ~window:10 events in
  check int "one feature per event" (List.length events) (Array.length features);
  let at index = features.(index) in
  check int "no trades before the first trade" 0 (at 0).S.trade_count;
  check int64 "one trade at index 1" 1_000_000L (at 1).S.trade_units;
  check int64 "two trades at index 2" 1_500_000L (at 2).S.trade_units;
  check int64 "buy aggressor volume" 1_000_000L (at 2).S.buy_units;
  check int64 "sell aggressor volume" 500_000L (at 2).S.sell_units;
  check int "buy ratio in bps" 6667 (at 2).S.buy_ratio_bps;
  (* Bids are three times the asks, so the imbalance is positive. *)
  check bool "book imbalance is positive" true ((at 3).S.book_imbalance_bps > 0);
  check int64 "mid range in ticks" 0L (at 3).S.mid_range_ticks

let test_prefetch_mid_range () =
  let events =
    [
      snapshot ();
      update ~second:2 [ level 1_000_200L 1_000_000L ] [ level 1_000_100L 0L; level 1_000_300L 1_000_000L ];
      update ~second:5 [ level 1_000_200L 0L ] [ level 1_000_300L 0L; level 1_000_100L 1_000_000L ];
    ]
  in
  let features = S.prefetch ~window:10 events in
  check bool "mid moved" true (features.(2).S.mid_range_ticks > 0L)

let test_window_limits_the_lookback () =
  let events =
    [
      snapshot ();
      trade ~second:1 ~buyer_is_maker:false ~quantity_units:1_000_000L ();
      trade ~second:2 ~buyer_is_maker:false ~quantity_units:1_000_000L ();
      trade ~second:3 ~buyer_is_maker:false ~quantity_units:1_000_000L ();
    ]
  in
  let features = S.prefetch ~window:2 events in
  check int64 "only the trailing window" 2_000_000L (features.(3)).S.trade_units

let test_strategy_sees_its_own_index () =
  let events =
    [
      snapshot ();
      trade ~second:1 ~buyer_is_maker:false ~quantity_units:2_000_000L ();
      update ~second:5 [] [];
      update ~second:6 ~previous:110L ~first:111L ~last:120L [] [];
    ]
  in
  let features = S.prefetch ~window:10 events in
  let seen = ref [] in
  let strategy =
    S.make ~features (fun context _ ->
        seen := context.L.index :: !seen;
        ignore context.L.book;
        [])
  in
  let config =
    A.make_config ~leverage:10 ~maintenance_margin_rate_bps:50 ~maker_fee_bps:2
      ~taker_fee_bps:4 ()
  in
  ignore
    (L.run ~mode:Market_simulator.Exec_fills.Conservative
       ~latency:L.default_latency ~config ~strategy
       ~initial_collateral:100_000_000L ~events);
  check (list int) "index per event" [ 0; 1; 2; 3 ] (List.rev !seen)

let test_feature_driven_quote_places_and_cancels () =
  (* Heavy sell pressure in the window suppresses the bid; a calm window
     restores it. The quote is driven only by prefetched features. *)
  let events =
    [
      snapshot ();
      trade ~second:1 ~buyer_is_maker:true ~quantity_units:9_000_000L ();
      update ~second:5 [] [];
      update ~second:9 ~previous:110L ~first:111L ~last:120L [] [];
    ]
  in
  let features = S.prefetch ~window:10 events in
  let strategy =
    S.skewed_quote ~features ~size_units:100_000L ~imbalance_floor_bps:2_000
  in
  let config =
    A.make_config ~leverage:10 ~maintenance_margin_rate_bps:50 ~maker_fee_bps:2
      ~taker_fee_bps:4 ()
  in
  let report =
    L.run ~mode:Market_simulator.Exec_fills.Conservative
      ~latency:L.default_latency ~config ~strategy
      ~initial_collateral:100_000_000_000L ~events
  in
  check int "a quote was submitted" 1 report.L.submitted;
  check int "and cancelled under sell pressure" 1 report.L.cancelled;
  check int64 "no fills" 0L report.L.filled_units

let () =
  run "exec_strategy"
    [
      ( "features",
        [ test_case "counts and imbalance" `Quick test_prefetch_counts_and_imbalance;
          test_case "mid range" `Quick test_prefetch_mid_range;
          test_case "window" `Quick test_window_limits_the_lookback;
          test_case "own index" `Quick test_strategy_sees_its_own_index ] );
      ( "strategy",
        [ test_case "feature driven quote" `Quick
            test_feature_driven_quote_places_and_cancels ] );
    ]
