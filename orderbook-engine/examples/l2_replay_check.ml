(** Replay canonical event fixtures into the aggregated L2 book.

    usage: l2_replay_check [--json-report] FIXTURE.jsonl [FIXTURE.jsonl ...]

    Each fixture is replayed with {!L2_book.replay}: snapshots seed the book,
    updates apply absolute level sizes, and the depth chain decides acceptance.
    The report lists the final best bid and ask, level counts, totals, and a
    deterministic book checksum. The exit status is nonzero when a fixture has
    parse errors or when the chain reports a gap. *)

module B = Market_simulator.L2_book
module E = Market_simulator.Exec_event
module Timestamp = Market_simulator.Timestamp

let usage () =
  prerr_endline "usage: l2_replay_check [--json-report] FIXTURE.jsonl ...";
  exit 2

let option_int64 = function
  | None -> `Null
  | Some value -> `Intlit (Int64.to_string value)

let read_events path =
  let ic = open_in path in
  let events = ref [] in
  let lines = ref 0 in
  let errors = ref [] in
  (try
     while true do
       let line = input_line ic in
       incr lines;
       if String.trim line <> "" then
         match E.of_string line with
         | Ok event -> events := event :: !events
         | Error message ->
             if List.length !errors < 5 then
               errors := Printf.sprintf "line %d: %s" !lines message :: !errors
     done
   with End_of_file -> close_in ic);
  (List.rev !events, !lines, List.rev !errors)

let report_fixture path json_report =
  let events, lines, errors = read_events path in
  let started = Unix.gettimeofday () in
  let result = B.replay events in
  let seconds = Unix.gettimeofday () -. started in
  let rows = List.length events in
  let depth_events =
    result.B.applied + result.B.superseded + result.B.gaps
    + result.B.unchecked_after_gap
  in
  let ok = errors = [] && result.B.gaps = 0 in
  if json_report then
    print_endline
      (Yojson.Safe.to_string
         (`Assoc
           [
             ("file", `String path);
             ("lines", `Int lines);
             ("rows", `Int rows);
             ("depth_events", `Int depth_events);
             ("snapshots", `Int result.B.snapshots);
             ("applied", `Int result.B.applied);
             ("superseded", `Int result.B.superseded);
             ("pending", `Int result.B.pending_updates);
             ("gaps", `Int result.B.gaps);
             ("unchecked_after_gap", `Int result.B.unchecked_after_gap);
             ("ignored", `Int result.B.ignored_events);
             ("gapped", `Bool result.B.gapped);
             ("best_bid", option_int64 (B.best_bid result.B.book));
             ("best_ask", option_int64 (B.best_ask result.B.book));
             ("bid_levels", `Int (B.level_count result.B.book B.Bid));
             ("ask_levels", `Int (B.level_count result.B.book B.Ask));
             ( "bid_quantity",
               `Intlit (Int64.to_string (B.total_quantity result.B.book B.Bid)) );
             ( "ask_quantity",
               `Intlit (Int64.to_string (B.total_quantity result.B.book B.Ask)) );
             ("checksum", `String (B.checksum result.B.book));
             ("seconds", `Float seconds);
             ("errors", `List (List.map (fun e -> `String e) errors));
           ]))
  else begin
    Printf.printf
      "file=%s rows=%d depth_events=%d applied=%d superseded=%d pending=%d gaps=%d unchecked=%d bid_levels=%d ask_levels=%d bid_qty=%Ld ask_qty=%Ld checksum=%s seconds=%.4f\n"
      path rows depth_events result.B.applied result.B.superseded
      result.B.pending_updates result.B.gaps result.B.unchecked_after_gap
      (B.level_count result.B.book B.Bid)
      (B.level_count result.B.book B.Ask)
      (B.total_quantity result.B.book B.Bid)
      (B.total_quantity result.B.book B.Ask)
      (B.checksum result.B.book) seconds;
    (match B.best_bid result.B.book with
    | Some bid -> Printf.printf "  best_bid=%s\n" (Printf.sprintf "%Ld" bid)
    | None -> print_endline "  best_bid=none");
    (match B.best_ask result.B.book with
    | Some ask -> Printf.printf "  best_ask=%s\n" (Printf.sprintf "%Ld" ask)
    | None -> print_endline "  best_ask=none");
    if B.crossed result.B.book then print_endline "  warning: crossed book";
    List.iter (fun message -> prerr_endline message) errors
  end;
  (ok, rows, seconds)

let () =
  let args = Array.to_list Sys.argv |> List.tl in
  let json_report, paths =
    match args with
    | "--json-report" :: rest -> (true, rest)
    | rest -> (false, rest)
  in
  if paths = [] then usage ();
  let all_ok = ref true in
  let total_rows = ref 0 in
  let total_seconds = ref 0.0 in
  List.iter
    (fun path ->
      if not (Sys.file_exists path) then begin
        prerr_endline ("missing fixture: " ^ path);
        exit 1
      end;
      let ok, rows, seconds = report_fixture path json_report in
      if not ok then all_ok := false;
      total_rows := !total_rows + rows;
      total_seconds := !total_seconds +. seconds)
    paths;
  if List.length paths > 1 then
    Printf.printf "total_rows=%d total_seconds=%.4f rows_per_second=%.0f\n"
      !total_rows !total_seconds
      (if !total_seconds > 0.0 then float !total_rows /. !total_seconds else 0.0);
  ignore Timestamp.to_string;
  if not !all_ok then exit 1
