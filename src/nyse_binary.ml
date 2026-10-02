(** Decoder for raw little-endian NYSE Pillar Integrated Feed messages. *)

type config = { venue : string; symbol_mappings : (int * string * int) list }

let default_config = { venue = "NYSE"; symbol_mappings = [] }
let failf fmt = Serror.failf fmt

let read_symbol_mapping path : (int * string * int) list Serror.t =
  try
    let ic = open_in path in
    let by_index = Hashtbl.create 100_000 in
    let rec loop line_number =
      match input_line ic with
      | exception End_of_file ->
          close_in ic;
          let mappings =
            Hashtbl.fold
              (fun index (symbol, scale) acc -> (index, symbol, scale) :: acc)
              by_index []
          in
          Ok
            (List.sort
               (fun (left, _, _) (right, _, _) -> compare left right)
               mappings)
      | line -> (
          let line = String.trim line in
          if line = "" then loop (line_number + 1)
          else
            let fields = String.split_on_char '|' line in
            if List.length fields < 8 then
              failf "invalid NYSE symbol mapping line %d" line_number
            else
              let symbol = List.nth fields 0 in
              let symbol_index = List.nth fields 2 in
              let price_scale = List.nth fields 7 in
              match
                (int_of_string_opt symbol_index, int_of_string_opt price_scale)
              with
              | Some index, Some scale
                when symbol <> "" && index >= 0 && scale >= 0 -> (
                  match Hashtbl.find_opt by_index index with
                  | Some (old_symbol, old_scale)
                    when old_symbol <> symbol || old_scale <> scale ->
                      failf "conflicting NYSE symbol mapping for index %d" index
                  | _ ->
                      Hashtbl.replace by_index index (symbol, scale);
                      loop (line_number + 1))
              | _ -> failf "invalid NYSE symbol mapping line %d" line_number)
    in
    loop 1
  with
  | Sys_error message -> Serror.fail ("IO error: " ^ message)
  | End_of_file -> Serror.fail "truncated NYSE symbol mapping file"

type symbol_info = { name : string; price_scale : int }

type decoder = {
  bytes : bytes;
  symbols : (int, symbol_info) Hashtbl.t;
  symbol_sequences : (int, int64) Hashtbl.t;
  symbol_epochs : (int, int) Hashtbl.t;
  mutable epoch : int;
  trading_date : string;
  mutable source_seconds : int64 option;
}

let ( let* ) result f = Result.bind result f
let byte bytes offset = Char.code (Bytes.get bytes offset)

let check decoder offset width =
  if offset < 0 || width < 0 || offset > Bytes.length decoder.bytes - width then
    failf "truncated NYSE binary message at offset %d" offset
  else Ok ()

let u16 decoder offset =
  let* () = check decoder offset 2 in
  Ok
    (Int64.logor
       (Int64.of_int (byte decoder.bytes offset))
       (Int64.shift_left (Int64.of_int (byte decoder.bytes (offset + 1))) 8))

let u32 decoder offset =
  let* () = check decoder offset 4 in
  let value = ref 0L in
  for index = 0 to 3 do
    value :=
      Int64.logor !value
        (Int64.shift_left
           (Int64.of_int (byte decoder.bytes (offset + index)))
           (8 * index))
  done;
  Ok !value

let u64 decoder offset =
  let* () = check decoder offset 8 in
  let value = ref 0L in
  for index = 0 to 7 do
    value :=
      Int64.logor !value
        (Int64.shift_left
           (Int64.of_int (byte decoder.bytes (offset + index)))
           (8 * index))
  done;
  Ok !value

let signed_i32 decoder offset =
  let* value = u32 decoder offset in
  if value > 0x7fffffffL then Ok (Int64.sub value 0x100000000L) else Ok value

let ascii decoder offset length =
  let* () = check decoder offset length in
  let value = Bytes.sub_string decoder.bytes offset length in
  let length =
    match String.index_opt value '\000' with
    | Some index -> index
    | None -> String.length value
  in
  Ok (String.trim (String.sub value 0 length))

let expect_size actual expected msg_type =
  if actual = expected then Ok ()
  else
    failf "NYSE message type %d has size %d, expected %d" msg_type actual
      expected

let symbol decoder index =
  match Hashtbl.find_opt decoder.symbols index with
  | Some info -> Ok info
  | None -> failf "NYSE symbol index %d is not mapped" index

let validate_symbol_sequence decoder symbol_index sequence =
  match Hashtbl.find_opt decoder.symbol_sequences symbol_index with
  | Some previous when sequence <> Int64.add previous 1L ->
      failf "NYSE symbol %d sequence gap: expected %Ld, got %Ld" symbol_index
        (Int64.add previous 1L) sequence
  | _ ->
      Hashtbl.replace decoder.symbol_sequences symbol_index sequence;
      Ok ()

let scaled_price raw scale =
  Price.of_float (Int64.to_float raw /. (10. ** float_of_int scale))

let timestamp_from_epoch seconds nanoseconds =
  match
    Ptime.of_float_s
      (Int64.to_float seconds +. (Int64.to_float nanoseconds /. 1e9))
  with
  | Some time -> Ok (Timestamp.of_ptime time)
  | None -> Serror.fail "invalid NYSE source timestamp"

let date_of_epoch_seconds seconds =
  match Ptime.of_float_s (Int64.to_float seconds) with
  | None -> None
  | Some time ->
      let year, month, day = Ptime.to_date time in
      Some (Printf.sprintf "%04d-%02d-%02d" year month day)

let validate_date decoder seconds =
  match date_of_epoch_seconds seconds with
  | Some date when date = decoder.trading_date -> Ok ()
  | Some date ->
      failf "NYSE source date %s does not match trading date %s" date
        decoder.trading_date
  | None -> failf "invalid NYSE source date"

let timestamp_for decoder seconds nanoseconds =
  let* () = validate_date decoder seconds in
  timestamp_from_epoch seconds nanoseconds

let timestamp decoder nanoseconds =
  match decoder.source_seconds with
  | None -> failf "NYSE message has no preceding time reference"
  | Some seconds -> timestamp_for decoder seconds nanoseconds

let side_of_byte decoder offset =
  let* () = check decoder offset 1 in
  match Bytes.get decoder.bytes offset with
  | 'B' -> Ok Side.Bid
  | 'S' -> Ok Side.Ask
  | side -> failf "invalid NYSE side %C" side

let symbol_epoch decoder symbol_index =
  match Hashtbl.find_opt decoder.symbol_epochs symbol_index with
  | Some epoch -> epoch
  | None -> decoder.epoch

let event decoder ~venue ~symbol_index ~symbol_info ~sequence ~timestamp
    ~order_id ~side ~price ~size ~action =
  {
    Market_data.venue;
    symbol = symbol_info.name;
    epoch = symbol_epoch decoder symbol_index;
    sequence;
    event_time = timestamp;
    received_time = None;
    event =
      {
        Market_types.timestamp;
        order_id;
        side;
        price;
        size;
        action;
        valid_time = None;
      };
  }

let control_event ?(validate = true) decoder ~venue ~symbol_index ~sequence
    ~timestamp ~kind =
  let* () =
    if validate then validate_symbol_sequence decoder symbol_index sequence
    else Ok ()
  in
  let* symbol_info = symbol decoder symbol_index in
  Ok
    [
      event decoder ~venue ~symbol_index ~symbol_info
        ~sequence:(Int64.to_int sequence) ~timestamp
        ~order_id:(Printf.sprintf "control:%d:%Ld" symbol_index sequence)
        ~side:Side.Bid ~price:(Price.of_int 0) ~size:Size.zero
        ~action:(Side.Control kind);
    ]

let control_from_fields decoder ~venue ~source_seconds ~source_time_ns
    ~symbol_index ~sequence ~kind =
  let* source_seconds = source_seconds in
  let* source_time_ns = source_time_ns in
  let* symbol_index = symbol_index in
  let* sequence = sequence in
  let* timestamp = timestamp_for decoder source_seconds source_time_ns in
  control_event decoder ~venue
    ~symbol_index:(Int64.to_int symbol_index)
    ~sequence ~timestamp ~kind

let decode_order decoder ~venue ~offset ~message_type =
  let* source_time_ns = u32 decoder (offset + 4) in
  let* symbol_index = u32 decoder (offset + 8) in
  let* sequence = u32 decoder (offset + 12) in
  let* () =
    validate_symbol_sequence decoder (Int64.to_int symbol_index) sequence
  in
  let* order_id = u64 decoder (offset + 16) in
  let* timestamp = timestamp decoder source_time_ns in
  let* symbol_info = symbol decoder (Int64.to_int symbol_index) in
  let sequence = Int64.to_int sequence in
  let order_id = Int64.to_string order_id in
  match message_type with
  | 100 ->
      let* raw_price = signed_i32 decoder (offset + 24) in
      let* volume = u32 decoder (offset + 28) in
      let* side = side_of_byte decoder (offset + 32) in
      Ok
        [
          event decoder ~venue
            ~symbol_index:(Int64.to_int symbol_index)
            ~symbol_info ~sequence ~timestamp ~order_id ~side
            ~price:(scaled_price raw_price symbol_info.price_scale)
            ~size:(Size.of_int (Int64.to_int volume))
            ~action:Side.Add;
        ]
  | 101 ->
      let* raw_price = signed_i32 decoder (offset + 24) in
      let* volume = u32 decoder (offset + 28) in
      let* side =
        let* value = check decoder (offset + 33) 1 in
        match value with
        | () ->
            if byte decoder.bytes (offset + 33) = 0 then Ok Side.Bid
            else side_of_byte decoder (offset + 33)
      in
      Ok
        [
          event decoder ~venue
            ~symbol_index:(Int64.to_int symbol_index)
            ~symbol_info ~sequence ~timestamp ~order_id ~side
            ~price:(scaled_price raw_price symbol_info.price_scale)
            ~size:(Size.of_int (Int64.to_int volume))
            ~action:Side.Amend;
        ]
  | 102 ->
      Ok
        [
          event decoder ~venue
            ~symbol_index:(Int64.to_int symbol_index)
            ~symbol_info ~sequence ~timestamp ~order_id ~side:Side.Bid
            ~price:(Price.of_int 0) ~size:Size.zero ~action:Side.Cancel;
        ]
  | 103 ->
      let* raw_price = signed_i32 decoder (offset + 28) in
      let* volume = u32 decoder (offset + 32) in
      Ok
        [
          event decoder ~venue
            ~symbol_index:(Int64.to_int symbol_index)
            ~symbol_info ~sequence ~timestamp ~order_id ~side:Side.Bid
            ~price:(scaled_price raw_price symbol_info.price_scale)
            ~size:(Size.of_int (Int64.to_int volume))
            ~action:Side.Execute;
        ]
  | 104 ->
      let* new_order_id = u64 decoder (offset + 24) in
      let* raw_price = signed_i32 decoder (offset + 32) in
      let* volume = u32 decoder (offset + 36) in
      Ok
        [
          event decoder ~venue
            ~symbol_index:(Int64.to_int symbol_index)
            ~symbol_info ~sequence ~timestamp
            ~order_id:(Int64.to_string new_order_id)
            ~side:Side.Bid
            ~price:(scaled_price raw_price symbol_info.price_scale)
            ~size:(Size.of_int (Int64.to_int volume))
            ~action:(Side.Replace order_id);
        ]
  | _ -> failf "unsupported NYSE order message type %d" message_type

let decode_refresh decoder ~venue offset =
  let* source_seconds = u32 decoder (offset + 4) in
  let* source_time_ns = u32 decoder (offset + 8) in
  let* symbol_index = u32 decoder (offset + 12) in
  let* sequence = u32 decoder (offset + 16) in
  let* () =
    validate_symbol_sequence decoder (Int64.to_int symbol_index) sequence
  in
  let* order_id = u64 decoder (offset + 20) in
  let* raw_price = signed_i32 decoder (offset + 28) in
  let* volume = u32 decoder (offset + 32) in
  let* side = side_of_byte decoder (offset + 36) in
  let* timestamp = timestamp_for decoder source_seconds source_time_ns in
  let* symbol_info = symbol decoder (Int64.to_int symbol_index) in
  Ok
    [
      event decoder ~venue
        ~symbol_index:(Int64.to_int symbol_index)
        ~symbol_info ~sequence:(Int64.to_int sequence) ~timestamp
        ~order_id:(Int64.to_string order_id) ~side
        ~price:(scaled_price raw_price symbol_info.price_scale)
        ~size:(Size.of_int (Int64.to_int volume))
        ~action:Side.Add;
    ]

let decode_message decoder ~venue offset size message_type =
  match message_type with
  | 1 ->
      let* () =
        if size = 14 || size = 16 then Ok ()
        else expect_size size 16 message_type
      in
      let* seconds = u32 decoder (offset + 4) in
      let* () = validate_date decoder seconds in
      decoder.source_seconds <- Some seconds;
      decoder.epoch <- decoder.epoch + 1;
      Hashtbl.clear decoder.symbol_epochs;
      Hashtbl.clear decoder.symbol_sequences;
      Ok []
  | 2 ->
      let* seconds = u32 decoder (offset + 12) in
      let* () = validate_date decoder seconds in
      decoder.source_seconds <- Some seconds;
      Ok []
  | 3 ->
      let* () = expect_size size 44 message_type in
      let* index = u32 decoder (offset + 4) in
      let* name = ascii decoder (offset + 8) 11 in
      let* () = check decoder (offset + 24) 1 in
      Hashtbl.replace decoder.symbols (Int64.to_int index)
        { name; price_scale = byte decoder.bytes (offset + 24) };
      Ok []
  | 32 ->
      let* source_seconds = u32 decoder (offset + 4) in
      let* source_time_ns = u32 decoder (offset + 8) in
      let* symbol_index = u32 decoder (offset + 12) in
      let* next_sequence = u32 decoder (offset + 16) in
      let* timestamp = timestamp_for decoder source_seconds source_time_ns in
      let symbol_index = Int64.to_int symbol_index in
      let next_epoch = symbol_epoch decoder symbol_index + 1 in
      let clear_sequence = Int64.max 0L (Int64.pred next_sequence) in
      Hashtbl.replace decoder.symbol_epochs symbol_index next_epoch;
      Hashtbl.replace decoder.symbol_sequences symbol_index clear_sequence;
      control_event ~validate:false decoder ~venue ~symbol_index
        ~sequence:clear_sequence ~timestamp ~kind:"symbol_clear"
  | 34 | 105 ->
      control_from_fields decoder ~venue
        ~source_seconds:(u32 decoder (offset + 4))
        ~source_time_ns:(u32 decoder (offset + 8))
        ~symbol_index:(u32 decoder (offset + 12))
        ~sequence:(u32 decoder (offset + 16))
        ~kind:(if message_type = 34 then "security_status" else "imbalance")
  | 35 -> Ok []
  | 223 ->
      let* () = expect_size size 36 message_type in
      Ok []
  | 100 | 101 | 102 | 103 | 104 ->
      let expected =
        match message_type with
        | 100 -> 39
        | 101 -> 35
        | 102 -> 25
        | 103 -> if size = 38 || size = 42 then size else 42
        | _ -> 42
      in
      let* () = expect_size size expected message_type in
      decode_order decoder ~venue ~offset ~message_type
  | 106 ->
      let* () = expect_size size 43 message_type in
      decode_refresh decoder ~venue offset
  | 140 ->
      let* () = expect_size size 34 message_type in
      let* source_time_ns = u32 decoder (offset + 4) in
      let* symbol_index = u32 decoder (offset + 8) in
      let* sequence = u32 decoder (offset + 12) in
      let* timestamp = timestamp decoder source_time_ns in
      control_event decoder ~venue
        ~symbol_index:(Int64.to_int symbol_index)
        ~sequence ~timestamp ~kind:"quote"
  | 220 ->
      let* () = expect_size size 36 message_type in
      control_from_fields decoder ~venue
        ~source_seconds:(u32 decoder (offset + 4))
        ~source_time_ns:(u32 decoder (offset + 8))
        ~symbol_index:(u32 decoder (offset + 12))
        ~sequence:(u32 decoder (offset + 16))
        ~kind:"trade"
  | 110 | 111 ->
      let* source_time_ns = u32 decoder (offset + 4) in
      let* symbol_index = u32 decoder (offset + 8) in
      let* sequence = u32 decoder (offset + 12) in
      let* timestamp = timestamp decoder source_time_ns in
      control_event decoder ~venue
        ~symbol_index:(Int64.to_int symbol_index)
        ~sequence ~timestamp
        ~kind:
          (if message_type = 110 then "non_displayed_trade" else "cross_trade")
  | 112 | 113 | 114 ->
      let minimum_size =
        if message_type = 114 then 17 else if message_type = 113 then 24 else 20
      in
      let* () = check decoder offset minimum_size in
      let* source_time_ns = u32 decoder (offset + 4) in
      let* symbol_index = u32 decoder (offset + 8) in
      let* sequence = u32 decoder (offset + 12) in
      let* timestamp = timestamp decoder source_time_ns in
      let* kind =
        match message_type with
        | 112 ->
            let* trade_id = u32 decoder (offset + 16) in
            Ok (Printf.sprintf "trade_cancel:%Ld" trade_id)
        | 113 ->
            let* cross_id = u32 decoder (offset + 16) in
            let* volume = u32 decoder (offset + 20) in
            Ok (Printf.sprintf "cross_correction:%Ld:%Ld" cross_id volume)
        | 114 ->
            let* indicator = check decoder (offset + 16) 1 in
            let indicator = byte decoder.bytes (offset + 16) in
            Ok (Printf.sprintf "retail_price_improvement:%d" indicator)
        | _ -> failf "invalid NYSE control message type %d" message_type
      in
      control_event decoder ~venue
        ~symbol_index:(Int64.to_int symbol_index)
        ~sequence ~timestamp ~kind
  | _ -> failf "unsupported NYSE message type %d" message_type

let parse_bytes ~trading_date (config : config) (bytes : bytes) :
    Market_data.feed_event list Serror.t =
  let length = Bytes.length bytes in
  let decoder =
    {
      bytes;
      symbols = Hashtbl.create 128;
      symbol_sequences = Hashtbl.create 128;
      symbol_epochs = Hashtbl.create 128;
      epoch = 0;
      trading_date;
      source_seconds = None;
    }
  in
  List.iter
    (fun (index, name, price_scale) ->
      Hashtbl.replace decoder.symbols index { name; price_scale })
    config.symbol_mappings;
  let decode_one offset stop acc =
    if offset > stop - 4 then
      failf "truncated NYSE message header at offset %d" offset
    else
      let* size64 = u16 decoder offset in
      let* type64 = u16 decoder (offset + 2) in
      let size = Int64.to_int size64 in
      let message_type = Int64.to_int type64 in
      if size < 4 || offset > stop - size then
        failf "invalid NYSE message size %d at offset %d" size offset
      else
        let* events =
          decode_message decoder ~venue:config.venue offset size message_type
        in
        Ok (offset + size, List.rev_append events acc)
  in
  let rec decode_messages offset stop remaining acc =
    if remaining = 0 then
      if offset = stop then Ok (offset, acc)
      else failf "NYSE packet has trailing bytes"
    else
      let* next, acc = decode_one offset stop acc in
      decode_messages next stop (remaining - 1) acc
  in
  let packet_mode = ref false in
  let last_channel_sequence = ref None in
  let known_delivery_flag = function
    | 1 | 10 | 11 | 12 | 13 | 15 | 17 | 18 | 19 | 20 | 21 -> true
    | _ -> false
  in
  let is_packet offset packet_size =
    packet_size >= 16
    && offset <= length - packet_size
    &&
    let delivery_flag = byte decoder.bytes (offset + 2) in
    let message_count = byte decoder.bytes (offset + 3) in
    known_delivery_flag delivery_flag
    &&
    if !packet_mode then true
    else
      message_count > 0
      && (delivery_flag = 10 || delivery_flag = 11 || delivery_flag = 12)
  in
  let validate_packet_sequence ~offset ~delivery_flag ~message_count =
    if message_count = 0 then Ok ()
    else
      let* sequence = u32 decoder (offset + 4) in
      if delivery_flag = 12 then (
        last_channel_sequence :=
          Some (Int64.add sequence (Int64.of_int (message_count - 1)));
        Ok ())
      else if delivery_flag = 10 || delivery_flag = 11 then (
        match !last_channel_sequence with
        | Some previous when sequence <> Int64.add previous 1L ->
            failf "NYSE packet sequence gap: expected %Ld, got %Ld"
              (Int64.add previous 1L) sequence
        | _ ->
            last_channel_sequence :=
              Some (Int64.add sequence (Int64.of_int (message_count - 1)));
            Ok ())
      else Ok ()
  in
  let rec loop offset acc =
    if offset = length then Ok (List.rev acc)
    else if offset > length - 4 then
      failf "truncated NYSE message header at offset %d" offset
    else
      let* declared_size = u16 decoder offset in
      let declared_size = Int64.to_int declared_size in
      if is_packet offset declared_size then (
        let delivery_flag = byte decoder.bytes (offset + 2) in
        let message_count = byte decoder.bytes (offset + 3) in
        packet_mode := true;
        let* () =
          validate_packet_sequence ~offset ~delivery_flag ~message_count
        in
        let* _, acc =
          decode_messages (offset + 16) (offset + declared_size) message_count
            acc
        in
        loop (offset + declared_size) acc)
      else
        let* next, acc = decode_one offset length acc in
        loop next acc
  in
  loop 0 []

let parse_payloads ~trading_date config payloads =
  let length =
    List.fold_left
      (fun total payload -> total + Bytes.length payload)
      0 payloads
  in
  let bytes = Bytes.create length in
  let offset = ref 0 in
  List.iter
    (fun payload ->
      Bytes.blit payload 0 bytes !offset (Bytes.length payload);
      offset := !offset + Bytes.length payload)
    payloads;
  parse_bytes ~trading_date config bytes

let parse_file ~trading_date (config : config) path :
    Market_data.feed_event list Serror.t =
  try
    let ic = open_in_bin path in
    let length = in_channel_length ic in
    let bytes = Bytes.create length in
    really_input ic bytes 0 length;
    close_in ic;
    parse_bytes ~trading_date config bytes
  with
  | Sys_error message -> Serror.fail ("IO error: " ^ message)
  | End_of_file -> Serror.fail "truncated NYSE binary file"
