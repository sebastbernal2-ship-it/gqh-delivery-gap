type fill = {
  order_id : string;
  side : Exec_event.side;
  at : Timestamp.t;
  price_ticks : int64;
  quantity_units : int64;
  fee : int64;
}

type result = {
  account : Asset_account.t;
  book : L2_book.t;
  submitted : int;
  rejected : int;
  unfilled : int;
  fills : fill list;
  last_mark_ticks : int64 option;
}

let ( let* ) result f = Result.bind result f

let valid_sha256 text =
  String.length text = 64
  && String.for_all
       (function '0' .. '9' | 'a' .. 'f' | 'A' .. 'F' -> true | _ -> false)
       text

let book_mark book =
  match (L2_book.best_bid book, L2_book.best_ask book) with
  | Some bid, Some ask -> Some (Int64.div (Int64.add bid ask) 2L)
  | Some bid, None -> Some bid
  | None, Some ask -> Some ask
  | None, None -> None

let validate_depth_levels spec ~snapshot levels =
  List.fold_left
    (fun prior (level : Exec_event.level) ->
      let* () = prior in
      if
        level.price_ticks <= 0L
        || level.price_ticks > Exec_units.price_ticks_max
        || Int64.rem level.price_ticks
             spec.Instrument_spec.price_increment_ticks
           <> 0L
      then Serror.fail "depth price violates instrument specification"
      else if
        level.quantity_units < 0L
        || (snapshot && level.quantity_units = 0L)
        || level.quantity_units <> 0L
           && Int64.rem level.quantity_units
                spec.Instrument_spec.quantity_increment_units
              <> 0L
      then Serror.fail "depth size violates instrument specification"
      else Ok ())
    (Ok ()) levels

let validate_event spec previous (event : Exec_event.t) =
  if
    event.venue <> spec.Instrument_spec.venue
    || event.symbol <> spec.Instrument_spec.symbol
  then Serror.fail "event instrument does not match account specification"
  else if
    event.source_id = "" || event.source_path = ""
    || not (valid_sha256 event.source_sha256)
  then Serror.fail "event provenance is incomplete or malformed"
  else if event.quality <> Exec_event.Healthy then
    Serror.fail "suspect event cannot affect asset execution"
  else if
    match previous with
    | None -> false
    | Some earlier -> Timestamp.compare event.receive_time earlier < 0
  then Serror.fail "events are not ordered by receive time"
  else Ok ()

let run spec ~initial_cash ~taker_fee_bps ~latency_ns ~equity_settlement events
    =
  if taker_fee_bps < 0 then
    Serror.fail "negative fee bps require a rebate policy"
  else if latency_ns < 0L || latency_ns > 3_600_000_000_000L then
    Serror.fail "latency must be between zero and one hour"
  else
    let* initial_account = Asset_account.create spec ~cash:initial_cash in
    let account = ref initial_account in
    let book = ref L2_book.empty in
    let chain = Depth_chain.create () in
    let submitted = ref 0 in
    let rejected = ref 0 in
    let unfilled = ref 0 in
    let fills = ref [] in
    let last_mark_ticks = ref None in
    let pending = ref [] in
    let next_seq = ref 0 in
    let seen_orders = Hashtbl.create 16 in
    let execute at (intent : Exec_event.intent) =
      if intent.tif = Exec_event.Gtc || intent.post_only then begin
        incr rejected;
        Ok ()
      end
      else if intent.quantity_units <= 0L then
        Serror.fail "order quantity must be positive"
      else if
        match intent.price_ticks with
        | None -> false
        | Some limit ->
            limit <= 0L
            || Int64.rem limit spec.Instrument_spec.price_increment_ticks <> 0L
      then begin
        incr rejected;
        Ok ()
      end
      else if
        intent.reduce_only
        &&
        let position = !account.Asset_account.position_units in
        position = 0L
        || (position > 0L && intent.side <> Exec_event.Sell)
        || (position < 0L && intent.side <> Exec_event.Buy)
        || Int64.abs position < intent.quantity_units
      then begin
        incr rejected;
        Ok ()
      end
      else
        let* taken =
          Exec_fills.take Exec_fills.Conservative ~book:!book ~side:intent.side
            ~quantity_units:intent.quantity_units
            ?limit_ticks:intent.price_ticks ()
        in
        if
          intent.tif = Exec_event.Fok
          && taken.filled_units <> intent.quantity_units
        then begin
          incr unfilled;
          Ok ()
        end
        else
          let rec apply local_account local_book local_fills = function
            | [] -> Ok (local_account, local_book, local_fills)
            | (piece : Exec_fills.taker_fill) :: rest -> (
                let settle_at =
                  match spec.Instrument_spec.kind with
                  | Instrument_spec.Equity when intent.side = Exec_event.Sell ->
                      Some (equity_settlement at)
                  | _ -> None
                in
                let fee_before = local_account.Asset_account.fees in
                let attempt =
                  Asset_account.fill local_account ~at ~side:intent.side
                    ~price_ticks:piece.price_ticks
                    ~quantity_units:piece.quantity_units ~fee_bps:taker_fee_bps
                    ~settle_at
                in
                match attempt with
                | Error _ when intent.tif = Exec_event.Ioc && local_fills <> []
                  ->
                    Ok (local_account, local_book, local_fills)
                | Error message -> Error message
                | Ok updated ->
                    let fee = Int64.sub updated.Asset_account.fees fee_before in
                    let side =
                      match intent.side with
                      | Exec_event.Buy -> L2_book.Ask
                      | Exec_event.Sell -> L2_book.Bid
                    in
                    let current =
                      List.find_opt
                        (fun (price, _) -> price = piece.price_ticks)
                        (L2_book.levels local_book side)
                    in
                    let* remaining =
                      match current with
                      | Some (_, size) when size >= piece.quantity_units ->
                          Ok (Int64.sub size piece.quantity_units)
                      | _ -> Serror.fail "visible depth changed during a fill"
                    in
                    let level =
                      {
                        Exec_event.price_ticks = piece.price_ticks;
                        quantity_units = remaining;
                      }
                    in
                    let local_book =
                      L2_book.apply_levels local_book side [ level ]
                    in
                    let recorded =
                      {
                        order_id = intent.order_id;
                        side = intent.side;
                        at;
                        price_ticks = piece.price_ticks;
                        quantity_units = piece.quantity_units;
                        fee;
                      }
                    in
                    apply updated local_book (recorded :: local_fills) rest)
          in
          match apply !account !book [] taken.fills with
          | Error _ ->
              incr rejected;
              Ok ()
          | Ok (updated, updated_book, new_fills) ->
              account := updated;
              book := updated_book;
              fills := new_fills @ !fills;
              let executed_units =
                List.fold_left
                  (fun total item -> Int64.add total item.quantity_units)
                  0L new_fills
              in
              if executed_units < intent.quantity_units then incr unfilled;
              Ok ()
    in
    let execute_due now =
      let due, later =
        List.partition
          (fun (at, _, _) -> Timestamp.compare at now <= 0)
          !pending
      in
      pending := later;
      let due =
        List.sort
          (fun (left_at, left_seq, _) (right_at, right_seq, _) ->
            let by_time = Timestamp.compare left_at right_at in
            if by_time <> 0 then by_time else Int.compare left_seq right_seq)
          due
      in
      List.fold_left
        (fun prior (at, _, intent) ->
          let* () = prior in
          execute at intent)
        (Ok ()) due
    in
    let rec process previous = function
      | [] ->
          Ok
            {
              account = !account;
              book = !book;
              submitted = !submitted;
              rejected = !rejected;
              unfilled = !unfilled + List.length !pending;
              fills = List.rev !fills;
              last_mark_ticks = !last_mark_ticks;
            }
      | event :: rest ->
          let* () = validate_event spec previous event in
          let at = event.Exec_event.receive_time in
          let* settled = Asset_account.settle_receivables !account ~at in
          account := settled;
          let* () = execute_due at in
          let* () =
            match event.Exec_event.payload with
            | Exec_event.Depth_snapshot snapshot ->
                let* () =
                  validate_depth_levels spec ~snapshot:true snapshot.bids
                in
                let* () =
                  validate_depth_levels spec ~snapshot:true snapshot.asks
                in
                book :=
                  L2_book.apply_snapshot !book ~bids:snapshot.bids
                    ~asks:snapshot.asks;
                (match snapshot.last_update_id with
                | Some last -> Depth_chain.reset chain last
                | None -> ());
                last_mark_ticks := book_mark !book;
                Ok ()
            | Exec_event.Depth_update update -> (
                let* () =
                  validate_depth_levels spec ~snapshot:false update.bids
                in
                let* () =
                  validate_depth_levels spec ~snapshot:false update.asks
                in
                let* previous_update_id =
                  match update.previous_update_id with
                  | Some value -> Ok value
                  | None -> Serror.fail "depth update lacks chain predecessor"
                in
                match
                  Depth_chain.apply chain
                    ~first_update_id:update.first_update_id
                    ~last_update_id:update.last_update_id ~previous_update_id
                with
                | Depth_chain.Accept ->
                    book :=
                      L2_book.apply_update !book ~bids:update.bids
                        ~asks:update.asks;
                    last_mark_ticks := book_mark !book;
                    Ok ()
                | Depth_chain.Superseded -> Ok ()
                | Depth_chain.Gap -> Serror.fail "depth sequence gap")
            | Exec_event.Order_intent intent ->
                incr submitted;
                if Hashtbl.mem seen_orders intent.order_id then incr rejected
                else begin
                  Hashtbl.add seen_orders intent.order_id ();
                  incr next_seq;
                  let effective = Timestamp.add_ns at latency_ns in
                  pending := (effective, !next_seq, intent) :: !pending
                end;
                Ok ()
            | Exec_event.Funding funding ->
                let* updated =
                  Asset_account.perpetual_funding !account
                    ~mark_ticks:funding.mark_ticks ~rate_units:funding.rate
                in
                account := updated;
                last_mark_ticks := Some funding.mark_ticks;
                Ok ()
            | Exec_event.Mark mark ->
                if
                  mark.mark_ticks <= 0L
                  || mark.mark_ticks > Exec_units.price_ticks_max
                then Serror.fail "mark price must be positive"
                else begin
                  last_mark_ticks := Some mark.mark_ticks;
                  Ok ()
                end
            | Exec_event.Observation observation ->
                let* updated =
                  Asset_replay.apply_observation !account at observation
                in
                account := updated;
                Ok ()
            | _ -> Ok ()
          in
          let* () = execute_due at in
          let* () =
            if L2_book.crossed !book then Serror.fail "crossed replay book"
            else
              match !last_mark_ticks with
              | None -> Ok ()
              | Some mark ->
                  let* breached =
                    Asset_account.maintenance_breach !account ~mark_ticks:mark
                  in
                  if breached then
                    Serror.fail
                      "maintenance breach needs a venue liquidation rule"
                  else Ok ()
          in
          process (Some at) rest
    in
    process None events
