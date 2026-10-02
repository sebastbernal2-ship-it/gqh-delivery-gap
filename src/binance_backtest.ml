(** Explicit Binance order replay using visible books, trades, and account rules. *)

type execution = Maker | Taker
type order = {
  id : string;
  side : Binance_account.side;
  quantity : float;
  price : float option;
  placed_at : Timestamp.t;
  execution : execution;
}

type order_result = {
  id : string;
  requested : float;
  filled : float;
  status : Binance_account.status;
}

type result = { account : Binance_account.state; orders : order_result list }
type maker_policy = Pessimistic | Optimistic

let ( let* ) result f = Result.bind result f

let execution_side = function
  | Binance_account.Buy -> Binance_maker_model.Buy
  | Binance_account.Sell -> Binance_maker_model.Sell

let visible_side = function
  | Binance_account.Buy -> L2_execution.Buy
  | Binance_account.Sell -> L2_execution.Sell

let find_snapshot snapshots placed_at =
  List.find_opt
    (fun (snapshot : Hf_l2.snapshot) ->
      Timestamp.compare snapshot.timestamp placed_at >= 0)
    snapshots

let decimal_of_float value = Printf.sprintf "%.17g" value

let validate_order instrument (request : order) =
  let* _ =
    Binance_units.to_quantity_lots instrument (decimal_of_float request.quantity)
  in
  match request.price with
  | None -> Ok ()
  | Some price ->
      let* _ = Binance_units.to_price_ticks instrument (decimal_of_float price) in
      Ok ()

let apply_fills ~config account order fills =
  let rec loop account order filled = function
    | [] -> Ok (account, order, filled)
    | fill :: rest ->
        let* order, account =
          Binance_account.apply_fill ~config Binance_account.Taker
            ~price:fill.L2_execution.price ~quantity:fill.size order account
        in
        loop account order (filled +. fill.size) rest
  in
  loop account order 0.0 fills

let run ~collateral ~config ~symbol ~instrument ~maker_policy ~states ~trades ~orders =
  match Binance_l2.to_hf_l2 ~instrument ~symbol states with
  | Error error -> Error error
  | Ok snapshots ->
      let rec process account results = function
        | [] -> Ok { account; orders = List.rev results }
        | (request : order) :: rest ->
            let rejected error =
              process account
                ({ id = request.id; requested = request.quantity; filled = 0.0; status = Rejected error }
                :: results)
                rest
            in
            (match validate_order instrument request with
            | Error error -> rejected error
            | Ok () ->
                match
                  Binance_account.submit_order ~config ~state:account ~id:request.id
                 ~side:request.side ~quantity:request.quantity
                 ?limit_price:request.price ()
                 with
                | Error error -> rejected error
                | Ok account_order -> (
                match request.execution with
                | Maker -> (
                    match request.price with
                    | None -> rejected "maker order requires a price"
                    | Some price ->
                        let estimate =
                          Binance_maker_model.estimate
                            ~side:(execution_side request.side) ~price
                            ~size:request.quantity ~placed_at:request.placed_at
                            ~states ~trades
                        in
                        let quantity =
                          match maker_policy with
                          | Pessimistic -> estimate.pessimistic_filled
                          | Optimistic -> estimate.optimistic_filled
                        in
                        if quantity <= 0.0 then
                          process account
                            ({ id = request.id; requested = request.quantity; filled = 0.0; status = account_order.status }
                            :: results)
                            rest
                        else
                          (match
                             Binance_account.apply_fill ~config Binance_account.Maker
                               ~price ~quantity account_order account
                           with
                          | Error error -> rejected error
                          | Ok (account_order, account) ->
                              process account
                                ({ id = request.id; requested = request.quantity; filled = quantity; status = account_order.status }
                                :: results)
                                rest))
                | Taker -> (
                    match find_snapshot snapshots request.placed_at with
                    | None -> rejected "no book snapshot at or after order placement"
                    | Some snapshot ->
                        let execution =
                          L2_execution.execute snapshot (visible_side request.side)
                            ?limit_price:request.price request.quantity
                        in
                        (match apply_fills ~config account account_order execution.fills with
                        | Error error -> rejected error
                        | Ok (account, account_order, filled) ->
                            process account
                              ({ id = request.id; requested = request.quantity; filled; status = account_order.status }
                              :: results)
                              rest))))
      in
      let orders =
        List.sort
          (fun left right -> Timestamp.compare left.placed_at right.placed_at)
          orders
      in
      process (Binance_account.empty_state ~collateral) [] orders
