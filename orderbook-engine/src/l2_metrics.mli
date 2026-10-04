(** Descriptive metrics for visible L2 snapshots. *)

type point = {
  timestamp : Timestamp.t;
  mid_price : float;
  spread_bps : float;
  bid_depth : float;
  ask_depth : float;
  imbalance : float;
}

type summary = {
  count : int;
  mean_spread_bps : float;
  min_spread_bps : float;
  max_spread_bps : float;
  mean_imbalance : float;
}

val measure : Hf_l2.snapshot -> point Serror.t
val summarize : point list -> summary
