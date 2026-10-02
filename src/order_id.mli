(** Order identifier type. Wraps a string. *)

type t = string [@@deriving show, eq, ord]

val sexp_of_t : t -> Sexplib0.Sexp.t
val t_of_sexp : Sexplib0.Sexp.t -> t

module Map : sig
  include Map.S with type key = t
end
