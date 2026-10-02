(** Snapshot-based strategy backtesting for derived L2 data. *)

type order = {
  side : L2_execution.side;
  size : float;
  limit_price : float option;
}

type portfolio = {
  timestamp : Timestamp.t;
  cash : float;
  position : float;
  equity : float;
  fees : float;
  funding_paid : float;
  trade_count : int;
}

type trade = {
  timestamp : Timestamp.t;
  side : L2_execution.side;
  price : float;
  size : float;
  fee : float;
}

type point = {
  timestamp : Timestamp.t;
  equity : float;
  cash : float;
  position : float;
}

type result = {
  initial_cash : float;
  final_portfolio : portfolio;
  trades : trade list;
  curve : point list;
}

type strategy = portfolio -> Hf_l2.snapshot -> order list
type funding_rate = Hf_l2.snapshot -> float

let signed_size side size =
  match side with L2_execution.Buy -> size | L2_execution.Sell -> -.size

let run ~(initial_cash : float) ?(fee_bps = 0.0) ?latency_snapshots
    ?latency_ms ?funding_rate (strategy : strategy)
    (snapshots : Hf_l2.snapshot list) : result =
  if Option.is_some latency_snapshots && Option.is_some latency_ms then
    invalid_arg "latency options conflict";
  let latency = Option.value latency_snapshots ~default:0 in
  if latency < 0 then invalid_arg "latency_snapshots must be nonnegative";
  (match latency_ms with
  | Some value when value < 0L -> invalid_arg "latency_ms must be nonnegative"
  | _ -> ());
  let empty_portfolio =
    {
      timestamp = Timestamp.zero;
      cash = initial_cash;
      position = 0.0;
      equity = initial_cash;
      fees = 0.0;
      funding_paid = 0.0;
      trade_count = 0;
    }
  in
  match snapshots with
  | [] ->
      {
        initial_cash;
        final_portfolio = empty_portfolio;
        trades = [];
        curve = [];
      }
  | _ ->
      let snapshots = Array.of_list snapshots in
      let scheduled = Array.make (Array.length snapshots + latency + 1) [] in
      let timed_scheduled = ref [] in
      let portfolio = ref empty_portfolio in
      let trades = ref [] in
      let curve = ref [] in
      let execute_orders snapshot orders =
        List.iter
          (fun (order : order) ->
            let execution =
              L2_execution.execute snapshot order.side
                ?limit_price:order.limit_price order.size
            in
            List.iter
              (fun (fill : L2_execution.fill) ->
                let notional = fill.price *. fill.size in
                let fee = notional *. fee_bps /. 10_000.0 in
                let signed = signed_size order.side fill.size in
                portfolio :=
                  {
                    !portfolio with
                    cash = !portfolio.cash -. (signed *. fill.price) -. fee;
                    position = !portfolio.position +. signed;
                    fees = !portfolio.fees +. fee;
                    trade_count = !portfolio.trade_count + 1;
                  };
                trades :=
                  {
                    timestamp = snapshot.timestamp;
                    side = order.side;
                    price = fill.price;
                    size = fill.size;
                    fee;
                  }
                  :: !trades)
              execution.fills)
          orders
      in
      let mark (snapshot : Hf_l2.snapshot) =
        portfolio :=
          {
            !portfolio with
            timestamp = snapshot.timestamp;
            equity =
              !portfolio.cash +. (!portfolio.position *. snapshot.mid_price);
          }
      in
      for index = 0 to Array.length snapshots - 1 do
        let snapshot = snapshots.(index) in
        let due_orders =
          match latency_ms with
          | None -> scheduled.(index)
          | Some _ ->
              let due, pending =
                List.partition
                  (fun (due, _) -> Timestamp.compare due snapshot.timestamp <= 0)
                  !timed_scheduled
              in
              timed_scheduled := pending;
              List.concat_map snd due
        in
        execute_orders snapshot due_orders;
        let funding =
          match funding_rate with None -> 0.0 | Some rate -> rate snapshot
        in
        let funding_payment =
          !portfolio.position *. snapshot.mid_price *. funding
        in
        portfolio :=
          {
            !portfolio with
            cash = !portfolio.cash -. funding_payment;
            funding_paid = !portfolio.funding_paid +. funding_payment;
          };
        mark snapshot;
        let orders = strategy !portfolio snapshot in
        (match latency_ms with
        | Some delay when delay = 0L ->
            execute_orders snapshot orders;
            mark snapshot
        | Some delay ->
            let due = Timestamp.add_seconds snapshot.timestamp (Int64.to_float delay /. 1000.0) in
            timed_scheduled := !timed_scheduled @ [ (due, orders) ]
        | None when latency = 0 ->
            execute_orders snapshot orders;
            mark snapshot
        | None when index + latency < Array.length scheduled ->
            scheduled.(index + latency) <- scheduled.(index + latency) @ orders
        | None -> ());
        curve :=
          {
            timestamp = snapshot.timestamp;
            equity = !portfolio.equity;
            cash = !portfolio.cash;
            position = !portfolio.position;
          }
          :: !curve
      done;
      {
        initial_cash;
        final_portfolio = !portfolio;
        trades = List.rev !trades;
        curve = List.rev !curve;
      }
