(** SonarX's public Hyperliquid L2 snapshot format. *)

type level = { price : string; size : string; order_count : int }

type snapshot = {
  height : int;
  block_time : Timestamp.t;
  market : string;
  bids : level list;
  asks : level list;
}

val parse_l2_file : string -> snapshot list Serror.t
(** [parse_l2_file path] parses a SonarX JSON or gzip-compressed JSON snapshot
    file. Decimal prices and sizes remain strings to avoid losing precision. *)
