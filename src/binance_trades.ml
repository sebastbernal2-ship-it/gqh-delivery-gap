(** Binance Futures aggregate trades captured beside depth updates. *)

type trade = {
  raw_line : string;
  received_time : Timestamp.t;
  event_time : Timestamp.t;
  trade_time : Timestamp.t;
  symbol : string;
  trade_id : int64;
  price : float;
  quantity : float;
  buyer_is_maker : bool;
}

let ( let* ) result f = Result.bind result f

let field name json =
  match Yojson.Safe.Util.member name json with
  | `Null -> Serror.failf "missing Binance trade field %s" name
  | value -> Ok value

let string_field name json =
  let* value = field name json in
  match value with
  | `String value -> Ok value
  | _ -> Serror.failf "Binance trade field %s is not a string" name

let bool_field name json =
  let* value = field name json in
  match value with
  | `Bool value -> Ok value
  | _ -> Serror.failf "Binance trade field %s is not a boolean" name

let int64_field name json =
  let* value = field name json in
  match value with
  | `Int value -> Ok (Int64.of_int value)
  | `Intlit value -> (
      match Int64.of_string_opt value with
      | Some value -> Ok value
      | None -> Serror.failf "invalid Binance trade integer %s" name)
  | _ -> Serror.failf "Binance trade field %s is not an integer" name

let float_field name json =
  let* value = string_field name json in
  try
    let value = float_of_string value in
    if Float.is_nan value || Float.is_infinite value || value <= 0.0 then
      Serror.failf "invalid Binance trade number %s" name
    else Ok value
  with Failure _ -> Serror.failf "invalid Binance trade number %s" name

let timestamp_ms name value =
  if value < 0L then Serror.failf "negative Binance trade timestamp %s" name
  else
    match Ptime.of_float_s (Int64.to_float value /. 1000.0) with
    | Some value -> Ok (Timestamp.of_ptime value)
    | None -> Serror.failf "invalid Binance trade timestamp %s" name

let timestamp_string value =
  match Timestamp.of_string value with
  | Ok timestamp -> Ok timestamp
  | Error message ->
      if
        String.length value >= 11
        && value.[4] = '.' && value.[7] = '.' && value.[10] = 'D'
      then
        let normalized = Bytes.of_string value in
        Bytes.set normalized 4 '-';
        Bytes.set normalized 7 '-';
        Bytes.set normalized 10 'T';
        (match Timestamp.of_string (Bytes.to_string normalized ^ "Z") with
        | Ok timestamp -> Ok timestamp
        | Error _ -> Serror.fail message)
      else Serror.fail message

let parse_data ~raw_line ~received_time data =
  let* event = string_field "e" data in
  let* () =
    if event = "aggTrade" then Ok ()
    else Serror.failf "unexpected Binance trade event %s" event
  in
  let* event_ms = int64_field "E" data in
  let* event_time = timestamp_ms "event" event_ms in
  let* trade_time_ms = int64_field "T" data in
  let* trade_time = timestamp_ms "trade" trade_time_ms in
  let* symbol = string_field "s" data in
  let* trade_id = int64_field "a" data in
  let* price = float_field "p" data in
  let* quantity = float_field "q" data in
  let* buyer_is_maker = bool_field "m" data in
  let* () =
    if symbol = "" then Serror.fail "empty Binance trade symbol"
    else if trade_id < 0L then Serror.fail "negative Binance trade ID"
    else Ok ()
  in
  Ok
    {
      raw_line;
      received_time;
      event_time;
      trade_time;
      symbol;
      trade_id;
      price;
      quantity;
      buyer_is_maker;
    }

let parse_line line =
  match String.index_opt line ' ' with
  | None -> Serror.fail "Binance trade line has no local timestamp"
  | Some separator ->
      let received = String.sub line 0 separator in
      let json =
        String.sub line (separator + 1) (String.length line - separator - 1)
      in
      let* received_time = timestamp_string received in
      let* json =
        try Ok (Yojson.Safe.from_string json)
        with Yojson.Json_error message ->
          Serror.fail ("JSON error: " ^ message)
      in
      let* data = field "data" json in
      parse_data ~raw_line:line ~received_time data

let parse_lines lines =
  let rec loop acc = function
    | [] -> Ok (List.rev acc)
    | line :: rest ->
        if String.trim line = "" then loop acc rest
        else
          let* value = parse_line line in
          loop (value :: acc) rest
  in
  loop [] lines

let parse_normalized_row json =
  let* received = string_field "received_time" json in
  let* received_time = timestamp_string received in
  let* event_ms = int64_field "event_time_ms" json in
  let* event_time = timestamp_ms "event" event_ms in
  let* trade_time_ms = int64_field "trade_time_ms" json in
  let* trade_time = timestamp_ms "trade" trade_time_ms in
  let* source_path = string_field "source_path" json in
  let* symbol = string_field "symbol" json in
  let* trade_id = int64_field "trade_id" json in
  let* price = float_field "price" json in
  let* quantity = float_field "quantity" json in
  let* buyer_is_maker = bool_field "buyer_is_maker" json in
  let* source_sha256 = string_field "source_sha256" json in
  let* () =
    if source_path = "" || source_sha256 = "" then
      Serror.fail "missing Binance trade provenance"
    else Ok ()
  in
  if trade_id < 0L then Serror.fail "negative Binance trade ID"
  else
    Ok
      {
        raw_line = source_path;
        received_time;
        event_time;
        trade_time;
        symbol;
        trade_id;
        price;
        quantity;
        buyer_is_maker;
      }

let parse_normalized_row_with_instrument instrument json =
  let* trade = parse_normalized_row json in
  let* price = string_field "price" json in
  let* quantity = string_field "quantity" json in
  let* _ = Binance_units.to_price_ticks instrument price in
  let* _ = Binance_units.to_quantity_lots instrument quantity in
  Ok trade

let parse_normalized_lines lines =
  let rec loop acc = function
    | [] -> Ok (List.rev acc)
    | line :: rest ->
        if String.trim line = "" then loop acc rest
        else
          let* json =
            try Ok (Yojson.Safe.from_string line)
            with Yojson.Json_error message ->
              Serror.fail ("JSON error: " ^ message)
          in
          let* value = parse_normalized_row json in
          loop (value :: acc) rest
  in
  loop [] lines

let parse_normalized_lines_with_instrument instrument lines =
  let rec loop acc = function
    | [] -> Ok (List.rev acc)
    | line :: rest ->
        if String.trim line = "" then loop acc rest
        else
          let* json =
            try Ok (Yojson.Safe.from_string line)
            with Yojson.Json_error message ->
              Serror.fail ("JSON error: " ^ message)
          in
          let* value = parse_normalized_row_with_instrument instrument json in
          loop (value :: acc) rest
  in
  loop [] lines

let read_lines path =
  try
    let ic = open_in path in
    let rec loop acc =
      match input_line ic with
      | line -> loop (line :: acc)
      | exception End_of_file ->
          close_in ic;
          Ok (List.rev acc)
    in
    loop []
  with Sys_error message -> Serror.fail ("IO error: " ^ message)

let parse_file path =
  let* lines = read_lines path in
  parse_lines lines

let parse_normalized_file path =
  let* lines = read_lines path in
  parse_normalized_lines lines

let parse_normalized_file_with_instrument instrument path =
  let* lines = read_lines path in
  parse_normalized_lines_with_instrument instrument lines
