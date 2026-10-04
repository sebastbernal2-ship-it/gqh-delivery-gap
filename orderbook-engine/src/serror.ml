(** Serror: a result type with string error messages.

    Modeled after Jane Street's [Core.Serror]. Wraps [Result] with a descriptive
    error string. Use instead of ad-hoc [(unit, string) result]. *)

type 'a t = ('a, string) Result.t

(** [return x] is [Ok x]. *)
let return x = Ok x

(** [fail msg] is [Error msg]. *)
let fail msg = Error msg

(** [failf fmt ...] formats an error message. *)
let failf fmt = Printf.ksprintf (fun s -> Error s) fmt

(** [map f x] applies [f] to [Ok x], passes through [Error]. *)
let map f = function Ok x -> Ok (f x) | Error _ as e -> e

(** [bind x ~f] applies [f] to [Ok x], passes through [Error]. *)
let bind x ~f = match x with Ok x -> f x | Error _ as e -> e

(** [map_error x ~f] applies [f] to the error message. *)
let map_error x ~f = match x with Ok _ -> x | Error e -> Error (f e)

(** [both a b] returns [Ok (x, y)] if both are [Ok], first error otherwise. *)
let both a b =
  match (a, b) with
  | Ok x, Ok y -> Ok (x, y)
  | Error e, _ -> Error e
  | _, Error e -> Error e

(** [all l] returns [Ok [x1; ...]] if all are [Ok], first error otherwise. *)
let all l =
  let rec aux acc = function
    | [] -> Ok (List.rev acc)
    | Ok x :: rest -> aux (x :: acc) rest
    | Error e :: _ -> Error e
  in
  aux [] l

(** [try_with f] catches exceptions and returns [Error]. *)
let try_with f = try Ok (f ()) with e -> Error (Printexc.to_string e)

(** [of_option x ~error] converts [Some x] to [Ok x], [None] to [Error error].
*)
let of_option x ~error = match x with Some x -> Ok x | None -> Error error

(** [ok_or_failwith x] unwraps or raises. *)
let ok_or_failwith = function Ok x -> x | Error e -> failwith e

(** [is_ok x] returns [true] if [Ok]. *)
let is_ok = function Ok _ -> true | Error _ -> false

(** [is_error x] returns [true] if [Error]. *)
let is_error = function Ok _ -> false | Error _ -> true

(** [value x ~default] returns the [Ok] value or [default]. *)
let value x ~default = match x with Ok x -> x | Error _ -> default

(** [filter_map l ~f] applies [f] to each element and keeps [Ok] results. *)
let filter_map l ~f =
  List.filter_map (fun x -> match f x with Ok y -> Some y | _ -> None) l

(** [map l ~f] applies [f] to each element. Returns [Ok] of mapped list if all
    succeed, [Error] on the first failure. *)
let map l ~f =
  let rec aux acc = function
    | [] -> Ok (List.rev acc)
    | x :: rest -> (
        match f x with Ok y -> aux (y :: acc) rest | Error _ as e -> e)
  in
  aux [] l
