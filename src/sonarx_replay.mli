(** Replay loop for SonarX L2 snapshots. *)

type snapshot = Sonarx.snapshot
type snapshot_handler = snapshot -> unit Lwt.t
type t

val create : snapshot list -> t
(** [create snapshots] creates a replay loop in file order. *)

val add_handler : t -> snapshot_handler -> unit
(** [add_handler loop handler] sends each snapshot to [handler]. *)

val process_one : t -> unit Serror.t Lwt.t
(** [process_one loop] sends the next snapshot to all handlers. *)

val run_fast : t -> unit Lwt.t
(** [run_fast loop] replays all snapshots without waiting between timestamps. *)

val run : t -> unit Lwt.t
(** [run loop] replays snapshots using their timestamp gaps. *)

val stop : t -> unit
(** [stop loop] stops an active replay. *)

val progress : t -> int * int
(** [progress loop] returns processed and total snapshot counts. *)

val current : t -> snapshot option
(** [current loop] returns the most recently emitted snapshot. *)
