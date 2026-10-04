(** Event-driven execution loop with decision and cancel latency.

    The loop consumes a merged canonical event stream and models a strategy
    that reacts to the book. Latency is a time offset on the replay clock:

    - A submit becomes live [decision_ns] after the event that decided it.
    - A cancel takes effect [cancel_ns] after the event that decided it, so the
      order stays exposed in between and can still be filled.

    Resting limit orders are filled by {!Exec_fills} under an explicit mode,
    taker intents walk visible depth at their effective time, and every reject
    is counted instead of aborting the run. A liquidated account closes at the
    book mid and accepts no new orders.

    The mark for equity and liquidation is the book mid, [((bid + ask) / 2)],
    rounded down to a tick. *)

type latency = { decision_ns : int64; cancel_ns : int64 }

type action = Submit of Exec_account.order | Cancel of string

type resting = {
  price_ticks : int64;
  queue_ahead_units : int64;
  level_units_before : int64;
  trades_units : int64;
  inferred_units : int64;
  placed_at : Timestamp.t;
}

type context = {
  index : int;
  event : Exec_event.t;
  book : L2_book.t;
  account : Exec_account.state;
  orders : Exec_account.order list;
}

type strategy = context -> action list

type fill_record = {
  at : Timestamp.t;
  price_ticks : int64;
  quantity_units : int64;
  liquidity : Exec_event.liquidity;
  fee : int64;
  realized : int64;
}

type report = {
  mode : Exec_fills.mode;
  latency : latency;
  events : int;
  chain_gaps : int;
  chain_superseded : int;
  min_bid_ticks : int64 option;
  max_bid_ticks : int64 option;
  min_ask_ticks : int64 option;
  max_ask_ticks : int64 option;
  decisions : int;
  submitted : int;
  rejected : int;
  cancelled : int;
  fills : int;
  filled_units : int64;
  taker_units : int64;
  maker_units : int64;
  liquidations : int;
  fills_log : fill_record list;
  book : L2_book.t;
  account : Exec_account.state;
  orders : Exec_account.order list;
}

let default_latency = { decision_ns = 0L; cancel_ns = 0L }

(** [merge_events left right] interleaves two event streams that are each
    ordered by receive time, keeping the combined stream ordered and stable for
    equal timestamps, where the left stream wins. *)
let merge_events left right =
  let rec loop acc left right =
    match (left, right) with
    | [], rest | rest, [] -> List.rev_append acc rest
    | l :: ls, r :: rs ->
        if Timestamp.compare l.Exec_event.receive_time r.Exec_event.receive_time <= 0
        then loop (l :: acc) ls right
        else loop (r :: acc) left rs
  in
  loop [] left right

let mid_ticks book =
  match (L2_book.best_bid book, L2_book.best_ask book) with
  | Some bid, Some ask -> Some (Int64.div (Int64.add bid ask) 2L)
  | Some bid, None -> Some bid
  | None, Some ask -> Some ask
  | None, None -> None

let level_units book side price_ticks =
  match
    List.find_opt
      (fun (price, _) -> Int64.equal price price_ticks)
      (L2_book.levels book side)
  with
  | Some (_, units) -> units
  | None -> 0L

let aggressive_units_for ~side event price_ticks =
  match event.Exec_event.payload with
  | Exec_event.Trade trade
    when Int64.equal trade.Exec_event.price_ticks price_ticks ->
      let aggressor_is_seller = not trade.Exec_event.buyer_is_maker in
      let matches =
        match side with
        | Exec_event.Buy -> aggressor_is_seller
        | Exec_event.Sell -> trade.Exec_event.buyer_is_maker
      in
      if matches then trade.Exec_event.quantity_units else 0L
  | _ -> 0L

let run ~mode ~latency ~config ~strategy ~initial_collateral ~events =
  let book = ref L2_book.empty in
  let account = ref (Exec_account.empty ~collateral:initial_collateral) in
  let resting = Hashtbl.create 8 in
  let pending = ref [] in
  let sequence = ref 0 in
  let events_handled = ref 0 in
  let decisions = ref 0 in
  let submitted = ref 0 in
  let rejected = ref 0 in
  let cancelled = ref 0 in
  let chain = Depth_chain.create () in
  let buffered = ref [] in
  let chain_gaps = ref 0 in
  let min_bid_ticks = ref None in
  let max_bid_ticks = ref None in
  let min_ask_ticks = ref None in
  let max_ask_ticks = ref None in
  let track_range () =
    (match L2_book.best_bid !book with
    | Some price ->
        min_bid_ticks :=
          Some
            (match !min_bid_ticks with
            | Some current -> Int64.min current price
            | None -> price);
        max_bid_ticks :=
          Some
            (match !max_bid_ticks with
            | Some current -> Int64.max current price
            | None -> price)
    | None -> ());
    match L2_book.best_ask !book with
    | Some price ->
        min_ask_ticks :=
          Some
            (match !min_ask_ticks with
            | Some current -> Int64.min current price
            | None -> price);
        max_ask_ticks :=
          Some
            (match !max_ask_ticks with
            | Some current -> Int64.max current price
            | None -> price)
    | None -> ()
  in
  let chain_superseded = ref 0 in
  let fills = ref 0 in
  let filled_units = ref 0L in
  let taker_units = ref 0L in
  let maker_units = ref 0L in
  let liquidations = ref 0 in
  let fills_log = ref [] in
  let order_list () =
    Hashtbl.fold (fun _ (order, _) acc -> order :: acc) resting []
  in
  let apply_fill ?(at = Timestamp.zero) order price_ticks quantity_units
      liquidity =
    let fee =
      match Exec_account.fee config liquidity ~price_ticks ~quantity_units with
      | Ok value -> value
      | Error _ -> 0L
    in
    let realized_before = (!account).Exec_account.realized_pnl in
    match
      Exec_account.apply_fill config !account order ~price_ticks ~quantity_units
        ~liquidity
    with
    | Error _ ->
        incr rejected;
        None
    | Ok (updated, updated_account) ->
        let realized =
          Int64.sub updated_account.Exec_account.realized_pnl realized_before
        in
        fills_log :=
          { at; price_ticks; quantity_units; liquidity; fee; realized }
          :: !fills_log;
        account := updated_account;
        incr fills;
        filled_units := Int64.add !filled_units quantity_units;
        (match liquidity with
        | Exec_event.Maker -> maker_units := Int64.add !maker_units quantity_units
        | Exec_event.Taker -> taker_units := Int64.add !taker_units quantity_units);
        (match Hashtbl.find_opt resting updated.Exec_account.id with
        | Some (_, metadata) ->
            Hashtbl.replace resting updated.Exec_account.id (updated, metadata)
        | None -> ());
        Some updated
  in
  let take_from_book order =
    let order =
      match Hashtbl.find_opt resting order.Exec_account.id with
      | Some (current, _) -> current
      | None -> order
    in
    match () with
    | () ->
        let result =
          Exec_fills.take mode ~book:!book ~side:order.Exec_account.side
            ~quantity_units:order.Exec_account.remaining_units
            ?limit_ticks:order.Exec_account.price_ticks ()
        in
        (match result with
        | Error _ -> incr rejected
        | Ok taken ->
            List.iter
              (fun (fill : Exec_fills.taker_fill) ->
                ignore
                  (apply_fill order fill.Exec_fills.price_ticks
                     fill.Exec_fills.quantity_units Exec_event.Taker))
              taken.Exec_fills.fills)
  in
  let submit order =
    match Exec_account.submit config !account order with
    | Error _ -> incr rejected
    | Ok (accepted, updated_account) ->
        account := updated_account;
        incr submitted;
        let price_ticks = match accepted.Exec_account.price_ticks with Some p -> p | None -> 0L in
        let metadata =
          {
            price_ticks;
            queue_ahead_units =
              (if price_ticks = 0L then 0L
               else
                 let side = accepted.Exec_account.side in
                 let book_side =
                   match side with
                   | Exec_event.Buy -> L2_book.Bid
                   | Exec_event.Sell -> L2_book.Ask
                 in
                 let units = level_units !book book_side price_ticks in
                 units);
            level_units_before =
              (if price_ticks = 0L then 0L
               else
                 let book_side =
                   match accepted.Exec_account.side with
                   | Exec_event.Buy -> L2_book.Bid
                   | Exec_event.Sell -> L2_book.Ask
                 in
                 level_units !book book_side price_ticks);
            trades_units = 0L;
            inferred_units = 0L;
            placed_at = Timestamp.zero;
          }
        in
        Hashtbl.replace resting accepted.Exec_account.id (accepted, metadata);
        let is_market = accepted.Exec_account.price_ticks = None in
        if is_market then begin
          (* A market order takes what is visible, then its remainder is
             cancelled like an IOC order at the venue. *)
          take_from_book accepted;
          match Hashtbl.find_opt resting accepted.Exec_account.id with
          | Some (current, _) when current.Exec_account.remaining_units > 0L -> (
              match Exec_account.cancel config !account current with
              | Ok (_, updated_account) ->
                  account := updated_account;
                  Hashtbl.remove resting accepted.Exec_account.id
              | Error _ -> incr rejected)
          | _ -> ()
        end
        else begin
          (* A limit that crosses the book takes liquidity at once. *)
          let crossing =
            match accepted.Exec_account.side with
            | Exec_event.Buy -> (
                match L2_book.best_ask !book with
                | Some ask -> Int64.compare price_ticks ask >= 0
                | None -> false)
            | Exec_event.Sell -> (
                match L2_book.best_bid !book with
                | Some bid -> Int64.compare price_ticks bid <= 0
                | None -> false)
          in
          if crossing then take_from_book accepted
        end
  in
  let cancel id =
    match Hashtbl.find_opt resting id with
    | None -> incr rejected
    | Some (order, _) -> (
        match Exec_account.cancel config !account order with
        | Error _ -> incr rejected
        | Ok (updated, updated_account) ->
            account := updated_account;
            incr cancelled;
            if updated.Exec_account.remaining_units > 0L then
              Hashtbl.remove resting id
            else Hashtbl.replace resting id (updated, snd (Hashtbl.find resting id)))
  in
  let schedule effective_time action =
    incr sequence;
    pending := (effective_time, !sequence, action) :: !pending
  in
  let apply_due now =
    let due, later =
      List.partition
        (fun (effective_time, _, _) ->
          Timestamp.compare effective_time now <= 0)
        !pending
    in
    pending := later;
    let ordered =
      List.sort
        (fun (time_a, seq_a, _) (time_b, seq_b, _) ->
          let by_time = Timestamp.compare time_a time_b in
          if by_time <> 0 then by_time else Int.compare seq_a seq_b)
        due
    in
    List.iter
      (function
        | _, _, Submit order -> submit order
        | _, _, Cancel id -> cancel id)
      ordered
  in
  let update_maker_fills event =
    Hashtbl.iter
      (fun _ ((order : Exec_account.order), (metadata : resting)) ->
        if
          order.Exec_account.remaining_units > 0L
          && metadata.price_ticks <> 0L
          && order.Exec_account.price_ticks <> None
        then begin
          let book_side =
            match order.Exec_account.side with
            | Exec_event.Buy -> L2_book.Bid
            | Exec_event.Sell -> L2_book.Ask
          in
          let level_after = level_units !book book_side metadata.price_ticks in
          let observation =
            {
              Exec_fills.level_units_before = metadata.level_units_before;
              queue_ahead_units = metadata.queue_ahead_units;
              trades_units = metadata.trades_units;
              level_units_after = level_after;
            }
          in
          let inferred =
            Exec_fills.infer_maker_fill mode
              ~order_units:order.Exec_account.quantity_units ~observation
          in
          let delta = Int64.sub inferred metadata.inferred_units in
          if delta > 0L then begin
            let delta =
              if delta > order.Exec_account.remaining_units then
                order.Exec_account.remaining_units
              else delta
            in
            ignore
              (apply_fill order metadata.price_ticks delta Exec_event.Maker);
            match Hashtbl.find_opt resting order.Exec_account.id with
            | Some (current, metadata) ->
                Hashtbl.replace resting order.Exec_account.id
                  (current, { metadata with inferred_units = inferred })
            | None -> ()
          end
        end)
      resting;
    ignore event
  in
  let accumulate_trades event =
    Hashtbl.iter
      (fun _ ((order : Exec_account.order), (metadata : resting)) ->
        if order.Exec_account.remaining_units > 0L && metadata.price_ticks <> 0L then begin
          let units =
            aggressive_units_for ~side:order.Exec_account.side event
              metadata.price_ticks
          in
          if units > 0L then
            match Hashtbl.find_opt resting order.Exec_account.id with
            | Some (current, metadata) ->
                Hashtbl.replace resting order.Exec_account.id
                  (current,
                   { metadata with
                     trades_units = Int64.add metadata.trades_units units })
            | None -> ()
        end)
      resting
  in
  let maybe_liquidate () =
    match mid_ticks !book with
    | None -> ()
    | Some mark -> (
        match Exec_account.should_liquidate config !account ~mark_ticks:mark with
        | Ok true -> (
            match Exec_account.liquidate config !account ~mark_ticks:mark with
            | Ok liquidated ->
                account := liquidated;
                Hashtbl.reset resting;
                incr liquidations
            | Error _ -> incr rejected)
        | Ok false -> ()
        | Error _ -> incr rejected)
  in
  List.iter
    (fun event ->
      incr events_handled;
      apply_due event.Exec_event.receive_time;
      (match event.Exec_event.payload with
      | Exec_event.Depth_snapshot snapshot ->
          book :=
            L2_book.apply_snapshot !book ~bids:snapshot.Exec_event.bids
              ~asks:snapshot.Exec_event.asks;
          (* The normalizer writes updates buffered during a snapshot fetch
             before the snapshot row, so they belong after it. Rebuild the
             fresh baseline and re-apply what the chain accepts. *)
          (match snapshot.Exec_event.last_update_id with
          | Some last_update_id ->
              Depth_chain.reset chain last_update_id;
              List.iter
                (fun (update : Exec_event.depth_update) ->
                  let previous =
                    match update.Exec_event.previous_update_id with
                    | Some value -> value
                    | None -> Int64.min_int
                  in
                  match
                    Depth_chain.apply chain
                      ~first_update_id:update.Exec_event.first_update_id
                      ~last_update_id:update.Exec_event.last_update_id
                      ~previous_update_id:previous
                  with
                  | Depth_chain.Accept ->
                      book :=
                        L2_book.apply_update !book
                          ~bids:update.Exec_event.bids
                          ~asks:update.Exec_event.asks
                  | Depth_chain.Superseded -> incr chain_superseded
                  | Depth_chain.Gap -> incr chain_gaps)
                (List.rev !buffered);
              buffered := []
          | None -> ())
      | Exec_event.Depth_update update ->
          book :=
            L2_book.apply_update !book ~bids:update.Exec_event.bids
              ~asks:update.Exec_event.asks;
          buffered := update :: !buffered
      | Exec_event.Trade _ -> accumulate_trades event
      | _ -> ());
      update_maker_fills event;
      maybe_liquidate ();
      track_range ();
      let context =
        {
          index = !events_handled - 1;
          event;
          book = !book;
          account = !account;
          orders = order_list ();
        }
      in
      let actions = strategy context in
      if actions <> [] then incr decisions;
      List.iter
        (function
          | Submit order ->
              schedule
                (Timestamp.add_ns event.Exec_event.receive_time latency.decision_ns)
                (Submit order)
          | Cancel id ->
              schedule
                (Timestamp.add_ns event.Exec_event.receive_time latency.cancel_ns)
                (Cancel id))
        actions)
    events;
  (* Resume any action left pending after the final event, so a slow decision
     still lands. *)
  (match !pending with
  | [] -> ()
  | _ ->
      let ordered =
        List.sort
          (fun (time_a, seq_a, _) (time_b, seq_b, _) ->
            let by_time = Timestamp.compare time_a time_b in
            if by_time <> 0 then by_time else Int.compare seq_a seq_b)
          !pending
      in
      List.iter
        (function
          | _, _, Submit order -> submit order
          | _, _, Cancel id -> cancel id)
        ordered);
  (* Apply whatever the chain still holds once the stream ends. *)
  (List.iter
     (fun (update : Exec_event.depth_update) ->
       let previous =
         match update.Exec_event.previous_update_id with
         | Some value -> value
         | None -> Int64.min_int
       in
       match
         Depth_chain.apply chain ~first_update_id:update.Exec_event.first_update_id
           ~last_update_id:update.Exec_event.last_update_id
           ~previous_update_id:previous
       with
       | Depth_chain.Accept ->
           book :=
             L2_book.apply_update !book ~bids:update.Exec_event.bids
               ~asks:update.Exec_event.asks
       | Depth_chain.Superseded -> incr chain_superseded
       | Depth_chain.Gap -> incr chain_gaps)
     (List.rev !buffered);
   buffered := []);
  {
    mode;
    latency;
    events = !events_handled;
    chain_gaps = !chain_gaps;
    chain_superseded = !chain_superseded;
    min_bid_ticks = !min_bid_ticks;
    max_bid_ticks = !max_bid_ticks;
    min_ask_ticks = !min_ask_ticks;
    max_ask_ticks = !max_ask_ticks;
    decisions = !decisions;
    submitted = !submitted;
    rejected = !rejected;
    cancelled = !cancelled;
    fills = !fills;
    filled_units = !filled_units;
    taker_units = !taker_units;
    maker_units = !maker_units;
    liquidations = !liquidations;
    fills_log = List.rev !fills_log;
    book = !book;
    account = !account;
    orders = order_list ();
  }
