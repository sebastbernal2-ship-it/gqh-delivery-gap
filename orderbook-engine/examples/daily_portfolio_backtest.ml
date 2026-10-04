module P = Market_simulator.Daily_portfolio
module T = Market_simulator.Timestamp

let fail message = prerr_endline message; exit 2
let member key json = Yojson.Safe.Util.member key json

let string_field name json =
  match member name json with
  | `String value when String.trim value <> "" -> value
  | _ -> fail ("field " ^ name ^ " must be a nonempty string")

let bool_field name json =
  match member name json with
  | `Bool value -> value
  | _ -> fail ("field " ^ name ^ " must be boolean")

let int64_value name = function
  | `Int value -> Int64.of_int value
  | `Intlit value -> (try Int64.of_string value with _ -> fail ("field " ^ name ^ " is outside int64 range"))
  | `String value -> (try Int64.of_string value with _ -> fail ("field " ^ name ^ " must be an integer string"))
  | _ -> fail ("field " ^ name ^ " must be an integer, never a float")

let int64_field name json = int64_value name (member name json)

let int_field name json =
  let value = int64_field name json in
  if value < Int64.of_int min_int || value > Int64.of_int max_int then
    fail ("field " ^ name ^ " is outside machine integer range");
  Int64.to_int value

let timestamp_field name json =
  match T.of_string (string_field name json) with
  | Ok value -> value
  | Error message -> fail ("invalid timestamp in " ^ name ^ ": " ^ message)

let string_array name json =
  match member name json with
  | `List values -> List.map (function `String s -> s | _ -> fail (name ^ " must contain strings")) values
  | _ -> fail (name ^ " must be an array")

let read_text path =
  try In_channel.with_open_text path In_channel.input_all
  with Sys_error message -> fail message

let parse_config text =
  let json = try Yojson.Safe.from_string text with Yojson.Json_error message -> fail ("invalid config JSON: " ^ message) in
  let config : P.config = {
    strategy_name = string_field "strategy_name" json;
    hypothesis_sha256 = string_field "hypothesis_sha256" json;
    primary_specification_id = string_field "primary_specification_id" json;
    source_name = string_field "source_name" json;
    source_url = string_field "source_url" json;
    license = string_field "license" json;
    cost_model_id = string_field "cost_model_id" json;
    cost_source = string_field "cost_source" json;
    universe = string_array "universe" json;
    initial_equity_money_units = int64_field "initial_equity_money_units" json;
    max_gross_exposure_bps = int_field "max_gross_exposure_bps" json;
    max_abs_net_exposure_bps = int_field "max_abs_net_exposure_bps" json;
    max_abs_name_weight_bps = int_field "max_abs_name_weight_bps" json;
    max_participation_bps = int_field "max_participation_bps" json;
    variants_attempted = int_field "variants_attempted" json;
    periods_per_year = int_field "periods_per_year" json;
  } in
  match P.validate_config config with Ok () -> config | Error message -> fail ("invalid config: " ^ message)

let parse_observation json =
  let row : P.observation = {
    session = string_field "session" json;
    symbol = string_field "symbol" json;
    sector = string_field "sector" json;
    regime = string_field "regime" json;
    signal_id = string_field "signal_id" json;
    feature_available_at = timestamp_field "feature_available_at" json;
    universe_available_at = timestamp_field "universe_available_at" json;
    adv_available_at = timestamp_field "adv_available_at" json;
    borrow_available_at = timestamp_field "borrow_available_at" json;
    decision_at = timestamp_field "decision_at" json;
    entry_at = timestamp_field "entry_at" json;
    exit_at = timestamp_field "exit_at" json;
    eligible = bool_field "eligible" json;
    target_weight_bps = int_field "target_weight_bps" json;
    forward_total_return_1e8 = int64_field "forward_total_return_1e8" json;
    benchmark_return_1e8 = int64_field "benchmark_return_1e8" json;
    sector_return_1e8 = int64_field "sector_return_1e8" json;
    adv_money_units = int64_field "adv_money_units" json;
    one_way_cost_bps = int_field "one_way_cost_bps" json;
    borrow_available = bool_field "borrow_available" json;
    borrow_rate_bps_annual = int_field "borrow_rate_bps_annual" json;
    borrow_days = int_field "borrow_days" json;
    source_id = string_field "source_id" json;
    source_sha256 = string_field "source_sha256" json;
    quality = string_field "quality" json;
    data_status = string_field "data_status" json;
  } in
  row

let read_jsonl path =
  let channel = open_in path in
  Fun.protect ~finally:(fun () -> close_in_noerr channel) (fun () ->
    let rec loop line_number rows =
      match input_line channel with
      | line ->
          let line = String.trim line in
          if line = "" then loop (line_number + 1) rows
          else
            let json =
              try Yojson.Safe.from_string line
              with Yojson.Json_error message -> fail (Printf.sprintf "input line %d: %s" line_number message)
            in
            let row = parse_observation json in
            (match P.validate_observation row with
            | Ok () -> loop (line_number + 1) (row :: rows)
            | Error message -> fail (Printf.sprintf "input line %d: %s" line_number message))
      | exception End_of_file -> List.rev rows
    in
    loop 1 [])

let shell_hash path =
  let command =
    if Sys.file_exists "/usr/bin/sha256sum" then "/usr/bin/sha256sum " ^ Filename.quote path
    else if Sys.file_exists "/usr/bin/shasum" then "LC_ALL=C /usr/bin/shasum -a 256 " ^ Filename.quote path
    else "sha256sum " ^ Filename.quote path
  in
  let channel = Unix.open_process_in command in
  let line, status = match input_line channel with line -> line, Unix.close_process_in channel | exception End_of_file -> "", Unix.close_process_in channel in
  (match status with Unix.WEXITED 0 -> () | _ -> fail ("could not hash " ^ path));
  match String.split_on_char ' ' line with hash :: _ when String.length hash = 64 -> hash | _ -> fail ("invalid hash output for " ^ path)

let executable_path () =
  let path = Sys.executable_name in
  if Filename.is_relative path then Filename.concat (Sys.getcwd ()) path else path

let j64 value = `Intlit (Int64.to_string value)
let utc_string t = Ptime.to_rfc3339 ~tz_offset_s:0 ~frac_s:9 (T.to_ptime t)
let jfloat = function Some x when Float.is_finite x -> `Float x | _ -> `Null
let jstr = function Some x -> `String x | None -> `Null

let metric_json (m : P.metric) =
  `Assoc [
    ("periods", `Int m.periods); ("start_session", jstr m.start_session);
    ("end_session", jstr m.end_session); ("initial_equity_money_units", j64 m.initial_equity);
    ("final_equity_money_units", j64 m.final_equity);
    ("annualized_return", jfloat m.annualized_return);
    ("annualized_volatility", jfloat m.annualized_volatility);
    ("sharpe_zero_rf", jfloat m.sharpe); ("max_drawdown_bps", j64 m.max_drawdown_bps);
    ("annualized_turnover", jfloat m.annualized_turnover);
    ("total_turnover_bps", j64 m.total_turnover_bps);
    ("mean_period_return_bps", jfloat m.mean_period_return_bps);
    ("worst_period_return_1e8", (match m.worst_period_return_1e8 with None -> `Null | Some x -> j64 x));
    ("best_period_return_1e8", (match m.best_period_return_1e8 with None -> `Null | Some x -> j64 x));
  ]

let metric_csv_row key (m : P.metric) =
  let opt = function None -> "" | Some x -> Printf.sprintf "%.10g" x in
  [key; string_of_int m.periods; Option.value m.start_session ~default:"";
   Option.value m.end_session ~default:""; Int64.to_string m.initial_equity;
   Int64.to_string m.final_equity; opt m.annualized_return; opt m.annualized_volatility;
   opt m.sharpe; Int64.to_string m.max_drawdown_bps; opt m.annualized_turnover;
   Int64.to_string m.total_turnover_bps]

let csv_escape text =
  if String.contains text ',' || String.contains text '"' || String.contains text '\n' then
    "\"" ^ String.concat "\"\"" (String.split_on_char '"' text) ^ "\""
  else text

let write_csv path header rows =
  let channel = open_out path in
  Fun.protect ~finally:(fun () -> close_out_noerr channel) (fun () ->
    let write row = output_string channel (String.concat "," (List.map csv_escape row) ^ "\n") in
    write header; List.iter write rows)

let path_data days initial selector =
  let values = List.map (fun day -> Int64.to_float (selector day) /. Int64.to_float initial) days in
  let all = 1. :: values in
  let minimum = List.fold_left Float.min infinity all in
  let maximum = List.fold_left Float.max neg_infinity all in
  (minimum, maximum, values)

let svg_path ~width ~height ~padding ~min_value ~max_value values =
  let n = List.length values in
  let span = max 1e-12 (max_value -. min_value) in
  let inner_width = float_of_int (width - (2 * padding)) in
  let inner_height = float_of_int (height - (2 * padding)) in
  values
  |> List.mapi (fun i value ->
       let x = float_of_int padding +. inner_width *. float_of_int i /. float_of_int (max 1 (n - 1)) in
       let y = float_of_int height -. float_of_int padding -. inner_height *. (value -. min_value) /. span in
       Printf.sprintf "%.2f,%.2f" x y)
  |> String.concat " "

let write_dashboard path result initial =
  let width = 1000 and height = 500 and padding = 48 in
  let series = [
    ("Gross strategy", "#7a96ff", (fun d -> d.P.gross_equity));
    ("Net strategy", "#21c7a8", (fun d -> d.P.net_equity));
    ("2x costs", "#ff9666", (fun d -> d.P.doubled_cost_equity));
    ("Market benchmark", "#c28aff", (fun d -> d.P.benchmark_equity));
    ("Sector benchmark", "#e4c65a", (fun d -> d.P.sector_equity));
  ] in
  let ranges = List.map (fun (_, _, get) -> path_data result.P.all_days initial get) series in
  let min_value = List.fold_left (fun x (a, _, _) -> Float.min x a) infinity ranges in
  let max_value = List.fold_left (fun x (_, b, _) -> Float.max x b) neg_infinity ranges in
  let oos_index =
    List.find_index (fun (d : P.day) -> d.P.session >= result.P.split_start_session) result.P.all_days
    |> Option.value ~default:0
  in
  let oos_x = float_of_int padding +. float_of_int (width - (2 * padding))
              *. float_of_int oos_index /. float_of_int (max 1 (List.length result.P.all_days - 1)) in
  let oos_marker = Printf.sprintf
      "<line x1=\"%.2f\" y1=\"%d\" x2=\"%.2f\" y2=\"%d\" stroke=\"#ffcc66\" stroke-width=\"2\" stroke-dasharray=\"7 6\"/><text x=\"%.2f\" y=\"%d\" fill=\"#ffcc66\" font-size=\"13\">OOS starts</text>"
      oos_x padding oos_x (height-padding) (min (float_of_int (width-140)) (oos_x+.6.)) (padding+20) in
  let paths = List.map2 (fun (name, color, _) (_, _, values) ->
    Printf.sprintf "<polyline fill=\"none\" stroke=\"%s\" stroke-width=\"3\" points=\"%s\"/><text x=\"%d\" y=\"%d\" fill=\"%s\" font-size=\"14\">%s</text>"
      color (svg_path ~width ~height ~padding ~min_value ~max_value values)
      (padding + (List.length values * 165)) (padding - 10) color name) series ranges |> String.concat "\n" in
  let labels = match result.P.all_days with [] -> "" | first :: rest ->
    let last = List.hd (List.rev result.P.all_days) in
    Printf.sprintf "<text x=\"%d\" y=\"%d\">%s</text><text x=\"%d\" y=\"%d\">%s</text>"
      padding (height - 12) first.P.session (width - 110) (height - 12) last.P.session in
  let channel = open_out path in
  Fun.protect ~finally:(fun () -> close_out_noerr channel) (fun () ->
    output_string channel (Printf.sprintf "<!doctype html><html><head><meta charset=\"utf-8\"><title>Daily strategy backtest</title><style>body{font:16px system-ui;background:#10131a;color:#e9edf5;margin:2rem}main{max-width:1100px;margin:auto}svg{width:100%%;background:#171c26;border:1px solid #30394a}p{color:#aeb9cb}</style></head><body><main><h1>Daily strategy backtest</h1><p>Net-of-cost portfolio equity, doubled-cost sensitivity and benchmarks. This is a daily return model, not order-book execution evidence. See accompanying metrics and positions CSVs.</p><svg viewBox=\"0 0 %d %d\" role=\"img\" aria-label=\"Equity curves with chronological OOS boundary\"><line x1=\"%d\" y1=\"%d\" x2=\"%d\" y2=\"%d\" stroke=\"#778196\"/>%s%s%s</svg><p>OOS begins %s. Review report.json and split boundaries before interpreting results.</p></main></body></html>"
      width height padding padding (width-padding) padding paths oos_marker labels result.P.split_start_session))

let write_outputs ~config_path ~input_path ~report_path ~curve_path ~positions_path ~breakdown_path ~dashboard_path result config config_sha input_sha executable_sha =
  let curve_rows = List.map (fun (d : P.day) -> [
    d.session; utc_string d.entry_at; utc_string d.exit_at; d.regime;
    Int64.to_string d.gross_return_1e8; Int64.to_string d.net_return_1e8;
    Int64.to_string d.doubled_cost_return_1e8; Int64.to_string d.benchmark_return_1e8;
    Int64.to_string d.sector_return_1e8; Int64.to_string d.gross_equity;
    Int64.to_string d.net_equity; Int64.to_string d.doubled_cost_equity;
    Int64.to_string d.benchmark_equity; Int64.to_string d.sector_equity;
    Int64.to_string d.turnover_bps; Int64.to_string d.transaction_cost_1e8;
    Int64.to_string d.borrow_cost_1e8; string_of_int d.active_names
  ]) result.P.all_days in
  write_csv curve_path
    ["session";"entry_at";"exit_at";"regime";"gross_return_1e8";"net_return_1e8";"double_cost_return_1e8";"benchmark_return_1e8";"sector_return_1e8";"gross_equity_money_units";"net_equity_money_units";"double_cost_equity_money_units";"benchmark_equity_money_units";"sector_equity_money_units";"turnover_bps";"transaction_cost_1e8";"borrow_cost_1e8";"active_names"] curve_rows;
  let position_rows = List.map (fun (p : P.position) -> [
    p.session;p.symbol;p.sector;p.regime;string_of_bool p.eligible;
    string_of_int p.target_weight_bps;Int64.to_string p.forward_total_return_1e8;
    Int64.to_string p.turnover_bps;Int64.to_string p.order_notional_money_units;
    Int64.to_string p.participation_bps;string_of_int p.one_way_cost_bps;
    Int64.to_string p.borrow_cost_1e8;
    Option.fold ~none:"" ~some:Int64.to_string p.capacity_money_units;
    p.source_id;p.source_sha256
  ]) result.P.positions in
  write_csv positions_path
    ["session";"symbol";"sector";"regime";"eligible";"target_weight_bps";"forward_total_return_1e8";"turnover_bps";"order_notional_money_units";"participation_bps";"one_way_cost_bps";"borrow_cost_1e8";"capacity_money_units_at_max_participation";"source_id";"source_sha256"] position_rows;
  let fixed_metrics = [
    ("full_gross", result.P.full_gross); ("full_net", result.P.full_net);
    ("full_double_cost", result.P.full_double); ("in_sample_net", result.P.in_sample_net);
    ("out_of_sample_net", result.P.out_of_sample_net);
    ("market_benchmark", result.P.full_benchmark);
    ("sector_benchmark", result.P.full_sector_benchmark)
  ] in
  let rows = List.map (fun (name, m) -> metric_csv_row name m) fixed_metrics
    @ List.map (fun (year, m) -> metric_csv_row ("year:" ^ string_of_int year) m) result.P.annual_net
    @ List.map (fun (regime, m) -> metric_csv_row ("regime:" ^ regime) m) result.P.regime_net in
  write_csv breakdown_path
    ["scope";"periods";"start_session";"end_session";"initial_equity_money_units";"final_equity_money_units";"annualized_return";"annualized_volatility";"sharpe_zero_rf";"max_drawdown_bps";"annualized_turnover";"total_turnover_bps"] rows;
  let report_json = `Assoc [
    ("schema_version", `String "daily-portfolio-report-v1");
    ("strategy_name", `String config.P.strategy_name);
    ("hypothesis_sha256", `String config.P.hypothesis_sha256);
    ("primary_specification_id", `String config.P.primary_specification_id);
    ("source", `Assoc [("name",`String config.P.source_name);("url",`String config.P.source_url);("license",`String config.P.license)]);
    ("cost_model", `Assoc [("id",`String config.P.cost_model_id);("source",`String config.P.cost_source)]);
    ("input_rows", `Int result.P.input_rows); ("sessions", `Int (List.length result.P.all_days));
    ("universe", `List (List.map (fun s -> `String s) config.P.universe));
    ("first_session", jstr (match result.P.all_days with [] -> None | d :: _ -> Some d.P.session));
    ("last_session", jstr (match List.rev result.P.all_days with [] -> None | d :: _ -> Some d.P.session));
    ("out_of_sample_start", `String result.P.split_start_session);
    ("oos_rule", `String "most recent 20 percent of sessions or most recent 2 calendar years, whichever is shorter");
    ("variants_attempted", `Int config.P.variants_attempted);
    ("portfolio_limits", `Assoc [
      ("max_gross_exposure_bps",`Int config.P.max_gross_exposure_bps);
      ("max_abs_net_exposure_bps",`Int config.P.max_abs_net_exposure_bps);
      ("max_abs_name_weight_bps",`Int config.P.max_abs_name_weight_bps);
      ("max_participation_bps",`Int config.P.max_participation_bps)]);
    ("capacity_summary", (let values = List.filter_map (fun (p : P.position) -> p.P.capacity_money_units) result.P.positions |> List.sort Int64.compare in
      let pick percentile =
        match values with [] -> `Null | xs ->
          let index = max 0 (((List.length xs * percentile + 99) / 100) - 1) in
          j64 (List.nth xs (min (List.length xs - 1) index))
      in
      `Assoc [ ("sample_count",`Int (List.length values));
        ("p10_money_units_nearest_rank",pick 10);
        ("median_money_units_nearest_rank",pick 50) ]));
    ("execution_model", `String "daily target-weight portfolio with one-way costs and forward total returns; not order-book execution");
    ("signal_generation", `String "external target_weight_bps supplied by the named strategy specification; this runner does not create alpha");
    ("return_unit", `String "fraction scaled by 1e8; decimal input prohibited");
    ("money_unit", `String "USD scaled by 1e8");
    ("sharpe_convention", `String "zero risk-free rate; sample volatility annualized using periods_per_year");
    ("periods_per_year", `Int config.P.periods_per_year);
    ("source_sha256", `List (List.map (fun h -> `String h) result.P.source_hashes));
    ("input_sha256", `String input_sha); ("config_sha256", `String config_sha);
    ("executable_sha256", `String executable_sha);
    ("metrics", `Assoc (List.map (fun (name,m) -> name, metric_json m) fixed_metrics));
    ("annual_metrics", `List (List.map (fun (year,m) -> `Assoc [ ("year",`Int year);("metrics",metric_json m) ]) result.P.annual_net));
    ("regime_metrics", `List (List.map (fun (name,m) -> `Assoc [ ("regime",`String name);("metrics",metric_json m) ]) result.P.regime_net));
    ("limitations", `List [
      `String "Not a signal generator: targets must be frozen, point-in-time strategy outputs.";
      `String "Forward total returns must include the declared split/dividend treatment.";
      `String "Daily costs and ADV participation are approximations; no intraday impact or queue simulation.";
      `String "The historical OOS window must not be opened until the strategy specification is frozen; this tool does not enforce one-time human access.";
    ]);
  ] in
  let channel = open_out report_path in
  Fun.protect ~finally:(fun () -> close_out_noerr channel) (fun () -> Yojson.Safe.pretty_to_channel channel report_json; output_char channel '\n');
  let initial = config.P.initial_equity_money_units in
  write_dashboard dashboard_path result initial;
  let artifacts = [report_path;curve_path;positions_path;breakdown_path;dashboard_path] in
  let manifest_json = `Assoc [
    ("schema_version",`String "daily-portfolio-manifest-v1");
    ("run_key",`String (input_sha ^ ":" ^ config_sha ^ ":" ^ executable_sha));
    ("config_path",`String config_path);("input_path",`String input_path);
    ("input_sha256",`String input_sha);("config_sha256",`String config_sha);
    ("executable_sha256",`String executable_sha);
    ("artifacts",`List (List.map (fun path -> `Assoc [("path",`String path);("sha256",`String (shell_hash path))]) artifacts));
  ] in
  let manifest_path = report_path ^ ".manifest.json" in
  let channel = open_out manifest_path in
  Fun.protect ~finally:(fun () -> close_out_noerr channel) (fun () -> Yojson.Safe.pretty_to_channel channel manifest_json; output_char channel '\n')

let usage () = fail "usage: daily_portfolio_backtest CONFIG.json TARGET_PANEL.jsonl REPORT.json CURVE.csv POSITIONS.csv BREAKDOWNS.csv DASHBOARD.html --open-oos"

let () =
  match Array.to_list Sys.argv |> List.tl with
  | [ config_path; input_path; report_path; curve_path; positions_path; breakdown_path; dashboard_path; "--open-oos" ] ->
      let paths = [config_path; input_path; report_path; curve_path; positions_path; breakdown_path; dashboard_path] in
      if List.length (List.sort_uniq String.compare paths) <> List.length paths then fail "all input/output paths must be distinct";
      let config_text = read_text config_path in
      let config_sha = shell_hash config_path and input_sha = shell_hash input_path in
      let executable_sha = shell_hash (executable_path ()) in
      let config = parse_config config_text in
      let rows = read_jsonl input_path in
      (match P.run config rows with
      | Error message -> fail ("backtest rejected: " ^ message)
      | Ok result ->
          write_outputs ~config_path ~input_path ~report_path ~curve_path ~positions_path ~breakdown_path ~dashboard_path result config config_sha input_sha executable_sha;
          print_endline ("backtest complete; report=" ^ report_path ^ " oos_start=" ^ result.P.split_start_session))
  | _ -> usage ()
