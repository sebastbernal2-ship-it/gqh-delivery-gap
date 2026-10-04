open Alcotest

module Units = Market_simulator.Binance_units

let unwrap = function Ok value -> value | Error error -> fail error

let test_units () =
  let spec = unwrap (Units.instrument ~symbol:"BTCUSDT" ~price_step:"0.10" ~quantity_step:"0.001") in
  check int64 "price ticks" 1234L (unwrap (Units.to_price_ticks spec "123.40"));
  check int64 "quantity lots" 2500L (unwrap (Units.to_quantity_lots spec "2.500"))

let test_reject_misaligned () =
  let spec = unwrap (Units.instrument ~symbol:"BTCUSDT" ~price_step:"0.10" ~quantity_step:"0.001") in
  match Units.to_price_ticks spec "123.45" with
  | Ok _ -> fail "expected price alignment rejection"
  | Error error -> check bool "error" true (String.length error > 0)

let test_reject_precision () =
  let spec = unwrap (Units.instrument ~symbol:"BTCUSDT" ~price_step:"0.10" ~quantity_step:"0.001") in
  match Units.to_quantity_lots spec "0.0001" with
  | Ok _ -> fail "expected quantity precision rejection"
  | Error error -> check bool "error" true (String.length error > 0)

let () =
  run "binance_units"
    [ ( "decimal",
        [ test_case "convert" `Quick test_units;
          test_case "misaligned" `Quick test_reject_misaligned;
          test_case "precision" `Quick test_reject_precision ] ) ]
