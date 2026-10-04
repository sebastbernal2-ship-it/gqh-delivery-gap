(** Validate a canonical event fixture against {!Exec_event}.

    Reports per-kind counts, the event-time range, sequence chain breaks
    between depth snapshots and updates, and receive-time ordering problems.
    Exits nonzero when any line fails to parse. *)

module E = Market_simulator.Exec_event
module Depth_chain = Market_simulator.Depth_chain
module Timestamp = Market_simulator.Timestamp

type depth_state = {
  chain : Depth_chain.t;
  mutable pending : (int64 * int64 * int64) list;
  (* Reversed arrival order, replayed once a snapshot arrives. *)
}

let usage () =
  prerr_endline "usage: exec_event_check [--json-report] EVENT_JSONL";
  exit 2

let () =
  let args = Array.to_list Sys.argv |> List.tl in
  let json_report, args =
    match args with
    | "--json-report" :: rest -> true, rest
    | rest -> false, rest
  in
  match args with
  | [ path ] -> (
      let ( lines,
            parsed,
            error_count,
            errors,
            kinds,
            first_event_time,
            last_event_time,
            first_receive_time,
            last_receive_time,
            suspect,
            chain_breaks,
            pending_updates,
            unbridged_updates,
            out_of_order_receive,
            superseded ) =
        let kinds = Hashtbl.create 8 in
        let lines = ref 0 in
        let parsed = ref 0 in
        let errors = ref [] in
        let error_count = ref 0 in
        let first_event_time = ref None in
        let last_event_time = ref None in
        let first_receive_time = ref None in
        let last_receive_time = ref None in
        let previous_receive = ref None in
        let suspect = ref 0 in
        let chain_breaks = ref 0 in
        let pending_updates = ref 0 in
        let out_of_order_receive = ref 0 in
        let depths = Hashtbl.create 8 in
        let superseded = ref 0 in
        let depth_for symbol =
          match Hashtbl.find_opt depths symbol with
          | Some state -> state
          | None ->
              let state = { chain = Depth_chain.create (); pending = [] } in
              Hashtbl.replace depths symbol state;
              state
        in
        let count_decision = function
          | Depth_chain.Accept -> ()
          | Depth_chain.Superseded -> incr superseded
          | Depth_chain.Gap -> incr chain_breaks
        in
        let apply_update state (first_id, last_id, previous_id) =
          count_decision
            (Depth_chain.apply state.chain ~first_update_id:first_id
               ~last_update_id:last_id ~previous_update_id:previous_id)
        in
        let note_error line message =
          incr error_count;
          if List.length !errors < 5 then
            errors := Printf.sprintf "line %d: %s" line message :: !errors
        in
        (try
           let ic = open_in path in
           (try
              while true do
                let line = input_line ic in
                incr lines;
                if String.trim line <> "" then
                  match E.of_string line with
                  | Error message -> note_error !lines message
                  | Ok event ->
                      incr parsed;
                      let name = E.kind_name event.E.payload in
                      Hashtbl.replace kinds name
                        (1 + try Hashtbl.find kinds name with Not_found -> 0);
                      (match event.E.quality with
                      | E.Healthy -> ()
                      | E.Suspect _ -> incr suspect);
                      (match !first_event_time with
                      | None -> first_event_time := Some event.E.event_time
                      | Some _ -> ());
                      last_event_time := Some event.E.event_time;
                      (match !first_receive_time with
                      | None -> first_receive_time := Some event.E.receive_time
                      | Some _ -> ());
                      last_receive_time := Some event.E.receive_time;
                      (match !previous_receive with
                      | Some previous
                        when Timestamp.compare event.E.receive_time previous < 0 ->
                          incr out_of_order_receive
                      | _ -> ());
                      previous_receive := Some event.E.receive_time;
                      (match event.E.payload with
                      | E.Depth_snapshot snapshot -> (
                          let state = depth_for event.E.symbol in
                          match snapshot.E.last_update_id with
                          | Some last_update_id ->
                              Depth_chain.reset state.chain last_update_id;
                              pending_updates :=
                                !pending_updates + List.length state.pending;
                              List.iter (apply_update state)
                                (List.rev state.pending);
                              state.pending <- []
                          | None -> ())
                      | E.Depth_update update -> (
                          (* Updates written before a snapshot were buffered
                             during its fetch and belong after it. *)
                          let state = depth_for event.E.symbol in
                          state.pending <-
                            ( update.E.first_update_id,
                              update.E.last_update_id,
                              match update.E.previous_update_id with
                              | Some value -> value
                              | None -> Int64.min_int )
                            :: state.pending)
                      | _ -> ())
              done
            with End_of_file -> close_in ic);
           ()
         with Sys_error message ->
           prerr_endline message;
           exit 1);
        let unbridged_updates =
          Hashtbl.fold
            (fun _ state total ->
              (* Anything still buffered is applied against the live chain, or
                 counted when the capture never carried a snapshot. *)
              match Depth_chain.current state.chain with
              | Some _ ->
                  List.iter (apply_update state) (List.rev state.pending);
                  state.pending <- [];
                  total
              | None -> total + List.length state.pending)
            depths 0
        in
        ( !lines,
          !parsed,
          !error_count,
          List.rev !errors,
          kinds,
          !first_event_time,
          !last_event_time,
          !first_receive_time,
          !last_receive_time,
          !suspect,
          !chain_breaks,
          !pending_updates,
          unbridged_updates,
          !out_of_order_receive,
          !superseded )
      in
      let time_option = function
        | None -> `Null
        | Some time -> `String (E.timestamp_to_string time)
      in
      let kind_pairs =
        Hashtbl.fold (fun name count acc -> (name, count) :: acc) kinds []
      in
      let kinds_json = List.map (fun (name, count) -> (name, `Int count)) kind_pairs in
      if json_report then
        print_endline
          (Yojson.Safe.to_string
             (`Assoc
               [
                 ("file", `String path);
                 ("lines", `Int lines);
                 ("parsed", `Int parsed);
                 ("errors", `Int error_count);
                 ("kind_counts", `Assoc kinds_json);
                 ("first_event_time", time_option first_event_time);
                 ("last_event_time", time_option last_event_time);
                 ("first_receive_time", time_option first_receive_time);
                 ("last_receive_time", time_option last_receive_time);
                 ("suspect", `Int suspect);
                 ("chain_breaks", `Int chain_breaks);
                 ("pending_updates", `Int pending_updates);
                 ("unbridged_updates", `Int unbridged_updates);
                 ("superseded", `Int superseded);
                 ("out_of_order_receive", `Int out_of_order_receive);
               ]))
      else begin
        Printf.printf
          "file=%s lines=%d parsed=%d errors=%d kinds=%s chain_breaks=%d pending_updates=%d unbridged_updates=%d superseded=%d out_of_order_receive=%d suspect=%d\n"
          path lines parsed error_count
          (String.concat ","
             (List.map
                (fun (name, count) -> name ^ ":" ^ string_of_int count)
                (List.rev kind_pairs)))
          chain_breaks pending_updates unbridged_updates superseded
          out_of_order_receive suspect;
        List.iter prerr_endline (List.rev errors)
      end;
      if error_count > 0 then exit 1)
  | _ -> usage ()
