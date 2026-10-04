open Alcotest

module Binance = Market_simulator.Binance_l2

let instrument =
  match
    Market_simulator.Binance_units.instrument ~symbol:"BTCUSDT"
      ~price_step:"0.10" ~quantity_step:"0.001"
  with
  | Ok value -> value
  | Error error -> failwith error

let row kind segment ids bids asks received event_time_ms applied =
  Printf.sprintf
    "{\"kind\":\"%s\",\"segment\":%d,\"symbol\":\"BTCUSDT\",\"received_time\":\"%s\",\"event_time_ms\":%Ld,\"source_path\":\"capture.gz\",\"source_sha256\":\"digest\",\"applied\":%s,%s,\"bids\":%s,\"asks\":%s}"
    kind segment received event_time_ms (if applied then "true" else "false")
    (match ids with
    | `Snapshot id ->
        Printf.sprintf
          "\"last_update_id\":%Ld,\"first_update_id\":null,\"final_update_id\":null,\"previous_update_id\":null"
          id
    | `Update (first_id, final_id, previous_id) ->
        Printf.sprintf
          "\"last_update_id\":null,\"first_update_id\":%Ld,\"final_update_id\":%Ld,\"previous_update_id\":%Ld"
          first_id final_id previous_id)
    bids asks

let snapshot =
  row "snapshot" 0 (`Snapshot 100L)
    "[[\"100.00\",\"2.0\"]]"
    "[[\"100.10\",\"3.0\"]]" "2024.01.01D00:00:00.000000000" 1704067200000L true

let update first_id final_id previous_id bids asks received event_time applied =
  row "update" 0 (`Update (first_id, final_id, previous_id)) bids asks received
    event_time applied

let test_parse_normalized () =
  match Binance.parse_normalized_lines [ snapshot ] with
  | Error error -> fail error
  | Ok [ parsed ] ->
      check string "symbol" "BTCUSDT" parsed.symbol;
      check int64 "segment" 0L parsed.segment;
      check bool "applied" true parsed.applied;
      check int64 "snapshot id" 100L
        (Option.get parsed.last_update_id);
      check int "bid levels" 1 (List.length parsed.bids)
  | Ok _ -> fail "expected one normalized row"

let test_replay_normalized () =
  let update =
    update 101L 101L 100L "[[\"100.00\",\"0\"]]"
      "[[\"100.10\",\"1.5\"]]" "2024-01-01T00:00:00.100Z"
      1704067200100L true
  in
  match Binance.parse_normalized_lines [ snapshot; update ] with
  | Error error -> fail error
  | Ok rows -> (
      match Binance.replay_normalized ~instrument rows with
      | Error error -> fail error
      | Ok [ _snapshot_state; state ] ->
          check int64 "final update id" 101L state.last_update_id;
          check int "removed bid" 0 (List.length state.bids);
          let ask = List.hd state.asks in
          check string "ask price" "100.1" ask.price;
          check string "ask size" "1.5" ask.size
      | Ok _ -> fail "expected snapshot and update states")

let test_reject_gap () =
  let update =
    update 102L 102L 101L "[]" "[]" "2024-01-01T00:00:00.200Z"
      1704067200200L true
  in
  match Binance.parse_normalized_lines [ snapshot; update ] with
  | Error error -> fail error
  | Ok rows -> (
      match Binance.replay_normalized ~instrument rows with
      | Ok _ -> fail "expected update gap rejection"
      | Error error -> check bool "gap" true (String.contains error 'g'))

let test_tick_validation () =
  let instrument =
    match
      Market_simulator.Binance_units.instrument ~symbol:"BTCUSDT"
        ~price_step:"0.10" ~quantity_step:"0.001"
    with
    | Ok value -> value
    | Error error -> fail error
  in
  let invalid =
    "{\"kind\":\"snapshot\",\"segment\":0,\"symbol\":\"BTCUSDT\",\"received_time\":\"2024.01.01D00:00:00.000000000\",\"event_time_ms\":1704067200000,\"source_path\":\"capture.gz\",\"source_sha256\":\"digest\",\"applied\":true,\"last_update_id\":100,\"first_update_id\":null,\"final_update_id\":null,\"previous_update_id\":null,\"bids\":[[\"100.05\",\"2.0\"]],\"asks\":[[\"100.10\",\"3.0\"]]}"
  in
  match
    Binance.parse_normalized_lines_with_instrument instrument [ invalid ]
  with
  | Ok _ -> fail "expected instrument alignment rejection"
  | Error error -> check bool "error" true (String.length error > 0)

let test_raw_normalized_equivalence () =
  let raw_snapshot =
    "2024-01-01T00:00:00.000Z {\"stream\":\"btcusdt@depth\",\"data\":{\"E\":1704067200000,\"lastUpdateId\":100,\"bids\":[[\"100.00\",\"2.0\"]],\"asks\":[[\"100.10\",\"3.0\"]]}}"
  in
  let raw_update =
    "2024-01-01T00:00:00.100Z {\"stream\":\"btcusdt@depth\",\"data\":{\"E\":1704067200100,\"U\":101,\"u\":101,\"pu\":100,\"b\":[[\"100.00\",\"0\"]],\"a\":[[\"100.10\",\"1.5\"]]}}"
  in
  match (Binance.parse_lines [ raw_snapshot; raw_update ],
         Binance.parse_normalized_lines [ snapshot; update 101L 101L 100L "[[\"100.00\",\"0\"]]" "[[\"100.10\",\"1.5\"]]" "2024-01-01T00:00:00.100Z" 1704067200100L true ]) with
  | Ok raw, Ok normalized -> (
      match
        ( Binance.replay ~instrument raw,
          Binance.replay_normalized ~instrument normalized )
      with
      | Ok raw_states, Ok normalized_states ->
          let ids (states : Binance.state list) =
            List.map
              (fun ({ last_update_id; _ } : Binance.state) -> last_update_id)
              states
          in
          check (list int64) "checkpoint IDs" (ids raw_states) (ids normalized_states)
      | Error error, _ | _, Error error -> fail error)
  | Error error, _ | _, Error error -> fail error

let () =
  run "binance_l2"
    [ ( "normalized",
        [ test_case "parse normalized row" `Quick test_parse_normalized;
          test_case "replay normalized rows" `Quick test_replay_normalized;
          test_case "reject update gap" `Quick test_reject_gap;
          test_case "tick validation" `Quick test_tick_validation;
          test_case "raw normalized equivalence" `Quick test_raw_normalized_equivalence ] ) ]
