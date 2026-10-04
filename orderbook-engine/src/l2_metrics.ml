(** Descriptive metrics for visible L2 snapshots. *)

type point = {
  timestamp : Timestamp.t;
  mid_price : float;
  spread_bps : float;
  bid_depth : float;
  ask_depth : float;
  imbalance : float;
}

type summary = {
  count : int;
  mean_spread_bps : float;
  min_spread_bps : float;
  max_spread_bps : float;
  mean_imbalance : float;
}

let depth levels =
  match List.rev levels with
  | [] -> 0.0
  | level :: _ -> max 0.0 level.Hf_l2.cumulative_size

let measure (snapshot : Hf_l2.snapshot) =
  match (snapshot.bids, snapshot.asks) with
  | bid :: _, ask :: _ when snapshot.mid_price > 0.0 ->
      let bid_depth = depth snapshot.bids in
      let ask_depth = depth snapshot.asks in
      let total_depth = bid_depth +. ask_depth in
      Ok
        {
          timestamp = snapshot.timestamp;
          mid_price = snapshot.mid_price;
          spread_bps =
            (ask.price -. bid.price) /. snapshot.mid_price *. 10_000.0;
          bid_depth;
          ask_depth;
          imbalance =
            (if total_depth = 0.0 then 0.0
             else (bid_depth -. ask_depth) /. total_depth);
        }
  | _ -> Serror.fail "cannot measure L2 snapshot without both sides"

let summarize points =
  match points with
  | [] ->
      {
        count = 0;
        mean_spread_bps = 0.0;
        min_spread_bps = 0.0;
        max_spread_bps = 0.0;
        mean_imbalance = 0.0;
      }
  | first :: rest ->
      let count = List.length points in
      let spread_sum, imbalance_sum, min_spread, max_spread =
        List.fold_left
          (fun (spread_sum, imbalance_sum, min_spread, max_spread) point ->
            ( spread_sum +. point.spread_bps,
              imbalance_sum +. point.imbalance,
              min min_spread point.spread_bps,
              max max_spread point.spread_bps ))
          (first.spread_bps, first.imbalance, first.spread_bps, first.spread_bps)
          rest
      in
      {
        count;
        mean_spread_bps = spread_sum /. float_of_int count;
        min_spread_bps = min_spread;
        max_spread_bps = max_spread;
        mean_imbalance = imbalance_sum /. float_of_int count;
      }
