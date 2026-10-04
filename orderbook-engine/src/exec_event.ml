(** Canonical event contract for the execution kernel.

    One envelope carries every event the kernel consumes or produces: venue
    market data, external observations, strategy decisions, and order
    lifecycle events. The contract is the single owner of the event field set
    and the JSONL interchange form used by replay fixtures.

    Units are owned by {!Exec_units} and
    {!docs/adr/ADR-007-execution-units.md}: integer price ticks (1e-4),
    quantity units (1e-6), money units (1e-8), and rate units (1e-8). No
    float appears in the contract.

    Timestamps serialize as RFC 3339 with nine fractional digits, because
    event and receive times drive replay order and latency and must keep
    nanosecond precision. *)

type side = Buy | Sell [@@deriving show, eq]
type liquidity = Maker | Taker [@@deriving show, eq]
type tif = Gtc | Ioc | Fok [@@deriving show, eq]
type quality = Healthy | Suspect of string [@@deriving show, eq]

type level = { price_ticks : int64; quantity_units : int64 }
[@@deriving show, eq]

type depth_snapshot = {
  last_update_id : int64 option;
  bids : level list;
  asks : level list;
}

type depth_update = {
  first_update_id : int64;
  last_update_id : int64;
  previous_update_id : int64 option;
  bids : level list;
  asks : level list;
}

type trade = {
  trade_id : int64;
  price_ticks : int64;
  quantity_units : int64;
  buyer_is_maker : bool;
}

type mark = {
  mark_ticks : int64;
  index_ticks : int64;
  rate : int64;
  next_funding_time : Timestamp.t;
}

type funding = { rate : int64; mark_ticks : int64 }

type liquidation = {
  side : side;
  price_ticks : int64;
  quantity_units : int64;
}

type observation = { data_type : string; payload : string }
type decision = { strategy : string; note : string option }

type intent = {
  order_id : string;
  side : side;
  price_ticks : int64 option;
  quantity_units : int64;
  tif : tif;
  reduce_only : bool;
  post_only : bool;
}

type ack = { order_id : string; accepted : bool; reason : string option }
type cancel = { order_id : string }

type fill = {
  order_id : string;
  side : side;
  price_ticks : int64;
  quantity_units : int64;
  fee : int64;
  liquidity : liquidity;
}

type payload =
  | Depth_snapshot of depth_snapshot
  | Depth_update of depth_update
  | Trade of trade
  | Mark of mark
  | Funding of funding
  | Liquidation of liquidation
  | Observation of observation
  | Decision of decision
  | Order_intent of intent
  | Order_ack of ack
  | Order_cancel of cancel
  | Fill of fill

type t = {
  venue : string;
  symbol : string;
  event_time : Timestamp.t;
  receive_time : Timestamp.t;
  sequence : int64 option;
  source_id : string;
  source_path : string;
  source_sha256 : string;
  quality : quality;
  payload : payload;
}

let ( let* ) result f = Result.bind result f

(* ---------------------------------------------------------------- *)
(* Serialization *)
(* ---------------------------------------------------------------- *)

let json_int value = `Intlit (Int64.to_string value)

let json_opt_int64 = function Some value -> json_int value | None -> `Null
let json_opt_string = function Some value -> `String value | None -> `Null

(* Nine fractional digits keep nanosecond precision, unlike
   [Timestamp.to_string] which defaults to whole seconds. *)
let timestamp_to_string (value : Timestamp.t) =
  Ptime.to_rfc3339 ~tz_offset_s:0 ~frac_s:9 (Timestamp.to_ptime value)

let json_side = function Buy -> `String "buy" | Sell -> `String "sell"

let json_tif = function
  | Gtc -> `String "gtc"
  | Ioc -> `String "ioc"
  | Fok -> `String "fok"

let json_liquidity = function
  | Maker -> `String "maker"
  | Taker -> `String "taker"

let json_level (level : level) =
  `List [ json_int level.price_ticks; json_int level.quantity_units ]

let json_levels levels = `List (List.map json_level levels)

let kind_name = function
  | Depth_snapshot _ -> "depth_snapshot"
  | Depth_update _ -> "depth_update"
  | Trade _ -> "trade"
  | Mark _ -> "mark"
  | Funding _ -> "funding"
  | Liquidation _ -> "liquidation"
  | Observation _ -> "observation"
  | Decision _ -> "decision"
  | Order_intent _ -> "order_intent"
  | Order_ack _ -> "order_ack"
  | Order_cancel _ -> "order_cancel"
  | Fill _ -> "fill"

let payload_fields = function
  | Depth_snapshot snapshot ->
      [
        ("last_update_id", json_opt_int64 snapshot.last_update_id);
        ("bids", json_levels snapshot.bids);
        ("asks", json_levels snapshot.asks);
      ]
  | Depth_update update ->
      [
        ("first_update_id", json_int update.first_update_id);
        ("last_update_id", json_int update.last_update_id);
        ("previous_update_id", json_opt_int64 update.previous_update_id);
        ("bids", json_levels update.bids);
        ("asks", json_levels update.asks);
      ]
  | Trade trade ->
      [
        ("trade_id", json_int trade.trade_id);
        ("price_ticks", json_int trade.price_ticks);
        ("quantity_units", json_int trade.quantity_units);
        ("buyer_is_maker", `Bool trade.buyer_is_maker);
      ]
  | Mark mark ->
      [
        ("mark_ticks", json_int mark.mark_ticks);
        ("index_ticks", json_int mark.index_ticks);
        ("rate", json_int mark.rate);
        ("next_funding_time", `String (timestamp_to_string mark.next_funding_time));
      ]
  | Funding funding ->
      [ ("rate", json_int funding.rate); ("mark_ticks", json_int funding.mark_ticks) ]
  | Liquidation liquidation ->
      [
        ("side", json_side liquidation.side);
        ("price_ticks", json_int liquidation.price_ticks);
        ("quantity_units", json_int liquidation.quantity_units);
      ]
  | Observation observation ->
      [
        ("data_type", `String observation.data_type);
        ("payload", `String observation.payload);
      ]
  | Decision decision ->
      [ ("strategy", `String decision.strategy); ("note", json_opt_string decision.note) ]
  | Order_intent intent ->
      [
        ("order_id", `String intent.order_id);
        ("side", json_side intent.side);
        ("price_ticks", json_opt_int64 intent.price_ticks);
        ("quantity_units", json_int intent.quantity_units);
        ("tif", json_tif intent.tif);
        ("reduce_only", `Bool intent.reduce_only);
        ("post_only", `Bool intent.post_only);
      ]
  | Order_ack ack ->
      [
        ("order_id", `String ack.order_id);
        ("accepted", `Bool ack.accepted);
        ("reason", json_opt_string ack.reason);
      ]
  | Order_cancel cancel -> [ ("order_id", `String cancel.order_id) ]
  | Fill fill ->
      [
        ("order_id", `String fill.order_id);
        ("side", json_side fill.side);
        ("price_ticks", json_int fill.price_ticks);
        ("quantity_units", json_int fill.quantity_units);
        ("fee", json_int fill.fee);
        ("liquidity", json_liquidity fill.liquidity);
      ]

let to_yojson event =
  let quality_fields =
    match event.quality with
    | Healthy -> [ ("quality", `String "healthy") ]
    | Suspect reason ->
        [ ("quality", `String "suspect"); ("quality_reason", `String reason) ]
  in
  let envelope =
    [
      ("kind", `String (kind_name event.payload));
      ("venue", `String event.venue);
      ("symbol", `String event.symbol);
      ("event_time", `String (timestamp_to_string event.event_time));
      ("receive_time", `String (timestamp_to_string event.receive_time));
      ("sequence", json_opt_int64 event.sequence);
      ("source_id", `String event.source_id);
      ("source_path", `String event.source_path);
      ("source_sha256", `String event.source_sha256);
    ]
    @ quality_fields
  in
  `Assoc (envelope @ payload_fields event.payload)

let to_string event = Yojson.Safe.to_string (to_yojson event)

(* ---------------------------------------------------------------- *)
(* Parsing *)
(* ---------------------------------------------------------------- *)

let member name json = Yojson.Safe.Util.member name json

let string_field name json =
  match member name json with
  | `String value -> Ok value
  | `Null -> Serror.failf "missing field %s" name
  | _ -> Serror.failf "field %s must be a string" name

let nonempty name value =
  if value = "" then Serror.failf "field %s must not be empty" name else Ok value

let bool_field name json =
  match member name json with
  | `Bool value -> Ok value
  | `Null -> Serror.failf "missing field %s" name
  | _ -> Serror.failf "field %s must be a boolean" name

let int64_field name json =
  match member name json with
  | `Int value -> Ok (Int64.of_int value)
  | `Intlit value -> (
      match Int64.of_string_opt value with
      | Some value -> Ok value
      | None -> Serror.failf "field %s is not a valid integer" name)
  | `String value -> (
      match Int64.of_string_opt value with
      | Some value -> Ok value
      | None -> Serror.failf "field %s is not a valid integer" name)
  | `Null -> Serror.failf "missing field %s" name
  | _ -> Serror.failf "field %s must be an integer" name

let optional_int64_field name json =
  match member name json with
  | `Null -> Ok None
  | _ -> (
      match int64_field name json with
      | Ok value -> Ok (Some value)
      | Error _ as error -> error)

let timestamp_field name json =
  let* text = string_field name json in
  match Timestamp.of_string text with
  | Ok value -> Ok value
  | Error _ -> Serror.failf "field %s is not an RFC 3339 timestamp" name

let nonnegative name value =
  if value < 0L then Serror.failf "field %s must not be negative" name
  else Ok value

let positive name value =
  if value <= 0L then Serror.failf "field %s must be positive" name
  else Ok value

let side_field name json =
  let* value = string_field name json in
  match value with
  | "buy" -> Ok Buy
  | "sell" -> Ok Sell
  | _ -> Serror.failf "field %s is not a side" name

let tif_field name json =
  let* value = string_field name json in
  match value with
  | "gtc" -> Ok Gtc
  | "ioc" -> Ok Ioc
  | "fok" -> Ok Fok
  | _ -> Serror.failf "field %s is not a time in force" name

let liquidity_field name json =
  let* value = string_field name json in
  match value with
  | "maker" -> Ok Maker
  | "taker" -> Ok Taker
  | _ -> Serror.failf "field %s is not a liquidity class" name

let levels_field name json =
  match member name json with
  | `List values ->
      Serror.map values ~f:(function
        | `List [ price; quantity ] ->
            let* price_ticks =
              match price with
              | `Int value -> Ok (Int64.of_int value)
              | `Intlit value -> (
                  match Int64.of_string_opt value with
                  | Some value -> Ok value
                  | None -> Serror.failf "invalid level price in %s" name)
              | `String value -> (
                  match Int64.of_string_opt value with
                  | Some value -> Ok value
                  | None -> Serror.failf "invalid level price in %s" name)
              | _ -> Serror.failf "invalid level price in %s" name
            in
            let* quantity_units =
              match quantity with
              | `Int value -> Ok (Int64.of_int value)
              | `Intlit value -> (
                  match Int64.of_string_opt value with
                  | Some value -> Ok value
                  | None -> Serror.failf "invalid level size in %s" name)
              | `String value -> (
                  match Int64.of_string_opt value with
                  | Some value -> Ok value
                  | None -> Serror.failf "invalid level size in %s" name)
              | _ -> Serror.failf "invalid level size in %s" name
            in
            let* price_ticks = positive name price_ticks in
            let* quantity_units = nonnegative name quantity_units in
            Ok { price_ticks; quantity_units }
        | _ -> Serror.failf "invalid level in %s" name)
  | `Null -> Serror.failf "missing field %s" name
  | _ -> Serror.failf "field %s must be an array" name

let quality_field json =
  let* value = string_field "quality" json in
  match value with
  | "healthy" -> Ok Healthy
  | "suspect" ->
      let* reason = string_field "quality_reason" json in
      let* reason = nonempty "quality_reason" reason in
      Ok (Suspect reason)
  | _ -> Serror.fail "quality must be healthy or suspect"

let parse_payload kind json =
  match kind with
  | "depth_snapshot" ->
      let* last_update_id = optional_int64_field "last_update_id" json in
      let* last_update_id =
        match last_update_id with
        | Some value -> (
            match nonnegative "last_update_id" value with
            | Ok value -> Ok (Some value)
            | Error _ as error -> error)
        | None -> Ok None
      in
      let* bids = levels_field "bids" json in
      let* asks = levels_field "asks" json in
      Ok (Depth_snapshot { last_update_id; bids; asks })
  | "depth_update" ->
      let* first_update_id = int64_field "first_update_id" json in
      let* last_update_id = int64_field "last_update_id" json in
      let* previous_update_id = optional_int64_field "previous_update_id" json in
      let* first_update_id = nonnegative "first_update_id" first_update_id in
      let* last_update_id = nonnegative "last_update_id" last_update_id in
      let* () =
        if last_update_id < first_update_id then
          Serror.fail "last_update_id must not precede first_update_id"
        else Ok ()
      in
      let* bids = levels_field "bids" json in
      let* asks = levels_field "asks" json in
      Ok (Depth_update { first_update_id; last_update_id; previous_update_id; bids; asks })
  | "trade" ->
      let* trade_id = int64_field "trade_id" json in
      let* price_ticks = int64_field "price_ticks" json in
      let* quantity_units = int64_field "quantity_units" json in
      let* buyer_is_maker = bool_field "buyer_is_maker" json in
      let* trade_id = nonnegative "trade_id" trade_id in
      let* price_ticks = positive "price_ticks" price_ticks in
      let* quantity_units = positive "quantity_units" quantity_units in
      Ok (Trade { trade_id; price_ticks; quantity_units; buyer_is_maker })
  | "mark" ->
      let* mark_ticks = int64_field "mark_ticks" json in
      let* index_ticks = int64_field "index_ticks" json in
      let* rate = int64_field "rate" json in
      let* next_funding_time = timestamp_field "next_funding_time" json in
      let* mark_ticks = positive "mark_ticks" mark_ticks in
      let* index_ticks = positive "index_ticks" index_ticks in
      Ok (Mark { mark_ticks; index_ticks; rate; next_funding_time })
  | "funding" ->
      let* rate = int64_field "rate" json in
      let* mark_ticks = int64_field "mark_ticks" json in
      let* mark_ticks = positive "mark_ticks" mark_ticks in
      Ok (Funding { rate; mark_ticks })
  | "liquidation" ->
      let* side = side_field "side" json in
      let* price_ticks = int64_field "price_ticks" json in
      let* quantity_units = int64_field "quantity_units" json in
      let* price_ticks = positive "price_ticks" price_ticks in
      let* quantity_units = positive "quantity_units" quantity_units in
      Ok (Liquidation { side; price_ticks; quantity_units })
  | "observation" ->
      let* data_type = string_field "data_type" json in
      let* data_type = nonempty "data_type" data_type in
      let* payload = string_field "payload" json in
      Ok (Observation { data_type; payload })
  | "decision" ->
      let* strategy = string_field "strategy" json in
      let* strategy = nonempty "strategy" strategy in
      let* note =
        match member "note" json with
        | `Null -> Ok None
        | _ ->
            let* note = string_field "note" json in
            let* note = nonempty "note" note in
            Ok (Some note)
      in
      Ok (Decision { strategy; note })
  | "order_intent" ->
      let* order_id = string_field "order_id" json in
      let* order_id = nonempty "order_id" order_id in
      let* side = side_field "side" json in
      let* price_ticks = optional_int64_field "price_ticks" json in
      let* price_ticks =
        match price_ticks with
        | Some value -> (
            match positive "price_ticks" value with
            | Ok value -> Ok (Some value)
            | Error _ as error -> error)
        | None -> Ok None
      in
      let* quantity_units = int64_field "quantity_units" json in
      let* quantity_units = positive "quantity_units" quantity_units in
      let* tif = tif_field "tif" json in
      let* reduce_only = bool_field "reduce_only" json in
      let* post_only = bool_field "post_only" json in
      Ok (Order_intent { order_id; side; price_ticks; quantity_units; tif; reduce_only; post_only })
  | "order_ack" ->
      let* order_id = string_field "order_id" json in
      let* order_id = nonempty "order_id" order_id in
      let* accepted = bool_field "accepted" json in
      let* reason =
        match member "reason" json with
        | `Null -> Ok None
        | _ ->
            let* reason = string_field "reason" json in
            let* reason = nonempty "reason" reason in
            Ok (Some reason)
      in
      let* () =
        if (not accepted) && reason = None then
          Serror.fail "a rejected order needs a reason"
        else Ok ()
      in
      Ok (Order_ack { order_id; accepted; reason })
  | "order_cancel" ->
      let* order_id = string_field "order_id" json in
      let* order_id = nonempty "order_id" order_id in
      Ok (Order_cancel { order_id })
  | "fill" ->
      let* order_id = string_field "order_id" json in
      let* order_id = nonempty "order_id" order_id in
      let* side = side_field "side" json in
      let* price_ticks = int64_field "price_ticks" json in
      let* quantity_units = int64_field "quantity_units" json in
      let* fee = int64_field "fee" json in
      let* liquidity = liquidity_field "liquidity" json in
      let* price_ticks = positive "price_ticks" price_ticks in
      let* quantity_units = positive "quantity_units" quantity_units in
      Ok (Fill { order_id; side; price_ticks; quantity_units; fee; liquidity })
  | other -> Serror.failf "unknown event kind %s" other

let of_yojson json =
  let* kind = string_field "kind" json in
  let* venue = string_field "venue" json in
  let* venue = nonempty "venue" venue in
  let* symbol = string_field "symbol" json in
  let* symbol = nonempty "symbol" symbol in
  let* event_time = timestamp_field "event_time" json in
  let* receive_time = timestamp_field "receive_time" json in
  let* sequence = optional_int64_field "sequence" json in
  let* sequence =
    match sequence with
    | Some value -> (
        match nonnegative "sequence" value with
        | Ok value -> Ok (Some value)
        | Error _ as error -> error)
    | None -> Ok None
  in
  let* source_id = string_field "source_id" json in
  let* source_id = nonempty "source_id" source_id in
  let* source_path = string_field "source_path" json in
  let* source_path = nonempty "source_path" source_path in
  let* source_sha256 = string_field "source_sha256" json in
  let* source_sha256 = nonempty "source_sha256" source_sha256 in
  let* quality = quality_field json in
  let* payload = parse_payload kind json in
  Ok
    {
      venue;
      symbol;
      event_time;
      receive_time;
      sequence;
      source_id;
      source_path;
      source_sha256;
      quality;
      payload;
    }

let of_string text =
  match Yojson.Safe.from_string text with
  | json -> of_yojson json
  | exception Yojson.Json_error message ->
      Serror.failf "invalid JSON: %s" message
