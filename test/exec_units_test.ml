open Alcotest

module U = Market_simulator.Exec_units

let ok = function
  | Ok value -> value
  | Error message -> failwith ("unexpected error: " ^ message)

let is_error = function
  | Ok _ -> false
  | Error _ -> true

let test_price_round_trip () =
  let cases =
    [ ("0.0001", 1L); ("1", 10_000L); ("100.5", 1_005_000L);
      ("214748.3647", 2_147_483_647L) ]
  in
  List.iter
    (fun (text, units) ->
      check int64 ("parse " ^ text) units (ok (U.parse_price text));
      check string ("format " ^ text) text (U.format_price units))
    cases

let test_quantity_round_trip () =
  check int64 "quantity" 1_000_001L (ok (U.parse_quantity "1.000001"));
  check string "quantity format" "1.000001" (U.format_quantity 1_000_001L)

let test_money_round_trip () =
  check int64 "money" 1_250_000_000L (ok (U.parse_money "12.5"));
  check int64 "negative money" (-1_500_000_00L) (ok (U.parse_money "-1.5"));
  check string "money format" "-1.5" (U.format_money (-150_000_000L));
  check string "money whole" "0" (U.format_money 0L)

let test_rate_round_trip () =
  check int64 "rate" 10_000L (ok (U.parse_rate "0.0001"));
  check string "rate format" "0.0001" (U.format_rate 10_000L)

let test_rejects_bad_decimals () =
  check bool "over precision" true (is_error (U.parse_price "0.00001"));
  check bool "trailing zeros ok" false (is_error (U.parse_price "1.50000"));
  check bool "empty" true (is_error (U.parse_price ""));
  check bool "garbage" true (is_error (U.parse_price "abc"));
  check bool "double point" true (is_error (U.parse_price "1.2.3"));
  check bool "overflow" true
    (is_error (U.parse_price "999999999999999999999"));
  check int64 "trailing zeros value" 15_000L (ok (U.parse_price "1.50000"))

let test_notional_exact () =
  check int64 "100 x 1" 10_000_000_000L
    (ok (U.notional ~price_ticks:1_000_000L ~quantity_units:1_000_000L));
  check int64 "large notional" 1_000_000_000_000_000L
    (ok (U.notional ~price_ticks:1_000_000_000L ~quantity_units:100_000_000L))

let test_notional_rounding () =
  check int64 "half rounds away" 1L
    (ok (U.notional ~price_ticks:1L ~quantity_units:50L));
  check int64 "below half rounds to zero" 0L
    (ok (U.notional ~price_ticks:1L ~quantity_units:49L));
  check int64 "negative half rounds away" (-1L)
    (ok (U.notional ~price_ticks:1L ~quantity_units:(-50L)))

let test_notional_overflow () =
  check bool "overflow" true
    (is_error (U.notional ~price_ticks:Int64.max_int ~quantity_units:Int64.max_int));
  check bool "zero price rejected" true
    (is_error (U.notional ~price_ticks:0L ~quantity_units:1_000_000L))

let test_bps () =
  check int64 "4 bps of 100" 4_000_000L (ok (U.bps ~money:10_000_000_000L ~bps:4));
  check int64 "round to zero" 0L (ok (U.bps ~money:50L ~bps:1));
  check int64 "half rounds away" 1L (ok (U.bps ~money:50L ~bps:100));
  check int64 "negative half rounds away" (-1L)
    (ok (U.bps ~money:(-50L) ~bps:100));
  check bool "negative fee bps rejected" true
    (is_error (U.bps ~money:1_000L ~bps:(-1)));
  check int64 "full rate" 100_000_000L (ok (U.bps ~money:100_000_000L ~bps:10_000))

let test_div_round_and_ceil () =
  check int64 "half away from zero" 1L (ok (U.div_round 5L 10L));
  check int64 "below half" 0L (ok (U.div_round 4L 10L));
  check int64 "negative half away" (-1L) (ok (U.div_round (-5L) 10L));
  check int64 "odd divisor rounds up past half" 1L (ok (U.div_round 2L 3L));
  check int64 "odd divisor rounds down" 0L (ok (U.div_round 1L 3L));
  check int64 "ceil exact" 4L (ok (U.div_ceil 12L 3L));
  check int64 "ceil rounds up" 5L (ok (U.div_ceil 13L 3L));
  check int64 "ceil zero" 0L (ok (U.div_ceil 0L 3L));
  check bool "ceil rejects negatives" true (is_error (U.div_ceil (-1L) 3L));
  check bool "zero divisor" true (is_error (U.div_round 1L 0L))

let test_price_interop () =
  check int64 "ticks of price" 1_005_000L
    (U.ticks_of_price (Market_simulator.Price.of_int 1_005_000));
  check int64 "price of ticks" 1_005_000L
    (ok (U.price_of_ticks 1_005_000L) |> Market_simulator.Price.to_int
   |> Int64.of_int);
  check bool "price range" true (is_error (U.price_of_ticks 2_147_483_648L))

let () =
  run "exec_units"
    [
      ( "decimal",
        [ test_case "price round trip" `Quick test_price_round_trip;
          test_case "quantity round trip" `Quick test_quantity_round_trip;
          test_case "money round trip" `Quick test_money_round_trip;
          test_case "rate round trip" `Quick test_rate_round_trip;
          test_case "bad decimals" `Quick test_rejects_bad_decimals ] );
      ( "arithmetic",
        [ test_case "notional exact" `Quick test_notional_exact;
          test_case "notional rounding" `Quick test_notional_rounding;
          test_case "notional overflow" `Quick test_notional_overflow;
          test_case "bps" `Quick test_bps;
          test_case "rounding" `Quick test_div_round_and_ceil;
          test_case "price interop" `Quick test_price_interop ] );
    ]
