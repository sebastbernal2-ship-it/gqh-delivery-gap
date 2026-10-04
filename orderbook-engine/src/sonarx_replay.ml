(** Replay loop for SonarX L2 snapshots. *)

open Lwt.Infix

type snapshot = Sonarx.snapshot
type snapshot_handler = snapshot -> unit Lwt.t

type t = {
  snapshots : snapshot array;
  mutable position : int;
  mutable running : bool;
  handlers : snapshot_handler list ref;
  mutable current : snapshot option;
}

let create snapshots =
  {
    snapshots = Array.of_list snapshots;
    position = 0;
    running = false;
    handlers = ref [];
    current = None;
  }

let add_handler loop handler = loop.handlers := handler :: !(loop.handlers)

let process_one loop : unit Serror.t Lwt.t =
  if loop.position >= Array.length loop.snapshots then Lwt.return (Ok ())
  else
    let snapshot = loop.snapshots.(loop.position) in
    loop.position <- loop.position + 1;
    loop.current <- Some snapshot;
    Lwt_list.iter_s (fun handler -> handler snapshot) !(loop.handlers)
    >|= fun () -> Ok ()

let rec run_steps loop ~(wait : snapshot -> snapshot -> unit Lwt.t) : unit Lwt.t
    =
  if not loop.running then Lwt.return ()
  else if loop.position >= Array.length loop.snapshots then begin
    loop.running <- false;
    Lwt.return ()
  end
  else
    let before = loop.current in
    let wait_for_previous =
      match before with
      | Some previous -> wait previous loop.snapshots.(loop.position)
      | None -> Lwt.return ()
    in
    wait_for_previous >>= fun () ->
    process_one loop >>= function
    | Ok () -> run_steps loop ~wait
    | Error _ ->
        loop.running <- false;
        Lwt.return ()

let run_fast loop : unit Lwt.t =
  loop.running <- true;
  run_steps loop ~wait:(fun _ _ -> Lwt.return ())

let run loop : unit Lwt.t =
  loop.running <- true;
  run_steps loop ~wait:(fun previous next ->
      let seconds =
        Timestamp.diff_seconds next.block_time previous.block_time
      in
      if seconds > 0.0 then Lwt_unix.sleep seconds else Lwt.return ())

let stop loop = loop.running <- false
let progress loop = (loop.position, Array.length loop.snapshots)
let current loop = loop.current
