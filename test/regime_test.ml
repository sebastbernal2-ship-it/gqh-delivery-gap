open Alcotest

module E = Market_simulator.Exec_event
module G = Market_simulator.Regime
module L = Market_simulator.Exec_loop
module S = Market_simulator.Exec_strategy
module T = Market_simulator.Timestamp

let time seconds =
  match T.of_string (Printf.sprintf "2026-10-04T00:00:%02d.000000000Z" seconds) with
  | Ok value -> value
  | Error message -> failwith message

let features travel = travel

let test_threshold_is_a_median () =
  let values = [| 10L; 30L; 20L |] in
  check int64 "odd median" 20L (G.threshold_from ~from:0 ~until:3 values);
  let values = [| 10L; 30L; 20L; 40L |] in
  check int64 "even median takes the lower middle" 20L
    (G.threshold_from ~from:0 ~until:4 values);
  check int64 "training slice only" 10L
    (G.threshold_from ~from:0 ~until:2 values)

let test_classify_boundary () =
  let labels = G.classify_all ~threshold:20L [| 19L; 20L; 21L |] in
  check bool "below" true (labels.(0) = G.Low_volatility);
  check bool "at the threshold counts as low" true
    (labels.(1) = G.Low_volatility);
  check bool "above" true (labels.(2) = G.High_volatility)

let event seconds =
  {
    E.venue = "test";
    symbol = "BTCUSDT";
    event_time = time seconds;
    receive_time = time seconds;
    sequence = None;
    source_id = "t";
    source_path = "t";
    source_sha256 = "abc";
    quality = E.Healthy;
    payload =
      E.Depth_snapshot { E.last_update_id = Some 1L; bids = []; asks = [] };
  }

let fill seconds price quantity realized fee =
  {
    L.at = time seconds;
    price_ticks = price;
    quantity_units = quantity;
    liquidity = E.Maker;
    fee;
    realized;
  }

let test_attribution_splits_by_regime () =
  let events = [ event 0; event 1; event 2; event 3 ] in
  let classified =
    [| G.Low_volatility; G.Low_volatility; G.High_volatility; G.High_volatility |]
  in
  let blotter = [ fill 0 100L 1_000L 500L 100L; fill 3 100L 2_000L (-300L) 200L ] in
  let attribution = G.attribute ~classified ~events blotter in
  let low = List.find (fun entry -> entry.G.label = G.Low_volatility) attribution in
  let high = List.find (fun entry -> entry.G.label = G.High_volatility) attribution in
  check int "low fills" 1 low.G.fills;
  check int64 "low realized" 500L low.G.realized;
  check int64 "low fees" 100L low.G.fees;
  check int "high fills" 1 high.G.fills;
  check int64 "high realized" (-300L) high.G.realized

(* Offsets may run past a minute, so the helper splits them. *)
let offset_time total =
  let minutes = total / 60 and seconds = total mod 60 in
  match
    T.of_string
      (Printf.sprintf "2026-10-04T00:%02d:%02d.000000000Z" minutes seconds)
  with
  | Ok value -> value
  | Error message -> failwith message

let depth_event offset ?(bids = []) ?(asks = []) () =
  {
    E.venue = "test";
    symbol = "BTCUSDT";
    event_time = offset_time offset;
    receive_time = offset_time offset;
    sequence = None;
    source_id = "t";
    source_path = "t";
    source_sha256 = "abc";
    quality = E.Healthy;
    payload =
      E.Depth_snapshot
        { E.last_update_id = Some 1L; bids; asks };
  }

let level price_ticks quantity_units = { E.price_ticks; quantity_units }

let test_prefetch_travel_rises_then_decays () =
  (* The mid sits at 10_000_050, then jumps and stays. Travel jumps with it and
     falls back to zero once the jump leaves the trailing window. *)
  let events =
    [
      depth_event 0 ~bids:[ level 1_000_000L 100L ] ~asks:[ level 1_000_100L 100L ] ();
      depth_event 1 ~bids:[ level 1_000_000L 100L ] ~asks:[ level 1_000_100L 100L ] ();
      depth_event 2 ~bids:[ level 1_000_200L 100L ] ~asks:[ level 1_000_300L 100L ] ();
      depth_event 3 ~bids:[ level 1_000_200L 100L ] ~asks:[ level 1_000_300L 100L ] ();
      depth_event 30 ~bids:[ level 1_000_200L 100L ] ~asks:[ level 1_000_300L 100L ] ();
      depth_event 90 ~bids:[ level 1_000_200L 100L ] ~asks:[ level 1_000_300L 100L ] ();
    ]
  in
  let travel = G.prefetch ~window_seconds:60.0 events in
  check int64 "quiet before the jump" 0L travel.(1);
  check int64 "travel after the jump" 200L travel.(2);
  check int64 "still inside the window" 200L travel.(3);
  check int64 "still inside at thirty seconds" 200L travel.(4);
  check int64 "decayed after ninety seconds" 0L travel.(5)

let test_conditioning_rule () =
  let attribution =
    [
      { G.label = G.Low_volatility; fills = 2; units = 10L; fees = 100L; realized = 900L };
      { G.label = G.High_volatility; fills = 1; units = 5L; fees = 100L; realized = (-400L) };
    ]
  in
  check (list string) "trade only where net is positive"
    [ "low_volatility" ]
    (List.map G.label_name (G.condition attribution));
  let both_positive =
    [
      { G.label = G.Low_volatility; fills = 1; units = 1L; fees = 0L; realized = 10L };
      { G.label = G.High_volatility; fills = 1; units = 1L; fees = 0L; realized = 10L };
    ]
  in
  check int "no restriction needed" 2 (List.length (G.condition both_positive));
  let both_negative =
    [
      { G.label = G.Low_volatility; fills = 1; units = 1L; fees = 0L; realized = -10L };
      { G.label = G.High_volatility; fills = 1; units = 1L; fees = 0L; realized = -10L };
    ]
  in
  check int "no regime helps" 0 (List.length (G.condition both_negative))

let () =
  run "regime"
    [
      ( "labels",
        [ test_case "threshold" `Quick test_threshold_is_a_median;
          test_case "boundary" `Quick test_classify_boundary;
          test_case "travel prefetch" `Quick test_prefetch_travel_rises_then_decays ] );
      ( "attribution",
        [ test_case "split" `Quick test_attribution_splits_by_regime;
          test_case "conditioning" `Quick test_conditioning_rule ] );
    ]
