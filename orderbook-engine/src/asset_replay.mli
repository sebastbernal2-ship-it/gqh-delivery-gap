(** Replay economic lifecycle events from canonical [Exec_event] rows. This
    consumes already matched fills; order matching remains a separate stage. *)

type result = {
  account : Asset_account.t;
  processed : int;
  last_mark_ticks : int64 option;
}

val apply_observation : Asset_account.t -> Timestamp.t -> Exec_event.observation -> Asset_account.t Serror.t

val run :
  Instrument_spec.t ->
  initial_cash:int64 ->
  equity_settlement:(Timestamp.t -> Timestamp.t) ->
  Exec_event.t list ->
  result Serror.t
