(** Price: integer-based (10000ths) for exact decimal arithmetic. *)

type t = int

let scale = 10_000
let of_float f = int_of_float (f *. float scale)
let to_float p = float p /. float scale
let of_int i = i
let to_int p = p
let compare = compare
let equal = ( = )
let to_string p = Printf.sprintf "%.4f" (to_float p)
let show = to_string
let pp fmt p = Format.pp_print_string fmt (to_string p)
let sexp_of_t p = Sexplib0.Sexp.Atom (to_string p)

let t_of_sexp = function
  | Sexplib0.Sexp.Atom s -> (
      try of_float (float_of_string s) with _ -> of_int 0)
  | _ -> of_int 0

module Map = Map.Make (struct
  type nonrec t = t

  let compare = compare
end)
