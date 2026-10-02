(** Binance Futures L2 updates captured by Tardis. *)

type level = { price : string; size : string }

type message =
  | Snapshot of {
      raw_line : string;
      received_time : Timestamp.t;
      event_time : Timestamp.t;
      last_update_id : int64;
      bids : level list;
      asks : level list;
    }
  | Update of {
      raw_line : string;
      received_time : Timestamp.t;
      event_time : Timestamp.t;
      first_update_id : int64;
      final_update_id : int64;
      previous_update_id : int64;
      bids : level list;
      asks : level list;
    }

type evidence = {
  source_path : string;
  byte_count : int;
  line_count : int;
  first_received_time : Timestamp.t option;
  last_received_time : Timestamp.t option;
}

type state = {
  raw_line : string;
  event_time : Timestamp.t;
  received_time : Timestamp.t;
  last_update_id : int64;
  bids : level list;
  asks : level list;
}

type normalized_kind = Snapshot_row | Update_row

type normalized_row = {
  kind : normalized_kind;
  segment : int64;
  symbol : string;
  received_time : Timestamp.t;
  event_time : Timestamp.t;
  source_path : string;
  source_sha256 : string;
  applied : bool;
  last_update_id : int64 option;
  first_update_id : int64 option;
  final_update_id : int64 option;
  previous_update_id : int64 option;
  bids : level list;
  asks : level list;
}

let ( let* ) result f = Result.bind result f

let field name json =
  match Yojson.Safe.Util.member name json with
  | `Null -> Serror.failf "missing Binance field %s" name
  | value -> Ok value

let string_field name json =
  let* value = field name json in
  match value with
  | `String value -> Ok value
  | _ -> Serror.failf "Binance field %s is not a string" name

let int64_field name json =
  let* value = field name json in
  match value with
  | `Int value -> Ok (Int64.of_int value)
  | `Intlit value -> (
      match Int64.of_string_opt value with
      | Some value -> Ok value
      | None -> Serror.failf "invalid Binance integer field %s" name)
  | _ -> Serror.failf "Binance field %s is not an integer" name

let timestamp_ms value =
  if value < 0L then Serror.failf "invalid negative Binance timestamp %Ld" value
  else
    match Ptime.of_float_s (Int64.to_float value /. 1000.0) with
    | Some timestamp -> Ok (Timestamp.of_ptime timestamp)
    | None -> Serror.failf "invalid Binance timestamp %Ld" value

let timestamp_string value =
  match Timestamp.of_string value with
  | Ok timestamp -> Ok timestamp
  | Error message ->
      if
        String.length value >= 11
        && value.[4] = '.' && value.[7] = '.' && value.[10] = 'D'
      then
        let normalized = Bytes.of_string value in
        Bytes.set normalized 4 '-';
        Bytes.set normalized 7 '-';
        Bytes.set normalized 10 'T';
        (match Timestamp.of_string (Bytes.to_string normalized ^ "Z") with
        | Ok timestamp -> Ok timestamp
        | Error _ -> Serror.fail message)
      else Serror.fail message

let levels name json =
  let* value = field name json in
  match value with
  | `List values ->
      let parse_level = function
        | `List [ `String price; `String size ] -> (
            try
              let price_value = float_of_string price in
              let size_value = float_of_string size in
              if
                Float.is_nan price_value || Float.is_infinite price_value
                || price_value <= 0.0 || Float.is_nan size_value
                || Float.is_infinite size_value || size_value < 0.0
              then Serror.fail "invalid Binance price or size"
              else
                let* price = Binance_units.canonical_decimal price in
                let* size = Binance_units.canonical_decimal size in
                Ok { price; size }
            with Failure _ -> Serror.fail "invalid Binance price or size")
        | _ -> Serror.fail "invalid Binance level"
      in
      let rec parse acc = function
        | [] -> Ok (List.rev acc)
        | value :: rest ->
            let* level = parse_level value in
            parse (level :: acc) rest
      in
      parse [] values
  | _ -> Serror.failf "Binance field %s is not an array" name

let parse_line line =
  match String.index_opt line ' ' with
  | None -> Serror.fail "Binance line has no local timestamp"
  | Some separator -> (
      let received = String.sub line 0 separator in
      let json =
        String.sub line (separator + 1) (String.length line - separator - 1)
      in
      let* received_time = timestamp_string received in
      let* json =
        try Ok (Yojson.Safe.from_string json)
        with Yojson.Json_error message ->
          Serror.fail ("JSON error: " ^ message)
      in
      let* data = field "data" json in
      let* event_ms = int64_field "E" data in
      let* event_time = timestamp_ms event_ms in
      match Yojson.Safe.Util.member "lastUpdateId" data with
      | `Int _ | `Intlit _ ->
          let* last_update_id = int64_field "lastUpdateId" data in
          let* () =
            if last_update_id < 0L then
              Serror.fail "Binance snapshot update ID is negative"
            else Ok ()
          in
          let* bids = levels "bids" data in
          let* asks = levels "asks" data in
          Ok
            (Snapshot
               {
                 raw_line = line;
                 received_time;
                 event_time;
                 last_update_id;
                 bids;
                 asks;
               })
      | _ ->
          let* first_update_id = int64_field "U" data in
          let* final_update_id = int64_field "u" data in
          let* previous_update_id = int64_field "pu" data in
          let* () =
            if
              first_update_id < 0L
              || final_update_id < first_update_id
              || previous_update_id < 0L
            then Serror.fail "invalid Binance update ID range"
            else Ok ()
          in
          let* bids = levels "b" data in
          let* asks = levels "a" data in
          Ok
            (Update
               {
                 raw_line = line;
                 received_time;
                 event_time;
                 first_update_id;
                 final_update_id;
                 previous_update_id;
                 bids;
                 asks;
               }))

let bool_field name json =
  let* value = field name json in
  match value with
  | `Bool value -> Ok value
  | _ -> Serror.failf "Binance normalized field %s is not a boolean" name

let optional_int64_field name json =
  match Yojson.Safe.Util.member name json with
  | `Null -> Ok None
  | value ->
      let* parsed =
        match value with
        | `Int value -> Ok (Int64.of_int value)
        | `Intlit value -> (
            match Int64.of_string_opt value with
            | Some value -> Ok value
            | None -> Serror.failf "invalid Binance integer field %s" name)
        | _ -> Serror.failf "Binance field %s is not an integer" name
      in
      Ok (Some parsed)

let parse_normalized_row json =
  let* kind = string_field "kind" json in
  let* kind =
    match kind with
    | "snapshot" -> Ok Snapshot_row
    | "update" -> Ok Update_row
    | _ -> Serror.failf "invalid Binance normalized kind %s" kind
  in
  let* segment = int64_field "segment" json in
  let* symbol = string_field "symbol" json in
  let* received_time = string_field "received_time" json in
  let* received_time = timestamp_string received_time in
  let* event_time_ms = int64_field "event_time_ms" json in
  let* event_time = timestamp_ms event_time_ms in
  let* source_path = string_field "source_path" json in
  let* source_sha256 = string_field "source_sha256" json in
  let* applied = bool_field "applied" json in
  let* last_update_id = optional_int64_field "last_update_id" json in
  let* first_update_id = optional_int64_field "first_update_id" json in
  let* final_update_id = optional_int64_field "final_update_id" json in
  let* previous_update_id = optional_int64_field "previous_update_id" json in
  let* bids = levels "bids" json in
  let* asks = levels "asks" json in
  let* () =
    if segment < 0L then Serror.fail "negative Binance normalized segment"
    else if symbol = "" then Serror.fail "empty Binance normalized symbol"
    else Ok ()
  in
  let* () =
    match kind with
    | Snapshot_row -> (
        match (last_update_id, first_update_id, final_update_id, previous_update_id) with
        | Some last_update_id, None, None, None when last_update_id >= 0L -> Ok ()
        | _ -> Serror.fail "invalid Binance normalized snapshot IDs")
    | Update_row -> (
        match (last_update_id, first_update_id, final_update_id, previous_update_id) with
        | None, Some first_update_id, Some final_update_id, Some previous_update_id
          when first_update_id >= 0L && final_update_id >= first_update_id
               && previous_update_id >= 0L -> Ok ()
        | _ -> Serror.fail "invalid Binance normalized update IDs")
  in
  Ok
    {
      kind;
      segment;
      symbol;
      received_time;
      event_time;
      source_path;
      source_sha256;
      applied;
      last_update_id;
      first_update_id;
      final_update_id;
      previous_update_id;
      bids;
      asks;
    }

let validate_level_units instrument name json =
  let* value = field name json in
  match value with
  | `List values ->
      let rec loop = function
        | [] -> Ok ()
        | `List [ `String price; `String size ] :: rest ->
            let* _ = Binance_units.to_price_ticks instrument price in
            let* _ = Binance_units.to_quantity_lots instrument size in
            loop rest
        | _ -> Serror.failf "invalid Binance %s level" name
      in
      loop values
  | _ -> Serror.failf "Binance field %s is not an array" name

let parse_normalized_row_with_instrument instrument json =
  let* row = parse_normalized_row json in
  let* () = validate_level_units instrument "bids" json in
  let* () = validate_level_units instrument "asks" json in
  Ok row

let parse_normalized_lines lines =
  let rec parse acc = function
    | [] -> Ok (List.rev acc)
    | line :: rest ->
        if String.trim line = "" then parse acc rest
        else
          let* json =
            try Ok (Yojson.Safe.from_string line)
            with Yojson.Json_error message ->
              Serror.fail ("JSON error: " ^ message)
          in
          let* row = parse_normalized_row json in
          parse (row :: acc) rest
  in
  parse [] lines

let parse_normalized_lines_with_instrument instrument lines =
  let rec parse acc = function
    | [] -> Ok (List.rev acc)
    | line :: rest ->
        if String.trim line = "" then parse acc rest
        else
          let* json =
            try Ok (Yojson.Safe.from_string line)
            with Yojson.Json_error message ->
              Serror.fail ("JSON error: " ^ message)
          in
          let* row = parse_normalized_row_with_instrument instrument json in
          parse (row :: acc) rest
  in
  parse [] lines

let parse_lines lines =
  let rec parse acc = function
    | [] -> Ok (List.rev acc)
    | line :: rest ->
        if String.trim line = "" then parse acc rest
        else
          let* message = parse_line line in
          parse (message :: acc) rest
  in
  parse [] lines

let read_lines path =
  try
    let ic = open_in path in
    let rec loop acc =
      match input_line ic with
      | line -> loop (line :: acc)
      | exception End_of_file ->
          close_in ic;
          Ok (List.rev acc)
    in
    loop []
  with Sys_error message -> Serror.fail ("IO error: " ^ message)

let parse_file path =
  let* lines = read_lines path in
  parse_lines lines

let parse_normalized_file path =
  let* lines = read_lines path in
  parse_normalized_lines lines

let parse_normalized_file_with_instrument instrument path =
  let* lines = read_lines path in
  parse_normalized_lines_with_instrument instrument lines

let evidence path =
  let* messages = parse_file path in
  let byte_count =
    try
      let ic = open_in_bin path in
      let buffer = Bytes.create 8192 in
      let rec count total =
        match input ic buffer 0 (Bytes.length buffer) with
        | 0 ->
            close_in ic;
            Ok total
        | size -> count (total + size)
      in
      count 0
    with Sys_error message -> Serror.fail ("IO error: " ^ message)
  in
  let received_time = function
    | Snapshot snapshot -> snapshot.received_time
    | Update update -> update.received_time
  in
  let first_received_time =
    match messages with [] -> None | first :: _ -> Some (received_time first)
  in
  let last_received_time =
    match List.rev messages with
    | [] -> None
    | last :: _ -> Some (received_time last)
  in
  let* byte_count = byte_count in
  Ok
    {
      source_path = path;
      byte_count;
      line_count = List.length messages;
      first_received_time;
      last_received_time;
    }

let validate_levels_with_instrument instrument levels =
  let rec loop = function
    | [] -> Ok ()
    | level :: rest ->
        let* _ = Binance_units.to_price_ticks instrument level.price in
        let* _ = Binance_units.to_quantity_lots instrument level.size in
        loop rest
  in
  loop levels

let apply_level levels level =
  let same_price existing =
    Binance_units.compare_decimal existing.price level.price = 0
  in
  let rest = List.filter (fun existing -> not (same_price existing)) levels in
  if Binance_units.compare_decimal level.size "0" = 0 then rest
  else level :: rest

let apply_levels levels updates = List.fold_left apply_level levels updates

let sort_levels ~descending levels =
  List.sort
    (fun left right ->
      let comparison = Binance_units.compare_decimal left.price right.price in
      if descending then -comparison else comparison)
    levels

let replay ~instrument messages =
  let received_time = function
    | Snapshot snapshot -> snapshot.received_time
    | Update update -> update.received_time
  in
  let rec validate_received previous = function
    | [] -> Ok ()
    | message :: rest -> (
        let current = received_time message in
        match previous with
        | Some previous when Timestamp.compare current previous < 0 ->
            Serror.fail "Binance capture timestamps are not monotonic"
        | _ -> validate_received (Some current) rest)
  in
  let* () = validate_received None messages in
  let rec validate_units = function
    | [] -> Ok ()
    | Snapshot snapshot :: rest ->
        let* () = validate_levels_with_instrument instrument snapshot.bids in
        let* () = validate_levels_with_instrument instrument snapshot.asks in
        validate_units rest
    | Update update :: rest ->
        let* () = validate_levels_with_instrument instrument update.bids in
        let* () = validate_levels_with_instrument instrument update.asks in
        validate_units rest
  in
  let* () = validate_units messages in
  let apply_update ~bootstrapped (state : state) = function
    | Update update ->
        if update.final_update_id <= state.last_update_id then
          Ok (state, bootstrapped, false)
        else
          let next_id = Int64.add state.last_update_id 1L in
          let bridges_snapshot =
            update.first_update_id <= next_id
            && next_id <= update.final_update_id
          in
          let contiguous =
            if bootstrapped then
              update.previous_update_id = state.last_update_id
            else
              update.previous_update_id = state.last_update_id
              || bridges_snapshot
          in
          if not contiguous then
            Serror.failf
              "Binance update gap: expected previous update %Ld, got %Ld"
              state.last_update_id update.previous_update_id
          else
            Ok
              ( {
                  raw_line = update.raw_line;
                  event_time = update.event_time;
                  received_time = update.received_time;
                  last_update_id = update.final_update_id;
                  bids = apply_levels state.bids update.bids;
                  asks = apply_levels state.asks update.asks;
                },
                true,
                true )
    | Snapshot _ -> Serror.fail "internal Binance snapshot update error"
  in
  let rec consume_pending state bootstrapped snapshots = function
    | [] -> Ok (state, bootstrapped, snapshots)
    | (Update _ as update_message) :: rest -> (
        match apply_update ~bootstrapped state update_message with
        | Error error -> Error error
        | Ok (state, bootstrapped, applied) ->
            let snapshots = if applied then state :: snapshots else snapshots in
            consume_pending state bootstrapped snapshots rest)
    | Snapshot _ :: _ -> Serror.fail "internal Binance snapshot pending error"
  in
  let rec loop state bootstrapped snapshots pending = function
    | [] -> (
        match state with
        | None when pending <> [] ->
            Serror.fail "Binance updates ended before a snapshot"
        | _ -> Ok (List.rev snapshots))
    | Snapshot snapshot :: rest -> (
        let state =
          {
            raw_line = snapshot.raw_line;
            event_time = snapshot.event_time;
            received_time = snapshot.received_time;
            last_update_id = snapshot.last_update_id;
            bids = snapshot.bids;
            asks = snapshot.asks;
          }
        in
        let snapshots = state :: snapshots in
        match consume_pending state false snapshots (List.rev pending) with
        | Error error -> Error error
        | Ok (state, bootstrapped, snapshots) ->
            loop (Some state) bootstrapped snapshots [] rest)
    | (Update update as update_message) :: rest -> (
        match state with
        | None ->
            (* Tardis records updates before its generated snapshot. *)
            loop None false snapshots (update_message :: pending) rest
        | Some state -> (
            match apply_update ~bootstrapped state update_message with
            | Error error -> Error error
            | Ok (state, bootstrapped, applied) ->
                let snapshots =
                  if applied then state :: snapshots else snapshots
                in
                loop (Some state) bootstrapped snapshots pending rest))
  in
  loop None false [] [] messages

let replay_normalized ~instrument rows =
  let received_time row = row.received_time in
  let rec validate_metadata symbol segment previous_received = function
    | [] -> Ok ()
    | row :: rest ->
        let* () =
          match symbol with
          | Some expected when expected <> row.symbol ->
              Serror.fail "Binance normalized rows contain multiple symbols"
          | _ -> Ok ()
        in
        let* () =
          match previous_received with
          | Some previous
            when Timestamp.compare (received_time row) previous < 0 ->
              Serror.fail "Binance normalized timestamps are not monotonic"
          | _ -> Ok ()
        in
        let* () =
          match (row.kind, segment) with
          | Update_row, Some expected when expected <> row.segment ->
              Serror.fail "Binance normalized segment changed without snapshot"
          | _ -> Ok ()
        in
        validate_metadata (Some row.symbol)
          (match row.kind with Snapshot_row -> Some row.segment | Update_row -> segment)
          (Some (received_time row)) rest
  in
  let* () = validate_metadata None None None rows in
  let rec validate_units = function
    | [] -> Ok ()
    | row :: rest ->
        let* () = validate_levels_with_instrument instrument row.bids in
        let* () = validate_levels_with_instrument instrument row.asks in
        validate_units rest
  in
  let* () = validate_units rows in
  let apply_update ~bootstrapped (state : state) row =
    match
      (row.first_update_id, row.final_update_id, row.previous_update_id)
    with
    | Some first_update_id, Some final_update_id, Some previous_update_id ->
        if not row.applied || final_update_id <= state.last_update_id then
          Ok (state, bootstrapped, false)
        else
          let next_id = Int64.add state.last_update_id 1L in
          let bridges_snapshot =
            first_update_id <= next_id && next_id <= final_update_id
          in
          let contiguous =
            if bootstrapped then previous_update_id = state.last_update_id
            else previous_update_id = state.last_update_id || bridges_snapshot
          in
          if not contiguous then
            Serror.failf
              "Binance normalized update gap: expected previous update %Ld, got %Ld"
              state.last_update_id previous_update_id
          else
            Ok
              ( {
                  raw_line = row.source_path;
                  event_time = row.event_time;
                  received_time = row.received_time;
                  last_update_id = final_update_id;
                  bids = apply_levels state.bids row.bids;
                  asks = apply_levels state.asks row.asks;
                },
                true,
                true )
    | _ -> Serror.fail "invalid Binance normalized update IDs"
  in
  let rec consume_pending state bootstrapped snapshots = function
    | [] -> Ok (state, bootstrapped, snapshots)
    | row :: rest -> (
        match row.kind with
        | Snapshot_row -> Serror.fail "snapshot found in pending Binance rows"
        | Update_row -> (
            match apply_update ~bootstrapped state row with
            | Error error -> Error error
            | Ok (state, bootstrapped, applied) ->
                let snapshots = if applied then state :: snapshots else snapshots in
                consume_pending state bootstrapped snapshots rest))
  in
  let rec loop state bootstrapped snapshots pending current_segment = function
    | [] -> (
        match state with
        | None when pending <> [] ->
            Serror.fail "Binance normalized updates ended before a snapshot"
        | _ -> Ok (List.rev snapshots))
    | row :: rest -> (
        match row.kind with
        | Snapshot_row -> (
            match (row.last_update_id, row.applied) with
            | Some last_update_id, true ->
                let state =
                  {
                    raw_line = row.source_path;
                    event_time = row.event_time;
                    received_time = row.received_time;
                    last_update_id;
                    bids = row.bids;
                    asks = row.asks;
                  }
                in
                let snapshots = state :: snapshots in
                let pending = List.rev pending in
                let* (state, bootstrapped, snapshots) =
                  consume_pending state false snapshots pending
                in
                loop (Some state) bootstrapped snapshots [] (Some row.segment) rest
            | _ -> Serror.fail "invalid or unapplied Binance normalized snapshot")
        | Update_row -> (
            match state with
            | None -> loop None false snapshots (row :: pending) current_segment rest
            | Some state -> (
                match apply_update ~bootstrapped state row with
                | Error error -> Error error
                | Ok (state, bootstrapped, applied) ->
                    let snapshots = if applied then state :: snapshots else snapshots in
                    loop (Some state) bootstrapped snapshots pending current_segment rest)))
  in
  loop None false [] [] None rows

let cumulative_levels ~mid_price ~bid levels =
  let ordered = sort_levels ~descending:bid levels in
  let total = ref 0.0 in
  List.filter_map
    (fun level ->
      let price = float_of_string level.price in
      let size = float_of_string level.size in
      if size <= 0.0 then None
      else begin
        total := !total +. size;
        Some
          {
            Hf_l2.price;
            cumulative_size = !total;
            distance_bps =
              (if bid then mid_price -. price else price -. mid_price)
              /. mid_price *. 10_000.0;
          }
      end)
    ordered

let to_hf_l2 ~instrument ~symbol states : Hf_l2.snapshot list Serror.t =
  let validate_state (state : state) =
    let* () = validate_levels_with_instrument instrument state.bids in
    validate_levels_with_instrument instrument state.asks
  in
  let* () =
    let rec validate = function
      | [] -> Ok ()
      | state :: rest ->
          let* () = validate_state state in
          validate rest
    in
    validate states
  in
  let convert (state : state) =
    match (sort_levels ~descending:true state.bids, sort_levels ~descending:false state.asks) with
    | bid :: _, ask :: _ ->
        let bid_price = float_of_string bid.price in
        let ask_price = float_of_string ask.price in
        if bid_price <= 0.0 || ask_price <= 0.0 then
          Serror.fail "Binance book snapshot has no valid top of book"
        else
        let mid_price = (bid_price +. ask_price) /. 2.0 in
        Ok
          {
            Hf_l2.timestamp = state.event_time;
            symbol;
            mid_price;
            traded_volume = 0.0;
            bids = cumulative_levels ~mid_price ~bid:true state.bids;
            asks = cumulative_levels ~mid_price ~bid:false state.asks;
          }
    | _ -> Serror.fail "Binance book snapshot has no valid top of book"
  in
  let rec map acc = function
    | [] -> Ok (List.rev acc)
    | state :: rest ->
        let* snapshot = convert state in
        map (snapshot :: acc) rest
  in
  map [] states
