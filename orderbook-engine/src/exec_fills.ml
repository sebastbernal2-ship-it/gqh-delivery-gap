(** Fill inference for the aggregated L2 replay mode.

    Taker fills always consume visible depth only: the walk starts at the
    touch, stops at the limit price, and the notional stays exact because the
    price-quantity numerator is summed before a single rounding step.

    Maker fills cannot be known from aggregated data, so they are inferred as a
    bound under an explicit mode. Every result records its mode, so a report
    can always state which uncertainty class produced a fill.

    - Conservative: only aggressive trade volume at the price can fill the
      order, and only after the queue visible ahead of it is exhausted.
      Cancellations ahead are ignored because they cannot be attributed.
    - Heuristic: cancellations ahead also advance the queue, estimated as the
      level reduction that trades do not already explain.
    - Optimistic: the order is assumed to sit at the front of the queue, so all
      depletion can fill it.

    The bounds are ordered: conservative <= heuristic <= optimistic. *)

type mode = Conservative | Heuristic | Optimistic

type taker_fill = { price_ticks : int64; quantity_units : int64 }

type taker_result = {
  mode : mode;
  side : Exec_event.side;
  requested_units : int64;
  filled_units : int64;
  remaining_units : int64;
  fills : taker_fill list;
  notional : int64;
}

type maker_observation = {
  level_units_before : int64;
  queue_ahead_units : int64;
  trades_units : int64;
  level_units_after : int64;
}

let ( let* ) result f = Result.bind result f

let notional_divisor = 100L

let mode_name = function
  | Conservative -> "conservative"
  | Heuristic -> "heuristic"
  | Optimistic -> "optimistic"

let consume ~side ~limit_ticks price_ticks =
  match limit_ticks with
  | None -> true
  | Some limit -> (
      match side with
      | Exec_event.Buy -> Int64.compare price_ticks limit <= 0
      | Exec_event.Sell -> Int64.compare price_ticks limit >= 0)

let take mode ~book ~side ~quantity_units ?limit_ticks () =
  if quantity_units < 0L then invalid_arg "quantity must be nonnegative"
  else
    let levels =
      match side with
      | Exec_event.Buy -> L2_book.levels book L2_book.Ask
      | Exec_event.Sell -> L2_book.levels book L2_book.Bid
    in
    let remaining = ref quantity_units in
    let numerator = ref 0L in
    let fills = ref [] in
    let rec walk = function
      | [] -> Ok ()
      | (price_ticks, size) :: rest ->
          if !remaining <= 0L then Ok ()
          else if size <= 0L || not (consume ~side ~limit_ticks price_ticks) then
            walk rest
          else
            let quantity_units = if size < !remaining then size else !remaining in
            let* product = Exec_units.checked_mul price_ticks quantity_units in
            let* total = Exec_units.checked_add !numerator product in
            numerator := total;
            remaining := Int64.sub !remaining quantity_units;
            fills := { price_ticks; quantity_units } :: !fills;
            walk rest
    in
    let* () = walk levels in
    let* notional = Exec_units.div_round !numerator notional_divisor in
    Ok
      {
        mode;
        side;
        requested_units = quantity_units;
        filled_units = Int64.sub quantity_units !remaining;
        remaining_units = !remaining;
        fills = List.rev !fills;
        notional;
      }

let require_nonnegative name value =
  if value < 0L then invalid_arg (name ^ " must be nonnegative") else value

let depletion mode ~(observation : maker_observation) =
  let trades = require_nonnegative "trades" observation.trades_units in
  match mode with
  | Conservative -> trades
  | Heuristic | Optimistic ->
      let drop =
        require_nonnegative "level_before" observation.level_units_before
        |> fun before ->
        require_nonnegative "level_after" observation.level_units_after
        |> fun after ->
        let difference = Int64.sub before after in
        if difference < 0L then 0L else difference
      in
      let cancellations = Int64.sub drop trades in
      Int64.add trades (if cancellations < 0L then 0L else cancellations)

let infer_maker_fill mode ~order_units ~(observation : maker_observation) =
  let order_units = require_nonnegative "order_units" order_units in
  let queue_ahead = require_nonnegative "queue_ahead" observation.queue_ahead_units in
  let depletion = depletion mode ~observation in
  let fillable =
    match mode with
    | Conservative | Heuristic -> Int64.sub depletion queue_ahead
    | Optimistic -> depletion
  in
  if fillable <= 0L then 0L else if order_units < fillable then order_units else fillable
