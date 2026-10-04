(** Parser for the free Hugging Face Hyperliquid L2 sample format. *)

type level = { price : float; cumulative_size : float; distance_bps : float }

type snapshot = {
  timestamp : Timestamp.t;
  symbol : string;
  mid_price : float;
  traded_volume : float;
  bids : level list;
  asks : level list;
}

let header =
  [
    "timestamp_utc";
    "instrument_symbol";
    "open_price";
    "high_price";
    "low_price";
    "close_price";
    "interval_traded_volume";
  ]
  @ (List.init 10 (fun index ->
         let level = index + 1 in
         [
           Printf.sprintf "bid_volume_level_%d" level;
           Printf.sprintf "ask_volume_level_%d" level;
           Printf.sprintf "bid_distance_level_%d" level;
           Printf.sprintf "ask_distance_level_%d" level;
         ])
    |> List.flatten)

let float_field row index =
  try float_of_string (List.nth row index)
  with Failure _ | Invalid_argument _ ->
    failwith "invalid Hugging Face number"

let parse_level row level_index ~mid_price ~bid =
  let offset = 7 + (level_index * 4) in
  let size = float_field row (offset + if bid then 0 else 1) in
  let distance_bps = float_field row (offset + if bid then 2 else 3) in
  let price =
    if bid then mid_price *. (1.0 -. (distance_bps /. 10_000.0))
    else mid_price *. (1.0 +. (distance_bps /. 10_000.0))
  in
  { price; cumulative_size = size; distance_bps }

let parse_row row =
  if List.length row <> List.length header then
    failwith "invalid Hugging Face L2 column count"
  else
    let timestamp =
      match Timestamp.of_string (List.nth row 0) with
      | Ok value -> value
      | Error _ -> failwith "invalid Hugging Face timestamp"
    in
    let mid_price = float_field row 5 in
    {
      timestamp;
      symbol = List.nth row 1;
      mid_price;
      traded_volume = float_field row 6;
      bids =
        List.init 10 (fun level -> parse_level row level ~mid_price ~bid:true);
      asks =
        List.init 10 (fun level -> parse_level row level ~mid_price ~bid:false);
    }

let parse_csv (path : string) : snapshot list Serror.t =
  try
    let ic = open_in path in
    let csv_ic = Csv.of_channel ic in
    let rows = ref [] in
    let first = ref true in
    Csv.iter
      ~f:(fun row ->
        if !first then begin
          first := false;
          if row <> header then failwith "invalid Hugging Face L2 header"
        end
        else rows := parse_row row :: !rows)
      csv_ic;
    close_in ic;
    Ok (List.rev !rows)
  with
  | Sys_error message -> Serror.fail ("IO error: " ^ message)
  | Failure message -> Serror.fail ("Parse error: " ^ message)
