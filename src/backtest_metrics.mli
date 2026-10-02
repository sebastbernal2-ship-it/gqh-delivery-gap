(** Summary metrics for a snapshot backtest. *)

type summary = {
  initial_equity : float;
  final_equity : float;
  total_return : float;
  max_drawdown : float;
  turnover : float;
  fees : float;
  funding_paid : float;
  trade_count : int;
}

val summarize : L2_backtest.result -> summary
