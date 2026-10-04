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

let summarize (result : L2_backtest.result) =
  let final_equity = result.final_portfolio.equity in
  let total_return =
    if result.initial_cash = 0.0 then 0.0
    else (final_equity -. result.initial_cash) /. result.initial_cash
  in
  let _, max_drawdown =
    List.fold_left
      (fun (peak, largest) (point : L2_backtest.point) ->
        let peak = max peak point.equity in
        let drawdown =
          if peak <= 0.0 then 0.0 else (peak -. point.equity) /. peak
        in
        (peak, max largest drawdown))
      (result.initial_cash, 0.0) result.curve
  in
  let turnover =
    List.fold_left
      (fun total (trade : L2_backtest.trade) ->
        total +. (trade.price *. trade.size))
      0.0 result.trades
  in
  {
    initial_equity = result.initial_cash;
    final_equity;
    total_return;
    max_drawdown;
    turnover;
    fees = result.final_portfolio.fees;
    funding_paid = result.final_portfolio.funding_paid;
    trade_count = result.final_portfolio.trade_count;
  }
