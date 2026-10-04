type report = {
  path : string;
  rows : int;
  states : int;
  gaps : int;
  seconds : float;
  peak_heap_bytes : int;
  final_update_id : int64;
  final_bid : string;
  final_ask : string;
}

let usage () =
  prerr_endline
    "usage: binance_replay_benchmark SYMBOL PRICE_TICK QUANTITY_STEP NORMALIZED_JSONL ...";
  exit 2

let option_value = function Some value -> value | None -> "none"

let top_level levels =
  match levels with
  | [] -> "none"
  | level :: _ -> level.Market_simulator.Binance_l2.price ^ "@"
                   ^ level.Market_simulator.Binance_l2.size

let gaps rows =
  let step (current, bootstrapped, count)
      (row : Market_simulator.Binance_l2.normalized_row) =
    match row.kind with
    | Snapshot_row -> (
        match row.last_update_id with
        | Some last_update_id -> Some last_update_id, false, count
        | None -> current, false, count)
    | Update_row -> (
        match
          (current, row.first_update_id, row.final_update_id,
           row.previous_update_id)
        with
        | None, _, _, _ -> None, false, count
        | Some current, Some first, Some final, Some previous
          when row.applied ->
            let next_id = Int64.add current 1L in
            let contiguous =
              previous = current
              || ((not bootstrapped) && first <= next_id && next_id <= final)
            in
            Some final, true, if contiguous then count else count + 1
        | _ -> current, bootstrapped, count)
  in
  let _, _, count = List.fold_left step (None, false, 0) rows in
  count

let heap_bytes () =
  let stat = Gc.stat () in
  stat.Gc.top_heap_words * (Sys.word_size / 8)

let run_file instrument path =
  let started = Unix.gettimeofday () in
  match
    Market_simulator.Binance_l2.parse_normalized_file_with_instrument instrument path
  with
  | Error error -> Error (Printf.sprintf "%s: %s" path error)
  | Ok rows -> (
      match Market_simulator.Binance_l2.replay_normalized ~instrument rows with
      | Error error -> Error (Printf.sprintf "%s: %s" path error)
      | Ok states -> (
          match List.rev states with
          | [] -> Error (Printf.sprintf "%s: no applied rows" path)
          | final_state :: _ ->
              Ok
                {
                  path;
                  rows = List.length rows;
                  states = List.length states;
                  gaps = gaps rows;
                  seconds = Unix.gettimeofday () -. started;
                  peak_heap_bytes = heap_bytes ();
                  final_update_id = final_state.last_update_id;
                  final_bid = top_level final_state.bids;
                  final_ask = top_level final_state.asks;
                }))

let print_report report =
  let rows_per_second =
    if report.seconds = 0.0 then infinity
    else float_of_int report.rows /. report.seconds
  in
  Printf.printf
    "fixture=%s rows=%d states=%d rows_per_second=%.0f seconds=%.3f \
     peak_heap_bytes=%d gaps=%d final_update_id=%Ld final_bid=%s final_ask=%s\n"
    report.path report.rows report.states rows_per_second report.seconds
    report.peak_heap_bytes report.gaps report.final_update_id report.final_bid
    report.final_ask

let () =
  match Array.to_list Sys.argv with
  | _ :: symbol :: price_step :: quantity_step :: paths -> (
      match
        Market_simulator.Binance_units.instrument ~symbol ~price_step
          ~quantity_step
      with
      | Error error -> prerr_endline error; exit 2
      | Ok instrument ->
          let rec loop total_rows total_states total_seconds total_gaps max_heap = function
            | [] ->
                let rows_per_second =
                  if total_seconds = 0.0 then infinity
                  else float_of_int total_rows /. total_seconds
                in
                Printf.printf
                  "total_rows=%d total_states=%d rows_per_second=%.0f seconds=%.3f total_gaps=%d peak_heap_bytes=%d\n"
                  total_rows total_states rows_per_second total_seconds
                  total_gaps max_heap
            | path :: rest -> (
                match run_file instrument path with
                | Error error -> prerr_endline error; exit 1
                | Ok report ->
                    print_report report;
                    loop (total_rows + report.rows)
                      (total_states + report.states)
                      (total_seconds +. report.seconds)
                      (total_gaps + report.gaps)
                      (max max_heap report.peak_heap_bytes) rest)
          in
          if paths = [] then usage ()
          else loop 0 0 0.0 0 0 paths)
  | _ -> usage ()
