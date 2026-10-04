type result = {
  account : Asset_account.t;
  processed : int;
  last_mark_ticks : int64 option;
}

let ( let* ) result f = Result.bind result f

let valid_sha256 text =
  String.length text = 64
  && String.for_all
       (function '0' .. '9' | 'a' .. 'f' | 'A' .. 'F' -> true | _ -> false)
       text

let json_object text =
  try
    match Yojson.Safe.from_string text with
    | `Assoc fields -> Ok fields
    | _ -> Serror.fail "lifecycle payload must be a JSON object"
  with Yojson.Json_error _ -> Serror.fail "invalid lifecycle JSON"

let int64_field fields name =
  let value = List.assoc_opt name fields in
  match value with
  | Some (`Int number) -> Ok (Int64.of_int number)
  | Some (`Intlit text) -> (
      try Ok (Int64.of_string text)
      with Failure _ -> Serror.failf "invalid integer field %s" name)
  | _ -> Serror.failf "missing integer field %s" name

let time_field fields name =
  match List.assoc_opt name fields with
  | Some (`String text) -> Timestamp.of_string text
  | _ -> Serror.failf "missing timestamp field %s" name

let apply_observation account at (observation : Exec_event.observation) =
  match observation.data_type with
  | "equity_cash_settlement" -> Asset_account.settle_receivables account ~at
  | "equity_split" ->
      let* fields = json_object observation.payload in
      let* numerator = int64_field fields "numerator" in
      let* denominator = int64_field fields "denominator" in
      Asset_account.split_equity account ~numerator ~denominator
  | "equity_dividend" ->
      let* fields = json_object observation.payload in
      let* amount_per_share = int64_field fields "amount_per_share" in
      let* payable_at = time_field fields "payable_at" in
      Asset_account.equity_dividend account ~amount_per_share ~payable_at
  | "future_settlement" ->
      let* fields = json_object observation.payload in
      let* settlement_ticks = int64_field fields "settlement_ticks" in
      Asset_account.future_settlement account ~at ~settlement_ticks
  | "future_expiry" ->
      let* fields = json_object observation.payload in
      let* final_ticks = int64_field fields "final_ticks" in
      Asset_account.future_expiry account ~at ~final_ticks
  | "option_expiry" ->
      let* fields = json_object observation.payload in
      let* underlying_ticks = int64_field fields "underlying_ticks" in
      Asset_account.option_expiry account ~at ~underlying_ticks
  | _ -> Ok account

let run spec ~initial_cash ~equity_settlement events =
  let* account = Asset_account.create spec ~cash:initial_cash in
  let rec replay previous_time processed last_mark account = function
    | [] -> Ok { account; processed; last_mark_ticks = last_mark }
    | event :: rest ->
        if
          event.Exec_event.venue <> spec.Instrument_spec.venue
          || event.Exec_event.symbol <> spec.Instrument_spec.symbol
        then Serror.fail "event instrument does not match account specification"
        else if
          event.Exec_event.source_id = ""
          || event.Exec_event.source_path = ""
          || not (valid_sha256 event.Exec_event.source_sha256)
        then Serror.fail "event provenance is incomplete or malformed"
        else if event.Exec_event.quality <> Exec_event.Healthy then
          Serror.fail "suspect event cannot change the account"
        else if
          match previous_time with
          | None -> false
          | Some previous ->
              Timestamp.compare event.Exec_event.receive_time previous < 0
        then Serror.fail "events are not ordered by receive time"
        else
          let at = event.Exec_event.receive_time in
          let* account, last_mark =
            match event.Exec_event.payload with
            | Exec_event.Fill fill ->
                let settle_at =
                  match spec.Instrument_spec.kind with
                  | Instrument_spec.Equity
                    when fill.Exec_event.side = Exec_event.Sell ->
                      Some (equity_settlement at)
                  | _ -> None
                in
                let* updated =
                  Asset_account.fill_with_fee account ~at
                    ~side:fill.Exec_event.side
                    ~price_ticks:fill.Exec_event.price_ticks
                    ~quantity_units:fill.Exec_event.quantity_units
                    ~fee:fill.Exec_event.fee ~settle_at
                in
                Ok (updated, Some fill.Exec_event.price_ticks)
            | Exec_event.Funding funding ->
                let* updated =
                  Asset_account.perpetual_funding account
                    ~mark_ticks:funding.Exec_event.mark_ticks
                    ~rate_units:funding.Exec_event.rate
                in
                Ok (updated, Some funding.Exec_event.mark_ticks)
            | Exec_event.Mark mark ->
                if mark.Exec_event.mark_ticks <= 0L then
                  Serror.fail "mark price must be positive"
                else Ok (account, Some mark.Exec_event.mark_ticks)
            | Exec_event.Observation observation ->
                let* updated = apply_observation account at observation in
                Ok (updated, last_mark)
            | _ -> Ok (account, last_mark)
          in
          replay (Some at) (processed + 1) last_mark account rest
  in
  replay None 0 None account events
