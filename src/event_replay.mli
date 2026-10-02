(** Strict, deterministic replay of interleaved venue and symbol feeds. *)

type t

type applied = {
  feed_event : Market_data.feed_event;
  snapshot : Market_types.book_snapshot;
  fills : Market_types.fill list;
}

val create : unit -> t

val apply : t -> Market_data.feed_event -> applied Serror.t
(** [apply replay feed_event] rejects sequence gaps, out-of-order event times,
    and invalid source identity before applying the event to its symbol book. *)

val run : Market_data.feed_event list -> applied list Serror.t
(** [run events] replays an interleaved feed and returns one result per event.
*)

val book_count : t -> int
