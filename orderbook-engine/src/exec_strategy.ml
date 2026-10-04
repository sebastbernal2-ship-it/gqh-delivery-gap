(** Prefetched features and a strategy interface for the execution loop.

    The rule from the plan holds here: a strategy never queries anything during
    replay. Every feature is computed in one pre-pass over the fixture, in
    exact integer units, and looked up by event index at decision time.

    Features cover a trailing window of events ending at the current one:

    - trade count and volume, split by aggressor side, with the buy share in
      basis points, rounded half away from zero;
    - the mid-price range and travel in ticks over the window, which are
      volatility proxies (travel sums absolute moves, so it also captures the
      path the price took);
    - book imbalance in basis points, positive when bids dominate. *)

type features = {
  trade_count : int;
  trade_units : int64;
  buy_units : int64;
  sell_units : int64;
  buy_ratio_bps : int;
  mid_range_ticks : int64;
  mid_travel_ticks : int64;
  book_imbalance_bps : int;
}

let empty_features =
  {
    trade_count = 0;
    trade_units = 0L;
    buy_units = 0L;
    sell_units = 0L;
    buy_ratio_bps = 5_000;
    mid_range_ticks = 0L;
    mid_travel_ticks = 0L;
    book_imbalance_bps = 0;
  }

type quote_phase = Idle | Pending | Live
(** A quote lifecycle: idle, submitted but not yet live, or resting live. *)

let checked_or_invalid label = function
  | Ok value -> value
  | Error _ -> invalid_arg (label ^ " overflow")

let add label left right =
  checked_or_invalid label (Exec_units.checked_add left right)

let sub label left right =
  checked_or_invalid label (Exec_units.checked_sub left right)

let imbalance_bps bids asks =
  let total = add "book imbalance total" bids asks in
  if total <= 0L then 0
  else
    let difference = sub "book imbalance difference" bids asks in
    let numerator = checked_or_invalid "book imbalance scaling"
        (Exec_units.checked_mul difference 10_000L) in
    let scaled = Int64.div numerator total in
    Int64.to_int scaled

let prefetch ~window (events : Exec_event.t list) =
  if window < 1 then invalid_arg "window must be positive";
  let book = ref L2_book.empty in
  let trades = Queue.create () in
  let trade_count = ref 0 in
  let trade_units = ref 0L in
  let buy_units = ref 0L in
  let sell_units = ref 0L in
  let mids = Queue.create () in
  let mid_min = ref None in
  let mid_max = ref None in
  let features = Array.make (List.length events) empty_features in
  let drop_oldest () =
    if Queue.length trades >= window then begin
      match Queue.pop trades with
      | (quantity, buyer_is_maker) ->
          trade_count := !trade_count - 1;
          trade_units := sub "rolling trade volume" !trade_units quantity;
          if buyer_is_maker then sell_units := sub "rolling sell volume" !sell_units quantity
          else buy_units := sub "rolling buy volume" !buy_units quantity
      | exception Queue.Empty -> ()
    end;
    if Queue.length mids >= window then begin
      ignore (Queue.pop mids : int64)
    end
  in
  let recompute_mid_travel () =
    let previous = ref None in
    Queue.fold
      (fun total value ->
        let step =
          match !previous with
          | None -> 0L
          | Some last ->
              let difference = sub "mid-price movement" value last in
              if difference = Int64.min_int then invalid_arg "mid-price movement overflow"
              else Int64.abs difference
        in
        previous := Some value;
        add "mid-price travel" total step)
      0L mids
  in
  let recompute_mid_range () =
    let minimum = Queue.fold (fun acc value -> match acc with None -> Some value | Some current -> Some (if value < current then value else current)) None mids in
    let maximum = Queue.fold (fun acc value -> match acc with None -> Some value | Some current -> Some (if value > current then value else current)) None mids in
    match (minimum, maximum) with
    | Some minimum, Some maximum -> sub "mid-price range" maximum minimum
    | _ -> 0L
  in
  List.iteri
    (fun index event ->
      (match event.Exec_event.payload with
      | Exec_event.Trade trade ->
          Queue.push (trade.Exec_event.quantity_units, trade.Exec_event.buyer_is_maker) trades;
          incr trade_count;
          trade_units := add "rolling trade volume" !trade_units trade.Exec_event.quantity_units;
          if trade.Exec_event.buyer_is_maker then
            sell_units := add "rolling sell volume" !sell_units trade.Exec_event.quantity_units
          else buy_units := add "rolling buy volume" !buy_units trade.Exec_event.quantity_units
      | _ -> ());
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
      (match Exec_loop.mid_ticks !book with
      | Some mid -> Queue.push mid mids
      | None -> ());
      ignore !mid_min;
      ignore !mid_max;
      let buy_ratio_bps =
        if !trade_units <= 0L then 5_000
        else
          match
            Result.bind (Exec_units.checked_mul !buy_units 10_000L)
              (fun numerator -> Exec_units.div_round numerator !trade_units)
          with
          | Ok value -> Int64.to_int value
          | Error _ -> 5_000
      in
      features.(index) <-
        {
          trade_count = !trade_count;
          trade_units = !trade_units;
          buy_units = !buy_units;
          sell_units = !sell_units;
          buy_ratio_bps;
          mid_range_ticks = recompute_mid_range ();
          mid_travel_ticks = recompute_mid_travel ();
          book_imbalance_bps =
            imbalance_bps
              (L2_book.total_quantity !book L2_book.Bid)
              (L2_book.total_quantity !book L2_book.Ask);
        };
      drop_oldest ())
    events;
  features

let make ~features (decide : Exec_loop.context -> features -> Exec_loop.action list) =
  fun context ->
    let index = context.Exec_loop.index in
    let features =
      if index >= 0 && index < Array.length features then features.(index)
      else empty_features
    in
    decide context features

(** A one-sided quote driven by prefetched features: keep a resting bid at the
    touch while buy pressure holds, and cancel it when sell pressure dominates.
    The strategy only reads the feature set, never the raw streams.

    It tracks a phase so a quote that never becomes live, for example one the
    venue drops, cannot deadlock the strategy into silence: idle submits,
    pending waits for the order to appear, live cancels when pressure turns. *)
let skewed_quote ~features ~size_units ~imbalance_floor_bps =
  let phase = ref Idle in
  make ~features (fun context feature ->
      let bids = L2_book.best_bid context.Exec_loop.book in
      let live =
        List.exists
          (fun (order : Exec_account.order) ->
            order.Exec_account.remaining_units > 0L)
          context.Exec_loop.orders
      in
      (match !phase with
      | Pending when live -> phase := Live
      | Live when not live -> phase := Idle
      | _ -> ());
      if feature.buy_ratio_bps < imbalance_floor_bps then
        match !phase with
        | Live ->
            phase := Idle;
            [ Exec_loop.Cancel "quote-1" ]
        | _ -> []
      else
        match (bids, !phase) with
        | Some price_ticks, Idle ->
            phase := Pending;
            [
              Exec_loop.Submit
                {
                  Exec_account.id = "quote-1";
                  side = Exec_event.Buy;
                  price_ticks = Some price_ticks;
                  quantity_units = size_units;
                  remaining_units = size_units;
                  tif = Exec_event.Gtc;
                  reduce_only = false;
                  post_only = true;
                  status = Exec_account.New;
                };
            ]
        | _ -> [])
