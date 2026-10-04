module E = Market_simulator.Exec_event
module S = Market_simulator.Instrument_spec
module L = Market_simulator.Asset_loop
module T = Market_simulator.Timestamp

let fail message = prerr_endline message; exit 2
let member key json = Yojson.Safe.Util.member key json

let string_field key json =
  match member key json with
  | `String value when value <> "" -> value
  | _ -> fail ("config field " ^ key ^ " must be a nonempty string")

let int64_value key = function
  | `Int value -> Int64.of_int value
  | `Intlit value -> (
      try Int64.of_string value
      with Failure _ -> fail ("config field " ^ key ^ " is outside int64 range"))
  | `String value -> (
      try Int64.of_string value
      with Failure _ -> fail ("config field " ^ key ^ " is not an integer string"))
  | _ -> fail ("config field " ^ key ^ " must be an integer or integer string")

let int64_field key json = int64_value key (member key json)

let int_field key json =
  let value = int64_field key json in
  if value < Int64.of_int min_int || value > Int64.of_int max_int then
    fail ("config field " ^ key ^ " is outside machine integer range");
  Int64.to_int value

let timestamp_field key json =
  match T.of_string (string_field key json) with
  | Ok value -> value
  | Error message -> fail ("invalid timestamp in " ^ key ^ ": " ^ message)

let optional_timestamp key json =
  match member key json with
  | `Null -> None
  | `String value -> (
      match T.of_string value with
      | Ok parsed -> Some parsed
      | Error message -> fail ("invalid timestamp in " ^ key ^ ": " ^ message))
  | _ -> fail ("config field " ^ key ^ " must be a timestamp or null")

let option_terms kind =
  let right =
    match string_field "right" kind with
    | "call" -> S.Call
    | "put" -> S.Put
    | _ -> fail "option right must be call or put"
  in
  let settlement =
    match string_field "settlement" kind with
    | "cash" -> S.Cash
    | "physical" -> S.Physical
    | _ -> fail "option settlement must be cash or physical"
  in
  {
    S.underlying = string_field "underlying" kind;
    strike_ticks = int64_field "strike_ticks" kind;
    expiry = timestamp_field "expiry" kind;
    right;
    settlement;
    deliverable_units = int64_field "deliverable_units" kind;
    exercise_multiplier = int64_field "exercise_multiplier" kind;
  }

let instrument_spec json =
  let kind_json = member "kind" json in
  let kind_type = string_field "type" kind_json in
  let kind =
    match kind_type with
    | "equity" -> S.Equity
    | "perpetual" ->
        S.Perpetual
          {
            initial_margin_bps = int_field "initial_margin_bps" kind_json;
            maintenance_margin_bps = int_field "maintenance_margin_bps" kind_json;
          }
    | "future" ->
        S.Future
          {
            expiry = timestamp_field "expiry" kind_json;
            initial_margin_bps = int_field "initial_margin_bps" kind_json;
            maintenance_margin_bps = int_field "maintenance_margin_bps" kind_json;
          }
    | "option" -> S.Option (option_terms kind_json)
    | _ -> fail "kind.type must be equity, future, perpetual, or option"
  in
  {
    S.venue = string_field "venue" json;
    symbol = string_field "symbol" json;
    currency = string_field "currency" json;
    effective_from = timestamp_field "effective_from" json;
    effective_until = optional_timestamp "effective_until" json;
    price_increment_ticks = int64_field "price_increment_ticks" json;
    quantity_increment_units = int64_field "quantity_increment_units" json;
    multiplier = int64_field "multiplier" json;
    kind;
  }

let read_events path =
  let channel = open_in path in
  let rec loop line_number events =
    match input_line channel with
    | line ->
        let trimmed = String.trim line in
        if trimmed = "" then loop (line_number + 1) events
        else
          (match E.of_string trimmed with
          | Ok event -> loop (line_number + 1) (event :: events)
          | Error message ->
              close_in_noerr channel;
              fail (Printf.sprintf "input line %d: %s" line_number message))
    | exception End_of_file ->
        close_in channel;
        List.rev events
  in
  loop 1 []

let sha256 path =
  let command =
    if Sys.file_exists "/usr/bin/sha256sum" then
      "/usr/bin/sha256sum " ^ Filename.quote path
    else if Sys.file_exists "/sbin/sha256sum" then
      "/sbin/sha256sum " ^ Filename.quote path
    else if Sys.file_exists "/usr/bin/shasum" then
      "LC_ALL=C /usr/bin/shasum -a 256 " ^ Filename.quote path
    else fail "sha256sum or shasum is required to record artifact provenance"
  in
  let channel = Unix.open_process_in command in
  let line, status =
    match input_line channel with
    | line -> (line, Unix.close_process_in channel)
    | exception End_of_file -> ("", Unix.close_process_in channel)
  in
  (match status with
  | Unix.WEXITED 0 -> ()
  | _ -> fail ("failed to hash " ^ path));
  match String.split_on_char ' ' line with
  | hash :: _ when String.length hash = 64 -> hash
  | _ -> fail ("could not parse SHA-256 output for " ^ path)

let write_curve path result fixture_sha256 config_sha256 =
  let channel = open_out path in
  Fun.protect
    ~finally:(fun () -> close_out_noerr channel)
    (fun () ->
      List.iteri
        (fun index (point : L.equity_point) ->
          let json =
            `Assoc
              [
                ("index", `Int index);
                ( "event_time",
                  `String (E.timestamp_to_string point.event_time) );
                ( "receive_time",
                  `String (E.timestamp_to_string point.receive_time) );
                ("event_kind", `String point.event_kind);
                ("equity", `Intlit (Int64.to_string point.equity));
                ("cash", `Intlit (Int64.to_string point.cash));
                ( "position_units",
                  `Intlit (Int64.to_string point.position_units) );
                ( "mark_ticks",
                  match point.mark_ticks with
                  | None -> `Null
                  | Some value -> `Intlit (Int64.to_string value) );
                ("fixture_sha256", `String fixture_sha256);
                ("config_sha256", `String config_sha256);
              ]
          in
          output_string channel (Yojson.Safe.to_string json ^ "\n"))
        result.L.equity_curve)

let event_range events field =
  match events with
  | [] -> `Null
  | first :: rest ->
      let get event = field event in
      let last = List.fold_left (fun _ event -> get event) (get first) rest in
      `Assoc
        [
          ("first", `String (E.timestamp_to_string (get first)));
          ("last", `String (E.timestamp_to_string last));
        ]

let source_hashes events =
  events
  |> List.map (fun event -> event.E.source_sha256)
  |> List.sort_uniq String.compare
  |> List.map (fun hash -> `String hash)

let kind_counts events =
  let counts = Hashtbl.create 12 in
  List.iter
    (fun event ->
      let kind = E.kind_name event.E.payload in
      Hashtbl.replace counts kind
        (1 + Option.value (Hashtbl.find_opt counts kind) ~default:0))
    events;
  Hashtbl.fold (fun kind count values -> (kind, `Int count) :: values) counts []
  |> List.sort compare

let usage () =
  fail
    "usage: asset_fixture_report CONFIG.json EVENTS.jsonl REPORT.json CURVE.jsonl"

let () =
  match Array.to_list Sys.argv |> List.tl with
  | [ config_path; input_path; report_path; curve_path ] ->
      if
        List.length
          (List.sort_uniq String.compare
             [ config_path; input_path; report_path; curve_path ])
        <> 4
      then fail "config, input, report and curve paths must be distinct";
      let config_text =
        try In_channel.with_open_text config_path In_channel.input_all
        with Sys_error message -> fail message
      in
      let config =
        try Yojson.Safe.from_string config_text
        with Yojson.Json_error message -> fail ("invalid config JSON: " ^ message)
      in
      let spec, initial_cash, fee_bps, latency_ns, settlement_lag_ns =
        try
          ( instrument_spec config,
            int64_field "initial_cash" config,
            int_field "taker_fee_bps" config,
            int64_field "latency_ns" config,
            int64_field "equity_settlement_lag_ns" config )
        with Yojson.Safe.Util.Type_error (message, _) ->
          fail ("invalid config shape: " ^ message)
      in
      if settlement_lag_ns < 0L then fail "equity settlement lag cannot be negative";
      let events =
        try read_events input_path
        with Sys_error message -> fail message
      in
      let fixture_sha256 = sha256 input_path in
      let config_sha256 = sha256 config_path in
      let engine_sha256 = sha256 Sys.executable_name in
      (match
         L.run spec ~initial_cash ~taker_fee_bps:fee_bps ~latency_ns
           ~equity_settlement:(fun at -> T.add_ns at settlement_lag_ns) events
       with
      | Error message -> fail ("replay failed closed: " ^ message)
      | Ok result ->
          (match
             Market_simulator.Asset_report.summarize ~initial_cash ~events result
           with
          | Error message -> fail ("report failed closed: " ^ message)
          | Ok summary ->
              write_curve curve_path result fixture_sha256 config_sha256;
              let output =
                `Assoc
                  [
                    ("report_version", `String "asset-replay-v1");
                    ("venue", `String spec.S.venue);
                    ("symbol", `String spec.S.symbol);
                    ("currency", `String spec.S.currency);
                    ("fixture_sha256", `String fixture_sha256);
                    ("config_sha256", `String config_sha256);
                    ("engine_binary_sha256", `String engine_sha256);
                    ( "run_key_components",
                      `Assoc
                        [
                          ("fixture_sha256", `String fixture_sha256);
                          ("config_sha256", `String config_sha256);
                          ("engine_binary_sha256", `String engine_sha256);
                        ] );
                    ( "event_time_range",
                      event_range events (fun event -> event.E.event_time) );
                    ( "receive_time_range",
                      event_range events (fun event -> event.E.receive_time) );
                    ("source_sha256s", `List (source_hashes events));
                    ("event_kind_counts", `Assoc (kind_counts events));
                    ("execution_model", `String "visible-depth-ioc-fok-conservative");
                    ("curve_rows", `Int (List.length result.L.equity_curve));
                    ("curve_artifact", `String (Filename.basename curve_path));
                    ("summary", Market_simulator.Asset_report.to_yojson summary);
                  ]
              in
              let channel = open_out report_path in
              Fun.protect
                ~finally:(fun () -> close_out_noerr channel)
                (fun () -> Yojson.Safe.pretty_to_channel channel output)))
  | _ -> usage ()
