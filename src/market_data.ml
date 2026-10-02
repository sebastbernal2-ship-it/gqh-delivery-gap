(** Market data: CSV parser and random market data generator. *)

open Market_types
open Side

(** CSV event format: timestamp,order_id,side,price,size,action[,valid_time]
    Example: 2026-09-01T09:30:00Z,ord001,bid,100.50,500,add
    2026-09-01T09:30:01Z,ord001,ask,100.55,200,amend *)

(** Parse a CSV file, optionally rejecting malformed data rows. *)
let rec parse_csv_internal ~(strict : bool) (path : string) :
    event list Serror.t =
  try
    let ic = open_in path in
    let csv_ic = Csv.of_channel ic in
    let events = ref [] in
    let handle_row row =
      let parsed =
        match row with
        | [ ts; oid; side_str; price_str; size_str; action_str ] ->
            parse_event_fields ts oid side_str price_str size_str action_str
              None
        | [ ts; oid; side_str; price_str; size_str; action_str; valid_str ] ->
            parse_event_fields ts oid side_str price_str size_str action_str
              (Some valid_str)
        | _ -> None
      in
      match parsed with
      | Some ev -> events := ev :: !events
      | None -> (
          match row with
          | first :: _ when String.length first > 0 && first.[0] = '#' -> ()
          | _ when strict -> raise (Failure "malformed CSV row")
          | _ -> ())
    in
    Csv.iter ~f:handle_row csv_ic;
    close_in ic;
    Ok (List.rev !events)
  with
  | Sys_error msg -> Serror.fail ("IO error: " ^ msg)
  | Failure msg -> Serror.fail ("Parse error: " ^ msg)

and parse_event_fields ts oid side_str price_str size_str action_str
    valid_str_opt : event option =
  let open Timestamp in
  let timestamp = match of_string ts with Ok t -> Some t | _ -> None in
  let side =
    match String.lowercase_ascii side_str with
    | "bid" | "b" -> Some Bid
    | "ask" | "a" | "offer" -> Some Ask
    | _ -> None
  in
  let price =
    try Some (Price.of_float (Base.Float.of_string price_str)) with _ -> None
  in
  let size =
    try Some (Size.of_int (Base.Int.of_string size_str)) with _ -> None
  in
  let action =
    match String.lowercase_ascii action_str with
    | "add" | "new" -> Some Add
    | "amend" | "modify" | "mod" -> Some Amend
    | "cancel" | "delete" | "del" -> Some Cancel
    | "execute" | "fill" | "exec" | "trade" -> Some Execute
    | action when String.starts_with ~prefix:"replace:" action ->
        Some (Replace (String.sub action 8 (String.length action - 8)))
    | action when String.starts_with ~prefix:"control:" action ->
        Some (Control (String.sub action 8 (String.length action - 8)))
    | _ -> None
  in
  let valid_time =
    match valid_str_opt with
    | Some s -> ( match of_string s with Ok t -> Some t | _ -> None)
    | None -> None
  in
  match (timestamp, side, price, size, action) with
  | Some timestamp, Some s, Some p, Some sz, Some a ->
      Some
        {
          timestamp;
          order_id = oid;
          side = s;
          price = p;
          size = sz;
          action = a;
          valid_time;
        }
  | _ -> None

(** [parse_csv path] reads events from a CSV file and skips malformed rows. *)
let parse_csv (path : string) : event list Serror.t =
  parse_csv_internal ~strict:false path

(** [parse_csv_strict path] reads events and rejects malformed rows. *)
let parse_csv_strict (path : string) : event list Serror.t =
  parse_csv_internal ~strict:true path

type feed_event = {
  venue : string;
  symbol : string;
  epoch : int;
  sequence : int;
  event_time : Timestamp.t;
  received_time : Timestamp.t option;
  event : event;
}
(** A source event carries feed identity outside the matching payload. *)

(** [parse_feed_csv path] parses a strict feed envelope. Columns are
    venue,symbol,sequence,event_time,received_time,order_id,side,
    price,size,action[,valid_time]. *)
let parse_feed_csv (path : string) : feed_event list Serror.t =
  try
    let ic = open_in path in
    let csv_ic = Csv.of_channel ic in
    let events = ref [] in
    let parse_received_time value =
      if value = "" then Some None
      else
        match Timestamp.of_string value with
        | Ok t -> Some (Some t)
        | Error _ -> None
    in
    let parse_row row =
      match row with
      | [
       venue;
       symbol;
       sequence;
       event_time;
       received_time;
       oid;
       side;
       price;
       size;
       action;
      ] ->
          ( venue,
            symbol,
            sequence,
            event_time,
            received_time,
            oid,
            side,
            price,
            size,
            action,
            None )
      | [
       venue;
       symbol;
       sequence;
       event_time;
       received_time;
       oid;
       side;
       price;
       size;
       action;
       valid_time;
      ] ->
          ( venue,
            symbol,
            sequence,
            event_time,
            received_time,
            oid,
            side,
            price,
            size,
            action,
            Some valid_time )
      | _ -> raise (Failure "malformed feed CSV row")
    in
    Csv.iter
      ~f:(fun row ->
        match row with
        | first :: _ when String.length first > 0 && first.[0] = '#' -> ()
        | _ -> (
            let ( venue,
                  symbol,
                  sequence,
                  event_time,
                  received_time,
                  oid,
                  side,
                  price,
                  size,
                  action,
                  valid_time ) =
              parse_row row
            in
            let sequence = int_of_string sequence in
            let event_time_string = event_time in
            let event_time =
              match Timestamp.of_string event_time_string with
              | Ok t -> t
              | Error _ -> raise (Failure "invalid feed event time")
            in
            let received_time =
              match parse_received_time received_time with
              | Some t -> t
              | None -> raise (Failure "invalid feed received time")
            in
            match
              parse_event_fields event_time_string oid side price size action
                valid_time
            with
            | Some event ->
                events :=
                  {
                    venue;
                    symbol;
                    epoch = 0;
                    sequence;
                    event_time;
                    received_time;
                    event;
                  }
                  :: !events
            | None -> raise (Failure "invalid feed event")))
      csv_ic;
    close_in ic;
    Ok (List.rev !events)
  with
  | Sys_error msg -> Serror.fail ("IO error: " ^ msg)
  | Failure msg -> Serror.fail ("Parse error: " ^ msg)

(** Random market data generator. *)

type gen_config = {
  symbols : string list;
  start_time : Timestamp.t;
  speed : float;  (** events per second *)
  volatility : float;  (** price volatility (std dev in pips) *)
  base_spread : float;  (** base spread in percent *)
  duration_s : float;  (** how many seconds of data to generate *)
  max_orders : int;  (** max concurrent orders in the book *)
  rng_seed : int option;
}
(** Generator configuration. *)

let default_config : gen_config =
  {
    symbols = [ "AAPL"; "MSFT"; "GOOGL" ];
    start_time = Timestamp.now ();
    speed = 10.0;
    volatility = 0.02;
    base_spread = 0.01;
    duration_s = 3600.0;
    max_orders = 100;
    rng_seed = None;
  }

(** [generate config] produces a list of market events from a random generator
    simulating realistic order flow. *)
let rec generate (config : gen_config) : event list =
  let rng =
    match config.rng_seed with
    | Some seed -> Random.State.make [| seed |]
    | None -> Random.State.make_self_init ()
  in
  let total_events = int_of_float (config.speed *. config.duration_s) in
  let events_per_symbol = total_events / List.length config.symbols in
  let all_events =
    List.concat
      (List.map
         (fun symbol ->
           generate_symbol_events rng config symbol events_per_symbol)
         config.symbols)
  in
  List.sort
    (fun (a : event) (b : event) -> Timestamp.compare a.timestamp b.timestamp)
    all_events

and generate_symbol_events (rng : Random.State.t) (config : gen_config)
    (symbol : string) (count : int) : event list =
  let mid_price = 100.0 +. Random.State.float rng 200.0 in
  let base_price = Price.of_float mid_price in
  let base_price_int = Price.to_int base_price in
  let events = ref [] in
  let active_orders : (Order_id.t * Side.side * Price.t * Size.t) list ref =
    ref []
  in
  let order_counter = ref 0 in

  for i = 0 to count - 1 do
    let t = Timestamp.add_seconds config.start_time (float i /. config.speed) in
    let movement =
      int_of_float
        (float base_price_int *. config.volatility *. Random.State.float rng 1.0)
    in
    let spread_ticks =
      max 1 (int_of_float (float base_price_int *. config.base_spread))
    in

    (* Occasionally add, sometimes cancel/execute. *)
    if
      List.length !active_orders < config.max_orders
      && Random.State.float rng 1.0 > 0.3
    then begin
      (* Add order *)
      order_counter := !order_counter + 1;
      let oid =
        Printf.sprintf "%s-%05d" (String.lowercase_ascii symbol) !order_counter
      in
      let side = if Random.State.bool rng then Bid else Ask in
      let size = Size.of_int (1 + Random.State.int rng 100) in
      let side_price =
        match side with
        | Bid -> Price.of_int (base_price_int - spread_ticks - movement)
        | Ask -> Price.of_int (base_price_int + spread_ticks + movement)
      in
      events :=
        {
          timestamp = t;
          order_id = oid;
          side;
          price = side_price;
          size;
          action = Add;
          valid_time = None;
        }
        :: !events;
      active_orders := (oid, side, side_price, size) :: !active_orders
    end
    else
      (* Cancel or execute an existing order *)
      begin match !active_orders with
      | [] -> ()
      | _ ->
          let arr = Array.of_list !active_orders in
          let idx = Random.State.int rng (Array.length arr) in
          let oid, side, oprice, osize = arr.(idx) in
          if Random.State.float rng 1.0 > 0.5 then begin
            (* Cancel *)
            events :=
              {
                timestamp = t;
                order_id = oid;
                side;
                price = oprice;
                size = osize;
                action = Cancel;
                valid_time = None;
              }
              :: !events;
            active_orders :=
              List.filter (fun (id, _, _, _) -> id <> oid) !active_orders
          end
          else begin
            (* Partial execute *)
            let exec_size =
              Size.of_int
                (1 + Random.State.int rng ((Size.to_int osize / 2) + 1))
            in
            let remaining = Size.sub osize exec_size in
            events :=
              {
                timestamp = t;
                order_id = oid;
                side;
                price = oprice;
                size = exec_size;
                action = Execute;
                valid_time = None;
              }
              :: !events;
            if remaining = Size.zero then
              active_orders :=
                List.filter (fun (id, _, _, _) -> id <> oid) !active_orders
            else
              active_orders :=
                List.map
                  (fun (id, s, p, sz) ->
                    if id = oid then (id, s, p, remaining) else (id, s, p, sz))
                  !active_orders
          end
      end
  done;

  (* Cancel remaining orders *)
  let now = Timestamp.add_seconds config.start_time config.duration_s in
  let remaining = List.rev !active_orders in
  let cleanup =
    List.mapi
      (fun i (oid, side, oprice, osize) ->
        {
          timestamp = Timestamp.add_seconds now (float i *. 0.001);
          order_id = oid;
          side;
          price = oprice;
          size = osize;
          action = Cancel;
          valid_time = None;
        })
      remaining
  in
  List.rev !events @ cleanup

(** [generate_feed config] adds symbol and stream sequence metadata to generated
    events. The legacy [generate] function remains available for callers that
    only need the matching payload. *)
let generate_feed (config : gen_config) : feed_event list =
  let symbol_of_order_id order_id =
    match String.split_on_char '-' order_id with
    | symbol :: _ -> String.uppercase_ascii symbol
    | [] -> "UNKNOWN"
  in
  generate config
  |> List.mapi (fun i event ->
      {
        venue = "SYNTHETIC";
        symbol = symbol_of_order_id event.order_id;
        epoch = 0;
        sequence = i + 1;
        event_time = event.timestamp;
        received_time = None;
        event;
      })

(** [group_by_symbol events] separates a feed into one event stream per symbol.
*)
let group_by_symbol (events : feed_event list) : (string * event list) list =
  let groups =
    List.fold_left
      (fun groups ({ symbol; event; _ } : feed_event) ->
        let rec add = function
          | [] -> [ (symbol, [ event ]) ]
          | (name, events) :: rest when name = symbol ->
              (name, event :: events) :: rest
          | group :: rest -> group :: add rest
        in
        add groups)
      [] events
  in
  List.rev_map (fun (symbol, events) -> (symbol, List.rev events)) groups

(** [validate_feed events] checks feed identity and monotonic sequence numbers.
*)
let validate_feed (events : feed_event list) : unit Serror.t =
  let rec check seen = function
    | [] -> Ok ()
    | ({ venue; symbol; epoch; sequence; _ } : feed_event) :: rest -> (
        if venue = "" || symbol = "" then
          Serror.fail "feed venue and symbol must be non-empty"
        else if sequence <= 0 then Serror.fail "feed sequence must be positive"
        else
          match List.assoc_opt (venue, symbol, epoch) seen with
          | Some previous when sequence <= previous ->
              Serror.fail
                (Printf.sprintf "feed sequence is not increasing for %s/%s"
                   venue symbol)
          | _ -> check (((venue, symbol, epoch), sequence) :: seen) rest)
  in
  check [] events

(** Parse the source time used by NYSE TAQ rows. *)
let nyse_timestamp (trading_date : string) (source_time : string) : Timestamp.t
    =
  let value =
    if String.contains source_time 'T' then source_time
    else trading_date ^ "T" ^ source_time ^ "Z"
  in
  match Timestamp.of_string value with
  | Ok timestamp -> timestamp
  | Error _ -> failwith "invalid NYSE source time"

(** [parse_nyse_taq ~trading_date path] parses the order messages from a NYSE
    National TAQ Integrated Feed CSV or gzip-compressed CSV file. Non-order
    messages are ignored. Replace messages become a cancel followed by an add
    because the matching payload has no replace action. *)
let parse_nyse_taq ~(trading_date : string) (path : string) :
    feed_event list Serror.t =
  let compressed = Filename.check_suffix path ".gz" in
  let ic =
    if compressed then
      Unix.open_process_in ("gzip -dc -- " ^ Filename.quote path)
    else open_in path
  in
  let next_sequence = ref 0 in
  let events = ref [] in
  let emit ~venue ~symbol ~event_time event =
    incr next_sequence;
    events :=
      {
        venue;
        symbol;
        epoch = 0;
        sequence = !next_sequence;
        event_time;
        received_time = None;
        event;
      }
      :: !events
  in
  let field row index = List.nth row index in
  let parse_side value =
    match String.uppercase_ascii value with
    | "B" -> Bid
    | "S" -> Ask
    | _ -> failwith "invalid NYSE side"
  in
  let parse_event row =
    let message_type = int_of_string (field row 0) in
    match message_type with
    | 100 | 106 ->
        let event_time = nyse_timestamp trading_date (field row 2) in
        let symbol = field row 3 in
        let order_id = field row 5 in
        let price = Price.of_float (float_of_string (field row 6)) in
        let size = Size.of_int (int_of_string (field row 7)) in
        let side = parse_side (field row 8) in
        emit ~venue:"NYSE_NATIONAL" ~symbol ~event_time
          {
            timestamp = event_time;
            order_id;
            side;
            price;
            size;
            action = Add;
            valid_time = None;
          }
    | 101 ->
        let event_time = nyse_timestamp trading_date (field row 2) in
        let symbol = field row 3 in
        let order_id = field row 5 in
        let price = Price.of_float (float_of_string (field row 6)) in
        let size = Size.of_int (int_of_string (field row 7)) in
        let side = parse_side (field row 9) in
        emit ~venue:"NYSE_NATIONAL" ~symbol ~event_time
          {
            timestamp = event_time;
            order_id;
            side;
            price;
            size;
            action = Amend;
            valid_time = None;
          }
    | 102 ->
        let event_time = nyse_timestamp trading_date (field row 2) in
        let symbol = field row 3 in
        let order_id = field row 5 in
        emit ~venue:"NYSE_NATIONAL" ~symbol ~event_time
          {
            timestamp = event_time;
            order_id;
            side = Bid;
            price = Price.of_int 0;
            size = Size.zero;
            action = Cancel;
            valid_time = None;
          }
    | 103 ->
        let event_time = nyse_timestamp trading_date (field row 2) in
        let symbol = field row 3 in
        let order_id = field row 5 in
        let price = Price.of_float (float_of_string (field row 7)) in
        let size = Size.of_int (int_of_string (field row 8)) in
        emit ~venue:"NYSE_NATIONAL" ~symbol ~event_time
          {
            timestamp = event_time;
            order_id;
            side = Bid;
            price;
            size;
            action = Execute;
            valid_time = None;
          }
    | 104 ->
        let event_time = nyse_timestamp trading_date (field row 2) in
        let symbol = field row 3 in
        let old_order_id = field row 5 in
        let new_order_id = field row 6 in
        let price = Price.of_float (float_of_string (field row 7)) in
        let size = Size.of_int (int_of_string (field row 8)) in
        let side = parse_side (field row 9) in
        emit ~venue:"NYSE_NATIONAL" ~symbol ~event_time
          {
            timestamp = event_time;
            order_id = old_order_id;
            side;
            price;
            size;
            action = Cancel;
            valid_time = None;
          };
        emit ~venue:"NYSE_NATIONAL" ~symbol ~event_time
          {
            timestamp = event_time;
            order_id = new_order_id;
            side;
            price;
            size;
            action = Add;
            valid_time = None;
          }
    | _ -> ()
  in
  let handle_row row =
    match row with
    | first :: _ when String.length first > 0 && first.[0] = '#' -> ()
    | _ -> (
        try parse_event row with
        | Failure message -> raise (Failure ("NYSE row: " ^ message))
        | Invalid_argument _ -> raise (Failure "NYSE row: missing field"))
  in
  try
    Csv.iter ~f:handle_row (Csv.of_channel ic);
    let close_result =
      if compressed then Unix.close_process_in ic
      else (
        close_in ic;
        Unix.WEXITED 0)
    in
    match close_result with
    | Unix.WEXITED 0 -> Ok (List.rev !events)
    | _ -> Serror.fail "gzip failed while reading NYSE data"
  with
  | Sys_error message -> Serror.fail ("IO error: " ^ message)
  | Failure message -> Serror.fail ("Parse error: " ^ message)

(** [write_csv path events] writes events to a CSV file. *)
let write_csv (path : string) (events : event list) : unit Serror.t =
  try
    let oc = open_out path in
    output_string oc "# timestamp,order_id,side,price,size,action\n";
    List.iter
      (fun (ev : event) ->
        let ts = Timestamp.to_string ev.timestamp in
        let side_str = match ev.side with Bid -> "bid" | Ask -> "ask" in
        let action_str =
          match ev.action with
          | Add -> "add"
          | Amend -> "amend"
          | Cancel -> "cancel"
          | Execute -> "execute"
          | Replace old_id -> "replace:" ^ old_id
          | Control name -> "control:" ^ name
        in
        let price_str = Price.to_string ev.price in
        let size_str = Base.Int.to_string (Size.to_int ev.size) in
        let line =
          Printf.sprintf "%s,%s,%s,%s,%s,%s\n" ts ev.order_id side_str price_str
            size_str action_str
        in
        output_string oc line)
      events;
    close_out oc;
    Ok ()
  with
  | Sys_error msg -> Serror.fail ("IO error: " ^ msg)
  | Failure msg -> Serror.fail ("Write error: " ^ msg)
