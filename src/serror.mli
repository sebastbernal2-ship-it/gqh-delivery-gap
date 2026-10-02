(** Serror: a result type with string error messages.

    Modeled after Jane Street's [Core.Serror]. A drop-in replacement for ad-hoc
    [(unit, string) result] types. *)

type 'a t = ('a, string) Result.t

val return : 'a -> 'a t
val fail : string -> 'a t
val failf : ('a, unit, string, 'b t) format4 -> 'a
val map : ('a -> 'b) -> 'a t -> 'b t
val bind : 'a t -> f:('a -> 'b t) -> 'b t
val map_error : 'a t -> f:(string -> string) -> 'a t
val both : 'a t -> 'b t -> ('a * 'b) t
val all : 'a t list -> 'a list t
val try_with : (unit -> 'a) -> 'a t
val of_option : 'a option -> error:string -> 'a t
val ok_or_failwith : 'a t -> 'a
val is_ok : 'a t -> bool
val is_error : 'a t -> bool
val value : 'a t -> default:'a -> 'a

val filter_map : 'a list -> f:('a -> 'b t) -> 'b list
(** [filter_map l ~f] applies [f] to each element and keeps [Ok] results. Drops
    [Error] elements silently. *)

val map : 'a list -> f:('a -> 'b t) -> 'b list t
(** [map l ~f] applies [f] to each element. Returns [Ok] of mapped list if all
    succeed, [Error] on the first failure. *)
