(** Point-in-time daily portfolio accounting over a frozen target-weight panel.

    The strategy adapter supplies target weights. This module never discovers
    alpha. Outcome returns are forward total-return fractions in 1e-8 units.
    P&L, costs, NAV, drawdown, exposure, and capacity arithmetic are integer
    fixed point. Floating point is used only to summarize standard statistics. *)

type observation = {
  session : string;
  symbol : string;
  sector : string;
  regime : string;
  signal_id : string;
  feature_available_at : Timestamp.t;
  universe_available_at : Timestamp.t;
  adv_available_at : Timestamp.t;
  borrow_available_at : Timestamp.t;
  decision_at : Timestamp.t;
  entry_at : Timestamp.t;
  exit_at : Timestamp.t;
  eligible : bool;
  target_weight_bps : int;
  forward_total_return_1e8 : int64;
  benchmark_return_1e8 : int64;
  sector_return_1e8 : int64;
  adv_money_units : int64;
  one_way_cost_bps : int;
  borrow_available : bool;
  borrow_rate_bps_annual : int;
  borrow_days : int;
  source_id : string;
  source_sha256 : string;
  quality : string;
  data_status : string;
}

type config = {
  strategy_name : string;
  hypothesis_sha256 : string;
  primary_specification_id : string;
  source_name : string;
  source_url : string;
  license : string;
  cost_model_id : string;
  cost_source : string;
  universe : string list;
  initial_equity_money_units : int64;
  max_gross_exposure_bps : int;
  max_abs_net_exposure_bps : int;
  max_abs_name_weight_bps : int;
  max_participation_bps : int;
  variants_attempted : int;
  periods_per_year : int;
}

type day = {
  session : string;
  entry_at : Timestamp.t;
  exit_at : Timestamp.t;
  regime : string;
  gross_return_1e8 : int64;
  net_return_1e8 : int64;
  doubled_cost_return_1e8 : int64;
  benchmark_return_1e8 : int64;
  sector_return_1e8 : int64;
  turnover_bps : int64;
  transaction_cost_1e8 : int64;
  borrow_cost_1e8 : int64;
  starting_equity : int64;
  gross_equity : int64;
  net_equity : int64;
  doubled_cost_equity : int64;
  benchmark_equity : int64;
  sector_equity : int64;
  active_names : int;
}

type position = {
  session : string;
  symbol : string;
  sector : string;
  regime : string;
  eligible : bool;
  target_weight_bps : int;
  forward_total_return_1e8 : int64;
  turnover_bps : int64;
  order_notional_money_units : int64;
  participation_bps : int64;
  one_way_cost_bps : int;
  borrow_cost_1e8 : int64;
  capacity_money_units : int64 option;
  source_id : string;
  source_sha256 : string;
}

type metric = {
  periods : int;
  start_session : string option;
  end_session : string option;
  initial_equity : int64;
  final_equity : int64;
  annualized_return : float option;
  annualized_volatility : float option;
  sharpe : float option;
  max_drawdown_bps : int64;
  annualized_turnover : float option;
  total_turnover_bps : int64;
  mean_period_return_bps : float option;
  worst_period_return_1e8 : int64 option;
  best_period_return_1e8 : int64 option;
}

type output = {
  split_start_session : string;
  all_days : day list;
  positions : position list;
  full_gross : metric;
  full_net : metric;
  full_double : metric;
  in_sample_net : metric;
  out_of_sample_net : metric;
  full_benchmark : metric;
  full_sector_benchmark : metric;
  annual_net : (int * metric) list;
  regime_net : (string * metric) list;
  source_hashes : string list;
  input_rows : int;
}

let ( let* ) = Result.bind
let return_scale = 100_000_000L
let bps_scale = 10_000L
let hash_is_valid value =
  String.length value = 64
  && String.for_all
       (function '0' .. '9' | 'a' .. 'f' | 'A' .. 'F' -> true | _ -> false)
       value

(** Overflow-safe rounded [a*b/divisor]. Binary quotient/remainder
    accumulation avoids ever materializing the potentially overflowing product.
    Rounding is half away from zero, matching the execution-unit policy. *)
let mul_div ~divisor a b =
  if divisor <= 0L then Error "divisor must be positive"
  else if a = Int64.min_int || b = Int64.min_int then Error "integer overflow"
  else
    let negative = (a < 0L) <> (b < 0L) in
    let a = if a < 0L then Int64.neg a else a
    and b = if b < 0L then Int64.neg b else b in
    let b_whole = Int64.div b divisor and b_remainder = Int64.rem b divisor in
    let add_mod x y =
      let gap = Int64.sub divisor y in
      if x >= gap then (Int64.sub x gap, 1L) else (Int64.add x y, 0L)
    in
    let rec bits bit quotient remainder =
      if bit < 0 then Ok (quotient, remainder)
      else
        let doubled_remainder, carry = add_mod remainder remainder in
        let* quotient = Exec_units.checked_mul quotient 2L in
        let* quotient = Exec_units.checked_add quotient carry in
        let set = Int64.logand a (Int64.shift_left 1L bit) <> 0L in
        if not set then bits (bit - 1) quotient doubled_remainder
        else
          let added_remainder, carry = add_mod doubled_remainder b_remainder in
          let* quotient = Exec_units.checked_add quotient b_whole in
          let* quotient = Exec_units.checked_add quotient carry in
          bits (bit - 1) quotient added_remainder
    in
    let* quotient, remainder = bits 62 0L 0L in
    let half = Int64.div divisor 2L in
    let round_up = remainder > half || (Int64.rem divisor 2L = 0L && remainder = half) in
    let* quotient = if round_up then Exec_units.checked_add quotient 1L else Ok quotient in
    if negative then Ok (Int64.neg quotient) else Ok quotient

let validate_config c =
  let required name value =
    if String.trim value = "" then Error (name ^ " is empty") else Ok ()
  in
  let* () = required "strategy_name" c.strategy_name in
  let* () = required "primary_specification_id" c.primary_specification_id in
  let* () = required "source_name" c.source_name in
  let* () = required "source_url" c.source_url in
  let* () = required "license" c.license in
  let* () = required "cost_model_id" c.cost_model_id in
  let* () = required "cost_source" c.cost_source in
  if not (hash_is_valid c.hypothesis_sha256) then
    Error "hypothesis_sha256 must be 64 hexadecimal characters"
  else if c.initial_equity_money_units <= 0L then Error "initial equity must be positive"
  else if c.universe = [] then Error "universe must not be empty"
  else if List.length c.universe <> List.length (List.sort_uniq String.compare c.universe) then
    Error "universe contains duplicate symbols"
  else if List.exists (fun symbol -> String.trim symbol = "") c.universe then
    Error "universe contains an empty symbol"
  else if c.max_gross_exposure_bps < 0 || c.max_gross_exposure_bps > 100_000 then
    Error "max gross exposure must be in [0,100000] bps"
  else if c.max_abs_net_exposure_bps < 0 || c.max_abs_net_exposure_bps > c.max_gross_exposure_bps then
    Error "invalid max net exposure"
  else if c.max_abs_name_weight_bps < 0 || c.max_abs_name_weight_bps > c.max_gross_exposure_bps then
    Error "invalid max name weight"
  else if c.max_participation_bps <= 0 || c.max_participation_bps > 10_000 then
    Error "max participation must be in (0,10000] bps"
  else if c.variants_attempted < 1 then Error "variants_attempted must be at least one"
  else if c.periods_per_year < 1 || c.periods_per_year > 366 then
    Error "periods_per_year must be in [1,366]"
  else Ok ()

let valid_session value =
  String.length value = 10
  && value.[4] = '-'
  && value.[7] = '-'
  && String.for_all
       (fun c -> (c >= '0' && c <= '9') || c = '-')
       value

let validate_observation (row : observation) =
  let required field value =
    if String.trim value = "" then Error (field ^ " is empty") else Ok ()
  in
  let* () = required "session" row.session in
  let* () = required "symbol" row.symbol in
  let* () = required "sector" row.sector in
  let* () = required "signal_id" row.signal_id in
  let* () = required "source_id" row.source_id in
  if not (valid_session row.session) then Error "session must be YYYY-MM-DD"
  else if (let y, m, d = Ptime.to_date (Timestamp.to_ptime row.entry_at) in
           Printf.sprintf "%04d-%02d-%02d" y m d) <> row.session then
    Error "session must match the UTC calendar date of entry_at"
  else if not (hash_is_valid row.source_sha256) then
    Error "source_sha256 must be 64 hexadecimal characters"
  else if row.quality <> "healthy" then
    Error ("input quality is not healthy: " ^ row.symbol ^ " " ^ row.session)
  else if row.data_status <> "observed" then
    Error ("non-observed market row fails closed: " ^ row.symbol ^ " " ^ row.session)
  else if Timestamp.compare row.feature_available_at row.decision_at > 0
          || Timestamp.compare row.universe_available_at row.decision_at > 0
          || Timestamp.compare row.adv_available_at row.decision_at > 0
          || Timestamp.compare row.borrow_available_at row.decision_at > 0 then
    Error "feature, membership, ADV, and borrow must be available by decision time"
  else if Timestamp.compare row.decision_at row.entry_at >= 0 then
    Error "entry must be strictly after decision time"
  else if Timestamp.compare row.entry_at row.exit_at >= 0 then
    Error "exit must be strictly after entry time"
  else if row.target_weight_bps < -100_000 || row.target_weight_bps > 100_000 then
    Error "target weight outside supported range"
  else if row.forward_total_return_1e8 < Int64.neg return_scale
          || row.forward_total_return_1e8 > Int64.mul 100L return_scale then
    Error "forward total return outside supported range"
  else if row.benchmark_return_1e8 < Int64.neg return_scale
          || row.sector_return_1e8 < Int64.neg return_scale then
    Error "benchmark total return cannot be below -100%"
  else if row.adv_money_units < 0L then Error "ADV must be nonnegative"
  else if row.one_way_cost_bps < 0 || row.one_way_cost_bps > 10_000 then
    Error "one-way cost outside supported range"
  else if row.borrow_rate_bps_annual < 0 || row.borrow_rate_bps_annual > 1_000_000 then
    Error "borrow rate outside supported range"
  else if row.borrow_days < 0 || row.borrow_days > 366 then
    Error "borrow_days outside supported range"
  else if not row.eligible && row.target_weight_bps <> 0 then
    Error "ineligible security has nonzero target weight"
  else if row.target_weight_bps < 0 && not row.borrow_available then
    Error ("short target has no borrow: " ^ row.symbol ^ " " ^ row.session)
  else Ok ()

let sum_int64 values =
  List.fold_left
    (fun acc value ->
      let* acc = acc in
      Exec_units.checked_add acc value)
    (Ok 0L) values

let abs64 value =
  if value = Int64.min_int then Error "int64 absolute-value overflow"
  else Ok (Int64.abs value)

let group_by_session (rows : observation list) =
  let sorted =
    List.sort
      (fun (a : observation) (b : observation) ->
        let c = Timestamp.compare a.entry_at b.entry_at in
        if c <> 0 then c else String.compare a.symbol b.symbol)
      rows
  in
  let rec loop key current acc = function
    | [] -> List.rev (if current = [] then acc else (key, List.rev current) :: acc)
    | (row : observation) :: rest ->
        if current = [] || row.session = key then loop row.session (row :: current) acc rest
        else loop row.session [ row ] ((key, List.rev current) :: acc) rest
  in
  loop "" [] [] sorted

let validate_panel c (groups : (string * observation list) list) =
  let expected = List.sort String.compare c.universe in
  let rec loop previous_exit previous_entry = function
    | [] -> Ok ()
    | (session, (rows : observation list)) :: rest ->
        let symbols = List.map (fun (row : observation) -> row.symbol) rows |> List.sort String.compare in
        let* () =
          if symbols <> expected then
            Error ("unbalanced panel at " ^ session ^ ": require one row per configured symbol")
          else Ok ()
        in
        let* first =
          match rows with [] -> Error "empty session group" | (first : observation) :: _ -> Ok first
        in
        let* () =
          if List.exists
               (fun (row : observation) ->
                 not (Timestamp.equal row.entry_at first.entry_at)
                 || not (Timestamp.equal row.exit_at first.exit_at)
                 || row.regime <> first.regime
                 || row.benchmark_return_1e8 <> first.benchmark_return_1e8
                 || row.sector_return_1e8 <> first.sector_return_1e8)
               rows
          then Error ("session-level timestamps/regime/benchmarks disagree at " ^ session)
          else Ok ()
        in
        let* () =
          match previous_exit with
          | Some previous when not (Timestamp.equal previous first.entry_at) ->
              Error ("daily intervals must be contiguous at " ^ session)
          | _ -> Ok ()
        in
        let* () =
          match previous_entry with
          | Some previous when Timestamp.compare previous first.entry_at >= 0 ->
              Error "sessions are not strictly chronological"
          | _ -> Ok ()
        in
        let weights = List.map (fun (row : observation) -> row.target_weight_bps) rows in
        let* gross = List.fold_left (fun acc w -> let* acc = acc in Exec_units.checked_add acc (Int64.of_int (abs w))) (Ok 0L) weights in
        let* net = List.fold_left (fun acc w -> let* acc = acc in Exec_units.checked_add acc (Int64.of_int w)) (Ok 0L) weights in
        if gross > Int64.of_int c.max_gross_exposure_bps then
          Error ("gross exposure cap breached at " ^ session)
        else if Int64.abs net > Int64.of_int c.max_abs_net_exposure_bps then
          Error ("net exposure cap breached at " ^ session)
        else if List.exists (fun (row : observation) -> abs row.target_weight_bps > c.max_abs_name_weight_bps) rows then
          Error ("single-name weight cap breached at " ^ session)
        else loop (Some first.exit_at) (Some first.entry_at) rest
  in
  loop None None groups

type account = { mutable nav : int64; mutable weights : (string * int64) list }

let held_weight symbol account = Option.value (List.assoc_opt symbol account.weights) ~default:0L

let nav_after_return nav return_1e8 =
  if return_1e8 <= Int64.neg return_scale then Error "portfolio return would eliminate all equity"
  else
    let* pnl = mul_div ~divisor:return_scale nav return_1e8 in
    Exec_units.checked_add nav pnl

let metrics ~periods_per_year ~initial_equity ~(days : day list) ~return_of ~equity_of ~turnover_of =
  let periods = List.length days in
  let rets = List.map (fun day -> Int64.to_float (return_of day) /. Int64.to_float return_scale) days in
  let mean =
    match rets with [] -> None | xs -> Some (List.fold_left ( +. ) 0. xs /. float_of_int (List.length xs))
  in
  let variance =
    match (mean, rets) with
    | Some _, _ :: _ :: _ ->
        let m = Option.get mean in
        Some (List.fold_left (fun s x -> s +. ((x -. m) ** 2.)) 0. rets /. float_of_int (List.length rets - 1))
    | _ -> None
  in
  let annualized_volatility = Option.map (fun x -> sqrt x *. sqrt (float_of_int periods_per_year)) variance in
  let final_equity = match List.rev days with [] -> initial_equity | day :: _ -> equity_of day in
  let annualized_return =
    if periods = 0 then None
    else if initial_equity <= 0L || final_equity <= 0L then Some (-1.)
    else Some (Float.pow (Int64.to_float final_equity /. Int64.to_float initial_equity)
                 (float_of_int periods_per_year /. float_of_int periods) -. 1.)
  in
  let sharpe =
    match mean, annualized_volatility with
    | Some mu, Some sigma when sigma > 0. -> Some (mu *. sqrt (float_of_int periods_per_year) /. sigma)
    | _ -> None
  in
  let curve = List.map equity_of days in
  let rec max_dd peak largest = function
    | [] -> largest
    | equity :: rest ->
        let peak = Int64.max peak equity in
        let drawdown = Int64.sub peak equity in
        let bps = match mul_div ~divisor:peak drawdown bps_scale with Ok x -> x | Error _ -> Int64.max_int in
        max_dd peak (Int64.max largest bps) rest
  in
  let total_turnover =
    match sum_int64 (List.map turnover_of days) with Ok x -> x | Error _ -> Int64.max_int
  in
  let years = float_of_int periods /. float_of_int periods_per_year in
  let sorted_returns = List.map return_of days in
  {
    periods;
    start_session = (match days with [] -> None | x :: _ -> Some x.session);
    end_session = (match List.rev days with [] -> None | x :: _ -> Some x.session);
    initial_equity;
    final_equity;
    annualized_return;
    annualized_volatility;
    sharpe;
    max_drawdown_bps = max_dd initial_equity 0L curve;
    annualized_turnover = if years <= 0. then None else Some (Int64.to_float total_turnover /. 10_000. /. years);
    total_turnover_bps = total_turnover;
    mean_period_return_bps = Option.map (fun x -> x *. 10_000.) mean;
    worst_period_return_1e8 = (match sorted_returns with [] -> None | xs -> Some (List.fold_left Int64.min Int64.max_int xs));
    best_period_return_1e8 = (match sorted_returns with [] -> None | xs -> Some (List.fold_left Int64.max Int64.min_int xs));
  }

let session_cutoff final_session =
  try
    let year = int_of_string (String.sub final_session 0 4) - 2 in
    let month = int_of_string (String.sub final_session 5 2) in
    let day = int_of_string (String.sub final_session 8 2) in
    let day = if month = 2 && day = 29 then 28 else day in
    Ok (Printf.sprintf "%04d-%02d-%02d" year month day)
  with _ -> Error "session must be YYYY-MM-DD"

let split_start groups =
  let count = List.length groups in
  if count < 2 then Error "at least two sessions are required for in-sample/OOS reporting"
  else
    let fraction_count = (count + 4) / 5 in
    let* final_session = match List.rev groups with [] -> Error "empty history" | (session, _) :: _ -> Ok session in
    let* two_year_start = session_cutoff final_session in
    let two_year_count = List.fold_left (fun n (session, _) -> if session >= two_year_start then n + 1 else n) 0 groups in
    let oos_count = min fraction_count two_year_count in
    if oos_count < 1 || oos_count >= count then Error "cannot form a nonempty chronological holdout"
    else
      let target = count - oos_count in
      let rec find i = function
        | [] -> Error "holdout boundary not found"
        | (session, _) :: _ when i = target -> Ok session
        | _ :: rest -> find (i + 1) rest
      in
      find 0 groups

let run config (rows : observation list) =
  let* () = validate_config config in
  if rows = [] then Error "input panel is empty"
  else
    let rec validate = function
      | [] -> Ok ()
      | row :: rest -> let* () = validate_observation row in validate rest
    in
    let* () = validate rows in
    let groups = group_by_session rows in
    let* () = validate_panel config groups in
    let* split_start_session = split_start groups |> Result.map (fun s -> s) in
    let accounts =
      List.init 5 (fun _ -> { nav = config.initial_equity_money_units; weights = [] })
    in
    let gross_account = List.nth accounts 0
    and net_account = List.nth accounts 1
    and double_account = List.nth accounts 2
    and market_account = List.nth accounts 3
    and sector_account = List.nth accounts 4 in
    let days = ref [] and positions = ref [] in
    let process (session, (group : observation list)) =
      let first = List.hd group in
      let scenario account cost_multiplier =
        let* trades =
          List.fold_left
            (fun acc (row : observation) ->
              let* acc = acc in
              let previous = held_weight row.symbol account in
              let* delta = Exec_units.checked_sub (Int64.of_int row.target_weight_bps) previous in
              let* delta_abs = if delta = Int64.min_int then Error "weight delta overflow" else Ok (Int64.abs delta) in
              let* notional = mul_div ~divisor:bps_scale account.nav delta_abs in
              if notional > 0L && row.adv_money_units <= 0L then
                Error ("positive trade has zero ADV: " ^ row.symbol ^ " " ^ session)
              else
                let* participation =
                  if notional = 0L then Ok 0L
                  else mul_div ~divisor:row.adv_money_units notional bps_scale
                in
                if participation > Int64.of_int config.max_participation_bps then
                  Error ("participation cap breached: " ^ row.symbol ^ " " ^ session)
                else
                  let* cost =
                    Exec_units.checked_mul delta_abs
                      (Int64.of_int (row.one_way_cost_bps * cost_multiplier))
                  in
                  let short_weight = max 0 (-row.target_weight_bps) in
                  let* annual_borrow =
                    Exec_units.checked_mul (Int64.of_int short_weight)
                      (Int64.of_int (row.borrow_rate_bps_annual * cost_multiplier))
                  in
                  let* borrow = mul_div ~divisor:252L annual_borrow (Int64.of_int row.borrow_days) in
                  let* capacity =
                    if delta_abs = 0L then Ok None
                    else mul_div ~divisor:delta_abs row.adv_money_units
                           (Int64.of_int config.max_participation_bps)
                         |> Result.map Option.some
                  in
                  Ok ((row, delta_abs, notional, participation, cost, borrow, capacity) :: acc))
            (Ok []) group
        in
        let trades = List.rev trades in
        let* gross_terms =
          List.fold_left
            (fun acc (row : observation) ->
              let* acc = acc in
              let* pnl = mul_div ~divisor:bps_scale
                  (Int64.of_int row.target_weight_bps) row.forward_total_return_1e8 in
              Ok (pnl :: acc)) (Ok []) group
        in
        let* gross_return = sum_int64 gross_terms in
        let* transaction_cost = sum_int64 (List.map (fun (_, _, _, _, cost, _, _) -> cost) trades) in
        let* borrow_cost = sum_int64 (List.map (fun (_, _, _, _, _, borrow, _) -> borrow) trades) in
        let* net_return = sum_int64 [ gross_return; Int64.neg transaction_cost; Int64.neg borrow_cost ] in
        let* turnover = sum_int64 (List.map (fun (_, delta, _, _, _, _, _) -> delta) trades) in
        let starting_equity = account.nav in
        let* new_nav = nav_after_return starting_equity net_return in
        let* new_weights =
          List.fold_left
            (fun acc (row : observation) ->
              let* acc = acc in
              let growth = Int64.add return_scale row.forward_total_return_1e8 in
              let denominator = Int64.add return_scale net_return in
              let* post_return = mul_div ~divisor:return_scale
                  (Int64.of_int row.target_weight_bps) growth in
              let* effective = mul_div ~divisor:denominator post_return return_scale in
              Ok ((row.symbol, effective) :: acc)) (Ok []) group
        in
        account.nav <- new_nav;
        account.weights <- List.rev new_weights;
        Ok (starting_equity, new_nav, net_return, gross_return, transaction_cost, borrow_cost, turnover, trades)
      in
      let* gross = scenario gross_account 0 in
      let* net = scenario net_account 1 in
      let* doubled = scenario double_account 2 in
      let* market_nav = nav_after_return market_account.nav first.benchmark_return_1e8 in
      let* sector_nav = nav_after_return sector_account.nav first.sector_return_1e8 in
      market_account.nav <- market_nav;
      sector_account.nav <- sector_nav;
      let _, gross_nav, _, gross_return, _, _, _, _ = gross in
      let starting_equity, net_nav, net_return, _, transaction_cost, borrow_cost, turnover_bps, net_trades = net in
      let _, _, double_return, _, _, _, _, _ = doubled in
      let active_names = List.length (List.filter (fun (row : observation) -> row.target_weight_bps <> 0) group) in
      let day = {
        session; entry_at = first.entry_at; exit_at = first.exit_at; regime = first.regime;
        gross_return_1e8 = gross_return; net_return_1e8 = net_return;
        doubled_cost_return_1e8 = double_return;
        benchmark_return_1e8 = first.benchmark_return_1e8;
        sector_return_1e8 = first.sector_return_1e8;
        turnover_bps; transaction_cost_1e8 = transaction_cost;
        borrow_cost_1e8 = borrow_cost; starting_equity; gross_equity = gross_nav;
        net_equity = net_nav; doubled_cost_equity = double_account.nav;
        benchmark_equity = market_nav; sector_equity = sector_nav; active_names;
      } in
      days := day :: !days;
      List.iter
        (fun ((row : observation), delta, notional, participation, _, borrow, capacity) ->
          positions := {
            session; symbol = row.symbol; sector = row.sector; regime = row.regime;
            eligible = row.eligible; target_weight_bps = row.target_weight_bps;
            forward_total_return_1e8 = row.forward_total_return_1e8;
            turnover_bps = delta; order_notional_money_units = notional;
            participation_bps = participation; one_way_cost_bps = row.one_way_cost_bps;
            borrow_cost_1e8 = borrow; capacity_money_units = capacity; source_id = row.source_id;
            source_sha256 = row.source_sha256;
          } :: !positions)
        net_trades;
      Ok ()
    in
    let rec process_all = function [] -> Ok () | group :: rest -> let* () = process group in process_all rest in
    let* () = process_all groups in
    let all_days = List.rev !days and positions = List.rev !positions in
    let select days pred = List.filter pred days in
    let within (days : day list) ret equity turnover initial =
      metrics ~periods_per_year:config.periods_per_year ~initial_equity:initial ~days
        ~return_of:ret ~equity_of:equity ~turnover_of:turnover
    in
    let full_gross = within all_days (fun d -> d.gross_return_1e8) (fun d -> d.gross_equity) (fun d -> d.turnover_bps) config.initial_equity_money_units in
    let full_net = within all_days (fun d -> d.net_return_1e8) (fun d -> d.net_equity) (fun d -> d.turnover_bps) config.initial_equity_money_units in
    let full_double = within all_days (fun d -> d.doubled_cost_return_1e8) (fun d -> d.doubled_cost_equity) (fun d -> d.turnover_bps) config.initial_equity_money_units in
    let in_days = select all_days (fun d -> d.session < split_start_session) in
    let out_days = select all_days (fun d -> d.session >= split_start_session) in
    let in_sample_net = within in_days (fun d -> d.net_return_1e8) (fun d -> d.net_equity) (fun d -> d.turnover_bps) config.initial_equity_money_units in
    let out_initial = match List.rev in_days with [] -> config.initial_equity_money_units | d :: _ -> d.net_equity in
    let out_of_sample_net = within out_days (fun d -> d.net_return_1e8) (fun d -> d.net_equity) (fun d -> d.turnover_bps) out_initial in
    let full_benchmark = within all_days (fun d -> d.benchmark_return_1e8) (fun d -> d.benchmark_equity) (fun _ -> 0L) config.initial_equity_money_units in
    let full_sector_benchmark = within all_days (fun d -> d.sector_return_1e8) (fun d -> d.sector_equity) (fun _ -> 0L) config.initial_equity_money_units in
    let grouped key_of =
      let table = Hashtbl.create 16 in
      List.iter (fun (day : day) -> let key = key_of day in let prior = Option.value (Hashtbl.find_opt table key) ~default:[] in Hashtbl.replace table key (day :: prior)) all_days;
      Hashtbl.fold
        (fun key days acc ->
          let days = List.rev days in
          let nav = ref config.initial_equity_money_units in
          let rebased = List.map (fun (day : day) ->
            let start = !nav in
            let next = match nav_after_return start day.net_return_1e8 with
              | Ok value -> value
              | Error message -> failwith message
            in
            nav := next;
            { day with starting_equity = start; net_equity = next }) days in
          (key, within rebased (fun d -> d.net_return_1e8) (fun d -> d.net_equity) (fun d -> d.turnover_bps) config.initial_equity_money_units) :: acc)
        table []
      |> List.sort compare
    in
    let annual_net = grouped (fun day -> try int_of_string (String.sub day.session 0 4) with _ -> 0) in
    let regime_net = grouped (fun day -> day.regime) in
    let source_hashes = List.map (fun (row : observation) -> row.source_sha256) rows |> List.sort_uniq String.compare in
    Ok { split_start_session; all_days; positions; full_gross; full_net; full_double;
         in_sample_net; out_of_sample_net; full_benchmark; full_sector_benchmark;
         annual_net; regime_net; source_hashes; input_rows = List.length rows }
