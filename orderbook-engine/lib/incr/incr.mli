(** Incremental computation engine.

    A minimal, self-contained adaptation of the Incremental library (Jane
    Street). Nodes form a DAG: when an input [Var] changes, only the affected
    downstream nodes recompute, in topological order, with cut-off when values
    do not change.

    Each call to {!make} creates a fresh engine instance with its own work
    queue and ID counter, so multiple order books can coexist without sharing
    mutable state. *)

(** The signature of an incremental engine instance. *)
module type S = sig
  type 'a t
  (** Type of an incremental node holding a value of type ['a]. *)

  (** A mutable input variable. *)
  module Var : sig
    type 'a t

    val create : 'a -> 'a t
    (** [Var.create x] creates a new input variable initialized to [x]. *)

    val set : 'a t -> 'a -> unit
    (** [Var.set v x] sets [v] to [x] and schedules downstream recomputation. *)

    val snapshot : 'a t -> 'a
    (** [snapshot v] reads the current value of [v] (stabilized or pending). *)
  end

  val of_var : 'a Var.t -> 'a t
  (** [of_var v] views a [Var.t] as an [Incr.t] for use with [map], etc. *)

  val return : 'a -> 'a t
  (** [return x] is a constant node holding [x]. *)

  val map : ('a -> 'b) -> 'a t -> 'b t
  (** [map f x] recomputes [f] when [x] changes. *)

  val map2 : ('a -> 'b -> 'c) -> 'a t -> 'b t -> 'c t
  (** [map2 f x y] recomputes [f] when either [x] or [y] changes. *)

  val map3 : ('a -> 'b -> 'c -> 'd) -> 'a t -> 'b t -> 'c t -> 'd t
  (** [map3 f x y z] recomputes [f] when any input changes. *)

  val bind : 'a t -> f:('a -> 'b t) -> 'b t
  (** [bind x ~f] flattens: when [x] changes, [f] produces a new incremental. *)

  val cutoff : 'a t -> f:('a -> 'a -> bool) -> 'a t
  (** [cutoff x ~f] returns a new node that mirrors [x] but uses [f] for
      cut-off instead of physical equality ([==]). If [f old new] returns
      [true], the value is considered unchanged and downstream nodes are not
      recomputed. *)

  val if_ : bool t -> then_:'a t -> else_:'a t -> 'a t
  (** [if_ cond t e] selects [t] or [e] based on [cond]. *)

  val snapshot : 'a t -> 'a
  (** [snapshot x] reads the current stabilized value. *)

  val stabilize : unit -> unit
  (** Stabilize the graph: propagate all pending changes. *)

  val is_stabilized : unit -> bool
  (** [is_stabilized ()] returns [true] if no changes are pending. *)

  val on_change : 'a t -> f:('a -> 'a -> unit) -> unit
  (** [on_change x ~f] registers a callback that runs when [x] changes after
      stabilization. [f new old] receives the new and old values. *)
end

(** [make ()] creates a fresh incremental engine instance with its own work
    queue and ID counter. Multiple instances are fully independent. *)
val make : unit -> (module S)