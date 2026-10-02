type t = string [@@deriving show, eq, ord]

let sexp_of_t s = Sexplib0.Sexp.Atom s

let t_of_sexp = function
  | Sexplib0.Sexp.Atom s -> s
  | _ -> raise (Invalid_argument "Order_id.t_of_sexp")

module Map = Map.Make (struct
  type nonrec t = t

  let compare = compare
end)
