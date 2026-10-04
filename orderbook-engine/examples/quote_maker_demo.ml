(** Quote a resting bid through the execution loop and report the outcome.

    usage: quote_maker_demo MODE DEPTH.jsonl [TRADES.jsonl] [DECISION_MS] [CANCEL_MS]

    MODE is conservative, heuristic, or optimistic. The strategy places one
    post-only bid at the touch on the first book it sees, and the loop models
    decision and cancel latency on the replay clock. The report states the
    mode, the latency, the fills, the account, and the book checksum. *)

module A = Market_simulator.Exec_account
module B = Market_simulator.L2_book
module E = Market_simulator.Exec_event
module F = Market_simulator.Exec_fills
module L = Market_simulator.Exec_loop
module T = Market_simulator.Timestamp

let usage () =
  prerr_endline
    "usage: quote_maker_demo MODE DEPTH.jsonl [TRADES.jsonl] [DECISION_MS] [CANCEL_MS]";
  exit 2

let parse_mode = function
  | "conservative" -> F.Conservative
  | "heuristic" -> F.Heuristic
  | "optimistic" -> F.Optimistic
  | other -> invalid_arg ("unknown mode: " ^ other)

let read_events path =
  let ic = open_in path in
  let events = ref [] in
  let errors = ref 0 in
  (try
     while true do
       let line = input_line ic in
       if String.trim line <> "" then
         match E.of_string line with
         | Ok event -> events := event :: !events
         | Error _ -> incr errors
     done
   with End_of_file -> close_in ic);
  (List.rev !events, !errors)

let ms_to_ns value = Int64.of_float (value *. 1_000_000.0)

let () =
  let args = Array.to_list Sys.argv |> List.tl in
  match args with
  | mode_text :: depth_path :: rest ->
      let trades_path, rest =
        match rest with
        | path :: tail when Filename.check_suffix path ".jsonl" -> (Some path, tail)
        | tail -> (None, tail)
      in
      let decision_ms, cancel_ms =
        match rest with
        | decision :: cancel :: _ -> (float_of_string decision, float_of_string cancel)
        | decision :: _ -> (float_of_string decision, 0.0)
        | [] -> (0.0, 0.0)
      in
      let mode = parse_mode mode_text in
      let depth_events, depth_errors = read_events depth_path in
      let trade_events, trade_errors =
        match trades_path with
        | Some path -> read_events path
        | None -> ([], 0)
      in
      let events = L.merge_events depth_events trade_events in
      let config =
        A.make_config ~leverage:10 ~maintenance_margin_rate_bps:50
          ~maker_fee_bps:2 ~taker_fee_bps:4 ~liquidation_fee_bps:125 ()
      in
      let latency =
        { L.decision_ns = ms_to_ns decision_ms; cancel_ns = ms_to_ns cancel_ms }
      in
      let placed = ref false in
      let strategy (context : L.context) =
        if !placed then []
        else
          match B.best_bid context.L.book with
          | None -> []
          | Some price_ticks ->
              placed := true;
              [
                L.Submit
                  {
                    A.id = "quote-1";
                    side = E.Buy;
                    price_ticks = Some price_ticks;
                    quantity_units = 100_000L;
                    remaining_units = 100_000L;
                    tif = E.Gtc;
                    reduce_only = false;
                    post_only = true;
                    status = A.New;
                  };
              ]
      in
      let started = Unix.gettimeofday () in
      let report =
        L.run ~mode ~latency ~config ~strategy ~initial_collateral:100_000_000_000L
          ~events
      in
      let seconds = Unix.gettimeofday () -. started in
      Printf.printf
        "mode=%s decision_ms=%.3f cancel_ms=%.3f events=%d depth_events=%d trade_events=%d errors=%d submitted=%d rejected=%d cancelled=%d fills=%d filled_units=%Ld taker_units=%Ld maker_units=%Ld liquidations=%d position=%Ld collateral=%Ld fees=%Ld realized_pnl=%Ld reserved=%Ld best_bid=%s best_ask=%s book_checksum=%s seconds=%.4f\n"
        (F.mode_name mode) decision_ms cancel_ms report.L.events
        (List.length depth_events) (List.length trade_events)
        (depth_errors + trade_errors) report.L.submitted report.L.rejected
        report.L.cancelled report.L.fills report.L.filled_units report.L.taker_units
        report.L.maker_units report.L.liquidations report.L.account.A.position
        report.L.account.A.collateral report.L.account.A.fees
        report.L.account.A.realized_pnl report.L.account.A.reserved_margin
        (match B.best_bid report.L.book with
        | Some price -> Printf.sprintf "%Ld" price
        | None -> "none")
        (match B.best_ask report.L.book with
        | Some price -> Printf.sprintf "%Ld" price
        | None -> "none")
        (B.checksum report.L.book) seconds;
      let uncertainty =
        match mode with
        | F.Conservative ->
            "fills are a lower bound: only aggressive trades past the queue ahead"
        | F.Heuristic ->
            "fills add cancellations ahead, estimated from unexplained level drops"
        | F.Optimistic ->
            "fills are an upper bound: the order is assumed first in the queue"
      in
      Printf.printf "uncertainty=%s\n" uncertainty;
      if depth_errors + trade_errors > 0 then exit 1
  | _ -> usage ()
