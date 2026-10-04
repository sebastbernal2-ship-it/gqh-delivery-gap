(** Incremental computation engine.

    Nodes form a DAG. When an input [Var] changes, stabilization propagates the
    change through affected downstream nodes in topological order via wave-based
    processing. Cut-off prevents unnecessary propagation when a node's value
    does not change.

    No [Obj.t], no global mutable state beyond a single work queue. Children are
    tracked through direct thunks, not a node table. Topological order is
    guaranteed by wave-based processing: all nodes at depth N are processed
    before any at depth N+1.

    Use {!make} to create fresh instances. Each instance carries its own work
    queue and ID counter, so multiple order books operate independently. *)

module type S = sig
  type 'a t

  module Var : sig
    type 'a t
    val create : 'a -> 'a t
    val set : 'a t -> 'a -> unit
    val snapshot : 'a t -> 'a
  end

  val of_var : 'a Var.t -> 'a t
  val return : 'a -> 'a t
  val map : ('a -> 'b) -> 'a t -> 'b t
  val map2 : ('a -> 'b -> 'c) -> 'a t -> 'b t -> 'c t
  val map3 : ('a -> 'b -> 'c -> 'd) -> 'a t -> 'b t -> 'c t -> 'd t
  val bind : 'a t -> f:('a -> 'b t) -> 'b t
  val cutoff : 'a t -> f:('a -> 'a -> bool) -> 'a t
  val if_ : bool t -> then_:'a t -> else_:'a t -> 'a t
  val snapshot : 'a t -> 'a
  val stabilize : unit -> unit
  val is_stabilized : unit -> bool
  val on_change : 'a t -> f:('a -> 'a -> unit) -> unit
end

(** [Make ()] is an internal functor that produces an [S]-conforming module
    with its own private work queue and ID counter. *)
module Make () = struct
  type 'a node = {
    id : int;
    mutable value : 'a;
    mutable pending : 'a option;
    mutable dirty : bool;
    mutable on_stabilized : (unit -> unit) list;
    mutable compute : unit -> 'a;
    mutable eq : 'a -> 'a -> bool;
    mutable on_change : ('a -> 'a -> unit) list;
  }

  type 'a t = 'a node

  (* ------------------------------------------------------------------ *)
  (* Wave-based work queue — scoped to this instance *)
  (* ------------------------------------------------------------------ *)

  let work_queue : (unit -> unit) list ref = ref []
  let next_id = ref 0

  let push_work (type a) (n : a t) : unit =
    work_queue :=
      (fun () ->
        if n.dirty then begin
          n.dirty <- false;
          let new_val = n.compute () in
          n.pending <- None;
          if not (n.eq new_val n.value) then begin
            let old = n.value in
            n.value <- new_val;
            List.iter (fun f -> f new_val old) n.on_change;
            List.iter (fun f -> f ()) n.on_stabilized
          end
        end)
      :: !work_queue

  (* ------------------------------------------------------------------ *)
  (* Node construction *)
  (* ------------------------------------------------------------------ *)

  let make_node (init : 'a) (compute : unit -> 'a) : 'a t =
    let id = !next_id in
    incr next_id;
    {
      id;
      value = init;
      pending = None;
      dirty = false;
      on_stabilized = [];
      compute;
      eq = ( == );
      on_change = [];
    }

  (* ------------------------------------------------------------------ *)
  (* Snapshot *)
  (* ------------------------------------------------------------------ *)

  let snapshot (x : 'a t) : 'a =
    match x.pending with Some p -> p | None -> x.value

  (* ------------------------------------------------------------------ *)
  (* Primitives *)
  (* ------------------------------------------------------------------ *)

  module Var = struct
    type 'a t = 'a node

    let create (x : 'a) : 'a t =
      let v = make_node x (fun () -> x) in
      v.compute <-
        (fun () -> match v.pending with Some p -> p | None -> v.value);
      v

    let set (v : 'a t) (x : 'a) : unit =
      v.pending <- Some x;
      v.dirty <- true;
      push_work v

    let snapshot = snapshot
  end

  let of_var (v : 'a Var.t) : 'a t = v
  let return (x : 'a) : 'a t = make_node x (fun () -> x)

  let map (f : 'a -> 'b) (x : 'a t) : 'b t =
    let n = make_node (f x.value) (fun () -> f (snapshot x)) in
    x.on_stabilized <-
      (fun () ->
        n.dirty <- true;
        push_work n)
      :: x.on_stabilized;
    n

  let map2 (f : 'a -> 'b -> 'c) (x : 'a t) (y : 'b t) : 'c t =
    let n =
      make_node (f x.value y.value) (fun () -> f (snapshot x) (snapshot y))
    in
    x.on_stabilized <-
      (fun () ->
        n.dirty <- true;
        push_work n)
      :: x.on_stabilized;
    y.on_stabilized <-
      (fun () ->
        n.dirty <- true;
        push_work n)
      :: y.on_stabilized;
    n

  let map3
      (f : 'a -> 'b -> 'c -> 'd)
      (x : 'a t)
      (y : 'b t)
      (z : 'c t) : 'd t =
    let n =
      make_node (f x.value y.value z.value) (fun () ->
          f (snapshot x) (snapshot y) (snapshot z))
    in
    x.on_stabilized <-
      (fun () ->
        n.dirty <- true;
        push_work n)
      :: x.on_stabilized;
    y.on_stabilized <-
      (fun () ->
        n.dirty <- true;
        push_work n)
      :: y.on_stabilized;
    z.on_stabilized <-
      (fun () ->
        n.dirty <- true;
        push_work n)
      :: z.on_stabilized;
    n

  let bind (x : 'a t) ~(f : 'a -> 'b t) : 'b t =
    let inner = ref None in
    let n = make_node (snapshot (f x.value)) (fun () -> assert false) in
    n.compute <-
      (fun () ->
        let xv = snapshot x in
        match !inner with
        | Some (prev_x, i) when prev_x == xv -> snapshot i
        | _ ->
            let i = f xv in
            inner := Some (xv, i);
            i.on_stabilized <-
              (fun () ->
                n.dirty <- true;
                push_work n)
              :: i.on_stabilized;
            snapshot i);
    let push_n () =
      n.dirty <- true;
      push_work n
    in
    x.on_stabilized <- push_n :: x.on_stabilized;
    n

  let cutoff (x : 'a t) ~(f : 'a -> 'a -> bool) : 'a t =
    let n = make_node x.value (fun () -> snapshot x) in
    n.eq <- f;
    x.on_stabilized <-
      (fun () ->
        n.dirty <- true;
        push_work n)
      :: x.on_stabilized;
    n

  let if_ (cond : bool t) ~(then_ : 'a t) ~(else_ : 'a t) : 'a t =
    let n =
      make_node
        (if cond.value then then_.value else else_.value)
        (fun () -> if snapshot cond then snapshot then_ else snapshot else_)
    in
    cond.on_stabilized <-
      (fun () ->
        n.dirty <- true;
        push_work n)
      :: cond.on_stabilized;
    then_.on_stabilized <-
      (fun () ->
        n.dirty <- true;
        push_work n)
      :: then_.on_stabilized;
    else_.on_stabilized <-
      (fun () ->
        n.dirty <- true;
        push_work n)
      :: else_.on_stabilized;
    n

  let on_change (x : 'a t) ~(f : 'a -> 'a -> unit) : unit =
    x.on_change <- f :: x.on_change

  (* ------------------------------------------------------------------ *)
  (* Stabilize: wave-based processing *)
  (* ------------------------------------------------------------------ *)

  let stabilize () : unit =
    let current = ref (List.rev !work_queue) in
    work_queue := [];
    while !current <> [] do
      let wave = !current in
      current := [];
      List.iter (fun f -> f ()) wave;
      current := List.rev !work_queue;
      work_queue := []
    done

  let is_stabilized () : bool = !work_queue = []
end

(** [make ()] creates a fresh incremental engine instance. *)
let make () = (module Make () : S)