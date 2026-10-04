(** Strict, deterministic replay of interleaved venue and symbol feeds. *)

type stream = {
  book : Order_book.t;
  mutable last_sequence : int option;
  mutable last_event_time : Timestamp.t option;
  mutable last_received_time : Timestamp.t option;
}

type stream_key = string * string * int

type t = { streams : (stream_key, stream) Hashtbl.t }

type applied = {
  feed_event : Market_data.feed_event;
  snapshot : Market_types.book_snapshot;
  fills : Market_types.fill list;
}

let create () = { streams = Hashtbl.create 16 }

let key (event : Market_data.feed_event) =
  (event.venue, event.symbol, event.epoch)

let valid_identity (event : Market_data.feed_event) =
  String.length event.venue > 0 && String.length event.symbol > 0

let validate_ordering stream (event : Market_data.feed_event) =
  let sequence_check =
    match stream.last_sequence with
    | None -> Ok ()
    | Some previous when event.sequence = previous + 1 -> Ok ()
    | Some previous ->
        Serror.failf "sequence gap for %s/%s: expected %d, got %d" event.venue
          event.symbol (previous + 1) event.sequence
  in
  let event_time_check =
    match stream.last_event_time with
    | None -> Ok ()
    | Some previous when Timestamp.compare event.event_time previous >= 0 ->
        Ok ()
    | Some _ ->
        Serror.failf "event time moved backwards for %s/%s" event.venue
          event.symbol
  in
  let received_time_check =
    match (stream.last_received_time, event.received_time) with
    | _, None -> Ok ()
    | None, Some _ -> Ok ()
    | Some previous, Some current when Timestamp.compare current previous >= 0
      ->
        Ok ()
    | Some _, Some _ ->
        Serror.failf "receive time moved backwards for %s/%s" event.venue
          event.symbol
  in
  match sequence_check with
  | Error _ as error -> error
  | Ok () -> (
      match event_time_check with
      | Error _ as error -> error
      | Ok () -> received_time_check)

let apply (replay : t) (event : Market_data.feed_event) : applied Serror.t =
  if not (valid_identity event) then Serror.fail "venue and symbol are required"
  else if event.epoch < 0 then Serror.fail "epoch must be nonnegative"
  else if event.sequence < 0 then Serror.fail "sequence must be nonnegative"
  else
    let stream, is_new =
      match Hashtbl.find_opt replay.streams (key event) with
      | Some stream -> (stream, false)
      | None ->
          let stream =
            {
              book = Order_book.create ();
              last_sequence = None;
              last_event_time = None;
              last_received_time = None;
            }
          in
          Hashtbl.add replay.streams (key event) stream;
          (stream, true)
    in
    match validate_ordering stream event with
    | Error _ as error ->
        if is_new then Hashtbl.remove replay.streams (key event);
        error
    | Ok () -> (
        match Order_book.apply_replay stream.book event.event with
        | Error message ->
            if is_new then Hashtbl.remove replay.streams (key event);
            Serror.failf "replay %s/%s sequence %d: %s" event.venue event.symbol
              event.sequence message
        | Ok (snapshot, fills) -> (
            match Order_book.validate stream.book with
            | Error message ->
                Serror.failf "invalid book after %s/%s sequence %d: %s"
                  event.venue event.symbol event.sequence message
            | Ok () ->
                stream.last_sequence <- Some event.sequence;
                stream.last_event_time <- Some event.event_time;
                stream.last_received_time <- event.received_time;
                Ok { feed_event = event; snapshot; fills }))

let run events =
  let replay = create () in
  let rec loop acc = function
    | [] -> Ok (List.rev acc)
    | event :: rest -> (
        match apply replay event with
        | Ok result -> loop (result :: acc) rest
        | Error _ as error -> error)
  in
  loop [] events

let book_count replay = Hashtbl.length replay.streams
