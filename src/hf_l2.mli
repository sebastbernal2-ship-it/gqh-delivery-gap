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

val parse_csv : string -> snapshot list Serror.t
(** [parse_csv path] parses the 47-column, 10-level derived L2 CSV format
    published by the free Hugging Face samples. *)
