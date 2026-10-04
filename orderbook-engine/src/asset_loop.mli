(** Single-instrument, visible-depth taker execution with asset-aware
    accounting. IOC and FOK are supported; passive GTC execution needs a
    separately bounded queue model. *)

type fill = {
  order_id : string;
  side : Exec_event.side;
  at : Timestamp.t;
  price_ticks : int64;
  quantity_units : int64;
  fee : int64;
}

type result = {
  account : Asset_account.t;
  book : L2_book.t;
  submitted : int;
  rejected : int;
  unfilled : int;
  fills : fill list;
  last_mark_ticks : int64 option;
}

val run :
  Instrument_spec.t ->
  initial_cash:int64 ->
  taker_fee_bps:int ->
  latency_ns:int64 ->
  equity_settlement:(Timestamp.t -> Timestamp.t) ->
  Exec_event.t list ->
  result Serror.t
