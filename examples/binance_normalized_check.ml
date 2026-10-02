let usage () =
  prerr_endline
    "usage: binance_normalized_check [--json-report] SYMBOL PRICE_TICK QUANTITY_STEP NORMALIZED_JSONL";
  exit 2

let () =
  let args = Array.to_list Sys.argv |> List.tl in
  let json_report, args =
    match args with
    | "--json-report" :: rest -> true, rest
    | rest -> false, rest
  in
  match args with
  | [ symbol; price_step; quantity_step; path ] -> (
      match
        Market_simulator.Binance_units.instrument ~symbol ~price_step
          ~quantity_step
      with
      | Error error ->
          prerr_endline error;
          exit 2
      | Ok instrument -> (
          match
            Market_simulator.Binance_l2.parse_normalized_file_with_instrument
              instrument path
          with
          | Error error ->
              prerr_endline error;
              exit 1
          | Ok rows -> (
              match
                Market_simulator.Binance_l2.replay_normalized ~instrument rows
              with
              | Error error ->
                  prerr_endline error;
                  exit 1
              | Ok [] ->
                  prerr_endline "no applied Binance normalized rows";
                  exit 1
              | Ok states ->
                  let final_state = List.hd (List.rev states) in
                  if json_report then
                    print_endline
                      (Yojson.Safe.to_string
                         (`Assoc
                           [ ("rows", `Int (List.length rows));
                             ("states", `Int (List.length states));
                             ("symbol", `String symbol);
                             ( "final_update_id",
                               `Intlit (Int64.to_string final_state.last_update_id) );
                             ("bids", `Int (List.length final_state.bids));
                             ("asks", `Int (List.length final_state.asks)) ]))
                  else
                    Printf.printf
                      "rows=%d states=%d symbol=%s final_update_id=%Ld bids=%d asks=%d\n"
                      (List.length rows) (List.length states) symbol
                      final_state.last_update_id
                      (List.length final_state.bids)
                      (List.length final_state.asks))))
  | _ -> usage ()
