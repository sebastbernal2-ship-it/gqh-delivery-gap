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
  | Some bid, Some ask -> (
      match Exec_units.checked_add bid ask with
      | Ok total -> Some (Int64.div total 2L)
      | Error _ -> None)
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
  let valid_sha256 text =
    String.length text = 64
    && String.for_all
         (function '0' .. '9' | 'a' .. 'f' | 'A' .. 'F' -> true | _ -> false)
         text
  in
  let validate_events events =
    let previous = ref None in
    let identity = ref None in
    List.iter
      (fun event ->
        if event.Exec_event.venue = "" || event.Exec_event.symbol = ""
           || event.Exec_event.source_id = "" || event.Exec_event.source_path = ""
           || not (valid_sha256 event.Exec_event.source_sha256)
        then invalid_arg "event provenance is incomplete or source_sha256 is not SHA-256";
        (match event.Exec_event.quality, event.Exec_event.payload with
        | Exec_event.Suspect _,
          (Exec_event.Depth_snapshot _ | Exec_event.Depth_update _ | Exec_event.Trade _
          | Exec_event.Mark _ | Exec_event.Funding _ | Exec_event.Liquidation _) ->
            invalid_arg "suspect market event cannot enter execution replay"
        | _ -> ());
        (match !identity with
        | None -> identity := Some (event.Exec_event.venue, event.Exec_event.symbol)
        | Some (venue, symbol)
          when venue <> event.Exec_event.venue || symbol <> event.Exec_event.symbol ->
            invalid_arg "one execution replay must contain exactly one venue and symbol"
        | Some _ -> ());
        (match !previous with
        | Some prior when Timestamp.compare event.Exec_event.receive_time prior < 0 ->
            invalid_arg "execution events must be ordered by receive_time"
        | _ -> ());
        previous := Some event.Exec_event.receive_time)
      events
  in
  validate_events events;
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
  let book_trusted = ref false in
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
  let apply_fill ~at order price_ticks quantity_units
      liquidity =
    let order =
      match Hashtbl.find_opt resting order.Exec_account.id with
      | Some (current, _) -> current
      | None -> order
    in
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
          match Exec_units.checked_sub updated_account.Exec_account.realized_pnl realized_before with
          | Ok value -> value
          | Error _ -> invalid_arg "fill realized P&L delta overflow"
        in
        fills_log :=
          { at; price_ticks; quantity_units; liquidity; fee; realized }
          :: !fills_log;
        account := updated_account;
        incr fills;
        (match Exec_units.checked_add !filled_units quantity_units with
        | Ok value -> filled_units := value
        | Error _ -> invalid_arg "report filled_units overflow");
        (match liquidity with
        | Exec_event.Maker ->
            (match Exec_units.checked_add !maker_units quantity_units with
            | Ok value -> maker_units := value
            | Error _ -> invalid_arg "report maker_units overflow")
        | Exec_event.Taker ->
            (match Exec_units.checked_add !taker_units quantity_units with
            | Ok value -> taker_units := value
            | Error _ -> invalid_arg "report taker_units overflow"));
        (match Hashtbl.find_opt resting updated.Exec_account.id with
        | Some (_, metadata) ->
            Hashtbl.replace resting updated.Exec_account.id (updated, metadata)
        | None -> ());
        Some updated
  in
  let consume_visible_fill side price quantity =
    let book_side = match side with Exec_event.Buy -> L2_book.Ask | Sell -> L2_book.Bid in
    let old = level_units !book book_side price in
    let remaining = Int64.sub old quantity in
    if remaining < 0L then invalid_arg "visible book liquidity was consumed twice";
    book :=
      L2_book.set_level !book book_side
        { Exec_event.price_ticks = price; quantity_units = remaining }
  in
  let take_from_book ~at order =
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
        match result with
        | Error _ -> incr rejected
        | Ok taken ->
            List.iter
              (fun (fill : Exec_fills.taker_fill) ->
                let current =
                  match Hashtbl.find_opt resting order.Exec_account.id with
                  | Some (current, _) -> current
                  | None -> order
                in
                match
                  apply_fill ~at current fill.Exec_fills.price_ticks
                    fill.Exec_fills.quantity_units Exec_event.Taker
                with
                | None -> ()
                | Some updated ->
                    consume_visible_fill updated.Exec_account.side
                      fill.Exec_fills.price_ticks fill.Exec_fills.quantity_units)
              taken.Exec_fills.fills
  in
  let fok_account_ok accepted submitted_account =
    match
      Exec_fills.take mode ~book:!book ~side:accepted.Exec_account.side
        ~quantity_units:accepted.Exec_account.quantity_units
        ?limit_ticks:accepted.Exec_account.price_ticks ()
    with
    | Error _ -> false
    | Ok taken when taken.Exec_fills.remaining_units <> 0L -> false
    | Ok taken ->
        let result =
          List.fold_left
            (fun state_result fill ->
              match state_result with
              | Error _ -> state_result
              | Ok (order, state) ->
                  Exec_account.apply_fill config state order
                    ~price_ticks:fill.Exec_fills.price_ticks
                    ~quantity_units:fill.Exec_fills.quantity_units
                    ~liquidity:Exec_event.Taker
                  |> Result.map (fun (order, state) -> (order, state)))
            (Ok (accepted, submitted_account)) taken.Exec_fills.fills
        in
        (match result with
        | Ok (order, _) -> order.Exec_account.remaining_units = 0L
        | Error _ -> false)
  in
  let submit ~at order =
    let crosses price_ticks side =
      match side with
      | Exec_event.Buy ->
          (match L2_book.best_ask !book with Some ask -> price_ticks >= ask | None -> false)
      | Exec_event.Sell ->
          (match L2_book.best_bid !book with Some bid -> price_ticks <= bid | None -> false)
    in
    let crossing =
      match order.Exec_account.price_ticks with
      | Some price -> crosses price order.Exec_account.side
      | None -> false
    in
    if not !book_trusted then incr rejected
    else if Hashtbl.mem resting order.Exec_account.id then incr rejected
    else if order.Exec_account.post_only && order.Exec_account.price_ticks = None then
      incr rejected
    else if order.Exec_account.post_only && crossing then incr rejected
    else
    let market_tif_full = order.Exec_account.tif = Exec_event.Fok in
    let fok_available =
      if not market_tif_full then true
      else
        match
          Exec_fills.take mode ~book:!book ~side:order.Exec_account.side
            ~quantity_units:order.Exec_account.quantity_units
            ?limit_ticks:order.Exec_account.price_ticks ()
        with
        | Ok result -> result.Exec_fills.remaining_units = 0L
        | Error _ -> false
    in
    if not fok_available then incr rejected
    else match Exec_account.submit config !account order with
    | Error _ -> incr rejected
    | Ok (accepted, updated_account)
      when accepted.Exec_account.tif = Exec_event.Fok
           && not (fok_account_ok accepted updated_account) ->
        incr rejected
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
            placed_at = at;
          }
        in
        Hashtbl.replace resting accepted.Exec_account.id (accepted, metadata);
        let is_market = accepted.Exec_account.price_ticks = None in
        if is_market then begin
          (* A market order takes what is visible, then its remainder is
             cancelled like an IOC order at the venue. *)
            take_from_book ~at accepted;
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
          if crossing then take_from_book ~at accepted;
          (match Hashtbl.find_opt resting accepted.Exec_account.id with
          | Some (current, _) when current.Exec_account.tif <> Exec_event.Gtc ->
              (match Exec_account.cancel config !account current with
              | Ok (_, updated_account) ->
                  account := updated_account;
                  Hashtbl.remove resting accepted.Exec_account.id
              | Error _ -> incr rejected)
          | _ -> ())
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
  let invalidate_book () =
    book := L2_book.empty;
    book_trusted := false;
    Hashtbl.iter
      (fun id (order, _) ->
        (match Exec_account.cancel config !account order with
        | Ok (_, updated_account) -> account := updated_account
        | Error _ -> incr rejected);
        Hashtbl.remove resting id)
      resting
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
        | effective_time, _, Submit order -> submit ~at:effective_time order
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
              (apply_fill ~at:event.Exec_event.receive_time order metadata.price_ticks delta Exec_event.Maker);
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
          book_trusted := true;
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
                  | Depth_chain.Gap ->
                      incr chain_gaps;
                      invalidate_book ())
                (List.rev !buffered);
              buffered := []
          | None ->
              Depth_chain.clear chain;
              buffered := [])
      | Exec_event.Depth_update update ->
          if not !book_trusted && Depth_chain.current chain = None then
            buffered := update :: !buffered
          else if not !book_trusted then incr chain_gaps
          else
            let previous =
              match update.Exec_event.previous_update_id with
              | Some value -> value
              | None -> Int64.min_int
            in
            (match
               Depth_chain.apply chain
                 ~first_update_id:update.Exec_event.first_update_id
                 ~last_update_id:update.Exec_event.last_update_id
                 ~previous_update_id:previous
             with
            | Depth_chain.Accept ->
                book :=
                  L2_book.apply_update !book ~bids:update.Exec_event.bids
                    ~asks:update.Exec_event.asks
            | Depth_chain.Superseded -> incr chain_superseded
            | Depth_chain.Gap ->
                incr chain_gaps;
                invalidate_book ())
      | Exec_event.Trade _ -> accumulate_trades event
      | _ -> ());
      if !book_trusted then begin
        update_maker_fills event;
        maybe_liquidate ()
      end;
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
      let actions = if !book_trusted then strategy context else [] in
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
        | effective_time, _, Submit order -> submit ~at:effective_time order
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
