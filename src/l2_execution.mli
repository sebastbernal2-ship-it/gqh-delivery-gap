(** Visible-liquidity execution for derived L2 snapshots. *)

type side = Buy | Sell
type fill = { price : float; size : float }

type result = {
  requested : float;
  filled : float;
  remaining : float;
  fills : fill list;
  vwap : float option;
}

val execute : Hf_l2.snapshot -> side -> ?limit_price:float -> float -> result
(** Execute against visible cumulative depth. [limit_price] is [None] for a
    market order. This does not model queue position or latency. *)
