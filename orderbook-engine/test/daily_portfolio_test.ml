open Alcotest
module P = Market_simulator.Daily_portfolio
module T = Market_simulator.Timestamp

let ok = function Ok x -> x | Error message -> failwith message
let timestamp value = ok (T.of_string value)
let sha = String.make 64 'a'
let initial = 10_000_000_000L

let config = {
  P.strategy_name = "unit-fixture";
  hypothesis_sha256 = sha;
  primary_specification_id = "spec-v1";
  source_name = "synthetic";
  source_url = "https://example.invalid";
  license = "test-only";
  cost_model_id = "test-cost-v1";
  cost_source = "synthetic test assumptions";
  universe = ["AAA"];
  initial_equity_money_units = initial;
  max_gross_exposure_bps = 1000;
  max_abs_net_exposure_bps = 1000;
  max_abs_name_weight_bps = 1000;
  max_participation_bps = 10_000;
  variants_attempted = 1;
  periods_per_year = 252;
}

let row ~session ~decision ~entry ~exit ~weight ~ret ?(cost=0) ?(borrow=true)
    ?(borrow_rate=0) ?(borrow_days=1) ?(adv=1_000_000_000_000_000L)
    ?(feature_available=None) () = {
  P.session;
  symbol = "AAA";
  sector = "industrials";
  regime = "normal";
  signal_id = "signal-v1";
  feature_available_at = Option.value feature_available ~default:(timestamp decision);
  universe_available_at = timestamp decision;
  adv_available_at = timestamp decision;
  borrow_available_at = timestamp decision;
  decision_at = timestamp decision;
  entry_at = timestamp entry;
  exit_at = timestamp exit;
  eligible = true;
  target_weight_bps = weight;
  forward_total_return_1e8 = ret;
  benchmark_return_1e8 = 100_000L;
  sector_return_1e8 = 80_000L;
  adv_money_units = adv;
  one_way_cost_bps = cost;
  borrow_available = borrow;
  borrow_rate_bps_annual = borrow_rate;
  borrow_days;
  source_id = "synthetic";
  source_sha256 = sha;
  quality = "healthy";
  data_status = "observed";
}

let two_rows first second = [first; second]

let test_net_cost_and_curve () =
  let first = row ~session:"2025-01-02" ~decision:"2025-01-01T20:00:00Z"
      ~entry:"2025-01-02T14:30:00Z" ~exit:"2025-01-03T14:30:00Z"
      ~weight:1000 ~ret:10_000_000L ~cost:10 () in
  let second = row ~session:"2025-01-03" ~decision:"2025-01-02T14:29:00Z"
      ~entry:"2025-01-03T14:30:00Z" ~exit:"2025-01-06T14:30:00Z"
      ~weight:1000 ~ret:0L () in
  let output = ok (P.run config (two_rows first second)) in
  let day = List.hd output.P.all_days in
  check int64 "gross 1%" 1_000_000L day.P.gross_return_1e8;
  check int64 "cost is 0.01%" 10_000L day.P.transaction_cost_1e8;
  check int64 "net 0.99%" 990_000L day.P.net_return_1e8;
  check int64 "equity exact" 10_099_000_000L day.P.net_equity;
  check int "one output row per symbol-period" 2 (List.length output.P.positions);
  check (option int64) "capacity at 100% ADV participation" (Some 10_000_000_000_000_000L)
    (List.hd output.P.positions).P.capacity_money_units;
  check bool "later one-fifth is the OOS boundary" true
    (output.P.split_start_session = "2025-01-03")

let test_short_borrow_exact () =
  let short_config = { config with P.max_gross_exposure_bps = 1000; max_abs_net_exposure_bps = 1000 } in
  let first = row ~session:"2025-01-02" ~decision:"2025-01-01T20:00:00Z"
      ~entry:"2025-01-02T14:30:00Z" ~exit:"2025-01-03T14:30:00Z"
      ~weight:(-1000) ~ret:0L ~borrow_rate:1000 ~borrow_days:252 () in
  let second = row ~session:"2025-01-03" ~decision:"2025-01-02T14:29:00Z"
      ~entry:"2025-01-03T14:30:00Z" ~exit:"2025-01-06T14:30:00Z"
      ~weight:(-1000) ~ret:0L ~borrow_rate:1000 ~borrow_days:252 () in
  let output = ok (P.run short_config [first; second]) in
  check int64 "10% of 10% annual borrow" 1_000_000L
    (List.hd output.P.all_days).P.borrow_cost_1e8

let test_timing_and_borrow_guards () =
  let base = row ~session:"2025-01-02" ~decision:"2025-01-01T20:00:00Z"
      ~entry:"2025-01-02T14:30:00Z" ~exit:"2025-01-03T14:30:00Z"
      ~weight:(-1000) ~ret:0L () in
  check bool "future feature fails" true
    (Result.is_error (P.validate_observation { base with P.feature_available_at = timestamp "2025-01-02T14:31:00Z" }));
  check bool "unavailable borrow fails" true
    (Result.is_error (P.validate_observation { base with P.borrow_available = false }))

let test_risk_and_liquidity_caps_fail_closed () =
  let first = row ~session:"2025-01-02" ~decision:"2025-01-01T20:00:00Z"
      ~entry:"2025-01-02T14:30:00Z" ~exit:"2025-01-03T14:30:00Z"
      ~weight:1000 ~ret:0L ~adv:1L () in
  let second = row ~session:"2025-01-03" ~decision:"2025-01-02T14:29:00Z"
      ~entry:"2025-01-03T14:30:00Z" ~exit:"2025-01-06T14:30:00Z"
      ~weight:1000 ~ret:0L ~adv:1L () in
  check bool "capacity breach fails, does not silently resize" true
    (Result.is_error (P.run config [first; second]));
  let over = { first with P.target_weight_bps = 1001 } in
  check bool "target outside gross/name caps fails" true
    (Result.is_error (P.run config [over; second]))

let test_large_fixed_point_product () =
  let large_config = { config with P.initial_equity_money_units = 1_000_000_000_000_000_000L;
    max_gross_exposure_bps = 10_000; max_abs_net_exposure_bps = 10_000;
    max_abs_name_weight_bps = 10_000 } in
  let first = row ~session:"2025-01-02" ~decision:"2025-01-01T20:00:00Z"
      ~entry:"2025-01-02T14:30:00Z" ~exit:"2025-01-03T14:30:00Z"
      ~weight:10_000 ~ret:100_000_000L ~adv:9_000_000_000_000_000_000L () in
  let second = row ~session:"2025-01-03" ~decision:"2025-01-02T14:29:00Z"
      ~entry:"2025-01-03T14:30:00Z" ~exit:"2025-01-06T14:30:00Z"
      ~weight:10_000 ~ret:0L ~adv:9_000_000_000_000_000_000L () in
  let output = ok (P.run large_config [first; second]) in
  check int64 "NAV times 100% return fits even though product overflows"
    2_000_000_000_000_000_000L (List.hd output.P.all_days).P.net_equity

let () =
  run "daily_portfolio"
    [ ("portfolio", [
        test_case "net cost and curve" `Quick test_net_cost_and_curve;
        test_case "short borrow exact" `Quick test_short_borrow_exact;
        test_case "timing and borrow guards" `Quick test_timing_and_borrow_guards;
        test_case "risk and liquidity caps" `Quick test_risk_and_liquidity_caps_fail_closed;
        test_case "large fixed-point product" `Quick test_large_fixed_point_product;
      ]) ]
