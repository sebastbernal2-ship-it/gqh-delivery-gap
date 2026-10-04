(** A deliberately optimistic baseline, for measuring the realism gap.

    A textbook backtest fills every order instantly and completely at the mark
    and ignores capital limits. This module reproduces exactly that: an intent
    fills in full at the book mid with a taker fee, cancels do nothing, and no
    order is ever refused.

    Running the same strategy through this baseline and through {!Exec_loop}
    produces the gap the engine exists to show: how much of the intended size
    never filled, how many orders the capital rule would refuse, and how far
    the naive result is from the realistic one. *)

type report = {
  orders : int;
  filled_units : int64;
  fees : int64;
  realized_pnl : int64;
  equity : int64;
  capital_blocked : int;
}

let mid_ticks book =
  match (L2_book.best_bid book, L2_book.best_ask book) with
  | Some bid, Some ask -> Some (Int64.div (Int64.add bid ask) 2L)
  | _ -> None

let taker_fee config price_ticks quantity_units =
  match Exec_units.notional ~price_ticks ~quantity_units with
  | Error _ -> None
  | Ok notional -> (
      match
        Exec_units.bps ~money:notional
          ~bps:config.Exec_account.taker_fee_bps
      with
      | Ok fee -> Some fee
      | Error _ -> None)

(* Would the realistic capital rule refuse an order this size? *)
let capital_blocked config state price_ticks quantity_units =
  match Exec_account.available_margin state ~mark_ticks:price_ticks with
  | Error _ -> false
  | Ok available -> (
      match
        Exec_account.required_margin config ~price_ticks ~quantity_units
      with
      | Error _ -> false
      | Ok required -> Int64.compare required available > 0)

let run ~config ~strategy ~initial_collateral ~events =
  let book = ref L2_book.empty in
  let state = ref (Exec_account.empty ~collateral:initial_collateral) in
  let orders = ref 0 in
  let filled_units = ref 0L in
  let fees = ref 0L in
  let blocked = ref 0 in
  let assumed = ref [] in
  let apply_intent (action : Exec_loop.action) =
    match action with
    | Exec_loop.Cancel _ -> ()
    | Exec_loop.Submit order -> (
        match mid_ticks !book with
        | None -> ()
        | Some mid -> (
            let side = order.Exec_account.side in
            let quantity_units = order.Exec_account.quantity_units in
            match
              ( taker_fee config mid quantity_units,
                Exec_account.apply_position !state ~price_ticks:mid
                  ~quantity_units ~side )
            with
            | Some fee, Ok (next, realized) ->
                if capital_blocked config !state mid quantity_units then
                  incr blocked;
                state :=
                  {
                    next with
                    Exec_account.collateral =
                      Int64.sub
                        (Int64.add next.Exec_account.collateral realized)
                        fee;
                    realized_pnl =
                      Int64.add next.Exec_account.realized_pnl realized;
                    fees = Int64.add next.Exec_account.fees fee;
                  };
                incr orders;
                filled_units := Int64.add !filled_units quantity_units;
                fees := Int64.add !fees fee;
                (* The strategy decides from the orders it believes it holds,
                   so the baseline keeps the same resting picture as the
                   realistic run even though it filled instantly. *)
                assumed := [ order ]
            | _ -> ()))
  in
  List.iteri
    (fun index event ->
      (match event.Exec_event.payload with
      | Exec_event.Depth_snapshot snapshot ->
          book :=
            L2_book.apply_snapshot !book ~bids:snapshot.Exec_event.bids
              ~asks:snapshot.Exec_event.asks
      | Exec_event.Depth_update update ->
          book :=
            L2_book.apply_update !book ~bids:update.Exec_event.bids
              ~asks:update.Exec_event.asks
      | _ -> ());
      let context =
        {
          (* The feature lookup is by event index, so the baseline must pass
             the real index or a strategy reads the wrong feature row. *)
          Exec_loop.index = index;
          event;
          book = !book;
          account = !state;
          orders = !assumed;
        }
      in
      List.iter apply_intent (strategy context))
    events;
  let equity =
    match mid_ticks !book with
    | None -> !state.Exec_account.collateral
    | Some mid -> (
        match Exec_account.equity !state ~mark_ticks:mid with
        | Ok value -> value
        | Error _ -> !state.Exec_account.collateral)
  in
  {
    orders = !orders;
    filled_units = !filled_units;
    fees = !fees;
    realized_pnl = !state.Exec_account.realized_pnl;
    equity;
    capital_blocked = !blocked;
  }
