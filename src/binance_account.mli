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

val make_config :
  leverage:float ->
  maintenance_margin_rate:float ->
  maker_fee_bps:float ->
  taker_fee_bps:float ->
  ?liquidation_fee_bps:float ->
  unit -> config

val empty_state : collateral:float -> state
val submit_order :
  config:config ->
  state:state ->
  id:string ->
  side:side ->
  quantity:float ->
  ?limit_price:float ->
  ?reduce_only:bool ->
  ?post_only:bool ->
  ?tif:tif ->
  unit ->
  (order, string) result

val apply_fill :
  config:config ->
  liquidity ->
  price:float ->
  quantity:float ->
  order ->
  state ->
  (order * state, string) result

val cancel : order -> order
val finalize : order -> order
val apply_funding : mark:float -> rate:float -> state -> state
val equity : mark:float -> state -> float
val maintenance_margin : mark:float -> config -> state -> float
val liquidation_price : config -> state -> float option
val is_liquidated : mark:float -> config -> state -> bool
val liquidate : mark:float -> config -> state -> (state, string) result
