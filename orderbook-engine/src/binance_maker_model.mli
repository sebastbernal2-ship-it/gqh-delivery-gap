(** Bounds for maker fills inferred from aggregated Binance L2 and trades. *)

type side = Buy | Sell

type estimate = {
  initial_queue_ahead : float;
  pessimistic_filled : float;
  optimistic_filled : float;
  pessimistic_remaining : float;
  optimistic_remaining : float;
}

val estimate :
  side:side ->
  price:float ->
  size:float ->
  placed_at:Timestamp.t ->
  states:Binance_l2.state list ->
  trades:Binance_trades.trade list ->
  estimate
(**
    Estimate maker fills without claiming FIFO accuracy.

    The pessimistic bound uses only aggressive public trades.
    The optimistic bound also treats visible level reductions as queue
    depletion, while avoiding double counting trades and book reductions.
*)
