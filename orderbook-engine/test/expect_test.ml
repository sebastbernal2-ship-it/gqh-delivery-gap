(** Expect tests for the market simulator.

    These tests capture the output of key operations as expected values. All
    tests use [Timestamp.zero] for deterministic, reproducible output. When
    behavior changes intentionally, run: dune promote

    to automatically update the expected output. *)

open Market_simulator.Market_types
open Market_simulator.Side

let zero_ts = Market_simulator.Timestamp.zero

(** A helper to print a snapshot for expect-test comparison. *)
let print_snapshot snap =
  Printf.printf "=== Snapshot ===\n";
  Printf.printf "Timestamp: %s\n"
    (Market_simulator.Timestamp.to_string snap.timestamp);
  Printf.printf "Bids (%d levels):\n" (List.length snap.bids);
  List.iter
    (fun (l : price_level) ->
      Printf.printf "  %s x %d (%d orders)\n"
        (Market_simulator.Price.to_string l.price)
        (Market_simulator.Size.to_int l.total_size)
        l.order_count)
    snap.bids;
  Printf.printf "Asks (%d levels):\n" (List.length snap.asks);
  List.iter
    (fun (l : price_level) ->
      Printf.printf "  %s x %d (%d orders)\n"
        (Market_simulator.Price.to_string l.price)
        (Market_simulator.Size.to_int l.total_size)
        l.order_count)
    snap.asks;
  let spread =
    match snap.spread with
    | Some s -> Market_simulator.Price.to_string s
    | None -> "N/A"
  in
  let mid =
    match snap.mid_price with
    | Some m -> Market_simulator.Price.to_string m
    | None -> "N/A"
  in
  Printf.printf "Spread: %s  Mid: %s\n" spread mid

(* ------------------------------------------------------------------ *)
(* Basic order book operations *)
(* ------------------------------------------------------------------ *)

let%expect_test "add one bid order" =
  let book = Market_simulator.Order_book.create () in
  let ev =
    {
      timestamp = zero_ts;
      order_id = "test001";
      side = Bid;
      price = Market_simulator.Price.of_float 100.50;
      size = Market_simulator.Size.of_int 500;
      action = Add;
      valid_time = None;
    }
  in
  let snap = Market_simulator.Order_book.apply_exn book ev in
  print_snapshot snap;
  Printf.printf "Order count: %d\n"
    (Market_simulator.Order_book.order_count book);
  [%expect
    {|
    === Snapshot ===
    Timestamp: 1970-01-01T00:00:00-00:00
    Bids (1 levels):
      100.5000 x 500 (1 orders)
    Asks (0 levels):
    Spread: N/A  Mid: N/A
    Order count: 1
    |}]

let%expect_test "add bid and ask, full book" =
  let book = Market_simulator.Order_book.create () in
  let _ =
    Market_simulator.Order_book.apply_exn book
      {
        timestamp = zero_ts;
        order_id = "b1";
        side = Bid;
        price = Market_simulator.Price.of_float 100.00;
        size = Market_simulator.Size.of_int 500;
        action = Add;
        valid_time = None;
      }
  in
  let _ =
    Market_simulator.Order_book.apply_exn book
      {
        timestamp = zero_ts;
        order_id = "b2";
        side = Bid;
        price = Market_simulator.Price.of_float 99.50;
        size = Market_simulator.Size.of_int 200;
        action = Add;
        valid_time = None;
      }
  in
  let snap =
    Market_simulator.Order_book.apply_exn book
      {
        timestamp = zero_ts;
        order_id = "a1";
        side = Ask;
        price = Market_simulator.Price.of_float 101.00;
        size = Market_simulator.Size.of_int 300;
        action = Add;
        valid_time = None;
      }
  in
  print_snapshot snap;
  Printf.printf "Order count: %d\n"
    (Market_simulator.Order_book.order_count book);
  [%expect
    {|
    === Snapshot ===
    Timestamp: 1970-01-01T00:00:00-00:00
    Bids (2 levels):
      100.0000 x 500 (1 orders)
      99.5000 x 200 (1 orders)
    Asks (1 levels):
      101.0000 x 300 (1 orders)
    Spread: 1.0000  Mid: 100.5000
    Order count: 3
    |}]

let%expect_test "add then cancel" =
  let book = Market_simulator.Order_book.create () in
  let _ =
    Market_simulator.Order_book.apply_exn book
      {
        timestamp = zero_ts;
        order_id = "o1";
        side = Bid;
        price = Market_simulator.Price.of_float 100.00;
        size = Market_simulator.Size.of_int 500;
        action = Add;
        valid_time = None;
      }
  in
  let snap =
    Market_simulator.Order_book.apply_exn book
      {
        timestamp = zero_ts;
        order_id = "o1";
        side = Bid;
        price = Market_simulator.Price.of_float 100.00;
        size = Market_simulator.Size.of_int 500;
        action = Cancel;
        valid_time = None;
      }
  in
  print_snapshot snap;
  [%expect
    {|
    === Snapshot ===
    Timestamp: 1970-01-01T00:00:00-00:00
    Bids (0 levels):
    Asks (0 levels):
    Spread: N/A  Mid: N/A
    |}]

(* ------------------------------------------------------------------ *)
(* Error path tests *)
(* ------------------------------------------------------------------ *)

let%expect_test "error on cancel unknown order" =
  let book = Market_simulator.Order_book.create () in
  let ev =
    {
      timestamp = zero_ts;
      order_id = "nonexistent";
      side = Bid;
      price = Market_simulator.Price.of_float 100.00;
      size = Market_simulator.Size.of_int 100;
      action = Cancel;
      valid_time = None;
    }
  in
  match Market_simulator.Order_book.apply book ev with
  | Ok _ -> Printf.printf "UNEXPECTED SUCCESS\n"
  | Error msg ->
      Printf.printf "Error: %s\n" msg;
      [%expect {|
    Error: order nonexistent not found for cancel action |}]

let%expect_test "amend unknown order returns error" =
  let book = Market_simulator.Order_book.create () in
  match
    Market_simulator.Order_book.apply book
      {
        timestamp = zero_ts;
        order_id = "ghost";
        side = Bid;
        price = Market_simulator.Price.of_float 100.00;
        size = Market_simulator.Size.of_int 100;
        action = Amend;
        valid_time = None;
      }
  with
  | Ok _ -> Printf.printf "UNEXPECTED SUCCESS\n"
  | Error msg ->
      Printf.printf "Error: %s\n" msg;
      [%expect {|
    Error: order ghost not found for amend action |}]

let%expect_test "execute unknown order returns error" =
  let book = Market_simulator.Order_book.create () in
  match
    Market_simulator.Order_book.apply book
      {
        timestamp = zero_ts;
        order_id = "phantom";
        side = Ask;
        price = Market_simulator.Price.of_float 101.00;
        size = Market_simulator.Size.of_int 100;
        action = Execute;
        valid_time = None;
      }
  with
  | Ok _ -> Printf.printf "UNEXPECTED SUCCESS\n"
  | Error msg ->
      Printf.printf "Error: %s\n" msg;
      [%expect {|
    Error: order phantom not found for execute action |}]

let%expect_test "double cancel returns error on second" =
  let book = Market_simulator.Order_book.create () in
  let _ =
    Market_simulator.Order_book.apply_exn book
      {
        timestamp = zero_ts;
        order_id = "o1";
        side = Bid;
        price = Market_simulator.Price.of_float 100.00;
        size = Market_simulator.Size.of_int 500;
        action = Add;
        valid_time = None;
      }
  in
  let _ =
    Market_simulator.Order_book.apply_exn book
      {
        timestamp = zero_ts;
        order_id = "o1";
        side = Bid;
        price = Market_simulator.Price.of_float 100.00;
        size = Market_simulator.Size.of_int 500;
        action = Cancel;
        valid_time = None;
      }
  in
  match
    Market_simulator.Order_book.apply book
      {
        timestamp = zero_ts;
        order_id = "o1";
        side = Bid;
        price = Market_simulator.Price.of_float 100.00;
        size = Market_simulator.Size.of_int 0;
        action = Cancel;
        valid_time = None;
      }
  with
  | Ok _ -> Printf.printf "UNEXPECTED SUCCESS\n"
  | Error msg ->
      Printf.printf "Error: %s\n" msg;
      [%expect {|
    Error: order o1 not found for cancel action |}]

let%expect_test "amend after cancel returns error" =
  let book = Market_simulator.Order_book.create () in
  let _ =
    Market_simulator.Order_book.apply_exn book
      {
        timestamp = zero_ts;
        order_id = "o1";
        side = Bid;
        price = Market_simulator.Price.of_float 100.00;
        size = Market_simulator.Size.of_int 500;
        action = Add;
        valid_time = None;
      }
  in
  let _ =
    Market_simulator.Order_book.apply_exn book
      {
        timestamp = zero_ts;
        order_id = "o1";
        side = Bid;
        price = Market_simulator.Price.of_float 100.00;
        size = Market_simulator.Size.of_int 500;
        action = Cancel;
        valid_time = None;
      }
  in
  match
    Market_simulator.Order_book.apply book
      {
        timestamp = zero_ts;
        order_id = "o1";
        side = Bid;
        price = Market_simulator.Price.of_float 101.00;
        size = Market_simulator.Size.of_int 200;
        action = Amend;
        valid_time = None;
      }
  with
  | Ok _ -> Printf.printf "UNEXPECTED SUCCESS\n"
  | Error msg ->
      Printf.printf "Error: %s\n" msg;
      [%expect {|
    Error: order o1 not found for amend action |}]

(* ------------------------------------------------------------------ *)
(* Execution scenarios *)
(* ------------------------------------------------------------------ *)

let%expect_test "add, execute partial, get snapshot" =
  let book = Market_simulator.Order_book.create () in
  let add_ev =
    {
      timestamp = zero_ts;
      order_id = "o1";
      side = Ask;
      price = Market_simulator.Price.of_float 101.00;
      size = Market_simulator.Size.of_int 500;
      action = Add;
      valid_time = None;
    }
  in
  let _ = Market_simulator.Order_book.apply_exn book add_ev in
  let exec_ev =
    {
      timestamp = zero_ts;
      order_id = "o1";
      side = Ask;
      price = Market_simulator.Price.of_float 101.00;
      size = Market_simulator.Size.of_int 200;
      action = Execute;
      valid_time = None;
    }
  in
  let snap = Market_simulator.Order_book.apply_exn book exec_ev in
  let stats = Market_simulator.Order_book.get_stats book in
  print_snapshot snap;
  Printf.printf "Remaining size: %d\n"
    (Market_simulator.Size.to_int stats.total_ask_size);
  [%expect
    {|
    === Snapshot ===
    Timestamp: 1970-01-01T00:00:00-00:00
    Bids (0 levels):
    Asks (1 levels):
      101.0000 x 300 (1 orders)
    Spread: N/A  Mid: N/A
    Remaining size: 300
    |}]

let%expect_test "execute more than order size clamps to remaining" =
  let book = Market_simulator.Order_book.create () in
  let ev =
    {
      timestamp = zero_ts;
      order_id = "o1";
      side = Ask;
      price = Market_simulator.Price.of_float 101.00;
      size = Market_simulator.Size.of_int 100;
      action = Add;
      valid_time = None;
    }
  in
  let _ = Market_simulator.Order_book.apply_exn book ev in
  let snap =
    Market_simulator.Order_book.apply_exn book
      {
        timestamp = zero_ts;
        order_id = "o1";
        side = Ask;
        price = Market_simulator.Price.of_float 101.00;
        size = Market_simulator.Size.of_int 200;
        action = Execute;
        valid_time = None;
      }
  in
  begin match snap.asks with
  | [] -> Printf.printf "Level fully executed\n"
  | l :: _ ->
      Printf.printf "Remaining: %d\n"
        (Market_simulator.Size.to_int l.total_size)
  end;
  Printf.printf "Order count: %d\n"
    (Market_simulator.Order_book.order_count book);
  [%expect {|
    Level fully executed
    Order count: 0 |}]

let%expect_test "execute zero size preserves order" =
  let book = Market_simulator.Order_book.create () in
  let ev =
    {
      timestamp = zero_ts;
      order_id = "o1";
      side = Ask;
      price = Market_simulator.Price.of_float 101.00;
      size = Market_simulator.Size.of_int 100;
      action = Add;
      valid_time = None;
    }
  in
  let _ = Market_simulator.Order_book.apply_exn book ev in
  let snap =
    Market_simulator.Order_book.apply_exn book
      {
        timestamp = zero_ts;
        order_id = "o1";
        side = Ask;
        price = Market_simulator.Price.of_float 101.00;
        size = Market_simulator.Size.of_int 0;
        action = Execute;
        valid_time = None;
      }
  in
  print_snapshot snap;
  [%expect
    {|
    === Snapshot ===
    Timestamp: 1970-01-01T00:00:00-00:00
    Bids (0 levels):
    Asks (1 levels):
      101.0000 x 100 (1 orders)
    Spread: N/A  Mid: N/A
    |}]

let%expect_test "crossing bid fills resting ask" =
  let book = Market_simulator.Order_book.create () in
  let _ =
    Market_simulator.Order_book.apply_exn book
      {
        timestamp = zero_ts;
        order_id = "ask-1";
        side = Ask;
        price = Market_simulator.Price.of_float 101.00;
        size = Market_simulator.Size.of_int 300;
        action = Add;
        valid_time = None;
      }
  in
  match
    Market_simulator.Order_book.apply book
      {
        timestamp = zero_ts;
        order_id = "bid-1";
        side = Bid;
        price = Market_simulator.Price.of_float 102.00;
        size = Market_simulator.Size.of_int 200;
        action = Add;
        valid_time = None;
      }
  with
  | Error msg -> Printf.printf "Error: %s\n" msg
  | Ok (snap, fills) ->
      Printf.printf "Fill count: %d\n" (List.length fills);
      List.iter
        (fun fill ->
          Printf.printf "Fill: %s -> %s @ %s x %d\n" fill.buy_order_id
            fill.sell_order_id
            (Market_simulator.Price.to_string fill.fill_price)
            (Market_simulator.Size.to_int fill.fill_size))
        fills;
      print_snapshot snap;
      [%expect
        {|
    Fill count: 1
    Fill: bid-1 -> ask-1 @ 101.0000 x 200
    === Snapshot ===
    Timestamp: 1970-01-01T00:00:00-00:00
    Bids (0 levels):
    Asks (1 levels):
      101.0000 x 100 (1 orders)
    Spread: N/A  Mid: N/A
    |}]

(* ------------------------------------------------------------------ *)
(* Amend scenarios *)
(* ------------------------------------------------------------------ *)

let%expect_test "amend moves order to different price level" =
  let book = Market_simulator.Order_book.create () in
  let _ =
    Market_simulator.Order_book.apply_exn book
      {
        timestamp = zero_ts;
        order_id = "o1";
        side = Ask;
        price = Market_simulator.Price.of_float 101.00;
        size = Market_simulator.Size.of_int 300;
        action = Add;
        valid_time = None;
      }
  in
  let _ =
    Market_simulator.Order_book.apply_exn book
      {
        timestamp = zero_ts;
        order_id = "o2";
        side = Ask;
        price = Market_simulator.Price.of_float 101.00;
        size = Market_simulator.Size.of_int 200;
        action = Add;
        valid_time = None;
      }
  in
  let snap =
    Market_simulator.Order_book.apply_exn book
      {
        timestamp = zero_ts;
        order_id = "o1";
        side = Ask;
        price = Market_simulator.Price.of_float 102.00;
        size = Market_simulator.Size.of_int 150;
        action = Amend;
        valid_time = None;
      }
  in
  print_snapshot snap;
  Printf.printf "Order count: %d\n"
    (Market_simulator.Order_book.order_count book);
  [%expect
    {|
    === Snapshot ===
    Timestamp: 1970-01-01T00:00:00-00:00
    Bids (0 levels):
    Asks (2 levels):
      101.0000 x 200 (1 orders)
      102.0000 x 150 (1 orders)
    Spread: N/A  Mid: N/A
    Order count: 2 |}]

let%expect_test "amend same price and size (no-op on level)" =
  let book = Market_simulator.Order_book.create () in
  let _ =
    Market_simulator.Order_book.apply_exn book
      {
        timestamp = zero_ts;
        order_id = "o1";
        side = Ask;
        price = Market_simulator.Price.of_float 101.00;
        size = Market_simulator.Size.of_int 300;
        action = Add;
        valid_time = None;
      }
  in
  let snap =
    Market_simulator.Order_book.apply_exn book
      {
        timestamp = zero_ts;
        order_id = "o1";
        side = Ask;
        price = Market_simulator.Price.of_float 101.00;
        size = Market_simulator.Size.of_int 300;
        action = Amend;
        valid_time = None;
      }
  in
  print_snapshot snap;
  [%expect
    {|
    === Snapshot ===
    Timestamp: 1970-01-01T00:00:00-00:00
    Bids (0 levels):
    Asks (1 levels):
      101.0000 x 300 (1 orders)
    Spread: N/A  Mid: N/A
    |}]

(* ------------------------------------------------------------------ *)
(* Serialization *)
(* ------------------------------------------------------------------ *)

let%expect_test "serialize event as sexp" =
  let ev =
    {
      timestamp = zero_ts;
      order_id = "o1";
      side = Bid;
      price = Market_simulator.Price.of_float 100.50;
      size = Market_simulator.Size.of_int 500;
      action = Add;
      valid_time = None;
    }
  in
  let sexp = Market_simulator.Market_types.sexp_of_event ev in
  Printf.printf "%s\n" (Sexplib0.Sexp.to_string sexp);
  [%expect
    {| ((timestamp 1970-01-01T00:00:00-00:00)(order_id o1)(side bid)(price 100.5000)(size 500)(action add)) |}]

let%expect_test "serialize book snapshot sexp" =
  let ev =
    {
      timestamp = zero_ts;
      order_id = "o1";
      side = Bid;
      price = Market_simulator.Price.of_float 100.00;
      size = Market_simulator.Size.of_int 500;
      action = Add;
      valid_time = None;
    }
  in
  let book = Market_simulator.Order_book.create () in
  let _ = Market_simulator.Order_book.apply_exn book ev in
  let snap = Market_simulator.Order_book.get_snapshot book in
  let sexp =
    Market_simulator.Market_types.sexp_of_market_event
      (Market_simulator.Market_types.BookSnapshot snap)
  in
  Printf.printf "%s\n" (Sexplib0.Sexp.to_string sexp);
  [%expect
    {| (book_snapshot((timestamp 1970-01-01T00:00:00-00:00)(bids(((price 100.0000)(total_size 500)(order_count 1))))(asks())(spread null)(mid_price null)(micro_price 0.0000))) |}]

let%expect_test "serialize stats update sexp" =
  let ev =
    {
      timestamp = zero_ts;
      order_id = "o1";
      side = Bid;
      price = Market_simulator.Price.of_float 100.00;
      size = Market_simulator.Size.of_int 500;
      action = Add;
      valid_time = None;
    }
  in
  let book = Market_simulator.Order_book.create () in
  let _ = Market_simulator.Order_book.apply_exn book ev in
  let stats = Market_simulator.Order_book.get_stats book in
  let sexp =
    Market_simulator.Market_types.sexp_of_market_event
      (Market_simulator.Market_types.StatsUpdate stats)
  in
  Printf.printf "%s\n" (Sexplib0.Sexp.to_string sexp);
  [%expect
    {| (stats_update((total_bid_size 500)(total_ask_size 0)(bid_count 1)(ask_count 0)(spread null)(mid_price null))) |}]

let%expect_test "serialize market events (all variants) as sexp" =
  let ev =
    {
      timestamp = zero_ts;
      order_id = "o1";
      side = Bid;
      price = Market_simulator.Price.of_float 100.00;
      size = Market_simulator.Size.of_int 500;
      action = Add;
      valid_time = None;
    }
  in
  let events : market_event list =
    [
      OrderAdded ev;
      OrderAmended ev;
      OrderCancelled ev;
      OrderExecuted (ev, Market_simulator.Size.of_int 200);
    ]
  in
  List.iter
    (fun me ->
      let sexp = Market_simulator.Market_types.sexp_of_market_event me in
      Printf.printf "%s\n" (Sexplib0.Sexp.to_string sexp))
    events;
  [%expect
    {|
    (order_added((timestamp 1970-01-01T00:00:00-00:00)(order_id o1)(side bid)(price 100.0000)(size 500)(action add)))
    (order_amended((timestamp 1970-01-01T00:00:00-00:00)(order_id o1)(side bid)(price 100.0000)(size 500)(action add)))
    (order_cancelled((timestamp 1970-01-01T00:00:00-00:00)(order_id o1)(side bid)(price 100.0000)(size 500)(action add)))
    (order_executed((timestamp 1970-01-01T00:00:00-00:00)(order_id o1)(side bid)(price 100.0000)(size 500)(action add))200)
    |}]

(* ------------------------------------------------------------------ *)
(* Side and action S-expression roundtrips *)
(* ------------------------------------------------------------------ *)

let%expect_test "side sexp roundtrip" =
  let sides = [ Bid; Ask ] in
  List.iter
    (fun s ->
      let sexp = Market_simulator.Side.sexp_of_side s in
      let back = Market_simulator.Side.side_of_sexp sexp in
      Printf.printf "side: %s, sexp: %s, back: %s\n"
        (Market_simulator.Side.show_side s)
        (Sexplib0.Sexp.to_string sexp)
        (Market_simulator.Side.show_side back))
    sides;
  [%expect
    {|
    side: Side.Bid, sexp: bid, back: Side.Bid
    side: Side.Ask, sexp: ask, back: Side.Ask
    |}]

let%expect_test "action sexp roundtrip" =
  let actions = [ Add; Amend; Cancel; Execute ] in
  List.iter
    (fun a ->
      let sexp = Market_simulator.Side.sexp_of_action a in
      let back = Market_simulator.Side.action_of_sexp sexp in
      Printf.printf "action: %s, sexp: %s, back: %s\n"
        (Market_simulator.Side.show_action a)
        (Sexplib0.Sexp.to_string sexp)
        (Market_simulator.Side.show_action back))
    actions;
  [%expect
    {|
    action: Side.Add, sexp: add, back: Side.Add
    action: Side.Amend, sexp: amend, back: Side.Amend
    action: Side.Cancel, sexp: cancel, back: Side.Cancel
    action: Side.Execute, sexp: execute, back: Side.Execute
    |}]

(* ------------------------------------------------------------------ *)
(* Complete scenario *)
(* ------------------------------------------------------------------ *)

let%expect_test "full scenario: add bids, asks, execute, cancel" =
  let book = Market_simulator.Order_book.create () in
  (* Add 3 bids *)
  let _ =
    Market_simulator.Order_book.apply_exn book
      {
        timestamp = zero_ts;
        order_id = "b1";
        side = Bid;
        price = Market_simulator.Price.of_float 100.00;
        size = Market_simulator.Size.of_int 200;
        action = Add;
        valid_time = None;
      }
  in
  let _ =
    Market_simulator.Order_book.apply_exn book
      {
        timestamp = zero_ts;
        order_id = "b2";
        side = Bid;
        price = Market_simulator.Price.of_float 99.00;
        size = Market_simulator.Size.of_int 300;
        action = Add;
        valid_time = None;
      }
  in
  let _ =
    Market_simulator.Order_book.apply_exn book
      {
        timestamp = zero_ts;
        order_id = "b3";
        side = Bid;
        price = Market_simulator.Price.of_float 101.00;
        size = Market_simulator.Size.of_int 150;
        action = Add;
        valid_time = None;
      }
  in
  (* Add 2 asks *)
  let _ =
    Market_simulator.Order_book.apply_exn book
      {
        timestamp = zero_ts;
        order_id = "a1";
        side = Ask;
        price = Market_simulator.Price.of_float 102.00;
        size = Market_simulator.Size.of_int 250;
        action = Add;
        valid_time = None;
      }
  in
  let _ =
    Market_simulator.Order_book.apply_exn book
      {
        timestamp = zero_ts;
        order_id = "a2";
        side = Ask;
        price = Market_simulator.Price.of_float 103.00;
        size = Market_simulator.Size.of_int 350;
        action = Add;
        valid_time = None;
      }
  in
  (* Snapshot before any action *)
  let s1 = Market_simulator.Order_book.get_snapshot book in
  print_snapshot s1;
  Printf.printf "---\n";
  (* Partially fill best ask *)
  let s2 =
    Market_simulator.Order_book.apply_exn book
      {
        timestamp = zero_ts;
        order_id = "a1";
        side = Ask;
        price = Market_simulator.Price.of_float 102.00;
        size = Market_simulator.Size.of_int 100;
        action = Execute;
        valid_time = None;
      }
  in
  print_snapshot s2;
  Printf.printf "---\n";
  (* Cancel middle bid *)
  let s3 =
    Market_simulator.Order_book.apply_exn book
      {
        timestamp = zero_ts;
        order_id = "b2";
        side = Bid;
        price = Market_simulator.Price.of_float 99.00;
        size = Market_simulator.Size.of_int 300;
        action = Cancel;
        valid_time = None;
      }
  in
  print_snapshot s3;
  [%expect
    {|
    === Snapshot ===
    Timestamp: 1970-01-01T00:00:00-00:00
    Bids (3 levels):
      101.0000 x 150 (1 orders)
      100.0000 x 200 (1 orders)
      99.0000 x 300 (1 orders)
    Asks (2 levels):
      102.0000 x 250 (1 orders)
      103.0000 x 350 (1 orders)
    Spread: 1.0000  Mid: 101.5000
    ---
    === Snapshot ===
    Timestamp: 1970-01-01T00:00:00-00:00
    Bids (3 levels):
      101.0000 x 150 (1 orders)
      100.0000 x 200 (1 orders)
      99.0000 x 300 (1 orders)
    Asks (2 levels):
      102.0000 x 150 (1 orders)
      103.0000 x 350 (1 orders)
    Spread: 1.0000  Mid: 101.5000
    ---
    === Snapshot ===
    Timestamp: 1970-01-01T00:00:00-00:00
    Bids (2 levels):
      101.0000 x 150 (1 orders)
      100.0000 x 200 (1 orders)
    Asks (2 levels):
      102.0000 x 150 (1 orders)
      103.0000 x 350 (1 orders)
    Spread: 1.0000  Mid: 101.5000
    |}]
