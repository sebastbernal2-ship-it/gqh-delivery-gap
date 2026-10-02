(** Visible-liquidity execution for derived L2 snapshots. *)

type side = Buy | Sell
type fill = { price : float; size : float }

type result = {
  requested : float;
  filled : float;
  remaining : float;
  fills : fill list;
  vwap : float option;
}

let execute (snapshot : Hf_l2.snapshot) side ?limit_price (requested : float) =
  if requested <= 0.0 then
    { requested; filled = 0.0; remaining = requested; fills = []; vwap = None }
  else
    let levels =
      match side with Buy -> snapshot.asks | Sell -> snapshot.bids
    in
    let consumes price =
      match limit_price with
      | None -> true
      | Some limit -> if side = Buy then price <= limit else price >= limit
    in
    let remaining = ref requested in
    let previous_cumulative = ref 0.0 in
    let fills = ref [] in
    List.iter
      (fun (level : Hf_l2.level) ->
        let available =
          max 0.0 (level.cumulative_size -. !previous_cumulative)
        in
        previous_cumulative := max !previous_cumulative level.cumulative_size;
        if !remaining > 0.0 && available > 0.0 && consumes level.price then begin
          let size = min !remaining available in
          fills := { price = level.price; size } :: !fills;
          remaining := !remaining -. size
        end)
      levels;
    let fills = List.rev !fills in
    let filled = requested -. !remaining in
    let notional =
      List.fold_left
        (fun total fill -> total +. (fill.price *. fill.size))
        0.0 fills
    in
    {
      requested;
      filled;
      remaining = !remaining;
      fills;
      vwap = (if filled > 0.0 then Some (notional /. filled) else None);
    }
