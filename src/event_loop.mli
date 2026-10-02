(** Lwt-based event loop engine.

    Drives market events through the order book, publishing snapshots and stats
    on each update. Supports replay at configurable speed. *)

open Lwt

type event_handler = Market_types.market_event -> unit Lwt.t
(** Callback type for event consumers. *)

type mode =
  | Replay
  | Simulation
      (** Replay applies venue events exactly; Simulation matches new orders. *)

type t
(** Opaque handle to an event loop instance. *)

val create : ?mode:mode -> Order_book.t -> Market_types.event list -> t
(** [create ?mode book events] creates an event loop over the given book and
    event sequence. Replay is the default mode. *)

val add_handler : t -> event_handler -> unit
(** [add_handler loop handler] registers a callback invoked on every event
    (order update, snapshot, stats update). *)

val run : t -> unit Lwt.t
(** [run loop] processes all events at real-time speed, respecting inter-event
    timestamps scaled by the speed multiplier. *)

val run_fast : t -> unit Lwt.t
(** [run_fast loop] processes all events without delays (for testing). *)

val stop : t -> unit
(** [stop loop] stops event processing. *)

val set_speed : t -> float -> unit
(** [set_speed loop speed] sets the replay speed multiplier (1.0 = real time,
    2.0 = 2x, 0.0 = instant). *)

val progress : t -> int * int
(** [progress loop] returns (processed_count, total_count). *)
