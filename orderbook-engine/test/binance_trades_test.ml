open Alcotest

module Trades = Market_simulator.Binance_trades

let normalized_row =
  "{\"received_time\":\"2024.01.01D00:00:00.100000000\",\"event_time_ms\":1704067200100,\"trade_time_ms\":1704067200099,\"source_path\":\"trades.gz\",\"source_sha256\":\"digest\",\"symbol\":\"BTCUSDT\",\"trade_id\":42,\"price\":\"100.10\",\"quantity\":\"0.5\",\"buyer_is_maker\":true}"

let raw_row =
  "2024-01-01T00:00:00.100Z {\"stream\":\"btcusdt@aggTrade\",\"data\":{\"e\":\"aggTrade\",\"E\":1704067200100,\"s\":\"BTCUSDT\",\"a\":42,\"p\":\"100.10\",\"q\":\"0.5\",\"T\":1704067200099,\"m\":true}}"

let test_normalized () =
  match Trades.parse_normalized_lines [ normalized_row ] with
  | Error error -> fail error
  | Ok [ trade ] ->
      check string "symbol" "BTCUSDT" trade.symbol;
      check int64 "trade id" 42L trade.trade_id;
      check bool "maker" true trade.buyer_is_maker;
      check (float 0.001) "price" 100.10 trade.price;
      check (float 0.001) "quantity" 0.5 trade.quantity
  | Ok _ -> fail "expected one trade"

let test_raw () =
  match Trades.parse_lines [ raw_row ] with
  | Error error -> fail error
  | Ok [ trade ] ->
      check string "symbol" "BTCUSDT" trade.symbol;
      check int64 "trade id" 42L trade.trade_id
  | Ok _ -> fail "expected one trade"

let test_reject_negative () =
  let invalid =
    "{\"received_time\":\"2024.01.01D00:00:00.100000000\",\"event_time_ms\":1704067200100,\"trade_time_ms\":1704067200099,\"source_path\":\"trades.gz\",\"source_sha256\":\"digest\",\"symbol\":\"BTCUSDT\",\"trade_id\":42,\"price\":\"100.10\",\"quantity\":\"-0.5\",\"buyer_is_maker\":true}"
  in
  match Trades.parse_normalized_lines [ invalid ] with
  | Ok _ -> fail "expected negative quantity rejection"
  | Error error -> check bool "error" true (String.length error > 0)

let () =
  run "binance_trades"
    [ ( "parser",
        [ test_case "normalized" `Quick test_normalized;
          test_case "raw" `Quick test_raw;
          test_case "reject negative" `Quick test_reject_negative ] ) ]
