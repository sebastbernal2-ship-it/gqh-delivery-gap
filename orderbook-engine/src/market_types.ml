open Side

type event = {
  timestamp : Timestamp.t;
  order_id : Order_id.t;
  side : side;
  price : Price.t;
  size : Size.t;
  action : action;
  valid_time : Timestamp.t option;
}
[@@deriving show, eq, ord]

let sexp_of_event e =
  Sexplib0.Sexp.List
    [
      Sexplib0.Sexp.List
        [ Sexplib0.Sexp.Atom "timestamp"; Timestamp.sexp_of_t e.timestamp ];
      Sexplib0.Sexp.List
        [ Sexplib0.Sexp.Atom "order_id"; Order_id.sexp_of_t e.order_id ];
      Sexplib0.Sexp.List [ Sexplib0.Sexp.Atom "side"; Side.sexp_of_side e.side ];
      Sexplib0.Sexp.List [ Sexplib0.Sexp.Atom "price"; Price.sexp_of_t e.price ];
      Sexplib0.Sexp.List [ Sexplib0.Sexp.Atom "size"; Size.sexp_of_t e.size ];
      Sexplib0.Sexp.List
        [ Sexplib0.Sexp.Atom "action"; Side.sexp_of_action e.action ];
    ]

type order = {
  id : Order_id.t;
  side : side;
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

let sexp_of_price_level l =
  Sexplib0.Sexp.List
    [
      Sexplib0.Sexp.List [ Sexplib0.Sexp.Atom "price"; Price.sexp_of_t l.price ];
      Sexplib0.Sexp.List
        [ Sexplib0.Sexp.Atom "total_size"; Size.sexp_of_t l.total_size ];
      Sexplib0.Sexp.List
        [
          Sexplib0.Sexp.Atom "order_count";
          Sexplib0.Sexp.Atom (Base.Int.to_string l.order_count);
        ];
    ]

type book_side = price_level list [@@deriving show, eq, ord]

let sexp_of_book_side l = Sexplib0.Sexp.List (List.map sexp_of_price_level l)

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

let sexp_of_fill f =
  Sexplib0.Sexp.List
    [
      Sexplib0.Sexp.List
        [ Sexplib0.Sexp.Atom "trade_time"; Timestamp.sexp_of_t f.trade_time ];
      Sexplib0.Sexp.List
        [ Sexplib0.Sexp.Atom "buy_order_id"; Order_id.sexp_of_t f.buy_order_id ];
      Sexplib0.Sexp.List
        [
          Sexplib0.Sexp.Atom "sell_order_id"; Order_id.sexp_of_t f.sell_order_id;
        ];
      Sexplib0.Sexp.List
        [ Sexplib0.Sexp.Atom "fill_price"; Price.sexp_of_t f.fill_price ];
      Sexplib0.Sexp.List
        [ Sexplib0.Sexp.Atom "fill_size"; Size.sexp_of_t f.fill_size ];
      Sexplib0.Sexp.List
        [
          Sexplib0.Sexp.Atom "aggressor_order_id";
          Order_id.sexp_of_t f.aggressor_order_id;
        ];
    ]

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

let sexp_of_market_event = function
  | OrderAdded e ->
      Sexplib0.Sexp.List [ Sexplib0.Sexp.Atom "order_added"; sexp_of_event e ]
  | OrderAmended e ->
      Sexplib0.Sexp.List [ Sexplib0.Sexp.Atom "order_amended"; sexp_of_event e ]
  | OrderCancelled e ->
      Sexplib0.Sexp.List
        [ Sexplib0.Sexp.Atom "order_cancelled"; sexp_of_event e ]
  | OrderExecuted (e, sz) ->
      Sexplib0.Sexp.List
        [
          Sexplib0.Sexp.Atom "order_executed";
          sexp_of_event e;
          Size.sexp_of_t sz;
        ]
  | OrderReplaced (e, old_id) ->
      Sexplib0.Sexp.List
        [
          Sexplib0.Sexp.Atom "order_replaced";
          sexp_of_event e;
          Order_id.sexp_of_t old_id;
        ]
  | ControlEvent e ->
      Sexplib0.Sexp.List [ Sexplib0.Sexp.Atom "control_event"; sexp_of_event e ]
  | Trade f -> Sexplib0.Sexp.List [ Sexplib0.Sexp.Atom "trade"; sexp_of_fill f ]
  | BookSnapshot s ->
      Sexplib0.Sexp.List
        [
          Sexplib0.Sexp.Atom "book_snapshot";
          Sexplib0.Sexp.List
            [
              Sexplib0.Sexp.List
                [
                  Sexplib0.Sexp.Atom "timestamp";
                  Timestamp.sexp_of_t s.timestamp;
                ];
              Sexplib0.Sexp.List
                [ Sexplib0.Sexp.Atom "bids"; sexp_of_book_side s.bids ];
              Sexplib0.Sexp.List
                [ Sexplib0.Sexp.Atom "asks"; sexp_of_book_side s.asks ];
              Sexplib0.Sexp.List
                [
                  Sexplib0.Sexp.Atom "spread";
                  (match s.spread with
                  | Some p -> Price.sexp_of_t p
                  | None -> Sexplib0.Sexp.Atom "null");
                ];
              Sexplib0.Sexp.List
                [
                  Sexplib0.Sexp.Atom "mid_price";
                  (match s.mid_price with
                  | Some p -> Price.sexp_of_t p
                  | None -> Sexplib0.Sexp.Atom "null");
                ];
              Sexplib0.Sexp.List
                [
                  Sexplib0.Sexp.Atom "micro_price";
                  (match s.micro_price with
                  | Some p -> Price.sexp_of_t p
                  | None -> Sexplib0.Sexp.Atom "null");
                ];
            ];
        ]
  | StatsUpdate s ->
      Sexplib0.Sexp.List
        [
          Sexplib0.Sexp.Atom "stats_update";
          Sexplib0.Sexp.List
            [
              Sexplib0.Sexp.List
                [
                  Sexplib0.Sexp.Atom "total_bid_size";
                  Size.sexp_of_t s.total_bid_size;
                ];
              Sexplib0.Sexp.List
                [
                  Sexplib0.Sexp.Atom "total_ask_size";
                  Size.sexp_of_t s.total_ask_size;
                ];
              Sexplib0.Sexp.List
                [
                  Sexplib0.Sexp.Atom "bid_count"; Base.Int.sexp_of_t s.bid_count;
                ];
              Sexplib0.Sexp.List
                [
                  Sexplib0.Sexp.Atom "ask_count"; Base.Int.sexp_of_t s.ask_count;
                ];
              Sexplib0.Sexp.List
                [
                  Sexplib0.Sexp.Atom "spread";
                  (match s.spread with
                  | Some p -> Price.sexp_of_t p
                  | None -> Sexplib0.Sexp.Atom "null");
                ];
              Sexplib0.Sexp.List
                [
                  Sexplib0.Sexp.Atom "mid_price";
                  (match s.mid_price with
                  | Some p -> Price.sexp_of_t p
                  | None -> Sexplib0.Sexp.Atom "null");
                ];
            ];
        ]
