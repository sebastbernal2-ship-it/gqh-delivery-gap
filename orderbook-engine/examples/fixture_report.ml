(** Replay a canonical fixture under all three fill modes and print one report.

    usage: fixture_report [--deterministic] DEPTH.jsonl [TRADES.jsonl] [MANIFEST.json] [DECISION_MS] [CANCEL_MS]

    The report carries the fixture provenance from the manifest, the data
    quality counters from a strict book replay, one summary per fill mode with
    the account outcome, and the fill-uncertainty bounds across the modes.
    With --deterministic the timing and heap fields are omitted, so two runs
    over the same fixtures print byte-identical JSON. *)

module A = Market_simulator.Exec_account
module B = Market_simulator.L2_book
module E = Market_simulator.Exec_event
module F = Market_simulator.Exec_fills
module L = Market_simulator.Exec_loop
module G = Market_simulator.Regime
module N = Market_simulator.Naive_backtest
module S = Market_simulator.Exec_strategy
module Timestamp = Market_simulator.Timestamp
module T = Market_simulator.Timestamp

let usage () =
  prerr_endline
    "usage: fixture_report [--deterministic] DEPTH.jsonl [TRADES.jsonl] [MANIFEST.json] [DECISION_MS] [CANCEL_MS]";
  exit 2

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

type summary = {
  mode_name : string;
  submitted : int;
  rejected : int;
  cancelled : int;
  fills : int;
  filled_units : int64;
  taker_units : int64;
  maker_units : int64;
  liquidations : int;
  position : int64;
  collateral : int64;
  fees : int64;
  realized_pnl : int64;
  reserved_margin : int64;
  checksum : string;
  book : B.t;
  blotter : L.fill_record list;
  min_bid_ticks : int64 option;
  max_bid_ticks : int64 option;
  min_ask_ticks : int64 option;
  max_ask_ticks : int64 option;
  seconds : float;
  heap_bytes : int;
}

let json_int64 value = `Intlit (Int64.to_string value)
let option_int64 = function Some value -> json_int64 value | None -> `Null

let summary_json summary =
  `Assoc
    [
      ("mode", `String summary.mode_name);
      ("submitted", `Int summary.submitted);
      ("rejected", `Int summary.rejected);
      ("cancelled", `Int summary.cancelled);
      ("fills", `Int summary.fills);
      ("filled_units", json_int64 summary.filled_units);
      ("taker_units", json_int64 summary.taker_units);
      ("maker_units", json_int64 summary.maker_units);
      ("liquidations", `Int summary.liquidations);
      ("position", json_int64 summary.position);
      ("collateral", json_int64 summary.collateral);
      ("fees", json_int64 summary.fees);
      ("realized_pnl", json_int64 summary.realized_pnl);
      ("reserved_margin", json_int64 summary.reserved_margin);
      ("book_checksum", `String summary.checksum);
      ("book_best_bid", option_int64 (B.best_bid summary.book));
      ("book_best_ask", option_int64 (B.best_ask summary.book));
      ("book_bid_levels", `Int (B.level_count summary.book B.Bid));
      ("book_ask_levels", `Int (B.level_count summary.book B.Ask));
      ("price_range_min_bid", option_int64 summary.min_bid_ticks);
      ("price_range_max_bid", option_int64 summary.max_bid_ticks);
      ("price_range_min_ask", option_int64 summary.min_ask_ticks);
      ("price_range_max_ask", option_int64 summary.max_ask_ticks);
      ("seconds", `Float summary.seconds);
      ("heap_bytes", `Int summary.heap_bytes);
    ]

let () =
  let args = Array.to_list Sys.argv |> List.tl in
  let deterministic, args =
    match args with
    | "--deterministic" :: rest -> (true, rest)
    | rest -> (false, rest)
  in
  if args = [] then usage ();
  let depth_path = List.nth args 0 in
  let optional index =
    if List.length args > index then Some (List.nth args index) else None
  in
  let trades_path =
    match optional 1 with
    | Some path when Filename.check_suffix path ".jsonl" -> Some path
    | _ -> None
  in
  let manifest_path =
    match optional 2 with
    | Some path when Filename.check_suffix path ".json" -> Some path
    | _ -> None
  in
  let decision_ms, cancel_ms =
    let offset = 1 + (match trades_path with Some _ -> 1 | None -> 0) + (match manifest_path with Some _ -> 1 | None -> 0) in
    let value index default =
      match optional (offset + index) with
      | Some text -> float_of_string text
      | None -> default
    in
    (value 0 0.0, value 1 0.0)
  in
  let depth_events, depth_errors = read_events depth_path in
  let trade_events, trade_errors =
    match trades_path with
    | Some path -> read_events path
    | None -> ([], 0)
  in
  let events = L.merge_events depth_events trade_events in
  let features = S.prefetch ~window:64 events in
  let config =
    A.make_config ~leverage:10 ~maintenance_margin_rate_bps:50 ~maker_fee_bps:2
      ~taker_fee_bps:4 ~liquidation_fee_bps:125 ()
  in
  let latency =
    { L.decision_ns = ms_to_ns decision_ms; L.cancel_ns = ms_to_ns cancel_ms }
  in
  let strategy () =
    S.skewed_quote ~features ~size_units:100_000L ~imbalance_floor_bps:4_000
  in
  let run_mode mode =
    let builder = strategy () in
    let started = Unix.gettimeofday () in
    let report =
      L.run ~mode ~latency ~config ~strategy:builder
        ~initial_collateral:100_000_000_000L ~events
    in
    let seconds = Unix.gettimeofday () -. started in
    let heap_bytes = (Gc.quick_stat ()).Gc.heap_words * 8 in
    {
      mode_name = F.mode_name mode;
      submitted = report.L.submitted;
      rejected = report.L.rejected;
      cancelled = report.L.cancelled;
      fills = report.L.fills;
      filled_units = report.L.filled_units;
      taker_units = report.L.taker_units;
      maker_units = report.L.maker_units;
      liquidations = report.L.liquidations;
      position = report.L.account.A.position;
      collateral = report.L.account.A.collateral;
      fees = report.L.account.A.fees;
      realized_pnl = report.L.account.A.realized_pnl;
      reserved_margin = report.L.account.A.reserved_margin;
      checksum = B.checksum report.L.book;
      book = report.L.book;
      blotter = report.L.fills_log;
      min_bid_ticks = report.L.min_bid_ticks;
      max_bid_ticks = report.L.max_bid_ticks;
      min_ask_ticks = report.L.min_ask_ticks;
      max_ask_ticks = report.L.max_ask_ticks;
      seconds = (if deterministic then 0.0 else seconds);
      heap_bytes = (if deterministic then 0 else heap_bytes);
    }
  in
  let summaries =
    List.map run_mode [ F.Conservative; F.Heuristic; F.Optimistic ]
  in
  (* The optimistic baseline the engine exists to refute. *)
  let naive =
    N.run ~config ~strategy:(strategy ())
      ~initial_collateral:100_000_000_000L ~events
  in
  (* Volatility regimes: the threshold comes from the first half of the run,
     and the same rule is then applied to the whole run and to each half, so the
     holdout half shows whether the condition survives. *)
  let event_count = List.length events in
  let travel = G.prefetch ~window_seconds:60.0 events in
  let threshold =
    G.threshold_from ~from:0 ~until:(max 1 (event_count / 2)) travel
  in
  let classified = G.classify_all ~threshold travel in
  let split_time =
    if event_count = 0 then None
    else Some (List.nth events (event_count / 2)).E.receive_time
  in
  let attribution_of blotter =
    List.map
      (fun (entry : G.attribution) ->
        `Assoc
          [
            ("label", `String (G.label_name entry.G.label));
            ("fills", `Int entry.G.fills);
            ("units", json_int64 entry.G.units);
            ("fees", json_int64 entry.G.fees);
            ("realized", json_int64 entry.G.realized);
            ("net", json_int64 (Int64.sub entry.G.realized entry.G.fees));
          ])
      (G.attribute ~classified ~events blotter)
  in
  let names labels = List.map (fun label -> `String (G.label_name label)) labels in
  let split_blotter summary predicate =
    List.filter (fun (fill : L.fill_record) -> predicate fill.L.at) summary.blotter
  in
  let regime_section =
    match summaries with
    | [] -> `Null
    | base :: _ ->
        let in_training moment =
          match split_time with
          | Some split -> Timestamp.compare moment split <= 0
          | None -> true
        in
        let training = split_blotter base in_training in
        let holdout =
          split_blotter base (fun moment ->
              not (in_training moment))
        in
        `Assoc
          [
            ("threshold_ticks", json_int64 threshold);
            ( "statement",
              `String
                "the volatility threshold is the median trailing mid travel of the first half; the holdout half applies the same threshold" );
            ("attribution", `List (attribution_of base.blotter));
            ("training_attribution", `List (attribution_of training));
            ("holdout_attribution", `List (attribution_of holdout));
            ( "rule_all",
              `List (names (G.condition (G.attribute ~classified ~events base.blotter))) );
            ( "rule_training",
              `List (names (G.condition (G.attribute ~classified ~events training))) );
            ( "rule_holdout",
              `List (names (G.condition (G.attribute ~classified ~events holdout))) );
            ("basis_mode", `String base.mode_name);
            ( "caveat",
              `String
                "one fixture is weak evidence: the rule describes this data set, not the future" );
          ]
  in
  let gap_for summary =
    `Assoc
      [
        ("mode", `String summary.mode_name);
        ( "fill_shortfall_units",
          json_int64 (Int64.sub naive.N.filled_units summary.filled_units) );
        ("naive_filled_units", json_int64 naive.N.filled_units);
        ("realistic_filled_units", json_int64 summary.filled_units);
        ( "fill_ratio_bps",
          `Int
            (if naive.N.filled_units <= 0L then 0
             else
               Int64.to_int
                 (Int64.div
                    (Int64.mul summary.filled_units 10_000L)
                    naive.N.filled_units)) );
        ("naive_equity", json_int64 naive.N.equity);
        ("realistic_equity", json_int64 summary.collateral);
        ("equity_gap", json_int64 (Int64.sub naive.N.equity summary.collateral));
        ("naive_fees", json_int64 naive.N.fees);
        ("realistic_fees", json_int64 summary.fees);
        ("realistic_rejected", `Int summary.rejected);
      ]
  in
  let filled_of name =
    List.find (fun summary -> summary.mode_name = name) summaries
  in
  let replay = B.replay depth_events in
  let manifest =
    match manifest_path with
    | None -> `Null
    | Some path -> (
        try Yojson.Safe.from_file path with _ -> `Null)
  in
  let json =
    `Assoc
      [
        ("depth_fixture", `String depth_path);
        ( "trades_fixture",
          match trades_path with Some path -> `String path | None -> `Null );
        ("depth_events", `Int (List.length depth_events));
        ("trade_events", `Int (List.length trade_events));
        ("events", `Int (List.length events));
        ("parse_errors", `Int (depth_errors + trade_errors));
        ("chain_gaps", `Int replay.B.gaps);
        ("chain_superseded", `Int replay.B.superseded);
        ("chain_pending", `Int replay.B.pending_updates);
        ("chain_pending", `Int replay.B.pending_updates);
        ("snapshots", `Int replay.B.snapshots);
        ("book_checksum", `String (B.checksum replay.B.book));
        ("book_best_bid", option_int64 (B.best_bid replay.B.book));
        ("book_best_ask", option_int64 (B.best_ask replay.B.book));
        ("book_bid_levels", `Int (B.level_count replay.B.book B.Bid));
        ("book_ask_levels", `Int (B.level_count replay.B.book B.Ask));
        ("latency_decision_ms", `Float decision_ms);
        ("latency_cancel_ms", `Float cancel_ms);
        ("manifest", manifest);
        ( "assumption_gap",
          `Assoc
            [
              ( "statement",
                `String
                  "the naive baseline fills every order in full at the mid with no capital limit; the difference against each mode is the realism gap" );
              ("naive", `Assoc [ ("orders", `Int naive.N.orders); ("filled_units", json_int64 naive.N.filled_units); ("fees", json_int64 naive.N.fees); ("equity", json_int64 naive.N.equity); ("capital_blocked", `Int naive.N.capital_blocked) ]);
              ("per_mode", `List (List.map gap_for summaries));
            ] );
        ("regimes", regime_section);
        ( "features",
          `Assoc
            [
              ( "buy_ratio_bps_min",
                `Int
                  (Array.fold_left
                     (fun acc feature -> min acc feature.S.buy_ratio_bps)
                     10_000 features) );
              ( "buy_ratio_bps_max",
                `Int
                  (Array.fold_left
                     (fun acc feature -> max acc feature.S.buy_ratio_bps)
                     0 features) );
              ( "events_above_floor",
                `Int
                  (Array.fold_left
                     (fun acc feature ->
                       if feature.S.buy_ratio_bps >= 4_000 then acc + 1 else acc)
                     0 features) ) ];
        );
        ("modes", `List (List.map summary_json summaries));
        ( "uncertainty",
          `Assoc
            [
              ( "filled_units_min",
                json_int64
                  (Int64.min (filled_of "conservative").filled_units
                     (Int64.min (filled_of "heuristic").filled_units
                        (filled_of "optimistic").filled_units)) );
              ( "filled_units_max",
                json_int64
                  (Int64.max (filled_of "conservative").filled_units
                     (Int64.max (filled_of "heuristic").filled_units
                        (filled_of "optimistic").filled_units)) );
              ("statement",
               `String
                 "maker fills are bounded: conservative is a lower bound and optimistic an upper bound for the same events");
            ] );
        ( "throughput",
          `Assoc
            [
              ( "events_per_second",
                `Float
                  (let total =
                     List.fold_left (fun acc s -> acc +. s.seconds) 0.0 summaries
                   in
                   if total > 0.0 then float_of_int (List.length events) /. total
                   else 0.0) );
              ("total_seconds", `Float (List.fold_left (fun acc s -> acc +. s.seconds) 0.0 summaries));
            ] );
      ]
  in
  let replay_checksum = B.checksum replay.B.book in
  let mismatch =
    List.exists
      (fun summary -> not (String.equal summary.checksum replay_checksum))
      summaries
  in
  let json =
    match json with
    | `Assoc fields ->
        `Assoc
          (fields
          @ [
              ("book_mismatch", `Bool mismatch);
              ( "book_mismatch_note",
                `String
                  (if mismatch then
                     "the loop book differs from the strict replay; the multi-window alignment is unresolved, see docs/quanthacks-backtester-plan.md"
                   else "the loop book matches the strict replay") );
            ])
    | other -> other
  in
  print_endline (Yojson.Safe.pretty_to_string json);
  if depth_errors + trade_errors > 0 || replay.B.gaps > 0 || mismatch then exit 1
