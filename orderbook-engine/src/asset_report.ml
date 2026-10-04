type t = {
  event_count : int;
  order_intent_count : int;
  fill_count : int;
  initial_equity : int64;
  final_equity : int64;
  net_pnl : int64;
  net_return_bps : int64;
  max_drawdown_bps : int64;
  fees : int64;
  realized_pnl : int64;
  funding_paid : int64;
  submitted : int;
  rejected : int;
  unfilled : int;
}

let ( let* ) result f = Result.bind result f
let json_int value = `Intlit (Int64.to_string value)

let summarize ~initial_cash ~events result =
  if initial_cash <= 0L then Serror.fail "initial equity must be positive"
  else
    let curve = result.Asset_loop.equity_curve in
    match List.rev curve with
    | [] -> Serror.fail "cannot report an empty replay"
    | final_point :: _ ->
        let rec validate previous_peak max_drawdown = function
          | [] -> Ok max_drawdown
          | point :: rest ->
              if point.Asset_loop.equity <= 0L then
                Serror.fail "equity curve contains nonpositive equity"
              else
                let peak = Int64.max previous_peak point.Asset_loop.equity in
                let drawdown = Int64.sub peak point.Asset_loop.equity in
                let* drawdown_bps =
                  Exec_units.mul_div ~divisor:peak drawdown 10_000L
                in
                validate peak (Int64.max max_drawdown drawdown_bps) rest
        in
        let* max_drawdown_bps = validate initial_cash 0L curve in
        let final_equity = final_point.Asset_loop.equity in
        let* net_pnl = Exec_units.checked_sub final_equity initial_cash in
        let* net_return_bps =
          Exec_units.mul_div ~divisor:initial_cash net_pnl 10_000L
        in
        let order_intent_count =
          List.fold_left
            (fun count event ->
              match event.Exec_event.payload with
              | Exec_event.Order_intent _ -> count + 1
              | _ -> count)
            0 events
        in
        Ok
          {
            event_count = List.length events;
            order_intent_count;
            fill_count = List.length result.Asset_loop.fills;
            initial_equity = initial_cash;
            final_equity;
            net_pnl;
            net_return_bps;
            max_drawdown_bps;
            fees = result.Asset_loop.account.Asset_account.fees;
            realized_pnl = result.Asset_loop.account.Asset_account.realized_pnl;
            funding_paid = result.Asset_loop.account.Asset_account.funding_paid;
            submitted = result.Asset_loop.submitted;
            rejected = result.Asset_loop.rejected;
            unfilled = result.Asset_loop.unfilled;
          }

let to_yojson report =
  `Assoc
    [
      ("event_count", `Int report.event_count);
      ("order_intent_count", `Int report.order_intent_count);
      ("fill_count", `Int report.fill_count);
      ("initial_equity", json_int report.initial_equity);
      ("final_equity", json_int report.final_equity);
      ("net_pnl", json_int report.net_pnl);
      ("net_return_bps", json_int report.net_return_bps);
      ("max_drawdown_bps", json_int report.max_drawdown_bps);
      ("fees", json_int report.fees);
      ("realized_pnl", json_int report.realized_pnl);
      ("funding_paid", json_int report.funding_paid);
      ("submitted", `Int report.submitted);
      ("rejected", `Int report.rejected);
      ("unfilled", `Int report.unfilled);
    ]
