(** Run a small visible-depth imbalance backtest over a Hugging Face sample. *)

let sum_depth levels count =
  levels
  |> Market_simulator.List_utils.take count
  |> List.fold_left
       (fun total (level : Market_simulator.Hf_l2.level) ->
         total +. level.cumulative_size)
       0.0

let () =
  if Array.length Sys.argv <> 2 then begin
    Printf.eprintf "usage: hf_l2_backtest <l2.csv>\n";
    exit 2
  end;
  match Market_simulator.Hf_l2.parse_csv Sys.argv.(1) with
  | Error message ->
      Printf.eprintf "parse error: %s\n" message;
      exit 1
  | Ok snapshots ->
      let signals = ref 0 in
      let strategy (portfolio : Market_simulator.L2_backtest.portfolio)
          (snapshot : Market_simulator.Hf_l2.snapshot) =
        let bid_depth = sum_depth snapshot.bids 5 in
        let ask_depth = sum_depth snapshot.asks 5 in
        let total_depth = bid_depth +. ask_depth in
        let imbalance =
          if total_depth > 0.0 then (bid_depth -. ask_depth) /. total_depth
          else 0.0
        in
        if imbalance > 0.20 && portfolio.position < 0.05 then begin
          incr signals;
          [
            {
              Market_simulator.L2_backtest.side =
                Market_simulator.L2_execution.Buy;
              size = 0.01;
              limit_price = None;
            };
          ]
        end
        else if imbalance < -0.20 && portfolio.position > -0.05 then begin
          incr signals;
          [
            {
              Market_simulator.L2_backtest.side =
                Market_simulator.L2_execution.Sell;
              size = 0.01;
              limit_price = None;
            };
          ]
        end
        else []
      in
      let result =
        Market_simulator.L2_backtest.run ~initial_cash:10_000.0 ~fee_bps:5.0
          ~latency_snapshots:1 strategy snapshots
      in
      let final = result.final_portfolio in
      let summary = Market_simulator.Backtest_metrics.summarize result in
      Printf.printf
        "snapshots=%d signals=%d trades=%d fees=%.6f funding=%.6f \
         position=%.6f cash=%.6f equity=%.6f return=%.6f max_drawdown=%.6f \
         turnover=%.6f\n"
        (List.length snapshots) !signals final.trade_count final.fees
        final.funding_paid final.position final.cash final.equity
        summary.total_return summary.max_drawdown summary.turnover
