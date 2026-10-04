open Alcotest

module E = Market_simulator.Exec_event
module T = Market_simulator.Timestamp

let ok = function
  | Ok value -> value
  | Error message -> failwith ("unexpected error: " ^ message)

let is_error = function Ok _ -> false | Error _ -> true

let time text = ok (T.of_string text)

let envelope payload =
  {
    E.venue = "binance-futures";
    symbol = "BTCUSDT";
    event_time = time "2024-01-01T00:00:00.100000000Z";
    receive_time = time "2024-01-01T00:00:00.150000000Z";
    sequence = Some 42L;
    source_id = "tardis";
    source_path = "captures/bookDepth-2024-01-01.csv.gz";
    source_sha256 = "5a1f0000000000000000000000000000000000000000000000000000000000ff";
    quality = E.Healthy;
    payload;
  }

let level price quantity = { E.price_ticks = price; quantity_units = quantity }

let round_trip name payload =
  let event = envelope payload in
  let text = E.to_string event in
  match E.of_string text with
  | Error message -> failwith (name ^ ": " ^ message)
  | Ok parsed ->
      check string (name ^ ": text") text (E.to_string parsed);
      check bool (name ^ ": event time") true
        (T.equal parsed.E.event_time event.E.event_time);
      check bool (name ^ ": payload") true (parsed.E.payload = payload);
      parsed

let test_depth_snapshot () =
  let payload =
    E.Depth_snapshot
      {
        E.last_update_id = Some 1_000L;
        bids = [ level 1_000_000L 2_000_000L; level 999_900L 500_000L ];
        asks = [ level 1_010_000L 1_000_000L ];
      }
  in
  match round_trip "depth snapshot" payload with
  | { E.payload = E.Depth_snapshot snapshot; _ } ->
      check int "bid levels" 2 (List.length snapshot.bids);
      check int64 "first bid price" 1_000_000L
        (List.hd snapshot.bids).E.price_ticks
  | _ -> failwith "unexpected payload"

let test_depth_update () =
  ignore
    (round_trip "depth update"
       (E.Depth_update
          {
            E.first_update_id = 10L;
            last_update_id = 12L;
            previous_update_id = Some 9L;
            bids = [ level 1_000_000L 0L ];
            asks = [ level 1_010_000L 300_000L ];
          }))

let test_trade () =
  ignore
    (round_trip "trade"
       (E.Trade
          {
            E.trade_id = 99L;
            price_ticks = 1_000_000L;
            quantity_units = 150_000L;
            buyer_is_maker = true;
          }))

let test_mark () =
  ignore
    (round_trip "mark"
       (E.Mark
          {
            E.mark_ticks = 1_000_000L;
            index_ticks = 999_990L;
            rate = 10_000L;
            next_funding_time = time "2024-01-01T08:00:00.000000000Z";
          }))

let test_funding () =
  ignore (round_trip "funding" (E.Funding { E.rate = -2_500L; mark_ticks = 1_000_000L }))

let test_liquidation () =
  ignore
    (round_trip "liquidation"
       (E.Liquidation
          { E.side = E.Sell; price_ticks = 990_000L; quantity_units = 30_000L }))

let test_observation () =
  ignore
    (round_trip "observation"
       (E.Observation
          { E.data_type = "aws-gpu-spot"; payload = {|{"instance_type":"p4d"}|} }))

let test_decision () =
  ignore
    (round_trip "decision"
       (E.Decision { E.strategy = "quote-maker"; note = Some "widen on inventory" }))

let test_intent () =
  ignore
    (round_trip "order intent"
       (E.Order_intent
          {
            E.order_id = "ord-1";
            side = E.Buy;
            price_ticks = Some 999_000L;
            quantity_units = 10_000L;
            tif = E.Gtc;
            reduce_only = false;
            post_only = true;
          }));
  ignore
    (round_trip "market intent"
       (E.Order_intent
          {
            E.order_id = "ord-2";
            side = E.Sell;
            price_ticks = None;
            quantity_units = 10_000L;
            tif = E.Ioc;
            reduce_only = true;
            post_only = false;
          }))

let test_ack () =
  ignore
    (round_trip "ack accepted"
       (E.Order_ack { E.order_id = "ord-1"; accepted = true; reason = None }));
  ignore
    (round_trip "ack rejected"
       (E.Order_ack
          {
            E.order_id = "ord-1";
            accepted = false;
            reason = Some "insufficient margin";
          }))

let test_cancel () = ignore (round_trip "cancel" (E.Order_cancel { E.order_id = "ord-1" }))

let test_fill () =
  ignore
    (round_trip "fill"
       (E.Fill
          {
            E.order_id = "ord-1";
            side = E.Buy;
            price_ticks = 1_000_000L;
            quantity_units = 10_000L;
            fee = -4_000L;
            liquidity = E.Maker;
          }))

let test_quality () =
  ignore
    (round_trip "suspect"
       (E.Depth_snapshot { E.last_update_id = None; bids = []; asks = [] }))

let base_json () =
  E.to_yojson
    (envelope
       (E.Depth_snapshot { E.last_update_id = Some 1L; bids = []; asks = [] }))

let drop name json =
  match json with
  | `Assoc fields -> `Assoc (List.filter (fun (key, _) -> key <> name) fields)
  | _ -> json

let set name value json =
  match json with
  | `Assoc fields ->
      `Assoc ((name, value) :: List.filter (fun (key, _) -> key <> name) fields)
  | _ -> json

let test_rejects_bad_envelopes () =
  check bool "missing source hash" true (is_error (E.of_yojson (drop "source_sha256" (base_json ()))));
  check bool "empty venue" true (is_error (E.of_yojson (set "venue" (`String "") (base_json ()))));
  check bool "empty source id" true (is_error (E.of_yojson (set "source_id" (`String "") (base_json ()))));
  check bool "unknown kind" true (is_error (E.of_yojson (set "kind" (`String "mystery") (base_json ()))));
  check bool "negative sequence" true (is_error (E.of_yojson (set "sequence" (`Int (-1)) (base_json ()))));
  check bool "suspect without reason" true
    (is_error (E.of_yojson (set "quality" (`String "suspect") (base_json ()))));
  check bool "invalid json" true (is_error (E.of_string "{not json"))

let test_rejects_bad_payloads () =
  let bad_levels json =
    E.of_yojson (set "bids" (`List [ `List [ `Int 0; `Int 1 ] ]) json)
  in
  check bool "zero level price" true (is_error (bad_levels (base_json ())));
  let bad_quantity json =
    E.of_yojson (set "bids" (`List [ `List [ `Int 1; `Int (-1) ] ]) json)
  in
  check bool "negative level size" true (is_error (bad_quantity (base_json ())));
  let trade = E.to_yojson (envelope (E.Trade { E.trade_id = 1L; price_ticks = 1L; quantity_units = 1L; buyer_is_maker = false })) in
  check bool "zero trade quantity" true
    (is_error (E.of_yojson (set "quantity_units" (`Int 0) trade)))

let test_suspect_round_trip () =
  let event =
    {
      (envelope (E.Depth_snapshot { E.last_update_id = None; bids = []; asks = [] }))
      with E.quality = E.Suspect "gap before snapshot";
    }
  in
  match E.of_string (E.to_string event) with
  | Error message -> failwith message
  | Ok parsed ->
      check bool "quality" true (parsed.E.quality = E.Suspect "gap before snapshot")

let () =
  run "exec_event"
    [
      ( "round trip",
        [ test_case "depth snapshot" `Quick test_depth_snapshot;
          test_case "depth update" `Quick test_depth_update;
          test_case "trade" `Quick test_trade;
          test_case "mark" `Quick test_mark;
          test_case "funding" `Quick test_funding;
          test_case "liquidation" `Quick test_liquidation;
          test_case "observation" `Quick test_observation;
          test_case "decision" `Quick test_decision;
          test_case "intent" `Quick test_intent;
          test_case "ack" `Quick test_ack;
          test_case "cancel" `Quick test_cancel;
          test_case "fill" `Quick test_fill ] );
      ( "validation",
        [ test_case "bad envelopes" `Quick test_rejects_bad_envelopes;
          test_case "bad payloads" `Quick test_rejects_bad_payloads;
          test_case "suspect quality" `Quick test_suspect_round_trip ] );
    ]
