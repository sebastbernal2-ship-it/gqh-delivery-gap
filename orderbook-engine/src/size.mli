(** Size: integer-based quantity (shares/contracts). *)

type t [@@deriving show, eq, ord]

val zero : t
val of_int : int -> t
val to_int : t -> int
val add : t -> t -> t
val sub : t -> t -> t
val min : t -> t -> t
val to_string : t -> string
val sexp_of_t : t -> Sexplib0.Sexp.t
val t_of_sexp : Sexplib0.Sexp.t -> t
