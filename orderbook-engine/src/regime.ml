(** Volatility regimes and per-regime attribution.

    A regime label comes from a trailing volatility feature: the mid-price
    travel in ticks over the feature window, compared against a threshold.

    The threshold is never fitted on the data it judges. [threshold_from]
    computes it from a training slice of events, and [classify_all] applies it
    everywhere, so a caller can compare the training half against the rest and
    see whether a conditioning rule survives out of sample.

    When both are available, a conditioning rule recommends trading only in the
    regimes whose net result is positive. It is a statement about the fixture
    it was measured on, not a promise about the future. *)

type label = Low_volatility | High_volatility

let label_name = function
  | Low_volatility -> "low_volatility"
  | High_volatility -> "high_volatility"

let compare_label left right = compare (label_name left) (label_name right)

(** Median of the trailing travel over the training slice. With an even count
    the lower middle value is used, which keeps the rule deterministic. *)
let threshold_from ~from ~until (travel : int64 array) =
  let from = max 0 from in
  let until = min (Array.length travel) until in
  let values = ref [] in
  for index = from to until - 1 do
    values := travel.(index) :: !values
  done;
  match List.sort Int64.compare !values with
  | [] -> 0L
  | sorted ->
      let middle = (List.length sorted - 1) / 2 in
      List.nth sorted middle

let classify_all ~threshold (travel : int64 array) =
  Array.map
    (fun value ->
      if Int64.compare value threshold <= 0 then Low_volatility
      else High_volatility)
    travel

(** Trailing mid-price travel in ticks, computed over a wall-clock window
    rather than a number of events, so trade bursts cannot dilute it. *)
let prefetch ~window_seconds (events : Exec_event.t list) =
  let window_ns = Int64.of_float (window_seconds *. 1_000_000_000.0) in
  let book = ref L2_book.empty in
  let steps = Queue.create () in
  let running = ref 0L in
  let last_mid = ref None in
  let travel = Array.make (List.length events) 0L in
  let expire cutoff =
    let continuing = ref true in
    while !continuing do
      match Queue.peek steps with
      | (at, step) when Timestamp.compare at cutoff < 0 ->
          running := Int64.sub !running step;
          ignore (Queue.pop steps)
      | _ -> continuing := false
      | exception Queue.Empty -> continuing := false
    done
  in
  let observe event index =
    match Exec_loop.mid_ticks !book with
    | None -> ()
    | Some mid ->
        let step =
          match !last_mid with
          | Some previous -> Int64.abs (Int64.sub mid previous)
          | None -> 0L
        in
        if step > 0L then begin
          Queue.push (event.Exec_event.receive_time, step) steps;
          running := Int64.add !running step
        end;
        last_mid := Some mid;
        expire (Timestamp.add_ns event.Exec_event.receive_time (Int64.neg window_ns));
        travel.(index) <- !running
  in
  List.iteri
    (fun index event ->
      (match event.Exec_event.payload with
      | Exec_event.Depth_snapshot snapshot ->
          book :=
            L2_book.apply_snapshot !book ~bids:snapshot.Exec_event.bids
              ~asks:snapshot.Exec_event.asks
      | Exec_event.Depth_update update ->
          book :=
            L2_book.apply_update !book ~bids:update.Exec_event.bids
              ~asks:update.Exec_event.asks
      | _ -> ());
      observe event index)
    events;
  travel

type attribution = {
  label : label;
  fills : int;
  units : int64;
  fees : int64;
  realized : int64;
}

let zero_attribution label =
  { label; fills = 0; units = 0L; fees = 0L; realized = 0L }

(** [attribute ~classified ~events blotter] folds a fill blotter into the
    regime in force at each fill, taken from the latest event at or before the
    fill's time. *)
let attribute ~classified ~(events : Exec_event.t list) (blotter : Exec_loop.fill_record list) =
  let event_array = Array.of_list events in
  let low = ref (zero_attribution Low_volatility) in
  let high = ref (zero_attribution High_volatility) in
  let index_at moment =
    (* Latest event whose receive time is at or before the fill. *)
    let rec search low_index high_index =
      if low_index > high_index then max 0 (min low_index (Array.length event_array - 1))
      else
        let middle = (low_index + high_index) / 2 in
        if
          Timestamp.compare event_array.(middle).Exec_event.receive_time moment
          <= 0
        then search (middle + 1) high_index
        else search low_index (middle - 1)
    in
    search 0 (Array.length event_array - 1)
  in
  List.iter
    (fun (fill : Exec_loop.fill_record) ->
      let index = index_at fill.Exec_loop.at in
      let label =
        if Array.length classified = 0 then Low_volatility
        else classified.(max 0 (min index (Array.length classified - 1)))
      in
      let entry = if label = Low_volatility then low else high in
      entry :=
        {
          !entry with
          fills = !entry.fills + 1;
          units = Int64.add !entry.units fill.Exec_loop.quantity_units;
          fees = Int64.add !entry.fees fill.Exec_loop.fee;
          realized = Int64.add !entry.realized fill.Exec_loop.realized;
        })
    blotter;
  [ !low; !high ]

let net (entry : attribution) = Int64.sub entry.realized entry.fees

(** The regimes whose net result is positive. An empty list means no regime
    paid, so conditioning cannot rescue the result. *)
let condition attribution =
  let positive = List.filter (fun entry -> Int64.compare (net entry) 0L > 0) attribution in
  if positive = [] then []
  else List.map (fun entry -> entry.label) positive
