(** Instrumentation and metrics for the order book. *)

type t = {
  timestamp : Timestamp.t;
  event_count : int;
  order_count : int;
  bid_count : int;
  ask_count : int;
  total_bid_size : Size.t;
  total_ask_size : Size.t;
  spread : Price.t option;
  mid_price : Price.t option;
  micro_price : Price.t option;
  top_bid_price : Price.t option;
  top_ask_price : Price.t option;
  events_per_second : float;
}
(** A snapshot of metrics at a point in time. *)

type collector
(** Opaque metrics collector. *)

val create : Order_book.t -> collector
(** [create book] creates a metrics collector attached to the given book. *)

val record : collector -> t
(** [record c] records a metric snapshot after processing an event. *)

val report : t -> unit
(** [report m] logs a formatted metrics report via the [Logs] library. *)

val json_report : t -> string
(** [json_report m] returns a JSON-formatted metrics report string. *)
