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

val parse_line : string -> trade Serror.t
val parse_lines : string list -> trade list Serror.t
val parse_file : string -> trade list Serror.t
val parse_normalized_row : Yojson.Safe.t -> trade Serror.t
val parse_normalized_row_with_instrument :
  Binance_units.instrument -> Yojson.Safe.t -> trade Serror.t
val parse_normalized_lines : string list -> trade list Serror.t
val parse_normalized_lines_with_instrument :
  Binance_units.instrument -> string list -> trade list Serror.t
val parse_normalized_file : string -> trade list Serror.t
val parse_normalized_file_with_instrument :
  Binance_units.instrument -> string -> trade list Serror.t
