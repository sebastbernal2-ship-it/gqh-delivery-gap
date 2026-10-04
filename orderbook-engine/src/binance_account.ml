(** Bounded Binance-style account, order, fee, funding, and liquidation rules. *)

type liquidity = Maker | Taker
type tif = Gtc | Ioc | Fok
type side = Buy | Sell
type status = New | Partially_filled | Filled | Canceled | Rejected of string

type config = {
  leverage : float;
  maintenance_margin_rate : float;
  maker_fee_bps : float;
  taker_fee_bps : float;
  liquidation_fee_bps : float;
}

type state = {
  collateral : float;
  position : float;
  entry_price : float option;
  realized_pnl : float;
  fees : float;
  funding_paid : float;
  liquidated : bool;
}

type order = {
  id : string;
  side : side;
  quantity : float;
  remaining : float;
  limit_price : float option;
  reduce_only : bool;
  post_only : bool;
  tif : tif;
  status : status;
}

let make_config ~leverage ~maintenance_margin_rate ~maker_fee_bps ~taker_fee_bps
    ?(liquidation_fee_bps = 0.0) () =
  if leverage <= 0.0 then invalid_arg "leverage must be positive";
  if maintenance_margin_rate < 0.0 || maintenance_margin_rate >= 1.0 then
    invalid_arg "maintenance margin rate must be in [0, 1)";
  if maker_fee_bps < 0.0 || taker_fee_bps < 0.0 || liquidation_fee_bps < 0.0 then
    invalid_arg "fee rates must be nonnegative";
  { leverage; maintenance_margin_rate; maker_fee_bps; taker_fee_bps;
    liquidation_fee_bps }

let empty_state ~collateral =
  if collateral < 0.0 then invalid_arg "collateral must be nonnegative";
  {
    collateral;
    position = 0.0;
    entry_price = None;
    realized_pnl = 0.0;
    fees = 0.0;
    funding_paid = 0.0;
    liquidated = false;
  }

let signed side quantity = match side with Buy -> quantity | Sell -> -.quantity
let same_sign left right = (left >= 0.0 && right >= 0.0) || (left <= 0.0 && right <= 0.0)

let submit_order ~config:_ ~state ~id ~side ~quantity ?limit_price
    ?(reduce_only = false) ?(post_only = false) ?(tif = Gtc) () =
  if id = "" then Error "order ID must not be empty"
  else if quantity <= 0.0 || Float.is_nan quantity || Float.is_infinite quantity then
    Error "order quantity must be positive and finite"
  else if state.liquidated then Error "account is liquidated"
  else
    let requested = signed side quantity in
    if reduce_only
       && (state.position = 0.0 || same_sign requested state.position
           || quantity > abs_float state.position)
    then Error "reduce-only order would increase the position"
    else
      Ok
        {
          id;
          side;
          quantity;
          remaining = quantity;
          limit_price;
          reduce_only;
          post_only;
          tif;
          status = New;
        }

let fee_bps config liquidity =
  match liquidity with Maker -> config.maker_fee_bps | Taker -> config.taker_fee_bps

let apply_position ~price ~quantity side state =
  let incoming = signed side quantity in
  match state.entry_price with
  | None -> { state with position = incoming; entry_price = Some price }, 0.0
  | Some entry when state.position = 0.0 ->
      { state with position = incoming; entry_price = Some price }, 0.0
  | Some entry when same_sign state.position incoming ->
      let old_size = abs_float state.position in
      let new_size = old_size +. quantity in
      let average = ((old_size *. entry) +. (quantity *. price)) /. new_size in
      { state with position = state.position +. incoming; entry_price = Some average }, 0.0
  | Some entry ->
      let closing = min (abs_float state.position) quantity in
      let direction = if state.position > 0.0 then 1.0 else -.1.0 in
      let realized = (price -. entry) *. closing *. direction in
      let remaining = quantity -. closing in
      if remaining <= 0.0 then
        {
          state with
          position = state.position +. incoming;
          entry_price = if abs_float (state.position +. incoming) < 1e-12 then None else Some entry;
        },
        realized
      else
        {
          state with position = signed side remaining; entry_price = Some price;
        },
        realized

let equity ~mark state =
  match state.entry_price with
  | None -> state.collateral
  | Some entry -> state.collateral +. (state.position *. (mark -. entry))

let apply_fill ~config liquidity ~price ~quantity order state =
  if price <= 0.0 || Float.is_nan price || Float.is_infinite price then
    Error "fill price must be positive and finite"
  else if quantity <= 0.0 || quantity > order.remaining then
    Error "fill quantity is outside the order remainder"
  else if order.status = Canceled || order.status = Filled then
    Error "order is not fillable"
  else if order.tif = Fok && quantity < order.remaining then
    Error "FOK order requires a complete fill"
  else if
    state.liquidated
    || equity ~mark:price state
       <= abs_float state.position *. price
          *. config.maintenance_margin_rate
  then Error "account is below maintenance margin"
  else
    let fee = price *. quantity *. fee_bps config liquidity /. 10_000.0 in
    let state, realized = apply_position ~price ~quantity order.side state in
    let state =
      {
        state with
        collateral = state.collateral +. realized -. fee;
        realized_pnl = state.realized_pnl +. realized;
        fees = state.fees +. fee;
      }
    in
    let required_initial_margin =
      abs_float state.position *. price /. config.leverage
    in
    if required_initial_margin > equity ~mark:price state +. 1e-9 then
      Error "fill exceeds configured leverage margin"
    else
      let remaining = order.remaining -. quantity in
      let status = if remaining <= 1e-12 then Filled else Partially_filled in
      Ok ({ order with remaining = max 0.0 remaining; status }, state)

let cancel order =
  match order.status with
  | New | Partially_filled -> { order with status = Canceled }
  | _ -> order

let finalize order =
  if order.remaining <= 1e-12 then { order with status = Filled }
  else
    match order.tif with
    | Gtc -> order
    | Ioc | Fok -> { order with status = Canceled }

let apply_funding ~mark ~rate state =
  if mark < 0.0 then invalid_arg "mark price must be nonnegative";
  let payment = state.position *. mark *. rate in
  {
    state with
    collateral = state.collateral -. payment;
    funding_paid = state.funding_paid +. payment;
  }

let maintenance_margin ~mark config state =
  abs_float state.position *. mark *. config.maintenance_margin_rate

let liquidation_price config state =
  match state.entry_price with
  | None -> None
  | Some _ when state.position = 0.0 -> None
  | Some entry ->
      let position = state.position in
      let factor = if position > 0.0 then 1.0 -. config.maintenance_margin_rate else 1.0 +. config.maintenance_margin_rate in
      let price = (position *. entry -. state.collateral) /. (position *. factor) in
      Some (max 0.0 price)

let is_liquidated ~mark config state =
  state.liquidated || equity ~mark state <= maintenance_margin ~mark config state

let liquidate ~mark config state =
  if not (is_liquidated ~mark config state) then
    Error "account is not below maintenance margin"
  else
    let unrealized =
      match state.entry_price with
      | None -> 0.0
      | Some entry -> state.position *. (mark -. entry)
    in
    let liquidation_fee =
      abs_float state.position *. mark *. config.liquidation_fee_bps /. 10_000.0
    in
    Ok
      {
        state with
        collateral = max 0.0 (equity ~mark state -. liquidation_fee);
        position = 0.0;
        entry_price = None;
        realized_pnl = state.realized_pnl +. unrealized;
        fees = state.fees +. liquidation_fee;
        liquidated = true;
      }
