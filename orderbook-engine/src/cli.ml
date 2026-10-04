(** CLI binary for the market simulator.

    Commands: msim run — replay market data through the order book msim generate
    — generate sample market data CSV msim serve — run the WebSocket server with
    live data msim query — bitemporal query on a replay log msim info — display
    book info from a CSV *)

(** Helper: count occurrences in a list. *)

open Market_simulator.Market_types
open Market_simulator.Side
open Lwt.Infix

(** Generate subcommand. *)
let generate_cmd =
  let open Cmdliner in
  let output =
    Arg.(
      value
      & opt string "market_data.csv"
      & info [ "o" ] ~doc:"Output CSV file path")
  in
  let events =
    Arg.(
      value & opt int 1000 & info [ "n" ] ~doc:"Number of events to generate")
  in
  let symbols =
    Arg.(
      value
      & opt string "AAPL,MSFT,GOOGL"
      & info [ "s" ] ~doc:"Symbols (comma-separated)")
  in
  let seed =
    Arg.(value & opt (some int) None & info [ "seed" ] ~doc:"Random seed")
  in
  let cmd =
    Term.(
      const (fun output events symbols seed ->
          let syms = String.split_on_char ',' symbols in
          let config =
            {
              Market_simulator.Market_data.symbols = syms;
              start_time = Market_simulator.Timestamp.now ();
              speed = 10.0;
              volatility = 0.02;
              base_spread = 0.01;
              duration_s = float events /. 10.0;
              max_orders = 100;
              rng_seed = seed;
            }
          in
          let evts = Market_simulator.Market_data.generate config in
          match Market_simulator.Market_data.write_csv output evts with
          | Ok () ->
              Printf.printf "Generated %d events -> %s\n" (List.length evts)
                output
          | Error e -> Printf.eprintf "Error: %s\n%!" e)
      $ output $ events $ symbols $ seed)
  in
  let info = Cmd.info "generate" ~doc:"Generate sample market data CSV" in
  Cmd.v info cmd

(** Run subcommand: replay events through the order book. *)
let run_cmd =
  let open Cmdliner in
  let input =
    Arg.(
      value
      & opt (some string) None
      & info [ "i"; "input" ]
          ~doc:"CSV input file (omit to generate random data)")
  in
  let count =
    Arg.(
      value
      & opt (some int) None
      & info [ "n"; "count" ]
          ~doc:"Number of events to generate (when no input file)")
  in
  let speed =
    Arg.(
      value
      & opt (some float) None
      & info [ "speed" ] ~doc:"Replay speed multiplier")
  in
  let cmd =
    Term.(
      const (fun input count speed ->
          let events =
            match input with
            | Some path -> (
                match Market_simulator.Market_data.parse_csv path with
                | Ok evts -> evts
                | Error e ->
                    Printf.eprintf "Error: %s\n%!" e;
                    Stdlib.exit 1)
            | None ->
                let n = match count with Some c -> c | None -> 1000 in
                let config =
                  {
                    Market_simulator.Market_data.default_config with
                    duration_s = float n /. 10.0;
                    rng_seed = Some 42;
                  }
                in
                Market_simulator.Market_data.generate config
          in
          Printf.printf "Loaded %d events\n" (List.length events);
          let book = Market_simulator.Order_book.create () in
          let loop = Market_simulator.Event_loop.create book events in
          (match speed with
          | Some s -> Market_simulator.Event_loop.set_speed loop s
          | None -> ());
          let _metrics_collector = Market_simulator.Metrics.create book in
          Market_simulator.Event_loop.add_handler loop (fun ev ->
              match ev with
              | BookSnapshot snap ->
                  let stats = Market_simulator.Order_book.get_stats book in
                  let spread_s =
                    match stats.spread with
                    | Some s -> Market_simulator.Price.to_string s
                    | None -> "N/A"
                  in
                  let mid_s =
                    match stats.mid_price with
                    | Some p -> Market_simulator.Price.to_string p
                    | None -> "N/A"
                  in
                  Printf.printf
                    "\rEvents: %d | Orders: %d | Bids: %d | Asks: %d | Spread: \
                     %s | Mid: %s | Top Bid: %s | Top Ask: %s%!"
                    (fst (Market_simulator.Event_loop.progress loop))
                    (Market_simulator.Order_book.order_count book)
                    (List.length snap.bids) (List.length snap.asks) spread_s
                    mid_s
                    (match snap.bids with
                    | b :: _ -> Market_simulator.Price.to_string b.price
                    | _ -> "N/A")
                    (match snap.asks with
                    | a :: _ -> Market_simulator.Price.to_string a.price
                    | _ -> "N/A");
                  Lwt.return ()
              | _ -> Lwt.return ());
          Lwt_main.run (Market_simulator.Event_loop.run_fast loop);
          Printf.printf "\n\n=== Final Book State ===\n";
          let snap = Market_simulator.Order_book.get_snapshot book in
          Printf.printf "Bids:\n";
          List.iter
            (fun l ->
              Printf.printf "  %s x %d (%d orders)\n"
                (Market_simulator.Price.to_string l.price)
                (Market_simulator.Size.to_int l.total_size)
                l.order_count)
            snap.bids;
          Printf.printf "Asks:\n";
          List.iter
            (fun l ->
              Printf.printf "  %s x %d (%d orders)\n"
                (Market_simulator.Price.to_string l.price)
                (Market_simulator.Size.to_int l.total_size)
                l.order_count)
            snap.asks;
          let stats = Market_simulator.Order_book.get_stats book in
          let spread_s =
            match stats.spread with
            | Some s -> Market_simulator.Price.to_string s
            | None -> "N/A"
          in
          let mid_s =
            match stats.mid_price with
            | Some p -> Market_simulator.Price.to_string p
            | None -> "N/A"
          in
          Printf.printf "Spread: %s  Mid: %s\n" spread_s mid_s;
          Printf.printf "Total events processed: %d\n"
            (fst (Market_simulator.Event_loop.progress loop)))
      $ input $ count $ speed)
  in
  let info = Cmd.info "run" ~doc:"Replay market data through the order book" in
  Cmd.v info cmd

(** Serve subcommand: run WebSocket server with live data. *)
let serve_cmd =
  let open Cmdliner in
  let port =
    Arg.(
      value & opt int 8080 & info [ "p"; "port" ] ~doc:"WebSocket server port")
  in
  let input =
    Arg.(
      value
      & opt (some string) None
      & info [ "i"; "input" ]
          ~doc:"CSV input file (omit to generate random data)")
  in
  let count =
    Arg.(
      value
      & opt (some int) None
      & info [ "n"; "count" ]
          ~doc:"Number of events to generate (when no input file)")
  in
  let cmd =
    Term.(
      const (fun port input count ->
          let events =
            match input with
            | Some path -> (
                match Market_simulator.Market_data.parse_csv path with
                | Ok evts -> evts
                | Error e ->
                    Printf.eprintf "Error: %s\n%!" e;
                    Stdlib.exit 1)
            | None ->
                let n = match count with Some c -> c | None -> 10000 in
                let config =
                  {
                    Market_simulator.Market_data.default_config with
                    duration_s = float n /. 10.0;
                    rng_seed = Some 42;
                  }
                in
                Market_simulator.Market_data.generate config
          in
          Printf.printf "Loaded %d events\n" (List.length events);
          let book = Market_simulator.Order_book.create () in
          let ws_server = Market_simulator.Websocket_server.create () in
          let loop = Market_simulator.Event_loop.create book events in
          Market_simulator.Event_loop.add_handler loop
            (Market_simulator.Websocket_server.make_broadcast_handler ws_server);
          Logs.set_level (Some Logs.Info);
          Logs.set_reporter (Logs.format_reporter ());
          Lwt_main.run
            ( Market_simulator.Websocket_server.start ws_server port
            >>= fun () ->
              Printf.eprintf "WebSocket server on ws://localhost:%d\n" port;
              Printf.eprintf "Replaying %d events...\n" (List.length events);
              Market_simulator.Event_loop.run loop >>= fun () ->
              Printf.eprintf "\nDone. Press Ctrl-C to stop.\n";
              fst (Lwt.wait ()) ))
      $ port $ input $ count)
  in
  let info = Cmd.info "serve" ~doc:"Run the WebSocket server with live data" in
  Cmd.v info cmd

(** Info subcommand: display book info from a CSV. *)
let info_cmd =
  let open Cmdliner in
  let input =
    Arg.(required & pos 0 (some string) None & info [] ~doc:"CSV input file")
  in
  let cmd =
    Term.(
      const (fun input ->
          let events =
            match Market_simulator.Market_data.parse_csv input with
            | Ok evts -> evts
            | Error e ->
                Printf.eprintf "Error: %s\n%!" e;
                Stdlib.exit 1
          in
          let book = Market_simulator.Order_book.create () in
          let sides = List.map (fun (e : event) -> e.side) events in
          let bid_count = List.length (List.filter (fun s -> s = Bid) sides) in
          let ask_count = List.length (List.filter (fun s -> s = Ask) sides) in
          let actions = List.map (fun (e : event) -> e.action) events in
          let add_c = List.length (List.filter (fun a -> a = Add) actions) in
          let amend_c =
            List.length (List.filter (fun a -> a = Amend) actions)
          in
          let cancel_c =
            List.length (List.filter (fun a -> a = Cancel) actions)
          in
          let exec_c =
            List.length (List.filter (fun a -> a = Execute) actions)
          in
          let price_range =
            if events <> [] then
              let prices =
                List.map
                  (fun (e : event) -> Market_simulator.Price.to_int e.price)
                  events
              in
              let min_p = List.fold_left min (List.hd prices) prices in
              let max_p = List.fold_left max (List.hd prices) prices in
              Some
                ( Market_simulator.Price.of_int min_p,
                  Market_simulator.Price.of_int max_p )
            else None
          in
          Printf.printf "=== Market Data Summary ===\n";
          Printf.printf "File: %s\n" input;
          Printf.printf "Events: %d\n" (List.length events);
          Printf.printf "  Add: %d  Amend: %d  Cancel: %d  Execute: %d\n" add_c
            amend_c cancel_c exec_c;
          Printf.printf "  Bids: %d  Asks: %d\n" bid_count ask_count;
          (match price_range with
          | Some (min_p, max_p) ->
              Printf.printf "  Price range: %s - %s\n"
                (Market_simulator.Price.to_string min_p)
                (Market_simulator.Price.to_string max_p)
          | None -> ());
          List.iter
            (fun e -> Market_simulator.Order_book.apply_exn book e |> ignore)
            events;
          let snap = Market_simulator.Order_book.get_snapshot book in
          Printf.printf "\n=== Final Book State ===\n";
          Printf.printf "Bids: %d levels\n" (List.length snap.bids);
          List.iter
            (fun l ->
              Printf.printf "  %s x %d (%d orders)\n"
                (Market_simulator.Price.to_string l.price)
                (Market_simulator.Size.to_int l.total_size)
                l.order_count)
            (Market_simulator.List_utils.take 5 snap.bids);
          Printf.printf "Asks: %d levels\n" (List.length snap.asks);
          List.iter
            (fun l ->
              Printf.printf "  %s x %d (%d orders)\n"
                (Market_simulator.Price.to_string l.price)
                (Market_simulator.Size.to_int l.total_size)
                l.order_count)
            (Market_simulator.List_utils.take 5 snap.asks);
          let stats = Market_simulator.Order_book.get_stats book in
          let spread_s =
            match stats.spread with
            | Some s -> Market_simulator.Price.to_string s
            | None -> "N/A"
          in
          let mid_s =
            match stats.mid_price with
            | Some p -> Market_simulator.Price.to_string p
            | None -> "N/A"
          in
          Printf.printf "Spread: %s  Mid: %s\n" spread_s mid_s;
          Printf.printf "Active orders: %d\n"
            (Market_simulator.Order_book.order_count book))
      $ input)
  in
  let info = Cmd.info "info" ~doc:"Display book info from a CSV" in
  Cmd.v info cmd

(** Query subcommand: bitemporal query. *)
let query_cmd =
  let open Cmdliner in
  let input =
    Arg.(required & pos 0 (some string) None & info [] ~doc:"CSV input file")
  in
  let valid_at =
    Arg.(
      value
      & opt (some string) None
      & info [ "valid-at" ] ~doc:"Valid-time query (RFC3339)")
  in
  let tx_at =
    Arg.(
      value
      & opt (some string) None
      & info [ "tx-at" ] ~doc:"Transaction-time query (RFC3339)")
  in
  let order_id =
    Arg.(
      value
      & opt (some string) None
      & info [ "order-id" ] ~doc:"Filter by order ID (uses indexed lookup)")
  in
  let cmd =
    Term.(
      const (fun input valid_at tx_at order_id ->
          let events =
            match Market_simulator.Market_data.parse_csv input with
            | Ok evts -> evts
            | Error e ->
                Printf.eprintf "Error: %s\n%!" e;
                Stdlib.exit 1
          in
          let bf_events = Market_simulator.Bitemporal.of_events events in
          let valid_time =
            match valid_at with
            | Some s -> (
                match Market_simulator.Timestamp.of_string s with
                | Ok t -> t
                | _ -> Market_simulator.Timestamp.now ())
            | None -> Market_simulator.Timestamp.now ()
          in
          let tx_time =
            match tx_at with
            | Some s -> (
                match Market_simulator.Timestamp.of_string s with
                | Ok t -> t
                | _ -> Market_simulator.Timestamp.now ())
            | None -> Market_simulator.Timestamp.now ()
          in
          Printf.printf "=== Bitemporal Query ===\n";
          Printf.printf "Valid time: %s\n"
            (Market_simulator.Timestamp.to_string valid_time);
          Printf.printf "Transaction time: %s\n"
            (Market_simulator.Timestamp.to_string tx_time);
          let filtered =
            match order_id with
            | Some oid ->
                let idx =
                  Market_simulator.Bitemporal.index_by_order_id bf_events
                in
                Market_simulator.Bitemporal.history_of_order idx oid
            | None ->
                Market_simulator.Bitemporal.filter_sequenced bf_events
                  valid_time tx_time
          in
          Printf.printf "Events matching: %d\n" (List.length filtered);
          List.iter
            (fun (ev : event) ->
              let side_s = match ev.side with Bid -> "BID" | Ask -> "ASK" in
              let action_s =
                match ev.action with
                | Add -> "ADD"
                | Amend -> "AMEND"
                | Cancel -> "CANCEL"
                | Execute -> "EXEC"
                | Replace old_id -> "REPLACE(" ^ old_id ^ ")"
                | Control name -> "CONTROL(" ^ name ^ ")"
              in
              Printf.printf "  %s %s %s @ %s x %s (order: %s)\n" action_s side_s
                (Market_simulator.Price.to_string ev.price)
                (Market_simulator.Size.to_string ev.size)
                (Market_simulator.Timestamp.to_string ev.timestamp)
                ev.order_id)
            filtered)
      $ input $ valid_at $ tx_at $ order_id)
  in
  let info = Cmd.info "query" ~doc:"Bitemporal query on a replay log" in
  Cmd.v info cmd

(** Main CLI. *)
let () =
  let open Cmdliner in
  let default_cmd =
    Cmd.group
      (Cmd.info "msim" ~version:"0.1.0"
         ~doc:"Incremental Market-Simulator: A Bitemporal Order Book in OCaml")
      [ generate_cmd; run_cmd; serve_cmd; info_cmd; query_cmd ]
  in
  Stdlib.exit (Cmd.eval default_cmd)
