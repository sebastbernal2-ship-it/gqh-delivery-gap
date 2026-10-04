(** Size: integer-based quantity (shares/contracts). *)

type t = int [@@deriving show, eq, ord]

let zero = 0
let of_int i = i
let to_int i = i
let add a b = a + b
let sub a b = a - b
let min a b = if a < b then a else b
let to_string i = string_of_int i
let sexp_of_t s = Sexplib0.Sexp.Atom (to_string s)

let t_of_sexp = function
  | Sexplib0.Sexp.Atom s -> ( try of_int (int_of_string s) with _ -> zero)
  | _ -> zero
