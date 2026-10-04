(** Bitemporal model for the order book.

    Every fact (order state) carries two time axes:
    - Valid time: when the fact is economically effective.
    - Transaction time: when the fact was recorded in the system.

    This enables queries like:
    - "What did the book look like at exchange time T (valid), as we knew it at
      our cutoff time C (transaction time)?"
    - "What amendments were made to order X between valid times V1 and V2?"
    - "What did we know at time T that we didn't know earlier?" *)

open Market_types

type bitemporal_interval = {
  valid_from : Timestamp.t;
  valid_until : Timestamp.t;
  tx_from : Timestamp.t;
  tx_until : Timestamp.t;
}
(** A bitemporal time interval. Valid when valid_from <= t < valid_until.
    Transaction when tx_from <= t < tx_until. *)

type 'a bitemporal_fact = { fact : 'a; interval : bitemporal_interval }
(** A fact recorded with its bitemporal interval. *)

type 'a t = 'a bitemporal_fact list
(** A bitemporal set: each value appears at most once per (valid, transaction)
    time region. *)

(** [singleton fact valid tx] creates a bitemporal fact with open-ended
    intervals. *)
let singleton (fact : 'a) (valid : Timestamp.t) (tx : Timestamp.t) : 'a t =
  (* Use a sentinel far future for open intervals *)
  let far_future = Timestamp.add_seconds valid (365. *. 86400. *. 100.) in
  let far_future_tx = Timestamp.add_seconds tx (365. *. 86400. *. 100.) in
  [
    {
      fact;
      interval =
        {
          valid_from = valid;
          valid_until = far_future;
          tx_from = tx;
          tx_until = far_future_tx;
        };
    };
  ]

(** [add ts fact valid tx] inserts a new fact with valid/tx times. *)
let add (ts : 'a t) (fact : 'a) (valid : Timestamp.t) (tx : Timestamp.t) : 'a t
    =
  singleton fact valid tx @ ts

(** [add_with_interval ts fact interval] inserts with a full interval. *)
let add_with_interval (ts : 'a t) (fact : 'a) (interval : bitemporal_interval) :
    'a t =
  { fact; interval } :: ts

(** [close_valid ts valid_time] closes the valid-time interval for the most
    recent fact produced at [valid_time]. *)
let close_valid (ts : 'a t) (valid_time : Timestamp.t) : 'a t =
  match ts with
  | [] -> []
  | h :: t ->
      let closed_interval = { h.interval with valid_until = valid_time } in
      { h with interval = closed_interval } :: t

(** [close_tx ts tx_time] closes the transaction-time interval. *)
let close_tx (ts : 'a t) (tx_time : Timestamp.t) : 'a t =
  match ts with
  | [] -> []
  | h :: t ->
      let closed_interval = { h.interval with tx_until = tx_time } in
      { h with interval = closed_interval } :: t

(** Sequenced query: "as of" a valid time AND a transaction time. Returns the
    state that was current at [valid_at] as known at transaction time [tx_at].
*)
let as_of (ts : 'a t) (valid_at : Timestamp.t) (tx_at : Timestamp.t) : 'a list =
  List.filter_map
    (fun bf ->
      let iv = bf.interval in
      let valid_ok =
        Timestamp.compare iv.valid_from valid_at <= 0
        && Timestamp.compare valid_at iv.valid_until < 0
      in
      let tx_ok =
        Timestamp.compare iv.tx_from tx_at <= 0
        && Timestamp.compare tx_at iv.tx_until < 0
      in
      if valid_ok && tx_ok then Some bf.fact else None)
    ts

(** Non-sequenced valid-time range query: "What was valid at any point between
    [valid_from] and [valid_until]?" *)
let between_valid (ts : 'a t) (valid_from : Timestamp.t)
    (valid_until : Timestamp.t) : 'a list =
  List.filter_map
    (fun bf ->
      let iv = bf.interval in
      let overlaps =
        Timestamp.compare iv.valid_from valid_until < 0
        && Timestamp.compare valid_from iv.valid_until < 0
      in
      if overlaps then Some bf.fact else None)
    ts

(** Non-sequenced transaction-time range query. *)
let between_tx (ts : 'a t) (tx_from : Timestamp.t) (tx_until : Timestamp.t) :
    'a list =
  List.filter_map
    (fun bf ->
      let iv = bf.interval in
      let overlaps =
        Timestamp.compare iv.tx_from tx_until < 0
        && Timestamp.compare tx_from iv.tx_until < 0
      in
      if overlaps then Some bf.fact else None)
    ts

(** Full non-sequenced query: both valid and tx ranges. *)
let between (ts : 'a t) (valid_from, valid_until) (tx_from, tx_until) : 'a list
    =
  List.filter_map
    (fun bf ->
      let iv = bf.interval in
      let v_overlap =
        Timestamp.compare iv.valid_from valid_until < 0
        && Timestamp.compare valid_from iv.valid_until < 0
      in
      let t_overlap =
        Timestamp.compare iv.tx_from tx_until < 0
        && Timestamp.compare tx_from iv.tx_until < 0
      in
      if v_overlap && t_overlap then Some bf.fact else None)
    ts

(** Sequenced snapshot: all facts that were current (valid-time) at [valid_at]
    and recorded (tx-time) at [tx_at]. Returns deduplicated by identity (last
    writer wins per id). *)
let sequenced_snapshot (ts : 'a t) (valid_at : Timestamp.t)
    (tx_at : Timestamp.t) : 'a list =
  as_of ts valid_at tx_at

(** Evolution of a single entity over valid time, as recorded up to [tx_at]. *)
let history (ts : 'a t) (tx_at : Timestamp.t) : 'a list =
  List.filter_map
    (fun bf ->
      let iv = bf.interval in
      if
        Timestamp.compare iv.tx_from tx_at <= 0
        && Timestamp.compare tx_at iv.tx_until < 0
      then Some bf.fact
      else None)
    ts

(** Current state: the latest version of each fact as recorded at the current
    transaction time. *)
let current (ts : 'a t) : 'a list =
  let now = Timestamp.now () in
  as_of ts now now

(** [of_list facts] converts facts from a list of events into bitemporal facts
    with the event timestamp as both valid and tx. *)
let of_events (events : event list) : event bitemporal_fact list =
  let far_future t = Timestamp.add_seconds t (365. *. 86400. *. 100.) in
  let make_fact (ev : event) (next : event option) : event bitemporal_fact =
    let valid_from =
      match ev.valid_time with Some vt -> vt | None -> ev.timestamp
    in
    let valid_until, tx_until =
      match next with
      | Some next ->
          ( (match next.valid_time with Some vt -> vt | None -> next.timestamp),
            next.timestamp )
      | None -> (far_future valid_from, far_future ev.timestamp)
    in
    {
      fact = ev;
      interval = { valid_from; valid_until; tx_from = ev.timestamp; tx_until };
    }
  in
  let rec loop next_by_order acc = function
    | [] -> acc
    | ev :: rest ->
        let next = Order_id.Map.find_opt ev.order_id next_by_order in
        let fact = make_fact ev next in
        loop (Order_id.Map.add ev.order_id ev next_by_order) (fact :: acc) rest
  in
  loop Order_id.Map.empty [] (List.rev events)

(** [filter_sequenced facts valid_at tx_at] returns facts valid at [valid_at]
    and known by [tx_at]. *)
let filter_sequenced (facts : event bitemporal_fact list)
    (valid_at : Timestamp.t) (tx_at : Timestamp.t) : event list =
  List.filter_map
    (fun bf ->
      let iv = bf.interval in
      let valid_ok =
        Timestamp.compare iv.valid_from valid_at <= 0
        && Timestamp.compare valid_at iv.valid_until < 0
      in
      let tx_ok =
        Timestamp.compare iv.tx_from tx_at <= 0
        && Timestamp.compare tx_at iv.tx_until < 0
      in
      if valid_ok && tx_ok then Some bf.fact else None)
    facts

(** [index_by_order_id facts] builds an [Order_id.Map] grouping facts by
    order_id. Useful for O(log n) per-order queries. *)
let index_by_order_id (facts : event bitemporal_fact list) :
    event bitemporal_fact list Order_id.Map.t =
  List.fold_left
    (fun acc bf ->
      let oid = bf.fact.order_id in
      let existing =
        match Order_id.Map.find_opt oid acc with Some l -> l | None -> []
      in
      Order_id.Map.add oid (bf :: existing) acc)
    Order_id.Map.empty facts

(** [history_of_order facts order_id] returns all facts for the given order,
    using the index for O(log n) lookup. Returns [] if the order is unknown. *)
let history_of_order (facts : event bitemporal_fact list Order_id.Map.t)
    (order_id : Order_id.t) : event list =
  match Order_id.Map.find_opt order_id facts with
  | Some bfs ->
      List.rev_map (fun bf -> bf.fact) bfs (* reverse to get chronological *)
  | None -> []
