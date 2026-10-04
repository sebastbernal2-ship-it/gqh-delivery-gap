(** Order book engine with incremental recomputation.

    The book state is fully immutable. Per-level order storage uses
    [Order_id.Map] for O(log n) lookup instead of linear list scans. Snapshots
    and stats are derived via [Incr.map] on the state var. When an event is
    applied, a completely new state is created with no aliasing — incr cut-off
    correctly detects unchanged values. *)

open Market_types
open Side

type order_tree = {
  price : Price.t;
  orders : Market_types.order Order_id.Map.t;
  total_size : Size.t;
}
(** A price level: orders at that price and cached total size. *)

type order_db = Market_types.order Order_id.Map.t

type book_state = {
  bids : order_tree Price.Map.t;
  asks : order_tree Price.Map.t;
  orders : order_db;
  sequence : int;
  last_update : Timestamp.t;
}
(** The full book state — fully immutable. *)

type t = {
  get_state : unit -> book_state;
  set_state : book_state -> unit;
  stabilize : unit -> unit;
  get_snapshot : unit -> book_snapshot;
  get_stats : unit -> book_stats;
}

let empty_state () : book_state =
  {
    bids = Price.Map.empty;
    asks = Price.Map.empty;
    orders = Order_id.Map.empty;
    sequence = 0;
    last_update = Timestamp.zero;
  }

let empty_tree (price : Price.t) : order_tree =
  { price; orders = Order_id.Map.empty; total_size = Size.zero }

(* ------------------------------------------------------------------ *)
(* Pure helpers — no mutation, O(log n) operations *)
(* ------------------------------------------------------------------ *)

let add_order_to_tree (o : order) (tree : order_tree) : order_tree =
  {
    tree with
    orders = Order_id.Map.add o.id o tree.orders;
    total_size = Size.add tree.total_size o.size;
  }

let remove_order_from_tree (oid : Order_id.t) (tree : order_tree) : order_tree =
  match Order_id.Map.find_opt oid tree.orders with
  | Some o ->
      {
        tree with
        orders = Order_id.Map.remove oid tree.orders;
        total_size = Size.sub tree.total_size o.size;
      }
  | None -> tree

let update_order_in_tree (oid : Order_id.t) (f : order -> order)
    (tree : order_tree) : order_tree =
  match Order_id.Map.find_opt oid tree.orders with
  | None -> tree
  | Some o ->
      let o' = f o in
      let size_diff = Size.sub o'.size o.size in
      {
        tree with
        orders = Order_id.Map.add oid o' tree.orders;
        total_size = Size.add tree.total_size size_diff;
      }

let upsert_level (m : order_tree Price.Map.t) (price : Price.t)
    (f : order_tree -> order_tree) : order_tree Price.Map.t =
  let tree =
    match Price.Map.find_opt price m with
    | Some t -> t
    | None -> empty_tree price
  in
  Price.Map.add price (f tree) m

(* ------------------------------------------------------------------ *)
(* Side-level helper for event application *)
(* ------------------------------------------------------------------ *)

let apply_to_side (s : book_state) (ev : event)
    (mutate_tree : order_tree -> order_tree) : book_state =
  let side = ev.side in
  let price = ev.price in
  let new_bids =
    if side = Bid then upsert_level s.bids price mutate_tree else s.bids
  in
  let new_asks =
    if side = Ask then upsert_level s.asks price mutate_tree else s.asks
  in
  { s with bids = new_bids; asks = new_asks }

(* ------------------------------------------------------------------ *)
(* Spread and mid price calculation *)
(* ------------------------------------------------------------------ *)

let compute_spread_mid (bids : price_level list) (asks : price_level list) :
    Price.t option * Price.t option =
  match (bids, asks) with
  | b :: _, a :: _ ->
      let s = Price.to_int a.price - Price.to_int b.price in
      let spread = if s > 0 then Some (Price.of_int s) else None in
      let mid =
        Some (Price.of_int ((Price.to_int b.price + Price.to_int a.price) / 2))
      in
      (spread, mid)
  | _ -> (None, None)

(* ------------------------------------------------------------------ *)

let collate_side (m : order_tree Price.Map.t) (ascending : bool) :
    price_level list =
  let result =
    Price.Map.fold
      (fun price tree acc ->
        if tree.total_size > Size.zero then
          {
            price;
            total_size = tree.total_size;
            order_count = Order_id.Map.cardinal tree.orders;
          }
          :: acc
        else acc)
      m []
  in
  if ascending then List.rev result else result

let compute_snapshot (s : book_state) : book_snapshot =
  let bids_all = collate_side s.bids false in
  let asks_all = collate_side s.asks true in
  let top_bids = List_utils.take 10 bids_all in
  let top_asks = List_utils.take 10 asks_all in
  let spread, mid_price = compute_spread_mid top_bids top_asks in
  let micro_price =
    let total_bid =
      List.fold_left
        (fun acc (l : price_level) -> Size.add acc l.total_size)
        Size.zero bids_all
    in
    let total_ask =
      List.fold_left
        (fun acc (l : price_level) -> Size.add acc l.total_size)
        Size.zero asks_all
    in
    let bid_int =
      match bids_all with b :: _ -> Price.to_int b.price | [] -> 0
    in
    let ask_int =
      match asks_all with a :: _ -> Price.to_int a.price | [] -> 0
    in
    let denom = Size.to_int total_bid + Size.to_int total_ask in
    if denom > 0 then
      let micro =
        float
          ((ask_int * Size.to_int total_bid) + (bid_int * Size.to_int total_ask))
        /. float denom
      in
      Some (Price.of_float micro)
    else mid_price
  in
  {
    timestamp = s.last_update;
    bids = top_bids;
    asks = top_asks;
    spread;
    mid_price;
    micro_price;
  }

let compute_stats_from (s : book_state) : book_stats =
  let total_bid =
    Price.Map.fold (fun _ t acc -> Size.add acc t.total_size) s.bids Size.zero
  in
  let total_ask =
    Price.Map.fold (fun _ t acc -> Size.add acc t.total_size) s.asks Size.zero
  in
  let bid_count = Price.Map.cardinal s.bids in
  let ask_count = Price.Map.cardinal s.asks in
  let top_bids = List_utils.take 1 (collate_side s.bids false) in
  let top_asks = List_utils.take 1 (collate_side s.asks true) in
  let spread, mid_price = compute_spread_mid top_bids top_asks in
  {
    total_bid_size = total_bid;
    total_ask_size = total_ask;
    bid_count;
    ask_count;
    spread;
    mid_price;
  }

let create () : t =
  let module I = (val Incr.make ()) in
  let state_var = I.Var.create (empty_state ()) in
  let snapshot_incr = I.map compute_snapshot (I.of_var state_var) in
  let stats_incr = I.map compute_stats_from (I.of_var state_var) in
  {
    get_state = (fun () -> I.Var.snapshot state_var);
    set_state = (fun state -> I.Var.set state_var state);
    stabilize = I.stabilize;
    get_snapshot = (fun () -> I.snapshot snapshot_incr);
    get_stats = (fun () -> I.snapshot stats_incr);
  }

(* ------------------------------------------------------------------ *)
(* Continuous double auction matching engine *)
(* ------------------------------------------------------------------ *)

let rec fill_orders_at_level (opp_map : order_tree Price.Map.t)
    (orders_map : order_db) (price : Price.t) (tree : order_tree)
    (aggressor_id : Order_id.t) (aggressor_side : side)
    (aggressor_price : Price.t) (remaining_size : Size.t)
    (ev_timestamp : Timestamp.t) (acc_fills : fill list) :
    order_tree Price.Map.t * order_db * Size.t * fill list =
  if Size.to_int remaining_size = 0 then
    (opp_map, orders_map, remaining_size, acc_fills)
  else
    (* Match resting orders by transaction time, then order ID. *)
    let order_list =
      Order_id.Map.bindings tree.orders
      |> List.sort (fun (oid_a, order_a) (oid_b, order_b) ->
          let time_cmp = Timestamp.compare order_a.tx_time order_b.tx_time in
          if time_cmp <> 0 then time_cmp
          else Int.compare order_a.arrival_sequence order_b.arrival_sequence)
    in
    let new_level_orders = ref tree.orders in
    let new_level_total = ref tree.total_size in
    let new_opp_map = ref opp_map in
    let new_orders_map = ref orders_map in
    let fills_acc = ref acc_fills in
    let remaining = ref remaining_size in
    List.iter
      (fun ((oid, o) : Order_id.t * order) ->
        if Size.to_int !remaining > 0 && Order_id.Map.mem oid !new_level_orders
        then begin
          let fill_sz = Size.min !remaining o.size in
          remaining := Size.sub !remaining fill_sz;
          new_level_total := Size.sub !new_level_total fill_sz;
          let fill_rec : fill =
            {
              trade_time = ev_timestamp;
              buy_order_id =
                (if aggressor_side = Bid then aggressor_id else oid);
              sell_order_id =
                (if aggressor_side = Bid then oid else aggressor_id);
              fill_price = o.price;
              fill_size = fill_sz;
              aggressor_order_id = aggressor_id;
            }
          in
          fills_acc := fill_rec :: !fills_acc;
          if Size.to_int (Size.sub o.size fill_sz) = 0 then begin
            new_level_orders := Order_id.Map.remove oid !new_level_orders;
            new_orders_map := Order_id.Map.remove oid !new_orders_map
          end
          else begin
            let updated = { o with size = Size.sub o.size fill_sz } in
            new_level_orders := Order_id.Map.add oid updated !new_level_orders;
            new_orders_map := Order_id.Map.add oid updated !new_orders_map
          end
        end)
      order_list;
    let updated_tree =
      { tree with orders = !new_level_orders; total_size = !new_level_total }
    in
    let updated_opp =
      if Order_id.Map.cardinal updated_tree.orders = 0 then
        Price.Map.remove price !new_opp_map
      else Price.Map.add price updated_tree !new_opp_map
    in
    (updated_opp, !new_orders_map, !remaining, !fills_acc)

(** [match_aggressor state aggressor_id side price size timestamp] matches an
    incoming order against the opposite side. Returns the new state, fills, and
    remaining size of the aggressor. *)
let match_aggressor (s : book_state) (aggressor_id : Order_id.t)
    (aggressor_side : side) (aggressor_price : Price.t)
    (aggressor_size : Size.t) (ev_timestamp : Timestamp.t) :
    book_state * fill list * Size.t =
  if Size.to_int aggressor_size = 0 then (s, [], aggressor_size)
  else
    let opp_map = match aggressor_side with Bid -> s.asks | Ask -> s.bids in
    (* Collect matching price levels in the right order:
       For Bid aggressor: asks with price <= bid price, ascending (best ask first)
       For Ask aggressor: bids with price >= ask price, descending (best bid first) *)
    let matching_levels =
      Price.Map.fold
        (fun price tree acc ->
          let qualifies =
            match aggressor_side with
            | Bid -> Price.compare price aggressor_price <= 0
            | Ask -> Price.compare price aggressor_price >= 0
          in
          if qualifies then (price, tree) :: acc else acc)
        opp_map []
    in
    let ordered_levels =
      List.sort
        (fun (price_a, _) (price_b, _) ->
          match aggressor_side with
          | Bid -> Price.compare price_a price_b
          | Ask -> Price.compare price_b price_a)
        matching_levels
    in
    let cur_opp = ref opp_map in
    let cur_orders = ref s.orders in
    let cur_remaining = ref aggressor_size in
    let all_fills = ref [] in
    List.iter
      (fun (price, tree) ->
        if Size.to_int !cur_remaining > 0 then begin
          let new_opp, new_orders, new_remaining, fills =
            fill_orders_at_level !cur_opp !cur_orders price tree aggressor_id
              aggressor_side aggressor_price !cur_remaining ev_timestamp
              !all_fills
          in
          cur_opp := new_opp;
          cur_orders := new_orders;
          cur_remaining := new_remaining;
          all_fills := fills
        end)
      ordered_levels;
    let new_state =
      match aggressor_side with
      | Bid -> { s with asks = !cur_opp; orders = !cur_orders }
      | Ask -> { s with bids = !cur_opp; orders = !cur_orders }
    in
    (new_state, List.rev !all_fills, !cur_remaining)

(* ------------------------------------------------------------------ *)
(* Event application — pure; matching scans eligible levels and orders. *)
(* ------------------------------------------------------------------ *)

let order_of_ev ~(arrival_sequence : int) (ev : event) : order =
  let valid_time =
    match ev.valid_time with Some v -> v | None -> ev.timestamp
  in
  let far_future t = Timestamp.add_seconds t (365. *. 86400. *. 100.) in
  {
    id = ev.order_id;
    side = ev.side;
    price = ev.price;
    size = ev.size;
    tx_time = ev.timestamp;
    arrival_sequence;
    valid_time;
    tx_interval = (ev.timestamp, far_future ev.timestamp);
    valid_interval = (valid_time, far_future valid_time);
  }

let apply_internal (book : t) ~(allow_matching : bool) (ev : event) :
    (book_snapshot * fill list) Serror.t =
  let s = book.get_state () in
  let seq = s.sequence + 1 in
  let new_state, fills =
    match ev.action with
    | Add ->
        if Order_id.Map.mem ev.order_id s.orders then (None, [])
        else
          let o = order_of_ev ~arrival_sequence:seq ev in
          (* Replay applies venue events exactly; simulation matches new orders. *)
          let s_matched, match_fills, remaining =
            if allow_matching then
              match_aggressor s o.id o.side o.price o.size ev.timestamp
            else (s, [], o.size)
          in
          let actually_added =
            if Size.to_int remaining > 0 then
              let remaining_o = { o with size = remaining } in
              let bids' =
                if o.side = Bid then
                  upsert_level s_matched.bids o.price
                    (add_order_to_tree remaining_o)
                else s_matched.bids
              in
              let asks' =
                if o.side = Ask then
                  upsert_level s_matched.asks o.price
                    (add_order_to_tree remaining_o)
                else s_matched.asks
              in
              Some
                {
                  bids = bids';
                  asks = asks';
                  orders = Order_id.Map.add o.id remaining_o s_matched.orders;
                  sequence = seq;
                  last_update = ev.timestamp;
                }
            else
              Some { s_matched with sequence = seq; last_update = ev.timestamp }
          in
          (actually_added, match_fills)
    | Amend -> (
        match Order_id.Map.find_opt ev.order_id s.orders with
        | Some old ->
            let valid_time =
              match ev.valid_time with Some v -> v | None -> ev.timestamp
            in
            let far_future t =
              Timestamp.add_seconds t (365. *. 86400. *. 100.)
            in
            let o =
              {
                old with
                price = ev.price;
                size = ev.size;
                valid_time;
                valid_interval = (valid_time, far_future valid_time);
                tx_time = ev.timestamp;
                tx_interval = (ev.timestamp, far_future ev.timestamp);
              }
            in
            let remove_ev = { ev with price = old.price; side = old.side } in
            let s' =
              apply_to_side s remove_ev (remove_order_from_tree ev.order_id)
            in
            (* If price changed, the order at its new price might cross *)
            let s_matched, match_fills, remaining =
              if allow_matching && Price.compare o.price old.price <> 0 then
                match_aggressor s' o.id o.side o.price o.size ev.timestamp
              else (s', [], o.size)
            in
            let actually_added =
              if Size.to_int remaining > 0 then
                let remaining_o = { o with size = remaining } in
                let bids' =
                  if o.side = Bid then
                    upsert_level s_matched.bids o.price
                      (add_order_to_tree remaining_o)
                  else s_matched.bids
                in
                let asks' =
                  if o.side = Ask then
                    upsert_level s_matched.asks o.price
                      (add_order_to_tree remaining_o)
                  else s_matched.asks
                in
                Some
                  {
                    bids = bids';
                    asks = asks';
                    orders =
                      Order_id.Map.add ev.order_id remaining_o s_matched.orders;
                    sequence = seq;
                    last_update = ev.timestamp;
                  }
              else
                Some
                  { s_matched with sequence = seq; last_update = ev.timestamp }
            in
            (actually_added, match_fills)
        | None -> (None, []))
    | Replace old_id -> (
        match Order_id.Map.find_opt old_id s.orders with
        | Some old ->
            if old_id <> ev.order_id && Order_id.Map.mem ev.order_id s.orders
            then (None, [])
            else
              let remove_ev =
                {
                  ev with
                  order_id = old_id;
                  side = old.side;
                  price = old.price;
                }
              in
              let removed =
                apply_to_side s remove_ev (remove_order_from_tree old_id)
              in
              let removed =
                {
                  removed with
                  orders = Order_id.Map.remove old_id removed.orders;
                }
              in
              let o =
                order_of_ev ~arrival_sequence:seq { ev with side = old.side }
              in
              let s_matched, match_fills, remaining =
                if allow_matching then
                  match_aggressor removed o.id o.side o.price o.size
                    ev.timestamp
                else (removed, [], o.size)
              in
              let new_state =
                if Size.to_int remaining > 0 then
                  let remaining_o = { o with size = remaining } in
                  let bids' =
                    if o.side = Bid then
                      upsert_level s_matched.bids o.price
                        (add_order_to_tree remaining_o)
                    else s_matched.bids
                  in
                  let asks' =
                    if o.side = Ask then
                      upsert_level s_matched.asks o.price
                        (add_order_to_tree remaining_o)
                    else s_matched.asks
                  in
                  Some
                    {
                      bids = bids';
                      asks = asks';
                      orders =
                        Order_id.Map.add o.id remaining_o s_matched.orders;
                      sequence = seq;
                      last_update = ev.timestamp;
                    }
                else
                  Some
                    {
                      s_matched with
                      sequence = seq;
                      last_update = ev.timestamp;
                    }
              in
              (new_state, match_fills)
        | None -> (None, []))
    | Control kind ->
        let new_state =
          if kind = "symbol_clear" then
            { (empty_state ()) with sequence = seq; last_update = ev.timestamp }
          else { s with sequence = seq; last_update = ev.timestamp }
        in
        (Some new_state, [])
    | Cancel -> (
        match Order_id.Map.find_opt ev.order_id s.orders with
        | Some old ->
            let new_orders = Order_id.Map.remove ev.order_id s.orders in
            let remove_ev = { ev with side = old.side; price = old.price } in
            let s' =
              apply_to_side s remove_ev (remove_order_from_tree ev.order_id)
            in
            ( Some
                {
                  s' with
                  orders = new_orders;
                  sequence = seq;
                  last_update = ev.timestamp;
                },
              [] )
        | None -> (None, []))
    | Execute -> (
        match Order_id.Map.find_opt ev.order_id s.orders with
        | Some old ->
            let exec_size = Size.min ev.size old.size in
            let remaining = Size.sub old.size exec_size in
            if remaining = Size.zero then
              let new_orders = Order_id.Map.remove ev.order_id s.orders in
              let remove_ev = { ev with side = old.side; price = old.price } in
              let s' =
                apply_to_side s remove_ev (remove_order_from_tree ev.order_id)
              in
              ( Some
                  {
                    s' with
                    orders = new_orders;
                    sequence = seq;
                    last_update = ev.timestamp;
                  },
                [] )
            else
              let o = { old with size = remaining; tx_time = ev.timestamp } in
              let new_orders = Order_id.Map.add ev.order_id o s.orders in
              let update_ev = { ev with side = old.side; price = old.price } in
              let s' =
                apply_to_side s update_ev
                  (update_order_in_tree ev.order_id (fun _ -> o))
              in
              ( Some
                  {
                    s' with
                    orders = new_orders;
                    sequence = seq;
                    last_update = ev.timestamp;
                  },
                [] )
        | None -> (None, []))
  in
  match new_state with
  | Some ns ->
      book.set_state ns;
      book.stabilize ();
      let snap = book.get_snapshot () in
      Ok (snap, fills)
  | None ->
      let reason =
        match ev.action with
        | Add when Order_id.Map.mem ev.order_id s.orders ->
            "already exists for add action"
        | Add -> "not found for add action"
        | Amend -> "not found for amend action"
        | Replace old_id -> "not found for replace action: " ^ old_id
        | Control _ -> "control action failed"
        | Cancel -> "not found for cancel action"
        | Execute -> "not found for execute action"
      in
      Serror.fail (Printf.sprintf "order %s %s" ev.order_id reason)

let apply (book : t) (ev : event) : (book_snapshot * fill list) Serror.t =
  apply_internal book ~allow_matching:true ev

let apply_replay (book : t) (ev : event) : (book_snapshot * fill list) Serror.t
    =
  apply_internal book ~allow_matching:false ev

let apply_exn (book : t) (ev : event) : book_snapshot =
  match apply book ev with Ok (snap, _) -> snap | Error msg -> failwith msg

let get_snapshot (book : t) : book_snapshot = book.get_snapshot ()
let get_stats (book : t) : book_stats = book.get_stats ()

let order_count (book : t) : int =
  let s = book.get_state () in
  Order_id.Map.cardinal s.orders

let reset (book : t) : unit =
  book.set_state (empty_state ());
  book.stabilize ()

let validate (book : t) : unit Serror.t =
  let s = book.get_state () in
  let level_ids = ref Order_id.Map.empty in
  let validate_side expected_side levels =
    let result = ref (Ok ()) in
    Price.Map.iter
      (fun price tree ->
        if Result.is_ok !result then
          begin if tree.price <> price then
            result := Serror.fail "price level key does not match its price"
          else
            let total = ref Size.zero in
            Order_id.Map.iter
              (fun order_id order ->
                if Order_id.Map.mem order_id !level_ids then
                  result := Serror.fail "order appears on both book sides"
                else if Size.to_int order.size <= 0 then
                  result := Serror.fail "book contains a non-positive order"
                else if order.side <> expected_side then
                  result := Serror.fail "order is stored on the wrong side"
                else if order.price <> price then
                  result := Serror.fail "order price does not match its level"
                else if not (Order_id.Map.mem order_id s.orders) then
                  result :=
                    Serror.fail "level order is missing from the order index"
                else begin
                  level_ids := Order_id.Map.add order_id order !level_ids;
                  total := Size.add !total order.size
                end)
              tree.orders;
            if !result = Ok () && !total <> tree.total_size then
              result :=
                Serror.fail "price level total does not match its orders"
          end)
      levels;
    !result
  in
  match validate_side Bid s.bids with
  | Error _ as error -> error
  | Ok () -> (
      match validate_side Ask s.asks with
      | Error _ as error -> error
      | Ok () ->
          let result = ref (Ok ()) in
          Order_id.Map.iter
            (fun order_id order ->
              if Result.is_ok !result then
                let levels = if order.side = Bid then s.bids else s.asks in
                match Price.Map.find_opt order.price levels with
                | None ->
                    result :=
                      Serror.fail "indexed order is missing its price level"
                | Some tree when not (Order_id.Map.mem order_id tree.orders) ->
                    result :=
                      Serror.fail "indexed order is missing from its level"
                | Some _ -> ())
            s.orders;
          if
            Result.is_ok !result
            && Order_id.Map.cardinal !level_ids
               <> Order_id.Map.cardinal s.orders
          then Serror.fail "order index and price levels disagree"
          else !result)
