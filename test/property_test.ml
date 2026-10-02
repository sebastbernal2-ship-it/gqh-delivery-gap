(** Property-based tests for the market simulator.

    Uses QCheck to verify invariants under random inputs. Covers financial
    invariants, edge case combinations, and serialization roundtrips. *)

open Market_simulator.Market_types
open Market_simulator.Side

(* ------------------------------------------------------------------ *)
(* Helpers *)
(* ------------------------------------------------------------------ *)

let arb_of_gen (type a) (gen : a QCheck.Gen.t) : a QCheck.arbitrary =
  QCheck.make gen

(* ------------------------------------------------------------------ *)
(* Generators *)
(* ------------------------------------------------------------------ *)

let gen_price =
  QCheck.Gen.(
    map
      (fun i -> Market_simulator.Price.of_float (float_of_int i))
      (int_range 1 1000000))

let gen_price_pos =
  QCheck.Gen.(
    map
      (fun i -> Market_simulator.Price.of_float (float_of_int i))
      (int_range 1 10000))

let gen_size =
  QCheck.Gen.map Market_simulator.Size.of_int QCheck.Gen.(int_range 1 10000)

let gen_size_pos =
  QCheck.Gen.map Market_simulator.Size.of_int QCheck.Gen.(int_range 1 1000)

let gen_side = QCheck.Gen.oneof [ QCheck.Gen.return Bid; QCheck.Gen.return Ask ]

let gen_action =
  QCheck.Gen.oneof
    [
      QCheck.Gen.return Add;
      QCheck.Gen.return Amend;
      QCheck.Gen.return Cancel;
      QCheck.Gen.return Execute;
    ]

let gen_order_id =
  QCheck.Gen.(map (fun i -> Printf.sprintf "ord-%06d" i) (int_bound 999999))

let gen_add_event =
  QCheck.Gen.map
    (fun i ->
      let id = Printf.sprintf "ord-%06d" i in
      let side = if i mod 2 = 0 then Bid else Ask in
      let price =
        Market_simulator.Price.of_float (100.0 +. float_of_int (i mod 1000))
      in
      let size = Market_simulator.Size.of_int (1 + (i mod 100)) in
      {
        timestamp = Market_simulator.Timestamp.now ();
        order_id = id;
        side;
        price;
        size;
        action = Add;
        valid_time = None;
      })
    (QCheck.Gen.int_bound 1000000)

let gen_bid_event =
  QCheck.Gen.map2
    (fun price size ->
      {
        timestamp = Market_simulator.Timestamp.now ();
        order_id = "test";
        side = Bid;
        price;
        size;
        action = Add;
        valid_time = None;
      })
    gen_price_pos gen_size_pos

let gen_ask_event =
  QCheck.Gen.map2
    (fun price size ->
      {
        timestamp = Market_simulator.Timestamp.now ();
        order_id = "test";
        side = Ask;
        price;
        size;
        action = Add;
        valid_time = None;
      })
    gen_price_pos gen_size_pos

(** Generator for pair of bid/ask events with bid < ask. *)
let gen_bid_ask_pair =
  QCheck.Gen.map2
    (fun bid_price ask_price ->
      assert (bid_price < ask_price);
      let b =
        {
          timestamp = Market_simulator.Timestamp.now ();
          order_id = "b1";
          side = Bid;
          price = Market_simulator.Price.of_int bid_price;
          size = Market_simulator.Size.of_int 100;
          action = Add;
          valid_time = None;
        }
      in
      let a =
        {
          b with
          order_id = "a1";
          side = Ask;
          price = Market_simulator.Price.of_int ask_price;
        }
      in
      (b, a))
    QCheck.Gen.(int_range 1 1000)
    QCheck.Gen.(int_range 1001 2000)

(* ------------------------------------------------------------------ *)
(* Core order book invariants *)
(* ------------------------------------------------------------------ *)

let prop_add_increases_count () =
  QCheck.Test.make ~name:"add increases order count" (arb_of_gen gen_add_event)
    (fun ev ->
      let book = Market_simulator.Order_book.create () in
      let before = Market_simulator.Order_book.order_count book in
      let _ = Market_simulator.Order_book.apply_exn book ev in
      Market_simulator.Order_book.order_count book = before + 1)

let prop_add_bid_creates_level () =
  QCheck.Test.make ~name:"add bid creates bid level" (arb_of_gen gen_bid_event)
    (fun ev ->
      let book = Market_simulator.Order_book.create () in
      let snap = Market_simulator.Order_book.apply_exn book ev in
      List.exists
        (fun l -> Market_simulator.Price.equal l.price ev.price)
        snap.bids)

let prop_add_ask_creates_level () =
  QCheck.Test.make ~name:"add ask creates ask level" (arb_of_gen gen_ask_event)
    (fun ev ->
      let book = Market_simulator.Order_book.create () in
      let snap = Market_simulator.Order_book.apply_exn book ev in
      List.exists
        (fun l -> Market_simulator.Price.equal l.price ev.price)
        snap.asks)

let prop_add_then_cancel () =
  QCheck.Test.make ~name:"add then cancel removes order"
    (arb_of_gen gen_add_event) (fun ev ->
      let book = Market_simulator.Order_book.create () in
      let _ = Market_simulator.Order_book.apply_exn book ev in
      let cancel = { ev with action = Cancel } in
      let _ = Market_simulator.Order_book.apply_exn book cancel in
      Market_simulator.Order_book.order_count book = 0)

let prop_add_then_execute_full () =
  QCheck.Test.make ~name:"add then full execute removes order"
    (arb_of_gen gen_bid_event) (fun ev ->
      let book = Market_simulator.Order_book.create () in
      let _ = Market_simulator.Order_book.apply_exn book ev in
      let exec = { ev with action = Execute; size = ev.size } in
      let _ = Market_simulator.Order_book.apply_exn book exec in
      Market_simulator.Order_book.order_count book = 0)

let prop_add_then_partial_execute () =
  QCheck.Test.make ~name:"add then partial execute reduces size"
    (arb_of_gen
       (QCheck.Gen.map2
          (fun price size ->
            let s = max 2 (Market_simulator.Size.to_int size) in
            {
              timestamp = Market_simulator.Timestamp.now ();
              order_id = "test";
              side = Ask;
              price;
              size = Market_simulator.Size.of_int s;
              action = Add;
              valid_time = None;
            })
          gen_price_pos gen_size_pos))
    (fun ev ->
      let book = Market_simulator.Order_book.create () in
      let _ = Market_simulator.Order_book.apply_exn book ev in
      let exec_size =
        Market_simulator.Size.of_int (Market_simulator.Size.to_int ev.size / 2)
      in
      let exec = { ev with action = Execute; size = exec_size } in
      let snap2 = Market_simulator.Order_book.apply_exn book exec in
      match snap2.asks with
      | l :: _ ->
          Market_simulator.Size.to_int l.total_size
          = Market_simulator.Size.to_int ev.size
            - Market_simulator.Size.to_int exec_size
      | [] -> false)

(* ------------------------------------------------------------------ *)
(* Sorting invariants *)
(* ------------------------------------------------------------------ *)

let prop_bids_sorted_descending () =
  QCheck.Test.make ~name:"bids sorted descending"
    (arb_of_gen
       (QCheck.Gen.map
          (fun n ->
            List.init n (fun i ->
                {
                  timestamp = Market_simulator.Timestamp.now ();
                  order_id = Printf.sprintf "b%d" i;
                  side = Bid;
                  price =
                    Market_simulator.Price.of_float
                      (100.0 +. float_of_int (i * 10));
                  size = Market_simulator.Size.of_int 100;
                  action = Add;
                  valid_time = None;
                }))
          (QCheck.Gen.int_bound 30)))
    (fun events ->
      let book = Market_simulator.Order_book.create () in
      List.iter
        (fun ev -> ignore (Market_simulator.Order_book.apply_exn book ev))
        events;
      let snap = Market_simulator.Order_book.get_snapshot book in
      let rec descending = function
        | [] | [ _ ] -> true
        | a :: b :: rest ->
            Market_simulator.Price.compare a.price b.price >= 0
            && descending (b :: rest)
      in
      descending snap.bids)

let prop_asks_sorted_ascending () =
  QCheck.Test.make ~name:"asks sorted ascending"
    (arb_of_gen
       (QCheck.Gen.map
          (fun n ->
            List.init n (fun i ->
                {
                  timestamp = Market_simulator.Timestamp.now ();
                  order_id = Printf.sprintf "a%d" i;
                  side = Ask;
                  price =
                    Market_simulator.Price.of_float
                      (100.0 +. float_of_int (i * 10));
                  size = Market_simulator.Size.of_int 100;
                  action = Add;
                  valid_time = None;
                }))
          (QCheck.Gen.int_bound 30)))
    (fun events ->
      let book = Market_simulator.Order_book.create () in
      List.iter
        (fun ev -> ignore (Market_simulator.Order_book.apply_exn book ev))
        events;
      let snap = Market_simulator.Order_book.get_snapshot book in
      let rec ascending = function
        | [] | [ _ ] -> true
        | a :: b :: rest ->
            Market_simulator.Price.compare a.price b.price <= 0
            && ascending (b :: rest)
      in
      ascending snap.asks)

(* ------------------------------------------------------------------ *)
(* Aggregation invariants *)
(* ------------------------------------------------------------------ *)

let prop_same_price_level_aggregates () =
  QCheck.Test.make ~name:"same price level aggregates size"
    (arb_of_gen
       (QCheck.Gen.map
          (fun n ->
            List.init n (fun i ->
                {
                  timestamp = Market_simulator.Timestamp.now ();
                  order_id = Printf.sprintf "o%d" i;
                  side = Bid;
                  price = Market_simulator.Price.of_float 100.0;
                  size = Market_simulator.Size.of_int 100;
                  action = Add;
                  valid_time = None;
                }))
          (QCheck.Gen.int_range 1 50)))
    (fun events ->
      let book = Market_simulator.Order_book.create () in
      List.iter
        (fun ev -> ignore (Market_simulator.Order_book.apply_exn book ev))
        events;
      let snap = Market_simulator.Order_book.get_snapshot book in
      match snap.bids with
      | l :: _ ->
          Market_simulator.Size.to_int l.total_size = 100 * List.length events
      | [] -> false)

let prop_order_count_consistent () =
  QCheck.Test.make ~name:"order count consistent (non-crossing)"
    (arb_of_gen
       (QCheck.Gen.map
          (fun i ->
            (* All bids, prices descending so they don't cross *)
            List.init i (fun j ->
                let price = 200.0 -. float_of_int j in
                {
                  timestamp = Market_simulator.Timestamp.now ();
                  order_id = Printf.sprintf "ord-%d" j;
                  side = Bid;
                  price = Market_simulator.Price.of_float price;
                  size = Market_simulator.Size.of_int 100;
                  action = Add;
                  valid_time = None;
                }))
          (QCheck.Gen.int_range 0 100)))
    (fun events ->
      let book = Market_simulator.Order_book.create () in
      List.iter
        (fun ev -> ignore (Market_simulator.Order_book.apply_exn book ev))
        events;
      Market_simulator.Order_book.order_count book = List.length events)

(* ------------------------------------------------------------------ *)
(* Financial invariants *)
(* ------------------------------------------------------------------ *)

(** Invariant: spread is strictly positive when both sides have orders. No
    crossed market. *)
let prop_spread_strictly_positive () =
  QCheck.Test.make ~name:"spread strictly positive (no cross)"
    (arb_of_gen gen_bid_ask_pair) (fun (b_ev, a_ev) ->
      let book = Market_simulator.Order_book.create () in
      let _ = Market_simulator.Order_book.apply_exn book b_ev in
      let _ = Market_simulator.Order_book.apply_exn book a_ev in
      let stats = Market_simulator.Order_book.get_stats book in
      match stats.spread with
      | Some s -> Market_simulator.Price.to_int s > 0
      | None -> true)

(** Invariant: add->cancel of same order restores the price level. *)
let prop_add_cancel_reversible () =
  QCheck.Test.make ~name:"add then cancel is reversible at price level"
    (arb_of_gen gen_add_event) (fun ev ->
      let book = Market_simulator.Order_book.create () in
      let snap_before = Market_simulator.Order_book.get_snapshot book in
      let bid_size_before =
        List.fold_left
          (fun acc l ->
            if Market_simulator.Price.equal l.price ev.price then
              Market_simulator.Size.to_int l.total_size
            else acc)
          0 snap_before.bids
      in
      let ask_size_before =
        List.fold_left
          (fun acc l ->
            if Market_simulator.Price.equal l.price ev.price then
              Market_simulator.Size.to_int l.total_size
            else acc)
          0 snap_before.asks
      in
      let _ = Market_simulator.Order_book.apply_exn book ev in
      let cancel = { ev with action = Cancel } in
      let snap_after = Market_simulator.Order_book.apply_exn book cancel in
      let bid_size_after =
        List.fold_left
          (fun acc l ->
            if Market_simulator.Price.equal l.price ev.price then
              Market_simulator.Size.to_int l.total_size
            else acc)
          0 snap_after.bids
      in
      let ask_size_after =
        List.fold_left
          (fun acc l ->
            if Market_simulator.Price.equal l.price ev.price then
              Market_simulator.Size.to_int l.total_size
            else acc)
          0 snap_after.asks
      in
      bid_size_before = bid_size_after && ask_size_before = ask_size_after)

(** Invariant: best bid < best ask when both exist. *)
let prop_best_bid_lt_best_ask () =
  QCheck.Test.make ~name:"best_bid < best_ask when both exist"
    (arb_of_gen
       (QCheck.Gen.map
          (fun n ->
            let bids =
              List.init
                ((n mod 5) + 1)
                (fun i ->
                  {
                    timestamp = Market_simulator.Timestamp.now ();
                    order_id = Printf.sprintf "b%d" i;
                    side = Bid;
                    price = Market_simulator.Price.of_int (100 - (i * 2));
                    size = Market_simulator.Size.of_int 100;
                    action = Add;
                    valid_time = None;
                  })
            in
            let asks =
              List.init
                ((n mod 5) + 1)
                (fun i ->
                  {
                    timestamp = Market_simulator.Timestamp.now ();
                    order_id = Printf.sprintf "a%d" i;
                    side = Ask;
                    price = Market_simulator.Price.of_int (101 + (i * 2));
                    size = Market_simulator.Size.of_int 100;
                    action = Add;
                    valid_time = None;
                  })
            in
            bids @ asks)
          (QCheck.Gen.int_bound 25)))
    (fun events ->
      let book = Market_simulator.Order_book.create () in
      List.iter
        (fun ev -> ignore (Market_simulator.Order_book.apply_exn book ev))
        events;
      let snap = Market_simulator.Order_book.get_snapshot book in
      let has_both = snap.bids <> [] && snap.asks <> [] in
      if not has_both then true
      else
        let best_bid = (List.hd snap.bids).price in
        let best_ask = (List.hd snap.asks).price in
        Market_simulator.Price.compare best_bid best_ask < 0)

(** Invariant: micro price is set when both sides have orders. *)
let prop_micro_price_set () =
  QCheck.Test.make ~name:"micro price set when both sides exist"
    (arb_of_gen
       (QCheck.Gen.map2
          (fun b a ->
            assert (a > b);
            [
              {
                timestamp = Market_simulator.Timestamp.now ();
                order_id = "b1";
                side = Bid;
                price = Market_simulator.Price.of_float (float_of_int b);
                size = Market_simulator.Size.of_int 100;
                action = Add;
                valid_time = None;
              };
              {
                timestamp = Market_simulator.Timestamp.now ();
                order_id = "a1";
                side = Ask;
                price = Market_simulator.Price.of_float (float_of_int a);
                size = Market_simulator.Size.of_int 100;
                action = Add;
                valid_time = None;
              };
            ])
          QCheck.Gen.(int_range 1 500)
          QCheck.Gen.(int_range 501 1000)))
    (fun events ->
      let book = Market_simulator.Order_book.create () in
      List.iter
        (fun ev -> ignore (Market_simulator.Order_book.apply_exn book ev))
        events;
      let snap = Market_simulator.Order_book.get_snapshot book in
      snap.micro_price <> None)

(** Invariant: top 10 levels are bounded by snapshot. *)
let prop_top_10_bounds () =
  QCheck.Test.make ~name:"snapshot limits to 10 levels per side"
    (arb_of_gen
       (QCheck.Gen.map
          (fun n ->
            List.init n (fun i ->
                let side = if i mod 2 = 0 then Bid else Ask in
                {
                  timestamp = Market_simulator.Timestamp.now ();
                  order_id = Printf.sprintf "o%d" i;
                  side;
                  price = Market_simulator.Price.of_int (100 + i);
                  size = Market_simulator.Size.of_int 10;
                  action = Add;
                  valid_time = None;
                }))
          (QCheck.Gen.int_bound 50)))
    (fun events ->
      let book = Market_simulator.Order_book.create () in
      List.iter
        (fun ev -> ignore (Market_simulator.Order_book.apply_exn book ev))
        events;
      let snap = Market_simulator.Order_book.get_snapshot book in
      List.length snap.bids <= 10 && List.length snap.asks <= 10)

(* ------------------------------------------------------------------ *)
(* State invariants *)
(* ------------------------------------------------------------------ *)

(** Invariant: snapshot stats are consistent with get_stats. *)
let prop_snapshot_stats_consistent () =
  QCheck.Test.make ~name:"snapshot and stats consistent"
    (arb_of_gen
       (QCheck.Gen.map
          (fun i ->
            [
              {
                timestamp = Market_simulator.Timestamp.now ();
                order_id = "b1";
                side = Bid;
                price = Market_simulator.Price.of_float (100.0 +. float_of_int i);
                size = Market_simulator.Size.of_int (100 + i);
                action = Add;
                valid_time = None;
              };
              {
                timestamp = Market_simulator.Timestamp.now ();
                order_id = "a1";
                side = Ask;
                price = Market_simulator.Price.of_float (200.0 +. float_of_int i);
                size = Market_simulator.Size.of_int (50 + i);
                action = Add;
                valid_time = None;
              };
            ])
          (QCheck.Gen.int_bound 100)))
    (fun events ->
      let book = Market_simulator.Order_book.create () in
      List.iter
        (fun ev -> ignore (Market_simulator.Order_book.apply_exn book ev))
        events;
      let snap = Market_simulator.Order_book.get_snapshot book in
      let stats = Market_simulator.Order_book.get_stats book in
      let snap_bid_size =
        List.fold_left
          (fun acc l -> Market_simulator.Size.add acc l.total_size)
          Market_simulator.Size.zero snap.bids
      in
      let snap_ask_size =
        List.fold_left
          (fun acc l -> Market_simulator.Size.add acc l.total_size)
          Market_simulator.Size.zero snap.asks
      in
      Market_simulator.Size.equal snap_bid_size stats.total_bid_size
      && Market_simulator.Size.equal snap_ask_size stats.total_ask_size)

(** Invariant: amend with same values is a no-op on level totals. *)
let prop_amend_same_noop () =
  QCheck.Test.make ~name:"amend with same values is level-neutral"
    (arb_of_gen
       (QCheck.Gen.map2
          (fun price size ->
            {
              timestamp = Market_simulator.Timestamp.now ();
              order_id = "o1";
              side = Ask;
              price;
              size;
              action = Add;
              valid_time = None;
            })
          gen_price_pos gen_size_pos))
    (fun ev ->
      let book = Market_simulator.Order_book.create () in
      let _ = Market_simulator.Order_book.apply_exn book ev in
      let snap_before = Market_simulator.Order_book.get_snapshot book in
      let amend = { ev with action = Amend } in
      let snap_after = Market_simulator.Order_book.apply_exn book amend in
      let level_before =
        List.find_opt
          (fun (l : price_level) ->
            Market_simulator.Price.equal l.price ev.price)
          snap_before.asks
      in
      let level_after =
        List.find_opt
          (fun (l : price_level) ->
            Market_simulator.Price.equal l.price ev.price)
          snap_after.asks
      in
      match (level_before, level_after) with
      | Some a, Some b ->
          Market_simulator.Size.equal a.total_size b.total_size
          && a.order_count = b.order_count
      | None, Some b ->
          Market_simulator.Size.to_int b.total_size
          = Market_simulator.Size.to_int ev.size
      | _, _ -> true)

(* ------------------------------------------------------------------ *)
(* Serialization roundtrip properties *)
(* ------------------------------------------------------------------ *)

(** Price sexp roundtrip. *)
let prop_price_sexp_roundtrip () =
  QCheck.Test.make ~name:"price sexp roundtrip" (arb_of_gen gen_price) (fun p ->
      let sexp = Market_simulator.Price.sexp_of_t p in
      let back = Market_simulator.Price.t_of_sexp sexp in
      Market_simulator.Price.equal p back)

(** Size sexp roundtrip. *)
let prop_size_sexp_roundtrip () =
  QCheck.Test.make ~name:"size sexp roundtrip" (arb_of_gen gen_size) (fun s ->
      let sexp = Market_simulator.Size.sexp_of_t s in
      let back = Market_simulator.Size.t_of_sexp sexp in
      Market_simulator.Size.equal s back)

(** Side sexp roundtrip (both variants). *)
let prop_side_sexp () =
  QCheck.Test.make ~name:"side sexp roundtrip" (arb_of_gen gen_side) (fun s ->
      let sexp = Market_simulator.Side.sexp_of_side s in
      let back = Market_simulator.Side.side_of_sexp sexp in
      Market_simulator.Side.equal_side s back)

(** Action sexp roundtrip. *)
let prop_action_sexp () =
  QCheck.Test.make ~name:"action sexp roundtrip" (arb_of_gen gen_action)
    (fun a ->
      let sexp = Market_simulator.Side.sexp_of_action a in
      let back = Market_simulator.Side.action_of_sexp sexp in
      Market_simulator.Side.equal_action a back)

(** Order id sexp roundtrip. *)
let prop_order_id_sexp () =
  QCheck.Test.make ~name:"order_id sexp roundtrip" (arb_of_gen gen_order_id)
    (fun oid ->
      let sexp = Market_simulator.Order_id.sexp_of_t oid in
      let back = Market_simulator.Order_id.t_of_sexp sexp in
      oid = back)

(* ------------------------------------------------------------------ *)
(* Reset invariants *)
(* ------------------------------------------------------------------ *)

(** Reset returns to empty state. *)
let prop_reset_empty () =
  QCheck.Test.make ~name:"reset clears all state"
    (arb_of_gen
       (QCheck.Gen.map
          (fun n ->
            List.init n (fun i ->
                {
                  timestamp = Market_simulator.Timestamp.now ();
                  order_id = Printf.sprintf "o%d" i;
                  side = (if i mod 2 = 0 then Bid else Ask);
                  price = Market_simulator.Price.of_int (100 + i);
                  size = Market_simulator.Size.of_int 10;
                  action = Add;
                  valid_time = None;
                }))
          (QCheck.Gen.int_range 0 20)))
    (fun events ->
      let book = Market_simulator.Order_book.create () in
      List.iter
        (fun ev -> ignore (Market_simulator.Order_book.apply_exn book ev))
        events;
      Market_simulator.Order_book.reset book;
      let snap = Market_simulator.Order_book.get_snapshot book in
      Market_simulator.Order_book.order_count book = 0
      && List.length snap.bids = 0
      && List.length snap.asks = 0)

(* ------------------------------------------------------------------ *)
(* Bitemporal invariants *)
(* ------------------------------------------------------------------ *)

(** Singleton facts are findable at their timestamp. *)
let prop_bitemporal_singleton () =
  QCheck.Test.make ~name:"bitemporal singleton found at time"
    (arb_of_gen (QCheck.Gen.int_bound 1000))
    (fun v ->
      let now = Market_simulator.Timestamp.now () in
      let ts = Market_simulator.Bitemporal.singleton v now now in
      let result = Market_simulator.Bitemporal.as_of ts now now in
      List.length result = 1 && List.hd result = v)

(** Bitemporal add forward: fact not found before add time. *)
let prop_bitemporal_not_before () =
  QCheck.Test.make ~name:"bitemporal not found before"
    (arb_of_gen (QCheck.Gen.int_bound 1000))
    (fun v ->
      let now = Market_simulator.Timestamp.now () in
      let before = Market_simulator.Timestamp.add_seconds now (-10.0) in
      let ts = Market_simulator.Bitemporal.singleton v now now in
      let result = Market_simulator.Bitemporal.as_of ts before before in
      List.length result = 0)

(* ------------------------------------------------------------------ *)
(* Main test runner *)
(* ------------------------------------------------------------------ *)

let () =
  QCheck_runner.run_tests_main
    [
      prop_add_increases_count ();
      prop_add_bid_creates_level ();
      prop_add_ask_creates_level ();
      prop_add_then_cancel ();
      prop_add_then_execute_full ();
      prop_add_then_partial_execute ();
      prop_bids_sorted_descending ();
      prop_asks_sorted_ascending ();
      prop_same_price_level_aggregates ();
      prop_spread_strictly_positive ();
      prop_add_cancel_reversible ();
      prop_best_bid_lt_best_ask ();
      prop_order_count_consistent ();
      prop_micro_price_set ();
      prop_top_10_bounds ();
      prop_snapshot_stats_consistent ();
      prop_amend_same_noop ();
      prop_price_sexp_roundtrip ();
      prop_size_sexp_roundtrip ();
      prop_side_sexp ();
      prop_action_sexp ();
      prop_order_id_sexp ();
      prop_reset_empty ();
      prop_bitemporal_singleton ();
      prop_bitemporal_not_before ();
    ]
