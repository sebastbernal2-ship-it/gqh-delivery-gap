type right = Call | Put
type settlement = Cash | Physical

type option_terms = {
  underlying : string;
  strike_ticks : int64;
  expiry : Timestamp.t;
  right : right;
  settlement : settlement;
  deliverable_units : int64;
  exercise_multiplier : int64;
}

type kind =
  | Equity
  | Future of {
      expiry : Timestamp.t;
      initial_margin_bps : int;
      maintenance_margin_bps : int;
    }
  | Perpetual of { initial_margin_bps : int; maintenance_margin_bps : int }
  | Option of option_terms

type t = {
  venue : string;
  symbol : string;
  currency : string;
  effective_from : Timestamp.t;
  effective_until : Timestamp.t option;
  price_increment_ticks : int64;
  quantity_increment_units : int64;
  multiplier : int64;
  kind : kind;
}

let ( let* ) result f = Result.bind result f

let validate_margin initial maintenance =
  if initial <= 0 || initial > 10_000 then
    Serror.fail "initial margin bps must be in (0, 10000]"
  else if maintenance < 0 || maintenance >= initial then
    Serror.fail "maintenance margin bps must be below initial margin"
  else Ok ()

let validate spec =
  if spec.venue = "" || spec.symbol = "" || spec.currency = "" then
    Serror.fail "instrument identity and currency are required"
  else if
    spec.price_increment_ticks <= 0L || spec.quantity_increment_units <= 0L
  then Serror.fail "tick and lot increments must be positive"
  else if spec.multiplier <= 0L then
    Serror.fail "contract multiplier must be positive"
  else if
    match spec.effective_until with
    | None -> false
    | Some ending -> Timestamp.compare ending spec.effective_from <= 0
  then Serror.fail "instrument effective interval is empty"
  else
    match spec.kind with
    | Equity ->
        if spec.multiplier <> 1L then
          Serror.fail "equity multiplier must be one"
        else Ok ()
    | Future { expiry; initial_margin_bps; maintenance_margin_bps } ->
        if Timestamp.compare expiry spec.effective_from <= 0 then
          Serror.fail "future expiry precedes effective date"
        else validate_margin initial_margin_bps maintenance_margin_bps
    | Perpetual { initial_margin_bps; maintenance_margin_bps } ->
        validate_margin initial_margin_bps maintenance_margin_bps
    | Option terms ->
        if
          terms.underlying = "" || terms.strike_ticks <= 0L
          || terms.deliverable_units <= 0L
          || terms.exercise_multiplier <= 0L
        then Serror.fail "option terms are incomplete"
        else if Timestamp.compare terms.expiry spec.effective_from <= 0 then
          Serror.fail "option expiry precedes effective date"
        else Ok ()

let validate_fill spec ~at ~price_ticks ~quantity_units =
  let* () = validate spec in
  if Timestamp.compare at spec.effective_from < 0 then
    Serror.fail "instrument specification is not effective yet"
  else if
    match spec.effective_until with
    | None -> false
    | Some ending -> Timestamp.compare at ending >= 0
  then Serror.fail "instrument specification has expired"
  else if
    price_ticks <= 0L
    || price_ticks > Exec_units.price_ticks_max
    || quantity_units <= 0L
  then Serror.fail "price and quantity must be positive"
  else if Int64.rem price_ticks spec.price_increment_ticks <> 0L then
    Serror.fail "price violates instrument tick increment"
  else if Int64.rem quantity_units spec.quantity_increment_units <> 0L then
    Serror.fail "quantity violates instrument lot increment"
  else
    match spec.kind with
    | Future { expiry; _ } when Timestamp.compare at expiry >= 0 ->
        Serror.fail "future is expired"
    | Option terms when Timestamp.compare at terms.expiry >= 0 ->
        Serror.fail "option is expired"
    | _ -> Ok ()

let notional spec ~price_ticks ~quantity_units =
  let* base = Exec_units.notional ~price_ticks ~quantity_units in
  Exec_units.checked_mul base spec.multiplier

let is_linear_derivative spec =
  match spec.kind with
  | Future _ | Perpetual _ -> true
  | Equity | Option _ -> false
