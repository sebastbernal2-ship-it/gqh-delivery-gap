let received_time = function
  | Market_simulator.Binance_l2.Snapshot snapshot -> snapshot.received_time
  | Market_simulator.Binance_l2.Update update -> update.received_time

let sort_messages messages =
  List.sort
    (fun left right ->
      Market_simulator.Timestamp.compare (received_time left)
        (received_time right))
    messages

let rec parse_pairs pairs = function
  | [] -> Ok (List.rev pairs)
  | updates_path :: snapshot_path :: rest -> (
      match
        ( Market_simulator.Binance_l2.parse_file updates_path,
          Market_simulator.Binance_l2.parse_file snapshot_path )
      with
      | Error error, _ | _, Error error -> Error error
      | Ok updates, Ok snapshots ->
          parse_pairs (sort_messages (updates @ snapshots) :: pairs) rest)
  | _ ->
      Error
        "usage: binance_l2_check SYMBOL UPDATES SNAPSHOT [UPDATES SNAPSHOT ...]"

let rec replay_pairs instrument states = function
  | [] -> Ok states
  | messages :: rest -> (
      match Market_simulator.Binance_l2.replay ~instrument messages with
      | Error error -> Error error
      | Ok day_states -> replay_pairs instrument (states @ day_states) rest)

let measure_snapshots snapshots =
  let rec loop points = function
    | [] -> Ok (List.rev points)
    | snapshot :: rest -> (
        match Market_simulator.L2_metrics.measure snapshot with
        | Error error -> Error error
        | Ok point -> loop (point :: points) rest)
  in
  loop [] snapshots

let () =
  let args = Array.to_list Sys.argv in
  let args = match args with _ :: rest -> rest | [] -> [] in
  match args with
  | symbol :: price_step :: quantity_step :: files -> (
      match
        Market_simulator.Binance_units.instrument ~symbol ~price_step
          ~quantity_step
      with
      | Error error ->
          prerr_endline error;
          exit 2
      | Ok instrument -> (
          match parse_pairs [] files with
      | Error error ->
          prerr_endline error;
          exit 2
      | Ok pairs -> (
          match replay_pairs instrument [] pairs with
          | Error error ->
              prerr_endline error;
              exit 1
          | Ok [] ->
              prerr_endline "no Binance states parsed";
              exit 1
          | Ok states -> (
              match
                Market_simulator.Binance_l2.to_hf_l2 ~instrument ~symbol states
              with
              | Error error ->
                  prerr_endline error;
                  exit 1
              | Ok snapshots -> (
                  match measure_snapshots snapshots with
                  | Error error ->
                      prerr_endline error;
                      exit 1
                  | Ok points ->
                      let summary =
                        Market_simulator.L2_metrics.summarize points
                      in
                      let strategy
                          (portfolio : Market_simulator.L2_backtest.portfolio)
                          _snapshot =
                        if portfolio.trade_count = 0 then
                          [
                            {
                              Market_simulator.L2_backtest.side =
                                Market_simulator.L2_execution.Buy;
                              size = 0.001;
                              limit_price = None;
                            };
                          ]
                        else []
                      in
                      let backtest =
                        Market_simulator.L2_backtest.run ~initial_cash:100_000.0
                          ~fee_bps:4.0 strategy snapshots
                      in
                      let backtest_summary =
                        Market_simulator.Backtest_metrics.summarize backtest
                      in
                      Printf.printf
                        "states=%d final_update_id=%Ld mean_spread_bps=%.6f \
                         mean_imbalance=%.6f benchmark_return=%.6f \
                         benchmark_trades=%d\n"
                        (List.length states)
                        (List.hd (List.rev states)).last_update_id
                        summary.mean_spread_bps summary.mean_imbalance
                        backtest_summary.total_return
                        backtest_summary.trade_count)))))
  | _ ->
      prerr_endline
        "usage: binance_l2_check SYMBOL PRICE_TICK QUANTITY_STEP UPDATES SNAPSHOT [UPDATES SNAPSHOT ...]";
      exit 2
