(** Timestamp with nanosecond precision backed by Ptime. *)

type t = Ptime.t

let now () = Ptime_clock.now ()

let add_seconds (t : t) (s : float) : t =
  match Ptime.Span.of_float_s s with
  | None -> t
  | Some ps -> ( match Ptime.add_span t ps with Some t' -> t' | None -> t)

let sub (t1 : t) (t2 : t) : float = Ptime.Span.to_float_s (Ptime.diff t1 t2)

(** [add_ns t nanoseconds] adds an exact nanosecond offset. Negative offsets
    subtract, which needs a day and a positive remainder because a span is
    stored as days plus nonnegative picoseconds. *)
let add_ns (t : t) (nanoseconds : int64) : t =
  let picoseconds = Int64.mul nanoseconds 1000L in
  let days, remainder =
    if picoseconds >= 0L then (0, picoseconds)
    else (-1, Int64.add 86_400_000_000_000_000L picoseconds)
  in
  match Ptime.Span.of_d_ps (days, remainder) with
  | None -> t
  | Some span -> ( match Ptime.add_span t span with Some t' -> t' | None -> t)
let compare = Ptime.compare
let equal = Ptime.equal
let to_ptime t = t
let of_ptime t = t
let to_string t = Ptime.to_rfc3339 t

let of_string s =
  match Ptime.of_rfc3339 s with
  | Ok (t, _, _) -> Ok t
  | _ -> Error "invalid timestamp"

let max a b = if Ptime.compare a b >= 0 then a else b
let min a b = if Ptime.compare a b <= 0 then a else b
let diff_seconds t1 t2 = Ptime.Span.to_float_s (Ptime.diff t1 t2)
let zero = Ptime.epoch
let show = to_string
let pp fmt t = Format.pp_print_string fmt (to_string t)
let sexp_of_t t = Sexplib0.Sexp.Atom (to_string t)

let t_of_sexp = function
  | Sexplib0.Sexp.Atom s -> ( match of_string s with Ok t -> t | _ -> zero)
  | _ -> zero
