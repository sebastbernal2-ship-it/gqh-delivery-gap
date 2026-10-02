let () =
  match Sys.argv with
  | [| _; pcap_path; mapping_path; trading_date |] -> (
      match Market_simulator.Nyse_binary.read_symbol_mapping mapping_path with
      | Error error ->
          prerr_endline error;
          exit 1
      | Ok symbol_mappings -> (
          match Market_simulator.Nyse_capture.read_pcap pcap_path with
          | Error error ->
              prerr_endline error;
              exit 1
          | Ok datagrams ->
              let config =
                {
                  Market_simulator.Nyse_binary.default_config with
                  symbol_mappings;
                }
              in
              let channels =
                Market_simulator.Nyse_capture.group_udp_channels datagrams
              in
              let failures = ref 0 in
              List.iteri
                (fun index (channel : Market_simulator.Nyse_capture.channel) ->
                  let payloads =
                    List.map
                      (fun (datagram : Market_simulator.Nyse_capture.datagram)
                         -> datagram.payload)
                      channel.datagrams
                  in
                  match
                    Market_simulator.Nyse_binary.parse_payloads ~trading_date
                      config payloads
                  with
                  | Ok events ->
                      Printf.printf "channel=%d events=%d\n" index
                        (List.length events)
                  | Error error ->
                      incr failures;
                      Printf.eprintf "channel=%d rejected: %s\n" index error)
                channels;
              if !failures <> 0 then exit 1))
  | _ ->
      prerr_endline "usage: nyse_pcap_replay_check PCAP MAPPING YYYY-MM-DD";
      exit 2
