(** Exact single-instrument account. Each account is bound to a validated,
    effective-dated instrument specification. Cash equities and options use
    premium cash flows; futures and perpetuals use linear variation margin. *)

type receivable = { due : Timestamp.t; amount : int64 }

type t = {
  spec : Instrument_spec.t;
  cash : int64;
  receivables : receivable list;
  position_units : int64;
  entry_ticks : int64 option;
  realized_pnl : int64;
  fees : int64;
  funding_paid : int64;
  closed : bool;
}

val create : Instrument_spec.t -> cash:int64 -> t Serror.t

val fill :
  t ->
  at:Timestamp.t ->
  side:Exec_event.side ->
  price_ticks:int64 ->
  quantity_units:int64 ->
  fee_bps:int ->
  settle_at:Timestamp.t option ->
  t Serror.t

val fill_with_fee :
  t ->
  at:Timestamp.t ->
  side:Exec_event.side ->
  price_ticks:int64 ->
  quantity_units:int64 ->
  fee:int64 ->
  settle_at:Timestamp.t option ->
  t Serror.t

val equity : t -> mark_ticks:int64 -> int64 Serror.t
val settle_receivables : t -> at:Timestamp.t -> t Serror.t
val split_equity : t -> numerator:int64 -> denominator:int64 -> t Serror.t

val equity_dividend :
  t -> amount_per_share:int64 -> payable_at:Timestamp.t -> t Serror.t

val future_settlement :
  t -> at:Timestamp.t -> settlement_ticks:int64 -> t Serror.t

val future_expiry : t -> at:Timestamp.t -> final_ticks:int64 -> t Serror.t
val perpetual_funding : t -> mark_ticks:int64 -> rate_units:int64 -> t Serror.t
val option_expiry : t -> at:Timestamp.t -> underlying_ticks:int64 -> t Serror.t
val maintenance_breach : t -> mark_ticks:int64 -> bool Serror.t
