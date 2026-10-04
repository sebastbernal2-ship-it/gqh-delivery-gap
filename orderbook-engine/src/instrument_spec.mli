(** Effective-dated economic terms for one traded instrument. All price and
    quantity values use the fixed-point wire units of [Exec_units]. *)

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

val validate : t -> unit Serror.t

val validate_fill :
  t ->
  at:Timestamp.t ->
  price_ticks:int64 ->
  quantity_units:int64 ->
  unit Serror.t

val notional : t -> price_ticks:int64 -> quantity_units:int64 -> int64 Serror.t
val is_linear_derivative : t -> bool
