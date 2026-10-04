let () =
  match Array.to_list Sys.argv with
  | [ _; symbol; price_step; quantity_step; path ] -> (
      match
        Market_simulator.Binance_units.instrument ~symbol ~price_step
          ~quantity_step
      with
      | Error error ->
          prerr_endline error;
          exit 2
      | Ok instrument -> (
          match
            Market_simulator.Binance_trades.parse_normalized_file_with_instrument
              instrument path
          with
      | Error error ->
          prerr_endline error;
          exit 1
      | Ok [] ->
          prerr_endline "no Binance trade rows";
          exit 1
      | Ok trades ->
          let first = List.hd trades in
          let last = List.hd (List.rev trades) in
          Printf.printf "trades=%d symbol=%s first_id=%Ld last_id=%Ld\n"
            (List.length trades) first.symbol first.trade_id last.trade_id))
  | _ ->
      prerr_endline
        "usage: binance_trades_check SYMBOL PRICE_TICK QUANTITY_STEP NORMALIZED_JSONL";
      exit 2
