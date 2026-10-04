open Alcotest

module F = Market_simulator.Exec_fills
module E = Market_simulator.Exec_event
module B = Market_simulator.L2_book

let ok = function
  | Ok value -> value
  | Error message -> failwith ("unexpected error: " ^ message)

let level price quantity = { E.price_ticks = price; quantity_units = quantity }

let book () =
  B.empty
  |> fun book -> B.set_level book B.Bid (level 1_000_000L 5_000_000L)
  |> fun book -> B.set_level book B.Bid (level 999_900L 10_000_000L)
  |> fun book -> B.set_level book B.Ask (level 1_000_100L 3_000_000L)
  |> fun book -> B.set_level book B.Ask (level 1_000_200L 7_000_000L)

let test_taker_walks_visible_depth () =
  let result =
    ok (F.take F.Conservative ~book:(book ()) ~side:E.Buy ~quantity_units:3_000_000L ())
  in
  check int64 "filled" 3_000_000L result.F.filled_units;
  check int64 "remaining" 0L result.F.remaining_units;
  check int "one level used" 1 (List.length result.F.fills);
  check int64 "notional" (Int64.div (Int64.mul 3_000_000L 1_000_100L) 100L)
    result.F.notional

let test_taker_crosses_levels () =
  let result =
    ok (F.take F.Conservative ~book:(book ()) ~side:E.Buy ~quantity_units:5_000_000L ())
  in
  check int "two levels" 2 (List.length result.F.fills);
  check int64 "notional" (Int64.div
       (Int64.add (Int64.mul 3_000_000L 1_000_100L)
          (Int64.mul 2_000_000L 1_000_200L))
       100L)
    result.F.notional;
  check bool "mode recorded" true (result.F.mode = F.Conservative)

let test_taker_respects_limit_and_thin_book () =
  let limited =
    ok
      (F.take F.Optimistic ~book:(book ()) ~side:E.Buy ~quantity_units:5_000_000L
         ~limit_ticks:1_000_100L ())
  in
  check int64 "filled at the limit only" 3_000_000L limited.F.filled_units;
  check int64 "remaining" 2_000_000L limited.F.remaining_units;
  let empty = ok (F.take F.Conservative ~book:B.empty ~side:E.Buy ~quantity_units:1_000L ()) in
  check int64 "no depth no fill" 0L empty.F.filled_units;
  check int64 "notional zero" 0L empty.F.notional

let test_taker_sells_into_bids () =
  let result =
    ok (F.take F.Conservative ~book:(book ()) ~side:E.Sell ~quantity_units:6_000_000L ())
  in
  check int64 "best bid first" 5_000_000L (List.hd result.F.fills).F.quantity_units;
  check int64 "notional" (Int64.div
       (Int64.add (Int64.mul 5_000_000L 1_000_000L)
          (Int64.mul 1_000_000L 999_900L))
       100L)
    result.F.notional

let observation ?(before = 10_000_000L) ?(queue = 10_000_000L)
    ?(trades = 0L) ?(after = 10_000_000L) () =
  {
    F.level_units_before = before;
    queue_ahead_units = queue;
    trades_units = trades;
    level_units_after = after;
  }

let test_conservative_ignores_cancels () =
  (* 4.0 traded at our price, 10.0 was ahead of us, and the level shrank by
     another 4.0 from cancels. Conservative sees only the trades. *)
  let fill =
    F.infer_maker_fill F.Conservative ~order_units:10_000_000L
      ~observation:(observation ~trades:4_000_000L ~after:2_000_000L ())
  in
  check int64 "no fill while the queue holds" 0L fill;
  let deeper =
    F.infer_maker_fill F.Conservative ~order_units:10_000_000L
      ~observation:(observation ~trades:12_000_000L ~after:0L ())
  in
  check int64 "fills past the queue" 2_000_000L deeper

let test_heuristic_counts_cancels_ahead () =
  (* 4.0 traded, and the level fell by 6.0, so 2.0 was cancelled ahead of us.
      With 5.0 ahead, cancels and trades together clear the queue plus 1.0. *)
  let fill =
    F.infer_maker_fill F.Heuristic ~order_units:10_000_000L
      ~observation:
        (observation ~queue:5_000_000L ~trades:4_000_000L ~after:4_000_000L ())
  in
  check int64 "cancels advance the queue" 1_000_000L fill

let test_optimistic_ignores_the_queue () =
  let fill =
    F.infer_maker_fill F.Optimistic ~order_units:10_000_000L
      ~observation:(observation ~trades:1_000_000L ~after:9_000_000L ())
  in
  check int64 "fills from the touch" 1_000_000L fill;
  let capped =
    F.infer_maker_fill F.Optimistic ~order_units:500_000L
      ~observation:(observation ~trades:9_000_000L ~after:0L ())
  in
  check int64 "capped by order size" 500_000L capped

let test_maker_modes_are_ordered () =
  let observation =
    observation ~queue:4_000_000L ~trades:6_000_000L ~after:3_000_000L ()
  in
  let conservative =
    F.infer_maker_fill F.Conservative ~order_units:10_000_000L ~observation
  in
  let heuristic = F.infer_maker_fill F.Heuristic ~order_units:10_000_000L ~observation in
  let optimistic = F.infer_maker_fill F.Optimistic ~order_units:10_000_000L ~observation in
  check int64 "conservative" 2_000_000L conservative;
  check int64 "heuristic" 3_000_000L heuristic;
  check int64 "optimistic" 7_000_000L optimistic

(* A deterministic randomized check of the mode ordering invariant. A simple
   linear congruential generator keeps the test dependency-free and repeatable. *)
let test_modes_are_ordered_over_random_inputs () =
  let state = ref 12345 in
  let next bound =
    state := (!state * 1103515245 + 12345) land 0x3FFFFFFF;
    !state mod bound
  in
  let failures = ref 0 in
  for _ = 1 to 5000 do
    let before = next 20_000_000 in
    let queue = next (before + 1) in
    let trades = next 20_000_000 in
    let after = next (before + 1) in
    let order_units = next 20_000_000 in
    let observation =
      {
        F.level_units_before = Int64.of_int before;
        queue_ahead_units = Int64.of_int queue;
        trades_units = Int64.of_int trades;
        level_units_after = Int64.of_int after;
      }
    in
    let order_units = Int64.of_int order_units in
    let conservative =
      F.infer_maker_fill F.Conservative ~order_units ~observation
    in
    let heuristic = F.infer_maker_fill F.Heuristic ~order_units ~observation in
    let optimistic = F.infer_maker_fill F.Optimistic ~order_units ~observation in
    if
      not
        (conservative <= heuristic && heuristic <= optimistic
        && optimistic <= order_units && conservative >= 0L)
    then incr failures
  done;
  check int "ordering violations" 0 !failures

let () =
  run "exec_fills"
    [
      ( "taker",
        [ test_case "walks visible depth" `Quick test_taker_walks_visible_depth;
          test_case "crosses levels" `Quick test_taker_crosses_levels;
          test_case "limit and thin book" `Quick test_taker_respects_limit_and_thin_book;
          test_case "sells into bids" `Quick test_taker_sells_into_bids ] );
      ( "maker",
        [ test_case "conservative" `Quick test_conservative_ignores_cancels;
          test_case "heuristic" `Quick test_heuristic_counts_cancels_ahead;
          test_case "optimistic" `Quick test_optimistic_ignores_the_queue;
          test_case "ordered modes" `Quick test_maker_modes_are_ordered ] );
      ( "property",
        [ test_case "ordered over random inputs" `Quick
            test_modes_are_ordered_over_random_inputs ] );
    ]
