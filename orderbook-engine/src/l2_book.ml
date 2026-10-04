(** Aggregated L2 book over integer price ticks and quantity units.

    This is the aggregated replay mode. Binance depth streams publish the new
    absolute size of a price level, and size zero removes the level, so the
    book stays a price-level aggregate with no order identity. It never claims
    order-level FIFO accuracy.

    Replay decisions follow {!Depth_chain}, which mirrors
    collector/normalize_capture.py. Updates that arrive before a snapshot are
    held pending and replayed against it, and a fresh snapshot restores trust
    after a gap. *)

type level = Exec_event.level
(** The contract owns the level shape: price ticks and quantity units. *)

type side = Bid | Ask

module Price_map = Map.Make (Int64)

type t = { bids : int64 Price_map.t; asks : int64 Price_map.t }

type replay_result = {
  book : t;
  snapshots : int;
  applied : int;
  superseded : int;
  pending_updates : int;
  gaps : int;
  unchecked_after_gap : int;
  ignored_events : int;
  gapped : bool;
}

let empty = { bids = Price_map.empty; asks = Price_map.empty }
let side_map t = function Bid -> t.bids | Ask -> t.asks

let with_side t side map =
  match side with Bid -> { t with bids = map } | Ask -> { t with asks = map }

let set_level t side (level : level) =
  if level.Exec_event.price_ticks <= 0L then
    invalid_arg "price ticks must be positive"
  else
    let levels = side_map t side in
    let levels =
      if level.Exec_event.quantity_units = 0L then
        Price_map.remove level.Exec_event.price_ticks levels
      else
        Price_map.add level.Exec_event.price_ticks level.Exec_event.quantity_units
          levels
    in
    with_side t side levels

let apply_levels t side levels =
  List.fold_left (fun book level -> set_level book side level) t levels

(** A snapshot defines the whole book, so both sides are replaced. Keeping the
    old ask side here once let stale asks accumulate across windows and crossed
    the book. *)
let apply_snapshot _t ~bids ~asks =
  let cleared = { bids = Price_map.empty; asks = Price_map.empty } in
  apply_levels (apply_levels cleared Bid bids) Ask asks

let apply_update t ~bids ~asks =
  apply_levels (apply_levels t Bid bids) Ask asks

(** [levels t side] lists price and quantity pairs in consumption order: asks
    ascending, bids descending. *)
let levels t side =
  match side with
  | Ask -> Price_map.bindings t.asks
  | Bid -> List.rev (Price_map.bindings t.bids)

let best_bid t =
  if Price_map.is_empty t.bids then None
  else Some (fst (Price_map.max_binding t.bids))

let best_ask t =
  if Price_map.is_empty t.asks then None
  else Some (fst (Price_map.min_binding t.asks))

let level_count t side = Price_map.cardinal (side_map t side)

let total_quantity t side =
  Price_map.fold
    (fun _ quantity total ->
      match Exec_units.checked_add total quantity with
      | Ok total -> total
      | Error _ -> invalid_arg "book side total quantity overflow")
    (side_map t side) 0L

let spread t =
  match (best_bid t, best_ask t) with
  | Some bid, Some ask -> Some (Int64.sub ask bid)
  | _ -> None

let crossed t =
  match (best_bid t, best_ask t) with
  | Some bid, Some ask -> Int64.compare bid ask >= 0
  | _ -> false

let render_side t side =
  let levels = side_map t side in
  let entries =
    match side with
    | Bid -> List.rev (Price_map.bindings levels)
    | Ask -> Price_map.bindings levels
  in
  String.concat ","
    (List.map
       (fun (price, quantity) ->
         Printf.sprintf "%Ld:%Ld" price quantity)
       entries)

let checksum t =
  Digest.to_hex
    (Digest.string
       (Printf.sprintf "bids[%s]asks[%s]" (render_side t Bid)
          (render_side t Ask)))

let replay (events : Exec_event.t list) =
  let chain = Depth_chain.create () in
  let book = ref empty in
  let pending = ref [] in
  let gapped = ref false in
  let snapshots = ref 0 in
  let applied = ref 0 in
  let superseded = ref 0 in
  let pending_updates = ref 0 in
  let gaps = ref 0 in
  let unchecked_after_gap = ref 0 in
  let ignored_events = ref 0 in
  let decide (update : Exec_event.depth_update) =
    let previous =
      match update.Exec_event.previous_update_id with
      | Some value -> value
      | None -> Int64.min_int
    in
    match
      Depth_chain.apply chain ~first_update_id:update.Exec_event.first_update_id
        ~last_update_id:update.Exec_event.last_update_id ~previous_update_id:previous
    with
    | Depth_chain.Accept ->
        book := apply_update !book ~bids:update.Exec_event.bids ~asks:update.Exec_event.asks;
        incr applied
    | Depth_chain.Superseded -> incr superseded
    | Depth_chain.Gap ->
        incr gaps;
        gapped := true
  in
  List.iter
    (fun event ->
      match event.Exec_event.payload with
      | Exec_event.Depth_snapshot snapshot ->
          incr snapshots;
          book :=
            apply_snapshot !book ~bids:snapshot.Exec_event.bids
              ~asks:snapshot.Exec_event.asks;
          (match snapshot.Exec_event.last_update_id with
          | Some last_update_id ->
              Depth_chain.reset chain last_update_id;
              gapped := false;
              List.iter decide (List.rev !pending);
              pending := []
          | None -> ())
      | Exec_event.Depth_update update ->
          if !gapped then incr unchecked_after_gap
          else if Depth_chain.current chain = None then begin
            incr pending_updates;
            pending := update :: !pending
          end
          else decide update
      | _ -> incr ignored_events)
    events;
  {
    book = !book;
    snapshots = !snapshots;
    applied = !applied;
    superseded = !superseded;
    pending_updates = !pending_updates;
    gaps = !gaps;
    unchecked_after_gap = !unchecked_after_gap;
    ignored_events = !ignored_events;
    gapped = !gapped;
  }
