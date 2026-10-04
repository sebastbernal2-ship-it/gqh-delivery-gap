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

val parse_mark_lines : string list -> mark_price list Serror.t
val parse_liquidation_lines : string list -> liquidation list Serror.t
val parse_mark_file : string -> mark_price list Serror.t
val parse_liquidation_file : string -> liquidation list Serror.t
val funding_rate : mark_price list -> Hf_l2.snapshot -> float
