open Alcotest

module B = Market_simulator.L2_book
module E = Market_simulator.Exec_event
module T = Market_simulator.Timestamp

let time text =
  match T.of_string text with
  | Ok value -> value
  | Error message -> failwith ("bad time: " ^ message)

let envelope payload =
  {
    E.venue = "binance-futures";
    symbol = "BTCUSDT";
    event_time = time "2026-10-03T23:42:24.000000000Z";
    receive_time = time "2026-10-03T23:42:24.100000000Z";
    sequence = None;
    source_id = "test";
    source_path = "test.jsonl";
    source_sha256 = "abc";
    quality = E.Healthy;
    payload;
  }

let level price_ticks quantity_units = { E.price_ticks; quantity_units }

let snapshot ?(last = Some 100L) bids asks =
  envelope (E.Depth_snapshot { E.last_update_id = last; bids; asks })

let update ?(previous = Some 100L) first last bids asks =
  envelope
    (E.Depth_update
       {
         E.first_update_id = first;
         E.last_update_id = last;
         E.previous_update_id = previous;
         bids;
         asks;
       })

let seeded () =
  B.replay
    [
      snapshot [ level 100L 5L; level 99L 3L ] [ level 101L 4L; level 102L 1L ];
    ]

let test_snapshot_seeds_the_book () =
  let result = seeded () in
  check (option int64) "best bid" (Some 100L) (B.best_bid result.B.book);
  check (option int64) "best ask" (Some 101L) (B.best_ask result.B.book);
  check (option int64) "spread" (Some 1L) (B.spread result.B.book);
  check int "bid levels" 2 (B.level_count result.B.book B.Bid);
  check int "ask levels" 2 (B.level_count result.B.book B.Ask);
  check int64 "bid quantity" 8L (B.total_quantity result.B.book B.Bid);
  check bool "not crossed" false (B.crossed result.B.book)

let test_updates_set_absolute_sizes () =
  let result =
    B.replay
      [
        snapshot [ level 100L 5L ] [ level 101L 4L ];
        update 101L 110L [ level 100L 7L ] [ level 101L 0L ];
      ]
  in
  check int64 "absolute size replaces" 7L (B.total_quantity result.B.book B.Bid);
  check (option int64) "removed ask level" None (B.best_ask result.B.book);
  check int "applied" 1 result.B.applied;
  check int "gaps" 0 result.B.gaps

let test_new_levels_join_the_book () =
  let result =
    B.replay
      [
        snapshot [ level 99L 5L ] [ level 105L 4L ];
        update 101L 110L [ level 100L 2L ]
          [ level 105L 0L; level 106L 1L ];
      ]
  in
  check (option int64) "best bid improves" (Some 100L) (B.best_bid result.B.book);
  check (option int64) "best ask moves out" (Some 106L)
    (B.best_ask result.B.book)

let test_pending_update_before_snapshot () =
  let result =
    B.replay
      [
        update ~previous:(Some 94L) 95L 105L [ level 100L 1L ] [ level 101L 1L ];
        snapshot ~last:(Some 100L) [ level 100L 5L ] [ level 101L 4L ];
        update ~previous:(Some 105L) 130L 140L [ level 100L 6L ] [];
      ]
  in
  check int "pending" 1 result.B.pending_updates;
  check int "applied" 2 result.B.applied;
  check int64 "pending update applied" 6L (B.total_quantity result.B.book B.Bid)

let test_gap_stops_the_book () =
  let result =
    B.replay
      [
        snapshot [ level 100L 5L ] [ level 101L 4L ];
        update ~previous:(Some 149L) 150L 160L [ level 100L 9L ] [];
        update ~previous:(Some 160L) 161L 170L [ level 100L 2L ] [];
      ]
  in
  check int "gap" 1 result.B.gaps;
  check bool "gapped" true result.B.gapped;
  check int "unchecked after gap" 1 result.B.unchecked_after_gap;
  check int64 "book frozen at the last accepted update" 5L
    (B.total_quantity result.B.book B.Bid)

let test_snapshot_recovers_after_a_gap () =
  let result =
    B.replay
      [
        snapshot [ level 100L 5L ] [ level 101L 4L ];
        update 150L 160L [ level 100L 9L ] [];
        snapshot ~last:(Some 200L) [ level 99L 1L ] [ level 102L 1L ];
        update ~previous:(Some 200L) 201L 210L [ level 99L 2L ] [];
      ]
  in
  check bool "recovered" false result.B.gapped;
  check int64 "second snapshot applied" 2L (B.total_quantity result.B.book B.Bid);
  check int "snapshots" 2 result.B.snapshots

let test_checksum_is_stable_and_sensitive () =
  let left = seeded () in
  let right = seeded () in
  check string "stable" (B.checksum left.B.book) (B.checksum right.B.book);
  let changed =
    B.replay [ snapshot [ level 100L 6L ] [ level 101L 4L; level 102L 1L ] ]
  in
  check bool "sensitive" false
    (String.equal (B.checksum left.B.book) (B.checksum changed.B.book))

let test_ignores_other_payloads () =
  let trade =
    envelope
      (E.Trade
         {
           E.trade_id = 1L;
           price_ticks = 100L;
           quantity_units = 1L;
           buyer_is_maker = true;
         })
  in
  let result = B.replay [ trade; snapshot [ level 100L 1L ] [] ] in
  check int "ignored" 1 result.B.ignored_events;
  check int "snapshots" 1 result.B.snapshots

let test_total_quantity_overflow_fails_closed () =
  let book =
    B.apply_snapshot B.empty
      ~bids:[ level 100L Int64.max_int; level 99L 1L ] ~asks:[]
  in
  check bool "overflow is not silently wrapped" true
    (try ignore (B.total_quantity book B.Bid); false with Invalid_argument _ -> true)

let () =
  run "l2_book"
    [
      ( "book",
        [ test_case "snapshot seeds" `Quick test_snapshot_seeds_the_book;
          test_case "absolute sizes" `Quick test_updates_set_absolute_sizes;
          test_case "new levels" `Quick test_new_levels_join_the_book;
          test_case "checksum" `Quick test_checksum_is_stable_and_sensitive ] );
      ( "replay",
        [ test_case "pending before snapshot" `Quick test_pending_update_before_snapshot;
          test_case "gap stops the book" `Quick test_gap_stops_the_book;
          test_case "snapshot recovers" `Quick test_snapshot_recovers_after_a_gap;
          test_case "ignores other payloads" `Quick test_ignores_other_payloads ] );
      ("overflow", [ test_case "quantity sum" `Quick test_total_quantity_overflow_fails_closed ]);
    ]
