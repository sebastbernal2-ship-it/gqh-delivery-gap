let () =
  match Sys.argv with
  | [| _; path |] -> (
      match
        Market_simulator.Nyse_binary.parse_file ~trading_date:"2022-02-23"
          Market_simulator.Nyse_binary.default_config path
      with
      | Ok events -> Printf.printf "parsed_events=%d\n" (List.length events)
      | Error error ->
          prerr_endline error;
          exit 1)
  | _ ->
      prerr_endline "usage: nyse_capture_check FILE";
      exit 2
