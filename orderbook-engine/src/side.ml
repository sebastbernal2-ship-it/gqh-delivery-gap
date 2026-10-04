type side = Bid | Ask [@@deriving show, eq, ord]

let sexp_of_side = function
  | Bid -> Sexplib0.Sexp.Atom "bid"
  | Ask -> Sexplib0.Sexp.Atom "ask"

let side_of_sexp = function
  | Sexplib0.Sexp.Atom "bid" -> Bid
  | Sexplib0.Sexp.Atom "ask" -> Ask
  | _ -> raise (Invalid_argument "side_of_sexp")

type action =
  | Add
  | Amend
  | Cancel
  | Execute
  | Replace of string
  | Control of string
[@@deriving show, eq, ord]

let sexp_of_action = function
  | Add -> Sexplib0.Sexp.Atom "add"
  | Amend -> Sexplib0.Sexp.Atom "amend"
  | Cancel -> Sexplib0.Sexp.Atom "cancel"
  | Execute -> Sexplib0.Sexp.Atom "execute"
  | Replace old_id ->
      Sexplib0.Sexp.List
        [ Sexplib0.Sexp.Atom "replace"; Sexplib0.Sexp.Atom old_id ]
  | Control name ->
      Sexplib0.Sexp.List
        [ Sexplib0.Sexp.Atom "control"; Sexplib0.Sexp.Atom name ]

let action_of_sexp = function
  | Sexplib0.Sexp.Atom "add" -> Add
  | Sexplib0.Sexp.Atom "amend" -> Amend
  | Sexplib0.Sexp.Atom "cancel" -> Cancel
  | Sexplib0.Sexp.Atom "execute" -> Execute
  | Sexplib0.Sexp.List
      [ Sexplib0.Sexp.Atom "replace"; Sexplib0.Sexp.Atom old_id ] ->
      Replace old_id
  | Sexplib0.Sexp.List [ Sexplib0.Sexp.Atom "control"; Sexplib0.Sexp.Atom name ]
    ->
      Control name
  | _ -> raise (Invalid_argument "action_of_sexp")
