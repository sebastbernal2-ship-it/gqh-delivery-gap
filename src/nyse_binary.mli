(** Decoder for raw little-endian NYSE Pillar Integrated Feed messages. *)

type config = { venue : string; symbol_mappings : (int * string * int) list }

val default_config : config
val read_symbol_mapping : string -> (int * string * int) list Serror.t

val parse_bytes :
  trading_date:string -> config -> bytes -> Market_data.feed_event list Serror.t

val parse_payloads :
  trading_date:string ->
  config ->
  bytes list ->
  Market_data.feed_event list Serror.t

val parse_file :
  trading_date:string ->
  config ->
  string ->
  Market_data.feed_event list Serror.t
(** [parse_file ~trading_date config path] decodes a concatenated raw binary
    message stream. Type 2 time references and Type 3 symbol mappings must
    precede the order messages that use them. *)
