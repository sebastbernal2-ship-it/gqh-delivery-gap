(** Bitemporal model for the order book.

    Every fact carries two time axes:
    - Valid time: when the fact is economically effective.
    - Transaction time: when the fact was recorded in the system.

    Enables queries such as:
    - "What was the book state at exchange time T, as known at cutoff C?"
    - "What amendments were made between valid times V1 and V2?"
    - "What did we know at time T that we didn't know earlier?" *)

type bitemporal_interval = {
  valid_from : Timestamp.t;
  valid_until : Timestamp.t;
  tx_from : Timestamp.t;
  tx_until : Timestamp.t;
}
(** A bitemporal time interval with closed-open semantics: valid_from <= t <
    valid_until and tx_from <= t < tx_until. *)

type 'a bitemporal_fact = { fact : 'a; interval : bitemporal_interval }
(** A fact annotated with its bitemporal interval. *)

type 'a t = 'a bitemporal_fact list
(** A collection of bitemporal facts. *)

val singleton : 'a -> Timestamp.t -> Timestamp.t -> 'a t
(** [singleton fact valid tx] creates a fact with open-ended intervals (sentinel
    far-future date for open end). *)

val add : 'a t -> 'a -> Timestamp.t -> Timestamp.t -> 'a t
(** [add ts fact valid tx] prepends a fact with the given valid/tx times. *)

val add_with_interval : 'a t -> 'a -> bitemporal_interval -> 'a t
(** [add_with_interval ts fact interval] prepends a fact with a full interval.
*)

val close_valid : 'a t -> Timestamp.t -> 'a t
(** [close_valid ts valid_time] closes the valid-time interval of the most
    recent fact in the set. *)

val close_tx : 'a t -> Timestamp.t -> 'a t
(** [close_tx ts tx_time] closes the transaction-time interval of the most
    recent fact in the set. *)

val as_of : 'a t -> Timestamp.t -> Timestamp.t -> 'a list
(** Sequenced query: facts valid at [valid_at] and recorded by [tx_at]. *)

val between_valid : 'a t -> Timestamp.t -> Timestamp.t -> 'a list
(** Valid-time range: facts whose valid interval overlaps the given range. *)

val between_tx : 'a t -> Timestamp.t -> Timestamp.t -> 'a list
(** Transaction-time range: facts whose transaction interval overlaps the given
    range. *)

val between :
  'a t -> Timestamp.t * Timestamp.t -> Timestamp.t * Timestamp.t -> 'a list
(** Full bitemporal range query: both valid and tx ranges. *)

val sequenced_snapshot : 'a t -> Timestamp.t -> Timestamp.t -> 'a list
(** Sequenced snapshot: alias for [as_of]. *)

val history : 'a t -> Timestamp.t -> 'a list
(** History of an entity up to [tx_at]: all facts recorded by [tx_at]. *)

val current : 'a t -> 'a list
(** Current state: latest version of each fact at current wall-clock time. *)

val of_events :
  Market_types.event list -> Market_types.event bitemporal_fact list
(** [of_events events] converts a list of market events into bitemporal facts
    using the event's timestamp as both valid and transaction time. *)

val filter_sequenced :
  Market_types.event bitemporal_fact list ->
  Timestamp.t ->
  Timestamp.t ->
  Market_types.event list
(** [filter_sequenced facts valid_at tx_at] returns events valid at [valid_at]
    and known by [tx_at]. Convenience wrapper over [as_of] for event types. *)

val index_by_order_id :
  Market_types.event bitemporal_fact list ->
  Market_types.event bitemporal_fact list Order_id.Map.t
(** [index_by_order_id facts] builds an [Order_id.Map] for O(log n) per-order
    lookup. Each order_id maps to its list of bitemporal facts (most recent
    first). *)

val history_of_order :
  Market_types.event bitemporal_fact list Order_id.Map.t ->
  Order_id.t ->
  Market_types.event list
(** [history_of_order idx order_id] returns all events for the given order in
    chronological order, using the pre-built index. Returns [] if unknown. *)
