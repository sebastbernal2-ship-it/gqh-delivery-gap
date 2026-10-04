type scale

type instrument = {
  symbol : string;
  price : scale;
  quantity : scale;
}

val scale_of_step : string -> scale Serror.t
val instrument : symbol:string -> price_step:string -> quantity_step:string -> instrument Serror.t
val canonical_decimal : string -> string Serror.t
val compare_decimal : string -> string -> int
val to_units : scale -> string -> int64 Serror.t
val to_price_ticks : instrument -> string -> int64 Serror.t
val to_quantity_lots : instrument -> string -> int64 Serror.t
