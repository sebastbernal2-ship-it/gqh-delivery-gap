(** Instrumentation and metrics for the order book. *)

open Market_types

type t = {
  timestamp : Timestamp.t;
  event_count : int;
  order_count : int;
  bid_count : int;
  ask_count : int;
  total_bid_size : Size.t;
  total_ask_size : Size.t;
  spread : Price.t option;
  mid_price : Price.t option;
  micro_price : Price.t option;
  top_bid_price : Price.t option;
  top_ask_price : Price.t option;
  events_per_second : float;
}
(** A snapshot of metrics at a point in time. *)

type collector = {
  book : Order_book.t;
  mutable events_processed : int;
  mutable start_time : Timestamp.t;
  mutable last_time : Timestamp.t;
  mutable last_event_count : int;
}
(** Metrics collector. *)

(** [create book] creates a metrics collector. *)
let create (book : Order_book.t) : collector =
  {
    book;
    events_processed = 0;
    start_time = Timestamp.now ();
    last_time = Timestamp.now ();
    last_event_count = 0;
  }

(** [record c] records a metric snapshot after processing an event. *)
let record (c : collector) : t =
  c.events_processed <- c.events_processed + 1;
  let now = Timestamp.now () in
  let dt = Timestamp.diff_seconds now c.last_time in
  let eps =
    if dt > 0.0 then float (c.events_processed - c.last_event_count) /. dt
    else 0.0
  in
  c.last_time <- now;
  c.last_event_count <- c.events_processed;
  let snap = Order_book.get_snapshot c.book in
  {
    timestamp = now;
    event_count = c.events_processed;
    order_count = Order_book.order_count c.book;
    bid_count = List.length snap.bids;
    ask_count = List.length snap.asks;
    total_bid_size =
      List.fold_left
        (fun acc l -> Size.add acc l.total_size)
        Size.zero snap.bids;
    total_ask_size =
      List.fold_left
        (fun acc l -> Size.add acc l.total_size)
        Size.zero snap.asks;
    spread = snap.spread;
    mid_price = snap.mid_price;
    micro_price = snap.micro_price;
    top_bid_price = (match snap.bids with b :: _ -> Some b.price | [] -> None);
    top_ask_price = (match snap.asks with a :: _ -> Some a.price | [] -> None);
    events_per_second = eps;
  }

(** [report m] logs a formatted metrics report. *)
let report (m : t) : unit =
  Logs.info (fun log ->
      let spread_s =
        match m.spread with Some s -> Price.to_string s | None -> "N/A"
      in
      let mid_s =
        match m.mid_price with Some p -> Price.to_string p | None -> "N/A"
      in
      let micro_s =
        match m.micro_price with Some p -> Price.to_string p | None -> "N/A"
      in
      log
        "Metrics: events=%d orders=%d bids=%d asks=%d bid_size=%d ask_size=%d \
         spread=%s mid=%s micro=%s eps=%.1f"
        m.event_count m.order_count m.bid_count m.ask_count
        (Size.to_int m.total_bid_size)
        (Size.to_int m.total_ask_size)
        spread_s mid_s micro_s m.events_per_second)

(** [json_report m] returns a JSON-formatted metrics report. *)
let json_report (m : t) : string =
  let spread =
    match m.spread with Some s -> `String (Price.to_string s) | None -> `Null
  in
  let mid =
    match m.mid_price with
    | Some p -> `String (Price.to_string p)
    | None -> `Null
  in
  let micro =
    match m.micro_price with
    | Some p -> `String (Price.to_string p)
    | None -> `Null
  in
  let top_bid =
    match m.top_bid_price with
    | Some p -> `String (Price.to_string p)
    | None -> `Null
  in
  let top_ask =
    match m.top_ask_price with
    | Some p -> `String (Price.to_string p)
    | None -> `Null
  in
  let json =
    `Assoc
      [
        ("type", `String "metrics");
        ("ts", `String (Timestamp.to_string m.timestamp));
        ("events", `Int m.event_count);
        ("orders", `Int m.order_count);
        ("bids", `Int m.bid_count);
        ("asks", `Int m.ask_count);
        ("bid_size", `Int (Size.to_int m.total_bid_size));
        ("ask_size", `Int (Size.to_int m.total_ask_size));
        ("spread", spread);
        ("mid", mid);
        ("micro", micro);
        ("top_bid", top_bid);
        ("top_ask", top_ask);
        ("eps", `Float m.events_per_second);
      ]
  in
  Yojson.Safe.to_string json
