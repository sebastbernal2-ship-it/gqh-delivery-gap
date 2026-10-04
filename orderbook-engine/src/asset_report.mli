(** Machine-readable summary for the asset-aware replay kernel. Monetary values
    and returns remain integer fixed-point values. *)

type t = {
  event_count : int;
  order_intent_count : int;
  fill_count : int;
  initial_equity : int64;
  final_equity : int64;
  net_pnl : int64;
  net_return_bps : int64;
  max_drawdown_bps : int64;
  fees : int64;
  realized_pnl : int64;
  funding_paid : int64;
  submitted : int;
  rejected : int;
  unfilled : int;
}

val summarize :
  initial_cash:int64 ->
  events:Exec_event.t list ->
  Asset_loop.result ->
  t Serror.t

val to_yojson : t -> Yojson.Safe.t
