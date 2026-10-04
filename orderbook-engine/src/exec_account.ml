(** Fixed-point account and order lifecycle for the execution kernel.

    Every amount is an integer in the units owned by {!Exec_units} and
    {!docs/adr/ADR-007-execution-units.md}: price ticks (1e-4), quantity units
    (1e-6), money (1e-8), and rates (1e-8).

    Rules that hold everywhere:

    - Required margin rounds up, so a capital check never under-reserves.
    - P&L, fees, and funding round half away from zero.
    - Collateral never goes below zero, even after a liquidation.
    - A reduce-only order never increases a position and reserves no capital.
    - A liquidated account accepts no new orders.

    Submission reserves initial margin only, so an order that consumes all
    available margin can still fail at fill once the fee is charged. Reserve
    headroom for fees when sizing orders. *)

type config = {
  leverage : int;
  maintenance_margin_rate_bps : int;
  maker_fee_bps : int;
  taker_fee_bps : int;
  liquidation_fee_bps : int;
}

type state = {
  collateral : int64;
  position : int64;
  entry_ticks : int64 option;
  realized_pnl : int64;
  fees : int64;
  funding_paid : int64;
  reserved_margin : int64;
  liquidated : bool;
}

type status = New | Partially_filled | Filled | Canceled

type order = {
  id : string;
  side : Exec_event.side;
  price_ticks : int64 option;
  quantity_units : int64;
  remaining_units : int64;
  tif : Exec_event.tif;
  reduce_only : bool;
  post_only : bool;
  status : status;
}

let bps_divisor = 10_000L
let notional_divisor = 100L
let funding_divisor = 100_000_000L

let magnitude value =
  if value = Int64.min_int then Serror.fail "position magnitude overflow"
  else Ok (Int64.abs value)

let make_config ~leverage ~maintenance_margin_rate_bps ~maker_fee_bps
    ~taker_fee_bps ?(liquidation_fee_bps = 0) () =
  if leverage < 1 then invalid_arg "leverage must be at least one";
  if maintenance_margin_rate_bps < 0 || maintenance_margin_rate_bps >= 10_000
  then invalid_arg "maintenance margin rate must be in [0, 10000)";
  if maker_fee_bps < 0 || taker_fee_bps < 0 || liquidation_fee_bps < 0 then
    invalid_arg "fee rates must be nonnegative";
  { leverage; maintenance_margin_rate_bps; maker_fee_bps; taker_fee_bps;
    liquidation_fee_bps }

let empty ~collateral =
  if collateral < 0L then invalid_arg "collateral must be nonnegative";
  {
    collateral;
    position = 0L;
    entry_ticks = None;
    realized_pnl = 0L;
    fees = 0L;
    funding_paid = 0L;
    reserved_margin = 0L;
    liquidated = false;
  }

let notional ~price_ticks ~quantity_units =
  Exec_units.notional ~price_ticks ~quantity_units

let required_margin config ~price_ticks ~quantity_units =
  let open Exec_units in
  let* notional = notional ~price_ticks ~quantity_units in
  div_ceil notional (Int64.of_int config.leverage)

let fee config liquidity ~price_ticks ~quantity_units =
  let open Exec_units in
  let* notional = notional ~price_ticks ~quantity_units in
  let rate_bps =
    match liquidity with
    | Exec_event.Maker -> config.maker_fee_bps
    | Exec_event.Taker -> config.taker_fee_bps
  in
  Exec_units.bps ~money:notional ~bps:rate_bps

let unrealized state ~mark_ticks =
  let open Exec_units in
  match state.entry_ticks with
  | None -> Ok 0L
  | Some entry ->
      let* difference = checked_add mark_ticks (Int64.neg entry) in
      let* product = checked_mul difference state.position in
      div_round product notional_divisor

let equity state ~mark_ticks =
  let open Exec_units in
  let* unrealized = unrealized state ~mark_ticks in
  checked_add state.collateral unrealized

let maintenance_margin config state ~mark_ticks =
  let open Exec_units in
  let* magnitude = magnitude state.position in
  let* product = checked_mul magnitude mark_ticks in
  let* notional = div_round product notional_divisor in
  bps ~money:notional ~bps:config.maintenance_margin_rate_bps

let available_margin state ~mark_ticks =
  let open Exec_units in
  let* equity = equity state ~mark_ticks in
  checked_add equity (Int64.neg state.reserved_margin)

let should_liquidate config state ~mark_ticks =
  let open Exec_units in
  let* equity = equity state ~mark_ticks in
  let* maintenance = maintenance_margin config state ~mark_ticks in
  Ok (state.liquidated || Int64.compare equity maintenance <= 0)

let signed side quantity =
  match side with Exec_event.Buy -> quantity | Exec_event.Sell -> Int64.neg quantity

let same_direction left right =
  (Int64.compare left 0L >= 0 && Int64.compare right 0L >= 0)
  || (Int64.compare left 0L <= 0 && Int64.compare right 0L <= 0)

let release_reservation config state ~price_ticks ~quantity_units =
  let open Exec_units in
  let* released = required_margin config ~price_ticks ~quantity_units in
  let* remaining = checked_sub state.reserved_margin released in
  let remaining = if remaining < 0L then 0L else remaining in
  Ok { state with reserved_margin = remaining }

let submit config state order =
  let open Exec_units in
  if order.id = "" then Serror.fail "order ID must not be empty"
  else if order.quantity_units <= 0L then
    Serror.fail "order quantity must be positive"
  else if order.remaining_units <> order.quantity_units || order.status <> New then
    Serror.fail "submitted order must be new with full remaining quantity"
  else if state.liquidated then Serror.fail "account is liquidated"
  else
    let* () =
      match order.price_ticks with
      | Some price when price <= 0L -> Serror.fail "limit price must be positive"
      | _ -> Ok ()
    in
    let requested = signed order.side order.quantity_units in
    let* () =
      if order.reduce_only then
        if state.position = 0L then Serror.fail "reduce-only order needs a position"
        else if same_direction requested state.position then
          Serror.fail "reduce-only order would increase the position"
        else
          let* position_size = magnitude state.position in
          if Int64.compare order.quantity_units position_size > 0 then
            Serror.fail "reduce-only order exceeds the position"
          else Ok ()
      else Ok ()
    in
    let* reservation =
      if order.reduce_only then Ok 0L
      else
        match order.price_ticks with
        | None -> Ok 0L
        | Some price ->
            required_margin config ~price_ticks:price
              ~quantity_units:order.quantity_units
    in
    let mark = match order.price_ticks with Some price -> price | None -> 0L in
    let* available =
      if reservation = 0L then Ok 0L else available_margin state ~mark_ticks:mark
    in
    if reservation > 0L && Int64.compare reservation available > 0 then
      Serror.fail "order exceeds available margin"
    else
      let* reserved_margin = checked_add state.reserved_margin reservation in
      Ok
        ( { order with status = New },
          { state with reserved_margin } )

let cancel config state order =
  match order.status with
  | Canceled -> Ok (order, state)
  | Filled -> Ok (order, state)
  | New | Partially_filled -> (
      match order.price_ticks with
      | None -> Ok ({ order with status = Canceled }, state)
      | Some price ->
          let open Exec_units in
          let* state =
            release_reservation config state ~price_ticks:price
              ~quantity_units:order.remaining_units
          in
          Ok ({ order with status = Canceled }, state))

let apply_position state ~price_ticks ~quantity_units ~side =
  let open Exec_units in
  let incoming = signed side quantity_units in
  match state.entry_ticks with
  | None ->
      Ok
        ( { state with position = incoming; entry_ticks = Some price_ticks },
          0L )
  | Some entry when state.position = 0L ->
      Ok
        ( { state with position = incoming; entry_ticks = Some price_ticks },
          0L )
  | Some entry when same_direction state.position incoming ->
      let* old_size = magnitude state.position in
      let* weighted = checked_mul old_size entry in
      let* added = checked_mul quantity_units price_ticks in
      let* total = checked_add weighted added in
      let* size = checked_add old_size quantity_units in
      let* average = div_round total size in
      let* position = checked_add state.position incoming in
      Ok
        ( { state with position; entry_ticks = Some average },
          0L )
  | Some entry ->
      let* magnitude = magnitude state.position in
      let closing =
        if Int64.compare magnitude quantity_units <= 0 then magnitude
        else quantity_units
      in
      let direction = if state.position > 0L then 1L else -1L in
      let* difference =
        if direction > 0L then checked_add price_ticks (Int64.neg entry)
        else checked_add entry (Int64.neg price_ticks)
      in
      let* product = checked_mul difference closing in
      let* realized = div_round product notional_divisor in
      let* remaining = checked_sub quantity_units closing in
      if remaining <= 0L then
        let* position = checked_add state.position incoming in
        let entry_ticks = if position = 0L then None else Some entry in
        Ok ({ state with position; entry_ticks }, realized)
      else
        Ok
          ( { state with position = signed side remaining;
              entry_ticks = Some price_ticks },
            realized )

let apply_fill config state order ~price_ticks ~quantity_units ~liquidity =
  let open Exec_units in
  if price_ticks <= 0L then Serror.fail "fill price must be positive"
  else if quantity_units <= 0L then Serror.fail "fill quantity must be positive"
  else if Int64.compare quantity_units order.remaining_units > 0 then
    Serror.fail "fill quantity is outside the order remainder"
  else if order.status = Canceled || order.status = Filled then
    Serror.fail "order is not fillable"
  else if state.liquidated then Serror.fail "account is liquidated"
  else
    let requested = signed order.side quantity_units in
    let* () =
      if order.reduce_only then
        if state.position = 0L then Serror.fail "reduce-only fill has no position"
        else if same_direction requested state.position then
          Serror.fail "reduce-only fill would increase the position"
        else
          let* position_size = magnitude state.position in
          if Int64.compare quantity_units position_size > 0 then
            Serror.fail "reduce-only fill exceeds the position"
          else Ok ()
      else Ok ()
    in
    let* fee = fee config liquidity ~price_ticks ~quantity_units in
    let* state, realized =
      apply_position state ~price_ticks ~quantity_units ~side:order.side
    in
    let* collateral = checked_add state.collateral realized in
    let* collateral = checked_sub collateral fee in
    let* realized_pnl = checked_add state.realized_pnl realized in
    let* fees = checked_add state.fees fee in
    let state = { state with collateral; realized_pnl; fees } in
    let* state =
      match order.price_ticks with
      | Some price ->
          release_reservation config state ~price_ticks:price ~quantity_units
      | None -> Ok state
    in
    let* () =
      if order.reduce_only then Ok ()
      else
        let* equity = equity state ~mark_ticks:price_ticks in
        let* required =
          if state.position = 0L then Ok 0L
          else
            let* position_size = magnitude state.position in
            required_margin config ~price_ticks ~quantity_units:position_size
        in
        let* available = checked_add equity (Int64.neg state.reserved_margin) in
        if Int64.compare required available > 0 then
          Serror.fail "fill exceeds available margin"
        else Ok ()
    in
    let* remaining = checked_sub order.remaining_units quantity_units in
    let status = if remaining = 0L then Filled else Partially_filled in
    Ok ({ order with remaining_units = remaining; status }, state)

let apply_funding state ~mark_ticks ~rate =
  let open Exec_units in
  if mark_ticks <= 0L then Serror.fail "mark price must be positive"
  else
    let* product = checked_mul state.position mark_ticks in
    let* notional = div_round product notional_divisor in
    let* scaled = checked_mul notional rate in
    let* payment = div_round scaled funding_divisor in
    let* collateral = checked_sub state.collateral payment in
    let* funding_paid = checked_add state.funding_paid payment in
    Ok { state with collateral; funding_paid }

let liquidate config state ~mark_ticks =
  let open Exec_units in
  let* liquidated_now = should_liquidate config state ~mark_ticks in
  if not liquidated_now then Serror.fail "account is above maintenance margin"
  else
    let* unrealized = unrealized state ~mark_ticks in
    let* magnitude = magnitude state.position in
    let* fee =
      if magnitude = 0L then Ok 0L
      else
        let* notional = notional ~price_ticks:mark_ticks ~quantity_units:magnitude in
        Exec_units.bps ~money:notional ~bps:config.liquidation_fee_bps
    in
    let* collateral = checked_add state.collateral unrealized in
    let* collateral = checked_sub collateral fee in
    let collateral = if collateral < 0L then 0L else collateral in
    let* realized_pnl = checked_add state.realized_pnl unrealized in
    let* fees = checked_add state.fees fee in
    Ok
      {
        state with
        collateral;
        position = 0L;
        entry_ticks = None;
        realized_pnl;
        fees;
        reserved_margin = 0L;
        liquidated = true;
      }
