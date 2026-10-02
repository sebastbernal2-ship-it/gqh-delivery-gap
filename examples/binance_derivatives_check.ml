let parse_liquidations path =
  match Market_simulator.Binance_derivatives.parse_liquidation_file path with
  | Error error ->
      prerr_endline error;
      exit 1
  | Ok liquidations -> liquidations

let () =
  match Sys.argv with
  | [| _; mark_path |] -> (
      match Market_simulator.Binance_derivatives.parse_mark_file mark_path with
      | Error error ->
          prerr_endline error;
          exit 1
      | Ok [] ->
          prerr_endline "no Binance mark-price records parsed";
          exit 1
      | Ok marks ->
          let total_funding =
            List.fold_left
              (fun total
                   (mark : Market_simulator.Binance_derivatives.mark_price) ->
                total +. mark.funding_rate)
              0.0 marks
          in
          Printf.printf "mark_records=%d mean_funding_rate=%.9f\n"
            (List.length marks)
            (total_funding /. float_of_int (List.length marks)))
  | [| _; mark_path; liquidation_path |] -> (
      match Market_simulator.Binance_derivatives.parse_mark_file mark_path with
      | Error error ->
          prerr_endline error;
          exit 1
      | Ok marks ->
          let liquidations = parse_liquidations liquidation_path in
          Printf.printf "mark_records=%d liquidation_records=%d\n"
            (List.length marks) (List.length liquidations))
  | _ ->
      prerr_endline
        "usage: binance_derivatives_check MARK_PRICE_FILE [LIQUIDATION_FILE]";
      exit 2
