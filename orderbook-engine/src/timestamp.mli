(** Timestamp with nanosecond precision backed by Ptime. *)

type t

val now : unit -> t
val add_seconds : t -> float -> t
val sub : t -> t -> float
val add_ns : t -> int64 -> t
val compare : t -> t -> int
val equal : t -> t -> bool
val to_ptime : t -> Ptime.t
val of_ptime : Ptime.t -> t
val to_string : t -> string
val of_string : string -> t Serror.t
val show : t -> string
val pp : Format.formatter -> t -> unit
val max : t -> t -> t
val min : t -> t -> t
val diff_seconds : t -> t -> float
val zero : t
val sexp_of_t : t -> Sexplib0.Sexp.t
val t_of_sexp : Sexplib0.Sexp.t -> t
