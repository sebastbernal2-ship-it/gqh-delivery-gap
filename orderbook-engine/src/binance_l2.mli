(** Binance Futures L2 updates captured by Tardis. *)

type level = { price : string; size : string }

type message =
  | Snapshot of {
      raw_line : string;
      received_time : Timestamp.t;
      event_time : Timestamp.t;
      last_update_id : int64;
      bids : level list;
      asks : level list;
    }
  | Update of {
      raw_line : string;
      received_time : Timestamp.t;
      event_time : Timestamp.t;
      first_update_id : int64;
      final_update_id : int64;
      previous_update_id : int64;
      bids : level list;
      asks : level list;
    }

type evidence = {
  source_path : string;
  byte_count : int;
  line_count : int;
  first_received_time : Timestamp.t option;
  last_received_time : Timestamp.t option;
}

type state = {
  raw_line : string;
  event_time : Timestamp.t;
  received_time : Timestamp.t;
  last_update_id : int64;
  bids : level list;
  asks : level list;
}

type normalized_kind = Snapshot_row | Update_row

type normalized_row = {
  kind : normalized_kind;
  segment : int64;
  symbol : string;
  received_time : Timestamp.t;
  event_time : Timestamp.t;
  source_path : string;
  source_sha256 : string;
  applied : bool;
  last_update_id : int64 option;
  first_update_id : int64 option;
  final_update_id : int64 option;
  previous_update_id : int64 option;
  bids : level list;
  asks : level list;
}

val parse_normalized_row : Yojson.Safe.t -> normalized_row Serror.t
val parse_normalized_row_with_instrument :
  Binance_units.instrument -> Yojson.Safe.t -> normalized_row Serror.t
val parse_normalized_lines : string list -> normalized_row list Serror.t
val parse_normalized_lines_with_instrument :
  Binance_units.instrument -> string list -> normalized_row list Serror.t
val parse_normalized_file : string -> normalized_row list Serror.t
val parse_normalized_file_with_instrument :
  Binance_units.instrument -> string -> normalized_row list Serror.t
val replay_normalized :
  instrument:Binance_units.instrument -> normalized_row list -> state list Serror.t

val parse_lines : string list -> message list Serror.t
val parse_file : string -> message list Serror.t
val evidence : string -> evidence Serror.t
val replay :
  instrument:Binance_units.instrument -> message list -> state list Serror.t
val to_hf_l2 :
  instrument:Binance_units.instrument ->
  symbol:string -> state list -> Hf_l2.snapshot list Serror.t
