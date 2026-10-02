(** Snapshot-based strategy backtesting for derived Hyperliquid L2 data. *)

type order = {
  side : L2_execution.side;
  size : float;
  limit_price : float option;
}

type portfolio = {
  timestamp : Timestamp.t;
  cash : float;
  position : float;
  equity : float;
  fees : float;
  funding_paid : float;
  trade_count : int;
}

type trade = {
  timestamp : Timestamp.t;
  side : L2_execution.side;
  price : float;
  size : float;
  fee : float;
}

type point = {
  timestamp : Timestamp.t;
  equity : float;
  cash : float;
  position : float;
}

type result = {
  initial_cash : float;
  final_portfolio : portfolio;
  trades : trade list;
  curve : point list;
}

type strategy = portfolio -> Hf_l2.snapshot -> order list
type funding_rate = Hf_l2.snapshot -> float

val run :
  initial_cash:float ->
  ?fee_bps:float ->
  ?latency_snapshots:int ->
  ?latency_ms:int64 ->
  ?funding_rate:funding_rate ->
  strategy ->
  Hf_l2.snapshot list ->
  result
(** [run ~initial_cash ~fee_bps ~latency_snapshots ~latency_ms strategy snapshots]
    runs [strategy] once per snapshot. Use one latency option. Snapshot latency
    schedules orders by index, while time latency schedules orders for the first
    later snapshot at or after the due timestamp. [funding_rate] returns a
    signed fractional rate, where a positive rate is paid by a long position. *)
