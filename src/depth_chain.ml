(** Depth update chain rule for Binance futures captures.

    The rule mirrors collector/normalize_capture.py, which owns ingestion.

    Binance futures update id ranges are not contiguous: consecutive updates
    jump ahead by tens of ids, so the first update id is not the previous
    final id plus one. Only the previous-update id chain is authoritative.

    - Accept: the update continues the chain, or bridges a fresh snapshot.
    - Superseded: the update predates the current snapshot and is dropped.
    - Gap: the chain has a hole, so book state is no longer trustworthy. *)

type decision = Accept | Superseded | Gap

type t = { mutable current : int64 option; mutable bootstrapped : bool }

let create () = { current = None; bootstrapped = false }
let current t = t.current

let reset t last_update_id =
  t.current <- Some last_update_id;
  t.bootstrapped <- false

let apply t ~first_update_id ~last_update_id ~previous_update_id =
  match t.current with
  | None -> Gap
  | Some current ->
      if last_update_id <= current then Superseded
      else if not t.bootstrapped then
        let bridges =
          first_update_id <= Int64.add current 1L
          && Int64.add current 1L <= last_update_id
        in
        if previous_update_id <> current && not bridges then Gap
        else begin
          t.bootstrapped <- true;
          t.current <- Some last_update_id;
          Accept
        end
      else if previous_update_id <> current then Gap
      else begin
        t.current <- Some last_update_id;
        Accept
      end
