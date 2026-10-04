(** Binance Futures mark-price and forced-liquidation streams captured by
    Tardis. *)

type mark_price = {
  received_time : Timestamp.t;
  event_time : Timestamp.t;
  symbol : string;
  mark : float;
  index : float;
  funding_rate : float;
  next_funding_time : Timestamp.t;
}

type liquidation = {
  received_time : Timestamp.t;
  event_time : Timestamp.t;
  symbol : string;
  side : string;
  price : float;
  quantity : float;
}

let ( let* ) result f = Result.bind result f

let timestamp_string value =
  match Timestamp.of_string value with
  | Ok value -> Ok value
  | Error message -> Serror.fail message

let timestamp_ms value =
  match Ptime.of_float_s (Int64.to_float value /. 1000.0) with
  | Some value -> Ok (Timestamp.of_ptime value)
  | None -> Serror.failf "invalid Binance timestamp %Ld" value

let string name json =
  match Yojson.Safe.Util.member name json with
  | `String value -> Ok value
  | _ -> Serror.failf "missing Binance string field %s" name

let float name json =
  let* value = string name json in
  try Ok (float_of_string value)
  with Failure _ -> Serror.failf "invalid Binance number %s" name

let int64 name json =
  match Yojson.Safe.Util.member name json with
  | `Int value -> Ok (Int64.of_int value)
  | `Intlit value -> (
      match Int64.of_string_opt value with
      | Some value -> Ok value
      | None -> Serror.failf "invalid Binance integer field %s" name)
  | _ -> Serror.failf "missing Binance integer field %s" name

let envelope line =
  match String.index_opt line ' ' with
  | None -> Serror.fail "Binance line has no local timestamp"
  | Some separator -> (
      let received = String.sub line 0 separator in
      let json =
        String.sub line (separator + 1) (String.length line - separator - 1)
      in
      let* received_time = timestamp_string received in
      let json =
        try Yojson.Safe.from_string json
        with Yojson.Json_error message -> raise (Failure message)
      in
      match Yojson.Safe.Util.member "data" json with
      | `Assoc _ as data -> Ok (received_time, data)
      | _ -> Serror.fail "Binance data field is not an object")

let parse_mark_line line =
  try
    let* received_time, data = envelope line in
    let* event_ms = int64 "E" data in
    let* event_time = timestamp_ms event_ms in
    let* funding_ms = int64 "T" data in
    let* next_funding_time = timestamp_ms funding_ms in
    let* symbol = string "s" data in
    let* mark = float "p" data in
    let* index = float "i" data in
    let* funding_rate = float "r" data in
    Ok
      {
        received_time;
        event_time;
        symbol;
        mark;
        index;
        funding_rate;
        next_funding_time;
      }
  with Failure message -> Serror.fail ("JSON error: " ^ message)

let parse_liquidation_line line =
  try
    let* received_time, data = envelope line in
    let* event_ms = int64 "E" data in
    let* event_time = timestamp_ms event_ms in
    let order = Yojson.Safe.Util.member "o" data in
    let* symbol = string "s" order in
    let* side = string "S" order in
    let* price = float "ap" order in
    let* quantity = float "z" order in
    Ok { received_time; event_time; symbol; side; price; quantity }
  with Failure message -> Serror.fail ("JSON error: " ^ message)

let parse_lines parse_line lines =
  let rec loop acc = function
    | [] -> Ok (List.rev acc)
    | line :: rest ->
        if String.trim line = "" then loop acc rest
        else
          let* value = parse_line line in
          loop (value :: acc) rest
  in
  loop [] lines

let parse_mark_lines lines = parse_lines parse_mark_line lines
let parse_liquidation_lines lines = parse_lines parse_liquidation_line lines

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

let parse_mark_file path =
  let* lines = read_lines path in
  parse_mark_lines lines

let parse_liquidation_file path =
  let* lines = read_lines path in
  parse_liquidation_lines lines

let funding_rate marks (snapshot : Hf_l2.snapshot) =
  List.fold_left
    (fun current (mark : mark_price) ->
      if Timestamp.compare mark.event_time snapshot.timestamp <= 0 then
        mark.funding_rate
      else current)
    0.0 marks
