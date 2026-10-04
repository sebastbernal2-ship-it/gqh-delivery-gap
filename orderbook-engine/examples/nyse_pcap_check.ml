let () =
  match Sys.argv with
  | [| _; path |] -> (
      match Market_simulator.Nyse_capture.read_pcap path with
      | Error error ->
          prerr_endline error;
          exit 1
      | Ok datagrams ->
          let channels =
            Market_simulator.Nyse_capture.group_udp_channels datagrams
          in
          Printf.printf "datagrams=%d channels=%d\n" (List.length datagrams)
            (List.length channels))
  | _ ->
      prerr_endline "usage: nyse_pcap_check PCAP";
      exit 2
