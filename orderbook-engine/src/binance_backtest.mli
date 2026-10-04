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

type result = {
  account : Binance_account.state;
  orders : order_result list;
}

type maker_policy = Pessimistic | Optimistic

val run :
  collateral:float ->
  config:Binance_account.config ->
  symbol:string ->
  instrument:Binance_units.instrument ->
  maker_policy:maker_policy ->
  states:Binance_l2.state list ->
  trades:Binance_trades.trade list ->
  orders:order list ->
  (result, string) Stdlib.result
(** Run explicit orders against Binance replay data.

    Taker orders consume the first visible book at or after placement.
    Maker orders use the selected bounded fill estimate. This is not FIFO
    proof because Binance public depth has no order identities.
*)
