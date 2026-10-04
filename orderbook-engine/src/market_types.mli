(** Event, order, and market event types for the order book. *)

type event = {
  timestamp : Timestamp.t;
  order_id : Order_id.t;
  side : Side.side;
  price : Price.t;
  size : Size.t;
  action : Side.action;
  valid_time : Timestamp.t option;
}
[@@deriving show, eq, ord]

val sexp_of_event : event -> Sexplib0.Sexp.t

type order = {
  id : Order_id.t;
  side : Side.side;
  price : Price.t;
  size : Size.t;
  tx_time : Timestamp.t;
  arrival_sequence : int;
  valid_time : Timestamp.t;
  tx_interval : Timestamp.t * Timestamp.t;
  valid_interval : Timestamp.t * Timestamp.t;
}
[@@deriving show, eq, ord]

type price_level = { price : Price.t; total_size : Size.t; order_count : int }
[@@deriving show, eq, ord]

val sexp_of_price_level : price_level -> Sexplib0.Sexp.t

type book_side = price_level list [@@deriving show, eq, ord]

val sexp_of_book_side : book_side -> Sexplib0.Sexp.t

type book_snapshot = {
  timestamp : Timestamp.t;
  bids : book_side;
  asks : book_side;
  spread : Price.t option;
  mid_price : Price.t option;
  micro_price : Price.t option;
}
[@@deriving show, eq, ord]

type book_stats = {
  total_bid_size : Size.t;
  total_ask_size : Size.t;
  bid_count : int;
  ask_count : int;
  spread : Price.t option;
  mid_price : Price.t option;
}
[@@deriving show, eq, ord]

type fill = {
  trade_time : Timestamp.t;
  buy_order_id : Order_id.t;
  sell_order_id : Order_id.t;
  fill_price : Price.t;
  fill_size : Size.t;
  aggressor_order_id : Order_id.t;
}
[@@deriving show, eq, ord]
(** A trade: the result of matching a crossing bid and ask. *)

val sexp_of_fill : fill -> Sexplib0.Sexp.t

type market_event =
  | OrderAdded of event
  | OrderAmended of event
  | OrderCancelled of event
  | OrderExecuted of event * Size.t
  | OrderReplaced of event * Order_id.t
  | ControlEvent of event
  | Trade of fill
  | BookSnapshot of book_snapshot
  | StatsUpdate of book_stats
[@@deriving show, eq, ord]

val sexp_of_market_event : market_event -> Sexplib0.Sexp.t
