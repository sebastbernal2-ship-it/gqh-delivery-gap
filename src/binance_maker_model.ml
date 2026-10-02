(** Bounded maker-fill inference for aggregated Binance data. *)

type side = Buy | Sell

type estimate = {
  initial_queue_ahead : float;
  pessimistic_filled : float;
  optimistic_filled : float;
  pessimistic_remaining : float;
  optimistic_remaining : float;
}

let level_size side price (state : Binance_l2.state) =
  let levels = match side with Buy -> state.Binance_l2.bids | Sell -> state.asks in
  match
    List.find_opt
      (fun (level : Binance_l2.level) -> float_of_string level.price = price)
      levels
  with
  | Some level -> float_of_string level.size
  | None -> 0.0

let aggressive_trade side price (trade : Binance_trades.trade) =
  let aggressive_buy = not trade.buyer_is_maker in
  match side with
  | Buy -> (not aggressive_buy) && trade.price <= price
  | Sell -> aggressive_buy && trade.price >= price

let estimate ~side ~price ~size ~placed_at ~states ~trades =
  if price <= 0.0 || size <= 0.0 then
    {
      initial_queue_ahead = 0.0;
      pessimistic_filled = 0.0;
      optimistic_filled = 0.0;
      pessimistic_remaining = max 0.0 size;
      optimistic_remaining = max 0.0 size;
    }
  else
    let states =
      List.filter
        (fun (state : Binance_l2.state) ->
          Timestamp.compare state.received_time placed_at >= 0)
        states
    in
    match states with
    | [] ->
        {
          initial_queue_ahead = 0.0;
          pessimistic_filled = 0.0;
          optimistic_filled = 0.0;
          pessimistic_remaining = size;
          optimistic_remaining = size;
        }
    | first_state :: _ ->
        let initial_queue_ahead = max 0.0 (level_size side price first_state) in
        let pessimistic_queue = ref initial_queue_ahead in
        let optimistic_queue = ref initial_queue_ahead in
        let pessimistic_filled = ref 0.0 in
        let optimistic_filled = ref 0.0 in
        let previous_state = ref first_state in
        let previous_time = ref placed_at in
        let consume queue filled volume =
          let volume = max 0.0 volume in
          let ahead = min !queue volume in
          queue := !queue -. ahead;
          let available = volume -. ahead in
          let fill = min (size -. !filled) available in
          filled := !filled +. fill
        in
        List.iter
          (fun (state : Binance_l2.state) ->
            if !pessimistic_filled < size then begin
              let traded_volume =
                List.fold_left
                  (fun total (trade : Binance_trades.trade) ->
                    if
                      Timestamp.compare trade.received_time !previous_time > 0
                      && Timestamp.compare trade.received_time state.received_time <= 0
                      && aggressive_trade side price trade
                    then total +. trade.quantity
                    else total)
                  0.0 trades
              in
              let previous_size = level_size side price !previous_state in
              let current_size = level_size side price state in
              let book_reduction = max 0.0 (previous_size -. current_size) in
              consume pessimistic_queue pessimistic_filled traded_volume;
              consume optimistic_queue optimistic_filled
                (max traded_volume book_reduction);
              previous_state := state;
              previous_time := state.received_time
            end)
          states;
        {
          initial_queue_ahead;
          pessimistic_filled = !pessimistic_filled;
          optimistic_filled = !optimistic_filled;
          pessimistic_remaining = max 0.0 (size -. !pessimistic_filled);
          optimistic_remaining = max 0.0 (size -. !optimistic_filled);
        }
