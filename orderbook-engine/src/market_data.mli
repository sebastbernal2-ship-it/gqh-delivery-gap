(** Market data: CSV parser and random market data generator. *)

type feed_event = {
  venue : string;
  symbol : string;
  epoch : int;
  sequence : int;
  event_time : Timestamp.t;
  received_time : Timestamp.t option;
  event : Market_types.event;
}
(** A market event plus source identity that is not part of matching logic. *)

type gen_config = {
  symbols : string list;
  start_time : Timestamp.t;
  speed : float;  (** events per second *)
  volatility : float;  (** price volatility (std dev in pips) *)
  base_spread : float;  (** base spread in percent *)
  duration_s : float;  (** how many seconds of data to generate *)
  max_orders : int;  (** max concurrent orders in the book *)
  rng_seed : int option;
}
(** Configuration for the random market data generator. *)

val default_config : gen_config

val parse_csv : string -> Market_types.event list Serror.t
(** [parse_csv path] reads events from a CSV file. Malformed rows are skipped.
    Format: timestamp,order_id,side,price,size,action[,valid_time]. *)

val parse_csv_strict : string -> Market_types.event list Serror.t
(** [parse_csv_strict path] rejects malformed data rows. *)

val parse_feed_csv : string -> feed_event list Serror.t
(** [parse_feed_csv path] parses venue and symbol metadata with strict row
    validation. *)

val generate : gen_config -> Market_types.event list
(** [generate config] produces a list of market events simulating realistic
    order flow (adds, cancels, partial fills). *)

val generate_feed : gen_config -> feed_event list
(** [generate_feed config] adds symbol and sequence metadata to generated
    events. *)

val group_by_symbol : feed_event list -> (string * Market_types.event list) list
(** [group_by_symbol events] returns one ordered event stream per symbol. *)

val validate_feed : feed_event list -> unit Serror.t
(** [validate_feed events] checks non-empty identity fields and increasing
    sequence numbers per venue and symbol. *)

val parse_nyse_taq : trading_date:string -> string -> feed_event list Serror.t
(** [parse_nyse_taq ~trading_date path] parses NYSE National TAQ Integrated Feed
    CSV or gzip CSV order messages. *)

val write_csv : string -> Market_types.event list -> unit Serror.t
(** [write_csv path events] writes events to a CSV file. *)
