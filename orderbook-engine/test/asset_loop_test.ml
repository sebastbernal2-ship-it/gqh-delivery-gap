open Alcotest
module S = Market_simulator.Instrument_spec
module A = Market_simulator.Asset_account
module L = Market_simulator.Asset_loop
module E = Market_simulator.Exec_event
module T = Market_simulator.Timestamp

let ok = function Ok value -> value | Error message -> failwith message
let is_error = function Error _ -> true | Ok _ -> false
let at = ok (T.of_string "2024-01-02T15:00:00Z")
let later = T.add_ns at 1_000_000_000L
let unit = 1_000_000L
let money dollars = Int64.mul dollars 100_000_000L

let spec kind =
  {
    S.venue = "fixture";
    symbol = "TEST";
    currency = "USD";
    effective_from = at;
    effective_until = None;
    price_increment_ticks = 100L;
    quantity_increment_units = unit;
    multiplier = 1L;
    kind;
  }

let event ?(receive_time = at) payload =
  {
    E.venue = "fixture";
    symbol = "TEST";
    event_time = receive_time;
    receive_time;
    sequence = None;
    source_id = "golden-fixture";
    source_path = "test/asset_loop_test.ml";
    source_sha256 = String.make 64 'a';
    quality = E.Healthy;
    payload;
  }

let level price quantity = { E.price_ticks = price; quantity_units = quantity }

let snapshot =
  event
    (E.Depth_snapshot
       {
         last_update_id = Some 100L;
         bids = [ level 99_000L unit ];
         asks = [ level 100_000L unit; level 101_000L unit ];
       })

let intent ?(order_id = "o1") ?(tif = E.Ioc) ?(quantity_units = unit) () =
  event
    (E.Order_intent
       {
         order_id;
         side = E.Buy;
         price_ticks = None;
         quantity_units;
         tif;
         reduce_only = false;
         post_only = false;
       })

let replay ?(latency_ns = 0L) ?(fee_bps = 0) ?(kind = S.Equity) events =
  L.run (spec kind) ~initial_cash:(money 100L) ~taker_fee_bps:fee_bps
    ~latency_ns
    ~equity_settlement:(fun timestamp -> T.add_ns timestamp 86_400_000_000_000L)
    events

let test_ioc_visible_depth_and_fee () =
  let result = ok (replay ~fee_bps:100 [ snapshot; intent () ]) in
  check int "one submitted" 1 result.L.submitted;
  check int "one fill" 1 (List.length result.L.fills);
  check int64 "position" unit result.L.account.A.position_units;
  check int64 "cash less principal and one percent" 8_990_000_000L
    result.L.account.A.cash;
  check int64 "fee recorded" 10_000_000L result.L.account.A.fees;
  check int64 "best ask depleted" 101_000L
    (Option.get (Market_simulator.L2_book.best_ask result.L.book));
  check int "one equity point per input event" 2
    (List.length result.L.equity_curve);
  let summary =
    ok
      (Market_simulator.Asset_report.summarize ~initial_cash:(money 100L)
         ~events:[ snapshot; intent () ] result)
  in
  check int64 "net return includes spread and fees" (-15L) summary.net_return_bps;
  check int64 "mark-to-market drawdown includes open inventory" 15L
    summary.max_drawdown_bps;
  check int "intent count" 1 summary.order_intent_count;
  check int "fill count" 1 summary.fill_count

let test_fok_and_partial_ioc () =
  let two = Int64.mul 2L unit in
  let more = Int64.mul 3L unit in
  let fok =
    ok (replay [ snapshot; intent ~tif:E.Fok ~quantity_units:more () ])
  in
  check int "FOK has no fills" 0 (List.length fok.L.fills);
  check int64 "FOK leaves book" 100_000L
    (Option.get (Market_simulator.L2_book.best_ask fok.L.book));
  let ioc = ok (replay [ snapshot; intent ~quantity_units:more () ]) in
  check int "IOC partial counted" 1 ioc.L.unfilled;
  check int "two visible levels filled" 2 (List.length ioc.L.fills);
  check int64 "only available depth" two ioc.L.account.A.position_units

let test_latency_and_duplicate () =
  let pending =
    ok (replay ~latency_ns:1_000_000_000L [ snapshot; intent () ])
  in
  check int "no lookahead fill" 0 (List.length pending.L.fills);
  check int "pending order" 1 pending.L.unfilled;
  let elapsed =
    ok
      (replay ~latency_ns:1_000_000_000L
         [
           snapshot;
           intent ();
           event ~receive_time:later
             (E.Trade
                {
                  trade_id = 1L;
                  price_ticks = 100_000L;
                  quantity_units = unit;
                  buyer_is_maker = false;
                });
         ])
  in
  check int "fill after receive latency" 1 (List.length elapsed.L.fills);
  check bool "fill timestamp is later" true
    (T.compare (List.hd elapsed.L.fills).L.at later = 0);
  let duplicate = ok (replay [ snapshot; intent (); intent () ]) in
  check int "duplicate rejected" 1 duplicate.L.rejected;
  check int "duplicate not executed" 1 (List.length duplicate.L.fills)

let test_fail_closed () =
  check bool "mixed symbols reject" true
    (is_error (replay [ { snapshot with E.symbol = "OTHER" } ]));
  check bool "bad provenance rejects" true
    (is_error (replay [ { snapshot with E.source_sha256 = "wrong" } ]));
  check bool "receive time regression rejects" true
    (is_error (replay [ { snapshot with E.receive_time = later }; intent () ]));
  let crossed =
    event
      (E.Depth_snapshot
         {
           last_update_id = None;
           bids = [ level 101_000L unit ];
           asks = [ level 100_000L unit ];
         })
  in
  check bool "crossed book rejects" true (is_error (replay [ crossed ]));
  let bad_size =
    event
      (E.Depth_snapshot
         {
           last_update_id = None;
           bids = [ level 99_000L 1L ];
           asks = [ level 100_000L unit ];
         })
  in
  check bool "nonconforming depth size rejects" true
    (is_error (replay [ bad_size ]))

let test_equity_sale_settles_on_clock () =
  let sale =
    event ~receive_time:later
      (E.Order_intent
         {
           order_id = "sale";
           side = E.Sell;
           price_ticks = None;
           quantity_units = unit;
           tif = E.Ioc;
           reduce_only = true;
           post_only = false;
         })
  in
  let after_due = T.add_ns later 86_400_000_000_001L in
  let tick =
    event ~receive_time:after_due
      (E.Trade
         {
           trade_id = 2L;
           price_ticks = 99_000L;
           quantity_units = unit;
           buyer_is_maker = true;
         })
  in
  let before = ok (replay [ snapshot; intent (); sale ]) in
  check int "sale not rejected" 0 before.L.rejected;
  check int "buy and sale fill" 2 (List.length before.L.fills);
  check int "sale receivable remains pending" 1
    (List.length before.L.account.A.receivables);
  let after = ok (replay [ snapshot; intent (); sale; tick ]) in
  check int "receivable settled" 0 (List.length after.L.account.A.receivables);
  check int64 "cash credited after settlement" 9_990_000_000L
    after.L.account.A.cash

let test_nanosecond_offsets_across_days () =
  let two_days = T.add_ns at 172_800_000_000_001L in
  check bool "positive multi-day offset" true (T.compare two_days at > 0);
  let restored = T.add_ns two_days (-172_800_000_000_001L) in
  check bool "negative multi-day offset" true (T.compare restored at = 0)

let () =
  run "asset-loop"
    [
      ( "visible-depth execution",
        [
          test_case "IOC and fee" `Quick test_ioc_visible_depth_and_fee;
          test_case "FOK and partial IOC" `Quick test_fok_and_partial_ioc;
          test_case "latency and duplicate" `Quick test_latency_and_duplicate;
          test_case "fail closed" `Quick test_fail_closed;
          test_case "equity settlement clock" `Quick
            test_equity_sale_settles_on_clock;
          test_case "nanosecond offsets across days" `Quick
            test_nanosecond_offsets_across_days;
        ] );
    ]
