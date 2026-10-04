type receivable = { due : Timestamp.t; amount : int64 }

type t = {
  spec : Instrument_spec.t;
  cash : int64;
  receivables : receivable list;
  position_units : int64;
  entry_ticks : int64 option;
  realized_pnl : int64;
  fees : int64;
  funding_paid : int64;
  closed : bool;
}

let ( let* ) result f = Result.bind result f
let checked_add = Exec_units.checked_add
let checked_mul = Exec_units.checked_mul

let create spec ~cash =
  let* () = Instrument_spec.validate spec in
  if cash < 0L then Serror.fail "initial cash must be nonnegative"
  else
    Ok
      {
        spec;
        cash;
        receivables = [];
        position_units = 0L;
        entry_ticks = None;
        realized_pnl = 0L;
        fees = 0L;
        funding_paid = 0L;
        closed = false;
      }

let magnitude value =
  if value = Int64.min_int then Serror.fail "position magnitude overflows"
  else Ok (Int64.abs value)

let signed side quantity =
  match side with
  | Exec_event.Buy -> quantity
  | Exec_event.Sell -> Int64.neg quantity

let position_pnl spec ~entry_ticks ~exit_ticks ~quantity_units ~direction =
  let* difference = checked_add exit_ticks (Int64.neg entry_ticks) in
  let* base =
    Exec_units.mul_div ~divisor:Exec_units.notional_divisor difference
      quantity_units
  in
  let* scaled = checked_mul base spec.Instrument_spec.multiplier in
  if direction < 0L then Ok (Int64.neg scaled) else Ok scaled

let position_after_fill state ~side ~price_ticks ~quantity_units =
  let incoming = signed side quantity_units in
  let position = state.position_units in
  let* next = checked_add position incoming in
  match state.entry_ticks with
  | None -> Ok (next, Some price_ticks, 0L)
  | Some _ when position = 0L -> Ok (next, Some price_ticks, 0L)
  | Some entry when position > 0L = (incoming > 0L) ->
      let* old_size = magnitude position in
      let* weighted_old = checked_mul old_size entry in
      let* weighted_new = checked_mul quantity_units price_ticks in
      let* total = checked_add weighted_old weighted_new in
      let* size = checked_add old_size quantity_units in
      let* average = Exec_units.div_round total size in
      Ok (next, Some average, 0L)
  | Some entry ->
      let* old_size = magnitude position in
      let closing = Int64.min old_size quantity_units in
      let direction = if position > 0L then 1L else -1L in
      let* realized =
        position_pnl state.spec ~entry_ticks:entry ~exit_ticks:price_ticks
          ~quantity_units:closing ~direction
      in
      let remaining_entry =
        if next = 0L then None
        else if next > 0L = (position > 0L) then Some entry
        else Some price_ticks
      in
      Ok (next, remaining_entry, realized)

let receivable_total state =
  List.fold_left
    (fun acc item ->
      let* total = acc in
      checked_add total item.amount)
    (Ok 0L) state.receivables

let unrealized state ~mark_ticks =
  match state.entry_ticks with
  | None -> Ok 0L
  | Some entry ->
      let* quantity_units = magnitude state.position_units in
      let direction = if state.position_units < 0L then -1L else 1L in
      position_pnl state.spec ~entry_ticks:entry ~exit_ticks:mark_ticks
        ~quantity_units ~direction

let equity state ~mark_ticks =
  if mark_ticks < 0L then Serror.fail "mark price must be nonnegative"
  else
    let* pending = receivable_total state in
    let* cash = checked_add state.cash pending in
    match state.spec.Instrument_spec.kind with
    | Instrument_spec.Equity | Instrument_spec.Option _ ->
        if state.position_units = 0L then Ok cash
        else if mark_ticks = 0L then Serror.fail "open position needs a mark"
        else
          let* value =
            Instrument_spec.notional state.spec ~price_ticks:mark_ticks
              ~quantity_units:state.position_units
          in
          checked_add cash value
    | Instrument_spec.Future _ | Instrument_spec.Perpetual _ ->
        let* change = unrealized state ~mark_ticks in
        checked_add cash change

let initial_margin_bps spec =
  match spec.Instrument_spec.kind with
  | Instrument_spec.Future terms -> Some terms.initial_margin_bps
  | Instrument_spec.Perpetual terms -> Some terms.initial_margin_bps
  | Instrument_spec.Equity | Instrument_spec.Option _ -> None

let fill_with_fee state ~at ~side ~price_ticks ~quantity_units ~fee ~settle_at =
  let* () =
    Instrument_spec.validate_fill state.spec ~at ~price_ticks ~quantity_units
  in
  if state.closed then Serror.fail "instrument lifecycle has closed"
  else if fee < 0L then
    Serror.fail "negative fees need an explicit rebate policy"
  else
    let* next_position, entry_ticks, realized =
      position_after_fill state ~side ~price_ticks ~quantity_units
    in
    let* () =
      match state.spec.Instrument_spec.kind with
      | (Instrument_spec.Equity | Instrument_spec.Option _)
        when next_position < 0L ->
          Serror.fail
            "short cash positions require a separate borrow or margin model"
      | _ -> Ok ()
    in
    let* value =
      Instrument_spec.notional state.spec ~price_ticks ~quantity_units
    in
    let* fees = checked_add state.fees fee in
    let* realized_pnl = checked_add state.realized_pnl realized in
    let* cash, receivables =
      match state.spec.Instrument_spec.kind with
      | Instrument_spec.Equity when side = Exec_event.Sell ->
          let* due =
            match settle_at with
            | Some due when Timestamp.compare due at > 0 -> Ok due
            | _ -> Serror.fail "equity sale needs a later settlement timestamp"
          in
          let* proceeds = checked_add value (Int64.neg fee) in
          Ok (state.cash, { due; amount = proceeds } :: state.receivables)
      | Instrument_spec.Equity | Instrument_spec.Option _ ->
          let flow = if side = Exec_event.Buy then Int64.neg value else value in
          let* cash = checked_add state.cash flow in
          let* cash = checked_add cash (Int64.neg fee) in
          Ok (cash, state.receivables)
      | Instrument_spec.Future _ | Instrument_spec.Perpetual _ ->
          let* cash = checked_add state.cash realized in
          let* cash = checked_add cash (Int64.neg fee) in
          Ok (cash, state.receivables)
    in
    if cash < 0L then Serror.fail "insufficient available cash"
    else
      let updated =
        {
          state with
          cash;
          receivables;
          position_units = next_position;
          entry_ticks;
          fees;
          realized_pnl;
        }
      in
      match initial_margin_bps state.spec with
      | None -> Ok updated
      | Some initial_bps ->
          let* size = magnitude next_position in
          if size = 0L then Ok updated
          else
            let* notional =
              Instrument_spec.notional state.spec ~price_ticks
                ~quantity_units:size
            in
            let* needed = Exec_units.bps ~money:notional ~bps:initial_bps in
            let* available = equity updated ~mark_ticks:price_ticks in
            if available < needed then Serror.fail "fill exceeds initial margin"
            else Ok updated

let fill state ~at ~side ~price_ticks ~quantity_units ~fee_bps ~settle_at =
  if fee_bps < 0 then Serror.fail "negative fees need an explicit rebate policy"
  else
    let* value =
      Instrument_spec.notional state.spec ~price_ticks ~quantity_units
    in
    let* fee = Exec_units.bps ~money:value ~bps:fee_bps in
    fill_with_fee state ~at ~side ~price_ticks ~quantity_units ~fee ~settle_at

let settle_receivables state ~at =
  let due, later =
    List.partition
      (fun item -> Timestamp.compare item.due at <= 0)
      state.receivables
  in
  let* cash =
    List.fold_left
      (fun acc item ->
        let* cash = acc in
        checked_add cash item.amount)
      (Ok state.cash) due
  in
  Ok { state with cash; receivables = later }

let split_equity state ~numerator ~denominator =
  match state.spec.Instrument_spec.kind with
  | Instrument_spec.Equity ->
      if numerator <= 0L || denominator <= 0L then
        Serror.fail "split ratio must be positive"
      else if state.position_units = 0L then Ok state
      else
        let* product = checked_mul state.position_units numerator in
        if Int64.rem product denominator <> 0L then
          Serror.fail
            "split creates fractional shares; cash-in-lieu event required"
        else
          let position_units = Int64.div product denominator in
          let* entry_ticks =
            match state.entry_ticks with
            | None -> Serror.fail "open equity position has no cost basis"
            | Some entry ->
                let* numerator_price = checked_mul entry denominator in
                if Int64.rem numerator_price numerator <> 0L then
                  Serror.fail "split cost basis exceeds price precision"
                else Ok (Some (Int64.div numerator_price numerator))
          in
          Ok { state with position_units; entry_ticks }
  | _ -> Serror.fail "split applies only to cash equity"

let equity_dividend state ~amount_per_share ~payable_at =
  match state.spec.Instrument_spec.kind with
  | Instrument_spec.Equity ->
      if amount_per_share < 0L then Serror.fail "dividend must be nonnegative"
      else
        let* amount =
          Exec_units.mul_div ~divisor:Exec_units.quantity_scale amount_per_share
            state.position_units
        in
        Ok
          {
            state with
            receivables = { due = payable_at; amount } :: state.receivables;
          }
  | _ -> Serror.fail "dividend applies only to cash equity"

let future_settlement state ~at ~settlement_ticks =
  match state.spec.Instrument_spec.kind with
  | Instrument_spec.Future terms ->
      if Timestamp.compare at terms.expiry > 0 then
        Serror.fail "future settlement is after expiry"
      else if settlement_ticks <= 0L then Serror.fail "invalid settlement price"
      else
        let* variation = unrealized state ~mark_ticks:settlement_ticks in
        let* cash = checked_add state.cash variation in
        let* realized_pnl = checked_add state.realized_pnl variation in
        Ok
          {
            state with
            cash;
            realized_pnl;
            entry_ticks =
              (if state.position_units = 0L then None else Some settlement_ticks);
          }
  | _ -> Serror.fail "daily settlement applies only to listed futures"

let future_expiry state ~at ~final_ticks =
  match state.spec.Instrument_spec.kind with
  | Instrument_spec.Future terms ->
      if Timestamp.compare at terms.expiry < 0 then
        Serror.fail "future has not expired"
      else
        let* settled =
          future_settlement state ~at:terms.expiry ~settlement_ticks:final_ticks
        in
        Ok
          {
            settled with
            position_units = 0L;
            entry_ticks = None;
            closed = true;
          }
  | _ -> Serror.fail "expiry applies only to listed futures"

let perpetual_funding state ~mark_ticks ~rate_units =
  match state.spec.Instrument_spec.kind with
  | Instrument_spec.Perpetual _ ->
      if state.position_units = 0L then Ok state
      else if mark_ticks <= 0L then Serror.fail "funding mark must be positive"
      else
        let* size = magnitude state.position_units in
        let* notional =
          Instrument_spec.notional state.spec ~price_ticks:mark_ticks
            ~quantity_units:size
        in
        let* amount =
          Exec_units.mul_div ~divisor:Exec_units.rate_scale notional rate_units
        in
        let amount =
          if state.position_units < 0L then Int64.neg amount else amount
        in
        let* cash = checked_add state.cash (Int64.neg amount) in
        let* funding_paid = checked_add state.funding_paid amount in
        Ok { state with cash; funding_paid }
  | _ -> Serror.fail "funding applies only to perpetuals"

let option_expiry state ~at ~underlying_ticks =
  match state.spec.Instrument_spec.kind with
  | Instrument_spec.Option terms ->
      if Timestamp.compare at terms.expiry < 0 then
        Serror.fail "option has not expired"
      else if
        underlying_ticks < 0L || underlying_ticks > Exec_units.price_ticks_max
      then Serror.fail "invalid underlying mark"
      else if terms.settlement = Instrument_spec.Physical then
        Serror.fail
          "physical exercise needs an atomic underlying delivery ledger"
      else
        let difference =
          match terms.right with
          | Instrument_spec.Call ->
              Int64.sub underlying_ticks terms.strike_ticks
          | Instrument_spec.Put -> Int64.sub terms.strike_ticks underlying_ticks
        in
        let intrinsic = Int64.max 0L difference in
        let* payoff =
          if intrinsic = 0L || state.position_units = 0L then Ok 0L
          else
            let* base =
              Exec_units.notional ~price_ticks:intrinsic
                ~quantity_units:state.position_units
            in
            checked_mul base terms.exercise_multiplier
        in
        let* cash = checked_add state.cash payoff in
        let* basis =
          match state.entry_ticks with
          | None -> Ok 0L
          | Some entry ->
              Instrument_spec.notional state.spec ~price_ticks:entry
                ~quantity_units:state.position_units
        in
        let* realized = checked_add payoff (Int64.neg basis) in
        let* realized_pnl = checked_add state.realized_pnl realized in
        Ok
          {
            state with
            cash;
            position_units = 0L;
            entry_ticks = None;
            realized_pnl;
            closed = true;
          }
  | _ -> Serror.fail "option expiry applies only to options"

let maintenance_breach state ~mark_ticks =
  let maintenance_bps =
    match state.spec.Instrument_spec.kind with
    | Instrument_spec.Future terms -> Some terms.maintenance_margin_bps
    | Instrument_spec.Perpetual terms -> Some terms.maintenance_margin_bps
    | Instrument_spec.Equity | Instrument_spec.Option _ -> None
  in
  match maintenance_bps with
  | None -> Ok false
  | Some rate ->
      let* size = magnitude state.position_units in
      if size = 0L then Ok false
      else
        let* notional =
          Instrument_spec.notional state.spec ~price_ticks:mark_ticks
            ~quantity_units:size
        in
        let* required = Exec_units.bps ~money:notional ~bps:rate in
        let* available = equity state ~mark_ticks in
        Ok (available <= required)
