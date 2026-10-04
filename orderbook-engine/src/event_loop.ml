(** Lwt-based event loop engine.

    Drives market events through the order book, publishing snapshots and stats
    on each update. Supports replay at configurable speed. *)

open Market_types
open Lwt.Infix

type event_handler = market_event -> unit Lwt.t
(** Callback type for event consumers. *)

type mode =
  | Replay
  | Simulation
      (** Replay applies venue events exactly; Simulation matches new orders. *)

type t = {
  book : Order_book.t;
  event_array : event array;
  mutable position : int;
  mutable running : bool;
  mutable speed : float;
  handlers : event_handler list ref;
  mutable start_real : Timestamp.t;
  mutable start_event_index : int;
  mode : mode;
}
(** Event loop state. *)

(** [create book events] creates a replay event loop by default. *)
let create ?(mode = Replay) (book : Order_book.t) (events : event list) : t =
  {
    book;
    event_array = Array.of_list events;
    position = 0;
    running = false;
    speed = 1.0;
    handlers = ref [];
    start_real = Timestamp.zero;
    start_event_index = 0;
    mode;
  }

(** [add_handler loop handler] registers an event handler. *)
let add_handler (loop : t) (handler : event_handler) : unit =
  loop.handlers := handler :: !(loop.handlers)

(** [notify loop ev] sends an event to all handlers. *)
let notify (loop : t) (ev : market_event) : unit Lwt.t =
  Lwt_list.iter_p (fun h -> h ev) !(loop.handlers)

(** [process_one loop] processes the next event. *)
let process_one (loop : t) : unit Serror.t Lwt.t =
  if loop.position >= Array.length loop.event_array then Lwt.return (Ok ())
  else
    let ev = loop.event_array.(loop.position) in
    loop.position <- loop.position + 1;
    match
      match loop.mode with
      | Replay -> Order_book.apply_replay loop.book ev
      | Simulation -> Order_book.apply loop.book ev
    with
    | Ok (snap, fills) ->
        let stats = Order_book.get_stats loop.book in
        let market_ev =
          match ev.action with
          | Add -> OrderAdded ev
          | Amend -> OrderAmended ev
          | Cancel -> OrderCancelled ev
          | Execute -> OrderExecuted (ev, ev.size)
          | Replace old_id -> OrderReplaced (ev, old_id)
          | Control _ -> ControlEvent ev
        in
        let trade_notifies = List.map (fun f -> Trade f) fills in
        let all_notifies =
          (market_ev :: trade_notifies)
          @ [ BookSnapshot snap; StatsUpdate stats ]
        in
        Lwt_list.iter_s (fun me -> notify loop me) all_notifies >>= fun () ->
        Lwt.return (Ok ())
    | Error msg -> Lwt.return (Error msg)

(** [run loop] runs the event loop to completion. *)
let run_internal (loop : t) ~(use_delay : bool) : unit Lwt.t =
  loop.running <- true;
  if use_delay then begin
    loop.start_real <- Timestamp.now ();
    loop.start_event_index <- loop.position
  end;
  let rec step () =
    if not loop.running then Lwt.return ()
    else
      let remaining = Array.length loop.event_array - loop.position in
      if remaining <= 0 then (
        loop.running <- false;
        Lwt.return ())
      else if
        use_delay && loop.position > loop.start_event_index && loop.speed > 0.0
      then
        let prev = loop.event_array.(loop.position - 1) in
        let dt =
          Timestamp.diff_seconds loop.event_array.(loop.position).timestamp
            prev.timestamp
        in
        let delay = dt /. loop.speed in
        if delay > 0.0 then
          Lwt_unix.sleep delay >>= fun () ->
          process_one loop >>= function
          | Ok () -> step ()
          | Error _ -> Lwt.return ()
        else
          process_one loop >>= function
          | Ok () -> step ()
          | Error _ -> Lwt.return ()
      else
        process_one loop >>= function
        | Ok () -> step ()
        | Error _ -> Lwt.return ()
  in
  step ()

(** [run loop] processes all events at real-time speed, respecting inter-event
    timestamps scaled by the speed multiplier. *)
let run (loop : t) : unit Lwt.t = run_internal loop ~use_delay:true

(** [run_fast loop] processes all events without delays (for testing). *)
let run_fast (loop : t) : unit Lwt.t = run_internal loop ~use_delay:false

(** [stop loop] stops the event loop. *)
let stop (loop : t) : unit = loop.running <- false

(** [set_speed loop speed] sets the replay speed multiplier. *)
let set_speed (loop : t) (speed : float) : unit = loop.speed <- speed

(** [progress loop] returns (processed, total) events. *)
let progress (loop : t) : int * int =
  (loop.position, Array.length loop.event_array)
