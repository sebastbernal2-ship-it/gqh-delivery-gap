(** Parser for SonarX's public Hyperliquid L2 summary snapshots. *)

type level = { price : string; size : string; order_count : int }

type snapshot = {
  height : int;
  block_time : Timestamp.t;
  market : string;
  bids : level list;
  asks : level list;
}

let member name json = Yojson.Safe.Util.member name json

let required_string name json =
  match member name json with
  | `String value -> value
  | _ -> failwith ("missing SonarX string field: " ^ name)

let required_int name json =
  match member name json with
  | `Int value -> value
  | `Intlit value -> int_of_string value
  | _ -> failwith ("missing SonarX integer field: " ^ name)

let parse_timestamp value =
  let value =
    if
      String.contains value 'T'
      && (String.contains value 'Z' || String.contains value '+')
    then value
    else value ^ "Z"
  in
  match Timestamp.of_string value with
  | Ok timestamp -> timestamp
  | Error _ -> failwith "invalid SonarX block_time"

let parse_level json =
  {
    price = required_string "px" json;
    size = required_string "sz" json;
    order_count = required_int "n" json;
  }

let parse_levels name json =
  match member name json with
  | `List levels -> List.map parse_level levels
  | _ -> failwith ("missing SonarX level array: " ^ name)

let parse_snapshot json =
  {
    height = required_int "height" json;
    block_time = parse_timestamp (required_string "block_time" json);
    market = required_string "market" json;
    bids = parse_levels "bids" json;
    asks = parse_levels "asks" json;
  }

let open_input path =
  if Filename.check_suffix path ".gz" then
    (`Process, Unix.open_process_in ("gzip -dc -- " ^ Filename.quote path))
  else (`File, open_in path)

let close_input kind ic =
  match kind with
  | `File ->
      close_in ic;
      Unix.WEXITED 0
  | `Process -> Unix.close_process_in ic

let parse_l2_file (path : string) : snapshot list Serror.t =
  try
    let kind, ic = open_input path in
    let json = Yojson.Safe.from_channel ic in
    let close_status = close_input kind ic in
    match close_status with
    | Unix.WEXITED 0 -> (
        match json with
        | `List snapshots -> Ok (List.map parse_snapshot snapshots)
        | _ -> Serror.fail "SonarX file must contain a JSON array")
    | _ -> Serror.fail "gzip failed while reading SonarX data"
  with
  | Sys_error message -> Serror.fail ("IO error: " ^ message)
  | Yojson.Json_error message -> Serror.fail ("JSON error: " ^ message)
  | Failure message -> Serror.fail ("Parse error: " ^ message)
  | Invalid_argument message -> Serror.fail ("Parse error: " ^ message)
