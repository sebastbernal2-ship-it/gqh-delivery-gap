(** Price: integer-based (10000ths) for exact decimal arithmetic. *)

type t [@@deriving show, eq, ord]

val of_float : float -> t
val to_float : t -> float
val of_int : int -> t
val to_int : t -> int
val to_string : t -> string
val sexp_of_t : t -> Sexplib0.Sexp.t
val t_of_sexp : Sexplib0.Sexp.t -> t

module Map : sig
  include Map.S with type key = t
end
