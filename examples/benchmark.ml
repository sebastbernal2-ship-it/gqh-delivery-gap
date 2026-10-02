(** Benchmarking the market simulator.

    Runs multiple iterations with a warmup phase and reports min/max/mean
    timing. Uses Unix.gettimeofday for monotonic wall-clock timing. *)

open Market_simulator.Market_types
open Market_simulator.Side

let timestamp () = Unix.gettimeofday ()

let fmt_throughput (n : int) (secs : float) : string =
  if secs > 0.0 then Printf.sprintf "%.0f events/sec" (float n /. secs)
  else "N/A"

let fmt_us (secs : float) (n : int) : string =
  if n > 0 then Printf.sprintf "%.3f us" (secs /. float n *. 1e6) else "N/A"

(** Run a benchmark iteration, returning elapsed seconds. *)
let run_iteration (event_groups : event list list) : float =
  let t0 = timestamp () in
  List.iter
    (fun events ->
      let book = Market_simulator.Order_book.create () in
      List.iter
        (fun ev -> ignore (Market_simulator.Order_book.apply_replay book ev))
        events)
    event_groups;
  timestamp () -. t0

(** Run a snapshot/stats benchmark iteration, returning elapsed seconds. *)
let run_snapshot_iteration (book : Market_simulator.Order_book.t) (count : int)
    : float =
  let t0 = timestamp () in
  for _ = 1 to count do
    ignore (Market_simulator.Order_book.get_snapshot book);
    ignore (Market_simulator.Order_book.get_stats book)
  done;
  timestamp () -. t0

let run_benchmark () =
  Printf.printf "\n=== Market Simulator Benchmarks ===\n\n";

  (* Setup: generate events *)
  Printf.printf "Setup: generating events...\n%!";
  let config =
    {
      Market_simulator.Market_data.default_config with
      symbols = [ "AAPL"; "MSFT"; "GOOGL" ];
      duration_s = 1000.0;
      speed = 10.0;
      rng_seed = Some 42;
    }
  in
  let feed = Market_simulator.Market_data.generate_feed config in
  let event_groups =
    Market_simulator.Market_data.group_by_symbol feed |> List.map snd
  in
  let events = List.concat event_groups in
  let n = List.length events in
  Printf.printf "  %d events generated across %d symbols\n\n%!" n
    (List.length event_groups);

  (* 1. Warmup: process events once to prime caches *)
  Printf.printf "1. Warmup phase...\n%!";
  List.iter
    (fun events ->
      let book = Market_simulator.Order_book.create () in
      List.iter
        (fun ev -> ignore (Market_simulator.Order_book.apply_replay book ev))
        events)
    event_groups;
  Printf.printf "   Done (cold start, results discarded)\n\n%!";

  (* 2. Throughput benchmark: 5 iterations, report min/max/mean *)
  let iterations = 5 in
  Printf.printf "2. Order book throughput (%d iterations)...\n%!" iterations;
  let times = Array.init iterations (fun _ -> run_iteration event_groups) in
  let min_t = Array.fold_left min Float.max_float times in
  let max_t = Array.fold_left max 0.0 times in
  let mean_t = Array.fold_left ( +. ) 0.0 times /. float iterations in
  Printf.printf "   Events: %d per iteration\n" n;
  Printf.printf "   Min: %.3fs (%s)\n" min_t (fmt_throughput n min_t);
  Printf.printf "   Max: %.3fs (%s)\n" max_t (fmt_throughput n max_t);
  Printf.printf "   Mean: %.3fs (%s)\n" mean_t (fmt_throughput n mean_t);
  Printf.printf "   Stddev: %.3fs\n%!"
    (sqrt
       (Array.fold_left (fun acc t -> acc +. ((t -. mean_t) ** 2.0)) 0.0 times
       /. float iterations));

  (* 3. Snapshot + stats retrieval benchmark *)
  let snap_count = 1000000 in
  (* Build a populated book for snapshot benchmarks. *)
  let book = Market_simulator.Order_book.create () in
  let first_group = match event_groups with group :: _ -> group | [] -> [] in
  let resting_events = List.filter (fun ev -> ev.action = Add) first_group in
  List.iter
    (fun ev -> ignore (Market_simulator.Order_book.apply_replay book ev))
    resting_events;
  Printf.printf "\n3. Snapshot + stats retrieval (%d iterations of %d)...\n%!"
    iterations snap_count;
  let snap_times =
    Array.init iterations (fun _ -> run_snapshot_iteration book snap_count)
  in
  let snap_min = Array.fold_left min Float.max_float snap_times in
  let snap_max = Array.fold_left max 0.0 snap_times in
  let snap_mean = Array.fold_left ( +. ) 0.0 snap_times /. float iterations in
  Printf.printf "   Min: %.3fs (%s each)\n" snap_min
    (fmt_us snap_min snap_count);
  Printf.printf "   Max: %.3fs (%s each)\n" snap_max
    (fmt_us snap_max snap_count);
  Printf.printf "   Mean: %.3fs (%s each)\n" snap_mean
    (fmt_us snap_mean snap_count);

  (* 4. Final book state summary *)
  let snap = Market_simulator.Order_book.get_snapshot book in
  let stats = Market_simulator.Order_book.get_stats book in
  Printf.printf "\n4. Final book state:\n";
  Printf.printf "   Bids: %d levels, Asks: %d levels, Orders: %d\n"
    (List.length snap.bids) (List.length snap.asks)
    (Market_simulator.Order_book.order_count book);
  let spread =
    match stats.spread with
    | Some s -> Market_simulator.Price.to_string s
    | None -> "N/A"
  in
  let mid =
    match stats.mid_price with
    | Some m -> Market_simulator.Price.to_string m
    | None -> "N/A"
  in
  Printf.printf "   Spread: %s  Mid: %s\n%!" spread mid;

  Printf.printf "\n=== Benchmarks Complete ===\n%!"

let () = run_benchmark ()
