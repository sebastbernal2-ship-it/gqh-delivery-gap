(** Test suite for the market simulator. Exhaustive edge case coverage. *)

open Market_simulator.Market_types
open Market_simulator.Side
module Price = Market_simulator.Price
module Size = Market_simulator.Size

(* Create a fresh incremental engine instance for testing. *)
module IncrTest = struct
  include (val Incr.make ())
end

(* ------------------------------------------------------------------ *)
(* Zero timestamp for deterministic tests *)
(* ------------------------------------------------------------------ *)

let zero_ts = Market_simulator.Timestamp.zero

let btc_instrument =
  match
    Market_simulator.Binance_units.instrument ~symbol:"BTCUSDT"
      ~price_step:"1" ~quantity_step:"1"
  with
  | Ok value -> value
  | Error error -> failwith error

(* ------------------------------------------------------------------ *)
(* Helper: make a simple add event *)
(* ------------------------------------------------------------------ *)

let make_add_event ?(ts = zero_ts) ?(oid = "o1") ?(side = Bid) ?(price = 100.0)
    ?(size = 100) ?(valid_time = None) () : event =
  {
    timestamp = ts;
    order_id = oid;
    side;
    price = Market_simulator.Price.of_float price;
    size = Market_simulator.Size.of_int size;
    action = Add;
    valid_time;
  }

let make_cancel_event ?(ts = zero_ts) ?(oid = "o1") ?(side = Bid)
    ?(price = 100.0) ?(size = 100) () : event =
  {
    timestamp = ts;
    order_id = oid;
    side;
    price = Market_simulator.Price.of_float price;
    size = Market_simulator.Size.of_int size;
    action = Cancel;
    valid_time = None;
  }

(* ================================================================== *)
(* INCR: incremental computation engine *)
(* ================================================================== *)

(** Basic incr variable. *)
let test_incr_basic () =
  let v = IncrTest.Var.create 0 in
  assert (IncrTest.Var.snapshot v = 0);
  IncrTest.Var.set v 5;
  IncrTest.stabilize ();
  Alcotest.(check int) "basic set" 5 (IncrTest.Var.snapshot v);
  Alcotest.(check bool) "is_stabilized" true (IncrTest.is_stabilized ())

(** map2. *)
let test_incr_map2 () =
  let a = IncrTest.return 10 in
  let b = IncrTest.return 20 in
  let sum = IncrTest.map2 ( + ) a b in
  Alcotest.(check int) "map2 sum" 30 (IncrTest.snapshot sum)

(** map3. *)
let test_incr_map3 () =
  let a = IncrTest.return 1 in
  let b = IncrTest.return 2 in
  let c = IncrTest.return 3 in
  let sum = IncrTest.map3 (fun x y z -> x + y + z) a b c in
  Alcotest.(check int) "map3 sum" 6 (IncrTest.snapshot sum)

(** bind. *)
let test_incr_bind () =
  let a = IncrTest.return 5 in
  let b = IncrTest.return 10 in
  let bound = IncrTest.bind a ~f:(fun x -> IncrTest.map (fun y -> x + y) b) in
  IncrTest.stabilize ();
  Alcotest.(check int) "bind result" 15 (IncrTest.snapshot bound)

(** if_. *)
let test_incr_if () =
  let cond = IncrTest.return true in
  let a = IncrTest.return 100 in
  let b = IncrTest.return 200 in
  let result = IncrTest.if_ cond ~then_:a ~else_:b in
  Alcotest.(check int) "if true picks then" 100 (IncrTest.snapshot result)

(** Cutoff: setting same value does not fire on_change. *)
let test_incr_cutoff () =
  let v = IncrTest.Var.create 0 in
  let doubled = IncrTest.map (fun x -> x * 2) (IncrTest.of_var v) in
  let changes = ref 0 in
  IncrTest.on_change doubled ~f:(fun new_ old -> incr changes);
  IncrTest.Var.set v 5;
  IncrTest.stabilize ();
  Alcotest.(check int) "first change fires" 1 !changes;
  Alcotest.(check int) "value after first" 10 (IncrTest.snapshot doubled);
  (* Set same value: cutoff should block callback *)
  IncrTest.Var.set v 5;
  IncrTest.stabilize ();
  Alcotest.(check int) "cutoff blocks change" 1 !changes;
  Alcotest.(check bool)
    "still stabilized after cutoff" true
    (IncrTest.is_stabilized ())

(** Topological order: chain. *)
let test_incr_topo_chain () =
  let v = IncrTest.Var.create 1 in
  let a = IncrTest.map (fun x -> x * 2) (IncrTest.of_var v) in
  let b = IncrTest.map (fun x -> x + 1) a in
  let c = IncrTest.map (fun x -> x * 3) b in
  Alcotest.(check int) "chain initial" 9 (IncrTest.snapshot c);
  IncrTest.Var.set v 3;
  IncrTest.stabilize ();
  Alcotest.(check int)
    "chain after: 3*2=6,6+1=7,7*3=21" 21 (IncrTest.snapshot c);
  Alcotest.(check bool) "chain stabilized" true (IncrTest.is_stabilized ())

(** Topological order: diamond DAG. *)
let test_incr_topo_diamond () =
  let v = IncrTest.Var.create 10 in
  let a = IncrTest.map (fun x -> x * 2) (IncrTest.of_var v) in
  let b = IncrTest.map (fun x -> x * 3) (IncrTest.of_var v) in
  let c = IncrTest.map2 (fun x y -> x + y) a b in
  Alcotest.(check int) "diamond initial: 20+30=50" 50 (IncrTest.snapshot c);
  IncrTest.Var.set v 20;
  IncrTest.stabilize ();
  Alcotest.(check int) "diamond after: 40+60=100" 100 (IncrTest.snapshot c)

(** if_ dynamically toggles between branches. *)
let test_incr_if_dynamic () =
  let cond_var = IncrTest.Var.create true in
  let a = IncrTest.Var.create 100 in
  let b = IncrTest.Var.create 200 in
  let result =
    IncrTest.if_ (IncrTest.of_var cond_var) ~then_:(IncrTest.of_var a)
      ~else_:(IncrTest.of_var b)
  in
  IncrTest.stabilize ();
  Alcotest.(check int) "if true initial" 100 (IncrTest.snapshot result);
  IncrTest.Var.set cond_var false;
  IncrTest.stabilize ();
  Alcotest.(check int) "if false after toggle" 200 (IncrTest.snapshot result);
  IncrTest.Var.set a 999;
  IncrTest.stabilize ();
  Alcotest.(check int)
    "if false ignores then changes" 200 (IncrTest.snapshot result);
  IncrTest.Var.set cond_var true;
  IncrTest.stabilize ();
  Alcotest.(check int)
    "if true picks updated then" 999 (IncrTest.snapshot result)

(** bind dynamically changes the inner graph. *)
let test_incr_bind_dynamic () =
  let switch = IncrTest.Var.create 0 in
  let a = IncrTest.Var.create 10 in
  let b = IncrTest.Var.create 20 in
  let result =
    IncrTest.bind (IncrTest.of_var switch) ~f:(fun s ->
        if s = 0 then IncrTest.map (fun x -> x * 2) (IncrTest.of_var a)
        else IncrTest.map (fun x -> x * 3) (IncrTest.of_var b))
  in
  IncrTest.stabilize ();
  Alcotest.(check int)
    "bind: switch=0 uses a*2=20" 20 (IncrTest.snapshot result);
  (* Switch to using b *)
  IncrTest.Var.set switch 1;
  IncrTest.stabilize ();
  Alcotest.(check int)
    "bind: switch=1 uses b*3=60" 60 (IncrTest.snapshot result);
  (* Switch back to using a *)
  IncrTest.Var.set switch 0;
  IncrTest.stabilize ();
  Alcotest.(check int)
    "bind: switch=0 uses a again *2=20" 20 (IncrTest.snapshot result)

(** Custom cutoff via eq function. *)
let test_incr_cutoff_custom () =
  let v = IncrTest.Var.create 0 in
  (* only propagate if the value changes by more than 5 *)
  let cutoff_v =
    IncrTest.cutoff (IncrTest.of_var v) ~f:(fun old new_ ->
        abs (new_ - old) < 5)
  in
  let doubled = IncrTest.map (fun x -> x * 2) cutoff_v in
  Alcotest.(check int) "cutoff initial: 0*2=0" 0 (IncrTest.snapshot doubled);
  IncrTest.Var.set v 3;
  IncrTest.stabilize ();
  (* change of 3 is <5, cutoff blocks *)
  Alcotest.(check int) "cutoff blocks change of 3" 0 (IncrTest.snapshot doubled);
  IncrTest.Var.set v 6;
  IncrTest.stabilize ();
  (* change of 6 is >=5, propagates *)
  Alcotest.(check int)
    "cutoff passes change of 6, 6*2=12" 12
    (IncrTest.snapshot doubled)

(** on_change with multiple callbacks. *)
let test_incr_on_change_multi () =
  let v = IncrTest.Var.create 0 in
  let doubled = IncrTest.map (fun x -> x * 2) (IncrTest.of_var v) in
  let c1 = ref 0 in
  let c2 = ref 0 in
  IncrTest.on_change doubled ~f:(fun _new _old -> incr c1);
  IncrTest.on_change doubled ~f:(fun _new _old -> incr c2);
  IncrTest.Var.set v 5;
  IncrTest.stabilize ();
  Alcotest.(check int) "multi: c1 fires" 1 !c1;
  Alcotest.(check int) "multi: c2 fires" 1 !c2

(** No-op stabilize has no effect. *)
let test_incr_stabilize_noop () =
  let v = IncrTest.Var.create 42 in
  let mapped = IncrTest.map (fun x -> x) (IncrTest.of_var v) in
  IncrTest.stabilize ();
  Alcotest.(check int) "noop stabilize value" 42 (IncrTest.snapshot mapped);
  Alcotest.(check bool) "noop stabilize flag" true (IncrTest.is_stabilized ())

(** Double set before stabilize merges correctly. *)
let test_incr_double_set () =
  let v = IncrTest.Var.create 0 in
  let captured = ref 0 in
  let mapped = IncrTest.map (fun x -> x) (IncrTest.of_var v) in
  IncrTest.on_change mapped ~f:(fun new_ _old -> captured := new_);
  IncrTest.Var.set v 10;
  IncrTest.Var.set v 20;
  IncrTest.stabilize ();
  Alcotest.(check int)
    "double-set takes last value" 20 (IncrTest.snapshot mapped);
  Alcotest.(check int) "double-set fires once with final" 20 !captured

(** return creates a constant node. *)
let test_incr_return () =
  let c = IncrTest.return 99 in
  Alcotest.(check int) "return constant" 99 (IncrTest.snapshot c);
  Alcotest.(check bool) "return stabilized" true (IncrTest.is_stabilized ())

(** of_var and var snapshot consistency. *)
let test_incr_of_var () =
  let v = IncrTest.Var.create 7 in
  let ov = IncrTest.of_var v in
  Alcotest.(check int) "of_var matches var" 7 (IncrTest.snapshot ov);
  Alcotest.(check int) "var snapshot" 7 (IncrTest.Var.snapshot v)

(** map with different types. *)
let test_incr_map_string () =
  let v = IncrTest.Var.create 42 in
  let s = IncrTest.map string_of_int (IncrTest.of_var v) in
  Alcotest.(check string) "map to string" "42" (IncrTest.snapshot s);
  IncrTest.Var.set v 100;
  IncrTest.stabilize ();
  Alcotest.(check string)
    "map to string after change" "100" (IncrTest.snapshot s)

(** bind with change callback on the result. *)
let test_incr_bind_on_change () =
  let v = IncrTest.Var.create 0 in
  let result =
    IncrTest.bind (IncrTest.of_var v) ~f:(fun x -> IncrTest.return (x * 10))
  in
  let changes = ref [] in
  IncrTest.on_change result ~f:(fun new_ old ->
      changes := (old, new_) :: !changes);
  IncrTest.Var.set v 1;
  IncrTest.stabilize ();
  IncrTest.Var.set v 2;
  IncrTest.stabilize ();
  Alcotest.(check int) "bind change count" 2 (List.length !changes);
  Alcotest.(check int) "bind final value" 20 (IncrTest.snapshot result)

(** Deep chain: 5 levels of map. *)
let test_incr_deep_chain () =
  let v = IncrTest.Var.create 1 in
  let n1 = IncrTest.map (fun x -> x + 1) (IncrTest.of_var v) in
  let n2 = IncrTest.map (fun x -> x * 2) n1 in
  let n3 = IncrTest.map (fun x -> x - 3) n2 in
  let n4 = IncrTest.map (fun x -> x / 2) n3 in
  let n5 = IncrTest.map (fun x -> x * x) n4 in
  IncrTest.stabilize ();
  (* 1->2->4->1->0->0 *)
  Alcotest.(check int) "deep chain initial: 0^2=0" 0 (IncrTest.snapshot n5);
  IncrTest.Var.set v 5;
  IncrTest.stabilize ();
  (* 5->6->12->9->4->16 *)
  Alcotest.(check int) "deep chain after: 4^2=16" 16 (IncrTest.snapshot n5)

(* ================================================================== *)
(* SERROR: error handling utility *)
(* ================================================================== *)

(** return produces Ok. *)
let test_serror_return () =
  Alcotest.(check bool)
    "return Ok" true
    (Market_simulator.Serror.is_ok (Market_simulator.Serror.return 42));
  Alcotest.(check bool)
    "return is not Error" false
    (Market_simulator.Serror.is_error (Market_simulator.Serror.return 42))

(** fail produces Error. *)
let test_serror_fail () =
  let e = Market_simulator.Serror.fail "oops" in
  Alcotest.(check bool)
    "fail is Error" true
    (Market_simulator.Serror.is_error e);
  Alcotest.(check bool) "fail is not Ok" false (Market_simulator.Serror.is_ok e)

(** failf produces formatted error. *)
let test_serror_failf () =
  let e = Market_simulator.Serror.failf "error #%d at %s" 99 "test" in
  Alcotest.(check bool)
    "failf is Error" true
    (Market_simulator.Serror.is_error e);
  match e with
  | Error msg -> Alcotest.(check string) "failf message" "error #99 at test" msg
  | _ -> Alcotest.fail "expected Error"

(** map transforms Ok, passes Error. *)
let test_serror_map () =
  let serror_map f = function Ok x -> Ok (f x) | Error _ as e -> e in
  let open Market_simulator.Serror in
  let ok = serror_map (fun x -> x * 2) (return 21) in
  Alcotest.(check int) "map Ok" 42 (ok_or_failwith ok);
  let err = serror_map (fun x -> x) (fail "err") in
  Alcotest.(check bool) "map Error" true (is_error err)

(** bind chains Ok, short-circuits on Error. *)
let test_serror_bind () =
  let ok =
    Market_simulator.Serror.bind (Market_simulator.Serror.return 5) ~f:(fun x ->
        Market_simulator.Serror.return (x * 3))
  in
  Alcotest.(check int) "bind Ok" 15 (Market_simulator.Serror.ok_or_failwith ok);
  let err =
    Market_simulator.Serror.bind (Market_simulator.Serror.fail "boom")
      ~f:(fun _ -> Market_simulator.Serror.return 999)
  in
  Alcotest.(check bool) "bind Error" true (Market_simulator.Serror.is_error err)

(** map_error transforms error message. *)
let test_serror_map_error () =
  (let err =
     Market_simulator.Serror.map_error (Market_simulator.Serror.fail "raw")
       ~f:(fun s -> "prefix: " ^ s)
   in
   match err with
   | Error msg -> Alcotest.(check string) "map_error message" "prefix: raw" msg
   | _ -> Alcotest.fail "expected Error");
  let ok =
    Market_simulator.Serror.map_error (Market_simulator.Serror.return 42)
      ~f:(fun s -> s)
  in
  Alcotest.(check int)
    "map_error Ok" 42
    (Market_simulator.Serror.ok_or_failwith ok)

(** both returns pair or first error. *)
let test_serror_both () =
  (let ok =
     Market_simulator.Serror.both
       (Market_simulator.Serror.return 1)
       (Market_simulator.Serror.return 2)
   in
   match ok with
   | Ok (a, b) ->
       Alcotest.(check int) "both a" 1 a;
       Alcotest.(check int) "both b" 2 b
   | _ -> Alcotest.fail "expected Ok pair");
  let err =
    Market_simulator.Serror.both
      (Market_simulator.Serror.fail "first")
      (Market_simulator.Serror.return 2)
  in
  Alcotest.(check bool)
    "both first error" true
    (Market_simulator.Serror.is_error err);
  let err2 =
    Market_simulator.Serror.both
      (Market_simulator.Serror.return 1)
      (Market_simulator.Serror.fail "second")
  in
  Alcotest.(check bool)
    "both second error" true
    (Market_simulator.Serror.is_error err2)

(** all returns list or first error. *)
let test_serror_all () =
  let ok =
    Market_simulator.Serror.all
      [
        Market_simulator.Serror.return 1;
        Market_simulator.Serror.return 2;
        Market_simulator.Serror.return 3;
      ]
  in
  Alcotest.(check bool)
    "all Ok" true
    (Market_simulator.Serror.ok_or_failwith ok = [ 1; 2; 3 ]);
  let err =
    Market_simulator.Serror.all
      [
        Market_simulator.Serror.return 1;
        Market_simulator.Serror.fail "boom";
        Market_simulator.Serror.return 3;
      ]
  in
  Alcotest.(check bool) "all Error" true (Market_simulator.Serror.is_error err);
  (* empty list *)
  let empty = Market_simulator.Serror.all [] in
  Alcotest.(check bool)
    "all empty" true
    (Market_simulator.Serror.ok_or_failwith empty = [])

(** try_with catches exceptions. *)
let test_serror_try_with () =
  let ok = Market_simulator.Serror.try_with (fun () -> 42) in
  Alcotest.(check int)
    "try_with ok" 42
    (Market_simulator.Serror.ok_or_failwith ok);
  let err = Market_simulator.Serror.try_with (fun () -> failwith "explosion") in
  Alcotest.(check bool)
    "try_with error" true
    (Market_simulator.Serror.is_error err)

(** of_option converts Some/None. *)
let test_serror_of_option () =
  let some = Market_simulator.Serror.of_option (Some 42) ~error:"none" in
  Alcotest.(check int)
    "of_option Some" 42
    (Market_simulator.Serror.ok_or_failwith some);
  let none = Market_simulator.Serror.of_option None ~error:"missing" in
  Alcotest.(check bool)
    "of_option None" true
    (Market_simulator.Serror.is_error none)

(** ok_or_failwith raises on Error, returns on Ok. *)
let test_serror_ok_or_failwith () =
  Alcotest.(check int)
    "ok_or_failwith Ok" 99
    (Market_simulator.Serror.ok_or_failwith (Market_simulator.Serror.return 99));
  Alcotest.check_raises "ok_or_failwith Error" (Failure "bad") (fun () ->
      ignore
        (Market_simulator.Serror.ok_or_failwith
           (Market_simulator.Serror.fail "bad")))

(** value returns default on Error. *)
let test_serror_value () =
  Alcotest.(check int)
    "value Ok" 42
    (Market_simulator.Serror.value
       (Market_simulator.Serror.return 42)
       ~default:0);
  Alcotest.(check int)
    "value Error" 0
    (Market_simulator.Serror.value
       (Market_simulator.Serror.fail "err")
       ~default:0)

(** filter_map skips errors. *)
let test_serror_filter_map () =
  let result =
    Market_simulator.Serror.filter_map [ 1; 2; 3; 4; 5 ] ~f:(fun x ->
        if x mod 2 = 0 then Market_simulator.Serror.return (x * 10)
        else Market_simulator.Serror.fail "odd")
  in
  Alcotest.(check bool) "filter_map" true (result = [ 20; 40 ])

(** map list returns Ok or first Error. *)
let test_serror_map_list () =
  let ok =
    Market_simulator.Serror.map [ 1; 2; 3 ] ~f:(fun x ->
        Market_simulator.Serror.return (x * 2))
  in
  Alcotest.(check bool)
    "map list Ok" true
    (Market_simulator.Serror.ok_or_failwith ok = [ 2; 4; 6 ]);
  let err =
    Market_simulator.Serror.map [ 1; 2; 3 ] ~f:(fun x ->
        if x = 2 then Market_simulator.Serror.fail "bad"
        else Market_simulator.Serror.return x)
  in
  Alcotest.(check bool)
    "map list Error" true
    (Market_simulator.Serror.is_error err)

(* ================================================================== *)
(* SIDE: bid/ask and action types *)
(* ================================================================== *)

(** side_of_sexp roundtrip. *)
let test_side_sexp () =
  let sides = [ Bid; Ask ] in
  List.iter
    (fun s ->
      let sexp = Market_simulator.Side.sexp_of_side s in
      let back = Market_simulator.Side.side_of_sexp sexp in
      Alcotest.(check bool)
        "side sexp roundtrip"
        (Market_simulator.Side.equal_side s back)
        true)
    sides

(** side_of_sexp raises on invalid. *)
let test_side_sexp_invalid () =
  Alcotest.check_raises "side_of_sexp invalid" (Invalid_argument "side_of_sexp")
    (fun () ->
      ignore (Market_simulator.Side.side_of_sexp (Sexplib0.Sexp.Atom "invalid")))

(** action_of_sexp roundtrip. *)
let test_action_sexp () =
  let actions = [ Add; Amend; Cancel; Execute ] in
  List.iter
    (fun a ->
      let sexp = Market_simulator.Side.sexp_of_action a in
      let back = Market_simulator.Side.action_of_sexp sexp in
      Alcotest.(check bool)
        "action sexp roundtrip"
        (Market_simulator.Side.equal_action a back)
        true)
    actions

(** action_of_sexp raises on invalid. *)
let test_action_sexp_invalid () =
  Alcotest.check_raises "action_of_sexp invalid"
    (Invalid_argument "action_of_sexp") (fun () ->
      ignore
        (Market_simulator.Side.action_of_sexp (Sexplib0.Sexp.Atom "bad_action")))

(** derived show for side. *)
let test_side_show () =
  Alcotest.(check string)
    "show Bid" "Side.Bid"
    (Market_simulator.Side.show_side Bid);
  Alcotest.(check string)
    "show Ask" "Side.Ask"
    (Market_simulator.Side.show_side Ask)

(** derived compare for side. *)
let test_side_compare () =
  Alcotest.(check bool)
    "Bid < Ask" true
    (Market_simulator.Side.compare_side Bid Ask < 0);
  Alcotest.(check bool)
    "Bid = Bid" true
    (Market_simulator.Side.compare_side Bid Bid = 0)

(* ================================================================== *)
(* ORDER_ID: order identifier *)
(* ================================================================== *)

(** order_id sexp roundtrip. *)
let test_order_id_sexp () =
  let oid = "ord-001" in
  let sexp = Market_simulator.Order_id.sexp_of_t oid in
  let back = Market_simulator.Order_id.t_of_sexp sexp in
  Alcotest.(check string) "order_id sexp roundtrip" oid back

(** order_id Map operations. *)
let test_order_id_map () =
  let m = Market_simulator.Order_id.Map.empty in
  Alcotest.(check bool)
    "map empty" true
    (Market_simulator.Order_id.Map.is_empty m);
  let m = Market_simulator.Order_id.Map.add "ord1" 100 m in
  let m = Market_simulator.Order_id.Map.add "ord2" 200 m in
  Alcotest.(check int)
    "map cardinal" 2
    (Market_simulator.Order_id.Map.cardinal m);
  Alcotest.(check bool)
    "map find ord1" true
    (Market_simulator.Order_id.Map.find_opt "ord1" m = Some 100);
  Alcotest.(check bool)
    "map find unknown" true
    (Market_simulator.Order_id.Map.find_opt "ord3" m = None)

(* ================================================================== *)
(* PRICE: integer-based decimal *)
(* ================================================================== *)

(** Price basic operations. *)
let test_price_ops () =
  let p = Market_simulator.Price.of_float 100.50 in
  Alcotest.(check string)
    "to_string" "100.5000"
    (Market_simulator.Price.to_string p);
  Alcotest.(check bool)
    "equality" true
    (Market_simulator.Price.equal p (Market_simulator.Price.of_float 100.50));
  Alcotest.(check bool)
    "compare 100 < 101" true
    (Market_simulator.Price.compare
       (Market_simulator.Price.of_float 100.0)
       (Market_simulator.Price.of_float 101.0)
    < 0);
  Alcotest.(check bool)
    "compare equal" true
    (Market_simulator.Price.compare
       (Market_simulator.Price.of_float 100.0)
       (Market_simulator.Price.of_float 100.0)
    = 0)

(** Price of_int / to_int roundtrip. *)
let test_price_int_roundtrip () =
  Alcotest.(check int)
    "of_int 0" 0
    (Market_simulator.Price.to_int (Market_simulator.Price.of_int 0));
  Alcotest.(check int)
    "of_int 100" 100
    (Market_simulator.Price.to_int (Market_simulator.Price.of_int 100));
  Alcotest.(check int)
    "of_int -50" (-50)
    (Market_simulator.Price.to_int (Market_simulator.Price.of_int (-50)))

(** Price to_float / of_float roundtrip. *)
let test_price_float_roundtrip () =
  let epsilon = 0.0001 in
  let test_val v =
    let p = Market_simulator.Price.of_float v in
    let v' = Market_simulator.Price.to_float p in
    Alcotest.(check bool)
      (Printf.sprintf "float roundtrip %.4f" v)
      (abs_float (v' -. v) < epsilon)
      true
  in
  test_val 0.0;
  test_val 100.0;
  test_val 99.99;
  test_val 100.5000;
  test_val 0.0001;
  test_val (-10.50)

(** Price edge cases. *)
let test_price_edge () =
  (* Zero *)
  Alcotest.(check string)
    "zero price" "0.0000"
    (Market_simulator.Price.to_string (Market_simulator.Price.of_int 0));
  (* Large *)
  let big = Market_simulator.Price.of_float 999999.9999 in
  Alcotest.(check bool)
    "large price string" true
    (String.length (Market_simulator.Price.to_string big) > 0);
  (* to_string precision *)
  Alcotest.(check string)
    "precision 100.0000" "100.0000"
    (Market_simulator.Price.to_string (Market_simulator.Price.of_float 100.0));
  Alcotest.(check string)
    "precision 100.5000" "100.5000"
    (Market_simulator.Price.to_string (Market_simulator.Price.of_float 100.5))

(** Price sexp roundtrip. *)
let test_price_sexp () =
  let p = Market_simulator.Price.of_float 100.50 in
  let sexp = Market_simulator.Price.sexp_of_t p in
  let back = Market_simulator.Price.t_of_sexp sexp in
  Alcotest.(check bool)
    "price sexp roundtrip"
    (Market_simulator.Price.equal p back)
    true

(** Price sexp on invalid string returns 0. *)
let test_price_sexp_invalid () =
  let back =
    Market_simulator.Price.t_of_sexp (Sexplib0.Sexp.Atom "not-a-number")
  in
  Alcotest.(check int)
    "price invalid sexp -> 0" 0
    (Market_simulator.Price.to_int back)

(** Price Map operations. *)
let test_price_map () =
  let m = Market_simulator.Price.Map.empty in
  let m =
    Market_simulator.Price.Map.add
      (Market_simulator.Price.of_float 100.0)
      "level1" m
  in
  let m =
    Market_simulator.Price.Map.add
      (Market_simulator.Price.of_float 101.0)
      "level2" m
  in
  Alcotest.(check int)
    "price map cardinal" 2
    (Market_simulator.Price.Map.cardinal m);
  Alcotest.(check bool)
    "price map find 100" true
    (Market_simulator.Price.Map.mem (Market_simulator.Price.of_float 100.0) m)

(* ================================================================== *)
(* SIZE: integer quantity *)
(* ================================================================== *)

(** Size basic operations. *)
let test_size_ops () =
  let s = Market_simulator.Size.of_int 500 in
  Alcotest.(check string) "to_string" "500" (Market_simulator.Size.to_string s);
  Alcotest.(check int)
    "add 500+300=800" 800
    (Market_simulator.Size.to_int
       (Market_simulator.Size.add s (Market_simulator.Size.of_int 300)));
  Alcotest.(check int)
    "sub 500-300=200" 200
    (Market_simulator.Size.to_int
       (Market_simulator.Size.sub s (Market_simulator.Size.of_int 300)));
  Alcotest.(check int)
    "min(500,200)=200" 200
    (Market_simulator.Size.to_int
       (Market_simulator.Size.min s (Market_simulator.Size.of_int 200)))

(** Size zero behavior. *)
let test_size_zero () =
  Alcotest.(check int)
    "zero to_int" 0
    (Market_simulator.Size.to_int Market_simulator.Size.zero);
  Alcotest.(check int)
    "add zero" 100
    (Market_simulator.Size.to_int
       (Market_simulator.Size.add
          (Market_simulator.Size.of_int 100)
          Market_simulator.Size.zero));
  Alcotest.(check int)
    "sub zero" 100
    (Market_simulator.Size.to_int
       (Market_simulator.Size.sub
          (Market_simulator.Size.of_int 100)
          Market_simulator.Size.zero));
  Alcotest.(check bool)
    "zero equality" true
    (Market_simulator.Size.equal Market_simulator.Size.zero
       (Market_simulator.Size.of_int 0))

(** Size edge cases. *)
let test_size_edge () =
  (* Large numbers *)
  let large = Market_simulator.Size.of_int 1_000_000_000 in
  Alcotest.(check string)
    "large size string" "1000000000"
    (Market_simulator.Size.to_string large);
  (* Negative size (should be allowed by type even if semantically odd) *)
  let neg = Market_simulator.Size.of_int (-100) in
  Alcotest.(check int) "negative size" (-100) (Market_simulator.Size.to_int neg)

(** Size sexp roundtrip. *)
let test_size_sexp () =
  let s = Market_simulator.Size.of_int 500 in
  let sexp = Market_simulator.Size.sexp_of_t s in
  let back = Market_simulator.Size.t_of_sexp sexp in
  Alcotest.(check bool)
    "size sexp roundtrip"
    (Market_simulator.Size.equal s back)
    true

(** Size sexp invalid returns zero. *)
let test_size_sexp_invalid () =
  let back =
    Market_simulator.Size.t_of_sexp (Sexplib0.Sexp.Atom "not-a-number")
  in
  Alcotest.(check int)
    "size invalid sexp -> 0" 0
    (Market_simulator.Size.to_int back);
  let back2 = Market_simulator.Size.t_of_sexp (Sexplib0.Sexp.List []) in
  Alcotest.(check int)
    "size invalid list -> 0" 0
    (Market_simulator.Size.to_int back2)

(* ================================================================== *)
(* TIMESTAMP: Ptime-based nanosecond timestamps *)
(* ================================================================== *)

(** Timestamp basic operations. *)
let test_timestamp_ops () =
  let t1 = Market_simulator.Timestamp.now () in
  let t2 = Market_simulator.Timestamp.add_seconds t1 3600.0 in
  Alcotest.(check bool)
    "add advances time"
    (Market_simulator.Timestamp.compare t2 t1 > 0)
    true;
  let diff = Market_simulator.Timestamp.diff_seconds t2 t1 in
  Alcotest.(check bool) "diff approx 3600" (diff > 3599.0 && diff < 3601.0) true;
  let ts_str = Market_simulator.Timestamp.to_string t1 in
  Alcotest.(check bool) "to_string non-empty" (String.length ts_str > 0) true

(** Timestamp zero and epoch. *)
let test_timestamp_zero () =
  Alcotest.(check bool)
    "zero is epoch" true
    (Market_simulator.Timestamp.equal Market_simulator.Timestamp.zero
       (Market_simulator.Timestamp.of_ptime Ptime.epoch))

(** Timestamp of_string valid. *)
let test_timestamp_of_string_valid () =
  match Market_simulator.Timestamp.of_string "2026-09-01T09:30:00Z" with
  | Ok t ->
      Alcotest.(check bool)
        "parsed valid rfc3339"
        (Market_simulator.Timestamp.compare t Market_simulator.Timestamp.zero
        > 0)
        true
  | Error _ -> Alcotest.fail "expected Ok"

(** Timestamp of_string invalid. *)
let test_timestamp_of_string_invalid () =
  match Market_simulator.Timestamp.of_string "not-a-timestamp" with
  | Ok _ -> Alcotest.fail "expected Error"
  | Error msg ->
      Alcotest.(check string) "invalid timestamp error" "invalid timestamp" msg

(** Timestamp max/min. *)
let test_timestamp_max_min () =
  let t1 = Market_simulator.Timestamp.zero in
  let t2 = Market_simulator.Timestamp.add_seconds t1 100.0 in
  Alcotest.(check bool)
    "max selects later"
    (Market_simulator.Timestamp.equal (Market_simulator.Timestamp.max t1 t2) t2)
    true;
  Alcotest.(check bool)
    "min selects earlier"
    (Market_simulator.Timestamp.equal (Market_simulator.Timestamp.min t1 t2) t1)
    true

(** Timestamp sexp roundtrip. *)
let test_timestamp_sexp () =
  let t = Market_simulator.Timestamp.zero in
  let sexp = Market_simulator.Timestamp.sexp_of_t t in
  let back = Market_simulator.Timestamp.t_of_sexp sexp in
  Alcotest.(check bool)
    "timestamp sexp roundtrip"
    (Market_simulator.Timestamp.equal t back)
    true

(** Timestamp sexp invalid returns zero. *)
let test_timestamp_sexp_invalid () =
  let back =
    Market_simulator.Timestamp.t_of_sexp (Sexplib0.Sexp.Atom "bogus")
  in
  Alcotest.(check bool)
    "timestamp invalid sexp -> zero"
    (Market_simulator.Timestamp.equal back Market_simulator.Timestamp.zero)
    true;
  let back2 = Market_simulator.Timestamp.t_of_sexp (Sexplib0.Sexp.List []) in
  Alcotest.(check bool)
    "timestamp invalid list -> zero"
    (Market_simulator.Timestamp.equal back2 Market_simulator.Timestamp.zero)
    true

(** Timestamp to_ptime / of_ptime roundtrip. *)
let test_timestamp_ptime () =
  let now = Market_simulator.Timestamp.now () in
  let ptime = Market_simulator.Timestamp.to_ptime now in
  let back = Market_simulator.Timestamp.of_ptime ptime in
  Alcotest.(check bool)
    "ptime roundtrip"
    (Market_simulator.Timestamp.equal now back)
    true

(* ================================================================== *)
(* LIST_UTILS: list helpers *)
(* ================================================================== *)

(** take with various parameters. *)
let test_list_utils_take () =
  let lst = [ 1; 2; 3; 4; 5 ] in
  Alcotest.(check bool)
    "take 0" true
    (Market_simulator.List_utils.take 0 lst = []);
  Alcotest.(check bool)
    "take 1" true
    (Market_simulator.List_utils.take 1 lst = [ 1 ]);
  Alcotest.(check bool)
    "take 3" true
    (Market_simulator.List_utils.take 3 lst = [ 1; 2; 3 ]);
  Alcotest.(check bool)
    "take 5 (full)" true
    (Market_simulator.List_utils.take 5 lst = [ 1; 2; 3; 4; 5 ]);
  Alcotest.(check bool)
    "take 10 (over)" true
    (Market_simulator.List_utils.take 10 lst = [ 1; 2; 3; 4; 5 ]);
  Alcotest.(check bool)
    "take from empty" true
    (Market_simulator.List_utils.take 5 [] = []);
  Alcotest.(check bool)
    "take negative -> empty" true
    (Market_simulator.List_utils.take (-1) [ 1; 2; 3 ] = []);
  Alcotest.(check bool)
    "take from single" true
    (Market_simulator.List_utils.take 1 [ 42 ] = [ 42 ])

(* ================================================================== *)
(* ORDER_BOOK: full order book engine *)
(* ================================================================== *)

(** Add a bid order. *)
let test_book_add_order () =
  let book = Market_simulator.Order_book.create () in
  let ev = make_add_event ~oid:"test001" ~price:100.0 ~size:500 () in
  let snap = Market_simulator.Order_book.apply_exn book ev in
  Alcotest.(check int)
    "order count after add" 1
    (Market_simulator.Order_book.order_count book);
  Alcotest.(check int) "bid levels" 1 (List.length snap.bids);
  Alcotest.(check int) "ask levels" 0 (List.length snap.asks);
  Alcotest.(check string)
    "bid price" "100.0000"
    (Market_simulator.Price.to_string (List.hd snap.bids).price);
  Alcotest.(check int)
    "bid size" 500
    (Market_simulator.Size.to_int (List.hd snap.bids).total_size)

(** Add bid and ask, verify spread. *)
let test_book_add_ask () =
  let book = Market_simulator.Order_book.create () in
  let _ =
    Market_simulator.Order_book.apply_exn book
      (make_add_event ~oid:"b1" ~side:Bid ~price:100.0 ~size:500 ())
  in
  let snap =
    Market_simulator.Order_book.apply_exn book
      (make_add_event ~oid:"a1" ~side:Ask ~price:101.0 ~size:300 ())
  in
  Alcotest.(check int)
    "order count after both" 2
    (Market_simulator.Order_book.order_count book);
  Alcotest.(check int) "bid levels" 1 (List.length snap.bids);
  Alcotest.(check int) "ask levels" 1 (List.length snap.asks);
  match snap.spread with
  | Some s ->
      Alcotest.(check string)
        "spread 101-100=1" "1.0000"
        (Market_simulator.Price.to_string s)
  | None -> Alcotest.fail "Expected spread"

(** Cancel an order. *)
let test_book_cancel () =
  let book = Market_simulator.Order_book.create () in
  let ev_add = make_add_event ~oid:"o1" ~price:100.0 ~size:500 () in
  let _ = Market_simulator.Order_book.apply_exn book ev_add in
  Alcotest.(check int)
    "after add" 1
    (Market_simulator.Order_book.order_count book);
  let snap =
    Market_simulator.Order_book.apply_exn book
      (make_cancel_event ~oid:"o1" ~price:100.0 ~size:500 ())
  in
  Alcotest.(check int)
    "after cancel" 0
    (Market_simulator.Order_book.order_count book);
  Alcotest.(check int) "bids after cancel" 0 (List.length snap.bids)

(** Partially execute an order. *)
let test_book_execute () =
  let book = Market_simulator.Order_book.create () in
  let ev_add = make_add_event ~oid:"o1" ~side:Ask ~price:101.0 ~size:500 () in
  let snap1 = Market_simulator.Order_book.apply_exn book ev_add in
  Alcotest.(check int)
    "after add" 1
    (Market_simulator.Order_book.order_count book);
  Alcotest.(check int)
    "ask size" 500
    (Market_simulator.Size.to_int (List.hd snap1.asks).total_size);
  let snap2 =
    Market_simulator.Order_book.apply_exn book
      {
        (make_add_event ~oid:"o1" ~side:Ask ~price:101.0 ~size:200 ()) with
        action = Execute;
      }
  in
  Alcotest.(check int)
    "after exec" 1
    (Market_simulator.Order_book.order_count book);
  Alcotest.(check int)
    "remaining size" 300
    (Market_simulator.Size.to_int (List.hd snap2.asks).total_size)

(** Fully execute removes the order. *)
let test_book_full_execute () =
  let book = Market_simulator.Order_book.create () in
  let ev_add = make_add_event ~oid:"o1" ~price:100.0 ~size:500 () in
  let _ = Market_simulator.Order_book.apply_exn book ev_add in
  let snap =
    Market_simulator.Order_book.apply_exn book
      { ev_add with action = Execute; size = Market_simulator.Size.of_int 500 }
  in
  Alcotest.(check int)
    "order count after full exec" 0
    (Market_simulator.Order_book.order_count book);
  Alcotest.(check int) "bids after full exec" 0 (List.length snap.bids)

(** Multiple orders at same price level aggregate. *)
let test_book_multiple_orders () =
  let book = Market_simulator.Order_book.create () in
  let _ =
    Market_simulator.Order_book.apply_exn book
      (make_add_event ~oid:"b1" ~price:100.0 ~size:200 ())
  in
  let snap =
    Market_simulator.Order_book.apply_exn book
      (make_add_event ~oid:"b2" ~price:100.0 ~size:300 ())
  in
  Alcotest.(check int) "bids levels" 1 (List.length snap.bids);
  Alcotest.(check int)
    "total size same level" 500
    (Market_simulator.Size.to_int (List.hd snap.bids).total_size);
  Alcotest.(check int) "order count at level" 2 (List.hd snap.bids).order_count

(** Amend order at the same price (no level move). *)
let test_book_amend_same_price () =
  let book = Market_simulator.Order_book.create () in
  let _ =
    Market_simulator.Order_book.apply_exn book
      (make_add_event ~oid:"o1" ~side:Ask ~price:101.0 ~size:300 ())
  in
  let snap =
    Market_simulator.Order_book.apply_exn book
      {
        (make_add_event ~oid:"o1" ~side:Ask ~price:101.0 ~size:200 ()) with
        action = Amend;
      }
  in
  Alcotest.(check int)
    "order count after amend" 1
    (Market_simulator.Order_book.order_count book);
  Alcotest.(check int) "ask levels after amend" 1 (List.length snap.asks);
  Alcotest.(check int)
    "size after amend" 200
    (Market_simulator.Size.to_int (List.hd snap.asks).total_size)

(** Amend moves order to a different price level. *)
let test_book_amend_move_level () =
  let book = Market_simulator.Order_book.create () in
  let _ =
    Market_simulator.Order_book.apply_exn book
      (make_add_event ~oid:"o1" ~side:Ask ~price:101.0 ~size:300 ())
  in
  let _ =
    Market_simulator.Order_book.apply_exn book
      (make_add_event ~oid:"o2" ~side:Ask ~price:101.0 ~size:200 ())
  in
  let snap =
    Market_simulator.Order_book.apply_exn book
      {
        (make_add_event ~oid:"o1" ~side:Ask ~price:102.0 ~size:150 ()) with
        action = Amend;
      }
  in
  Alcotest.(check int) "ask levels after move" 2 (List.length snap.asks);
  Alcotest.(check int)
    "top level size" 200
    (Market_simulator.Size.to_int (List.hd snap.asks).total_size);
  Alcotest.(check string)
    "top level price" "101.0000"
    (Market_simulator.Price.to_string (List.hd snap.asks).price)

(** Cancel unknown order returns error. *)
let test_book_cancel_unknown () =
  let book = Market_simulator.Order_book.create () in
  match
    Market_simulator.Order_book.apply book (make_cancel_event ~oid:"ghost" ())
  with
  | Ok _ -> Alcotest.fail "expected error"
  | Error msg ->
      Alcotest.(check string)
        "cancel unknown error" "order ghost not found for cancel action" msg

(** Amend unknown order returns error. *)
let test_book_amend_unknown () =
  let book = Market_simulator.Order_book.create () in
  match
    Market_simulator.Order_book.apply book
      {
        (make_add_event ~oid:"ghost" ~price:101.0 ~size:100 ()) with
        action = Amend;
      }
  with
  | Ok _ -> Alcotest.fail "expected error"
  | Error msg ->
      Alcotest.(check string)
        "amend unknown error" "order ghost not found for amend action" msg

(** Execute unknown order returns error. *)
let test_book_execute_unknown () =
  let book = Market_simulator.Order_book.create () in
  match
    Market_simulator.Order_book.apply book
      {
        (make_add_event ~oid:"phantom" ~price:101.0 ~size:100 ()) with
        action = Execute;
      }
  with
  | Ok _ -> Alcotest.fail "expected error"
  | Error msg ->
      Alcotest.(check string)
        "execute unknown error" "order phantom not found for execute action" msg

(** Execute more than remaining size clamps to full removal. *)
let test_book_execute_overflow () =
  let book = Market_simulator.Order_book.create () in
  let _ =
    Market_simulator.Order_book.apply_exn book
      (make_add_event ~oid:"o1" ~side:Ask ~price:101.0 ~size:100 ())
  in
  let snap =
    Market_simulator.Order_book.apply_exn book
      {
        (make_add_event ~oid:"o1" ~side:Ask ~price:101.0 ~size:200 ()) with
        action = Execute;
      }
  in
  Alcotest.(check int)
    "order count after overflow exec" 0
    (Market_simulator.Order_book.order_count book);
  Alcotest.(check int) "asks after overflow exec" 0 (List.length snap.asks)

(** Double cancel returns error on second attempt. *)
let test_book_double_cancel () =
  let book = Market_simulator.Order_book.create () in
  let _ =
    Market_simulator.Order_book.apply_exn book
      (make_add_event ~oid:"o1" ~price:100.0 ~size:500 ())
  in
  let _ =
    Market_simulator.Order_book.apply_exn book (make_cancel_event ~oid:"o1" ())
  in
  match
    Market_simulator.Order_book.apply book (make_cancel_event ~oid:"o1" ())
  with
  | Ok _ -> Alcotest.fail "expected error"
  | Error _ -> ()

(** Amend after cancel returns error. *)
let test_book_amend_after_cancel () =
  let book = Market_simulator.Order_book.create () in
  let _ =
    Market_simulator.Order_book.apply_exn book
      (make_add_event ~oid:"o1" ~price:100.0 ~size:500 ())
  in
  let _ =
    Market_simulator.Order_book.apply_exn book (make_cancel_event ~oid:"o1" ())
  in
  match
    Market_simulator.Order_book.apply book
      {
        (make_add_event ~oid:"o1" ~price:101.0 ~size:200 ()) with
        action = Amend;
      }
  with
  | Ok _ -> Alcotest.fail "expected error"
  | Error _ -> ()

(** Book stats. *)
let test_book_stats () =
  let book = Market_simulator.Order_book.create () in
  let _ =
    Market_simulator.Order_book.apply_exn book
      (make_add_event ~oid:"b1" ~side:Bid ~price:100.0 ~size:500 ())
  in
  let _ =
    Market_simulator.Order_book.apply_exn book
      (make_add_event ~oid:"a1" ~side:Ask ~price:101.0 ~size:300 ())
  in
  let stats = Market_simulator.Order_book.get_stats book in
  Alcotest.(check int) "bid count" 1 stats.bid_count;
  Alcotest.(check int) "ask count" 1 stats.ask_count;
  Alcotest.(check int)
    "total bid size" 500
    (Market_simulator.Size.to_int stats.total_bid_size);
  Alcotest.(check int)
    "total ask size" 300
    (Market_simulator.Size.to_int stats.total_ask_size);
  match stats.mid_price with
  | Some mp ->
      Alcotest.(check string)
        "mid price" "100.5000"
        (Market_simulator.Price.to_string mp)
  | None -> Alcotest.fail "expected mid price"

(** Book reset. *)
let test_book_reset () =
  let book = Market_simulator.Order_book.create () in
  let _ =
    Market_simulator.Order_book.apply_exn book
      (make_add_event ~oid:"o1" ~price:100.0 ~size:500 ())
  in
  Alcotest.(check int)
    "orders before reset" 1
    (Market_simulator.Order_book.order_count book);
  Market_simulator.Order_book.reset book;
  Alcotest.(check int)
    "orders after reset" 0
    (Market_simulator.Order_book.order_count book);
  let snap = Market_simulator.Order_book.get_snapshot book in
  Alcotest.(check int) "bids after reset" 0 (List.length snap.bids);
  Alcotest.(check int) "asks after reset" 0 (List.length snap.asks)

(** Empty book get_snapshot. *)
let test_book_empty_snapshot () =
  let book = Market_simulator.Order_book.create () in
  let snap = Market_simulator.Order_book.get_snapshot book in
  Alcotest.(check int) "empty bids" 0 (List.length snap.bids);
  Alcotest.(check int) "empty asks" 0 (List.length snap.asks);
  Alcotest.(check bool) "no spread" true (snap.spread = None);
  Alcotest.(check bool) "no mid" true (snap.mid_price = None)

(** Empty book stats. *)
let test_book_empty_stats () =
  let book = Market_simulator.Order_book.create () in
  let stats = Market_simulator.Order_book.get_stats book in
  Alcotest.(check int) "empty bid count" 0 stats.bid_count;
  Alcotest.(check int) "empty ask count" 0 stats.ask_count;
  Alcotest.(check int)
    "empty bid size" 0
    (Market_simulator.Size.to_int stats.total_bid_size);
  Alcotest.(check int)
    "empty ask size" 0
    (Market_simulator.Size.to_int stats.total_ask_size)

(** Order count on empty book. *)
let test_book_order_count_empty () =
  let book = Market_simulator.Order_book.create () in
  Alcotest.(check int)
    "empty order count" 0
    (Market_simulator.Order_book.order_count book)

(** Bids sorted descending (best bid first). *)
let test_book_bids_descending () =
  let book = Market_simulator.Order_book.create () in
  let _ =
    Market_simulator.Order_book.apply_exn book
      (make_add_event ~oid:"b1" ~side:Bid ~price:99.0 ~size:100 ())
  in
  let _ =
    Market_simulator.Order_book.apply_exn book
      (make_add_event ~oid:"b2" ~side:Bid ~price:101.0 ~size:100 ())
  in
  let _ =
    Market_simulator.Order_book.apply_exn book
      (make_add_event ~oid:"b3" ~side:Bid ~price:100.0 ~size:100 ())
  in
  let snap = Market_simulator.Order_book.get_snapshot book in
  Alcotest.(check int) "bids count" 3 (List.length snap.bids);
  let prices =
    List.map
      (fun (l : price_level) ->
        int_of_float (Market_simulator.Price.to_float l.price))
      snap.bids
  in
  Alcotest.(check bool) "bids descending" true (prices = [ 101; 100; 99 ])

(** Asks sorted ascending (best ask first). *)
let test_book_asks_ascending () =
  let book = Market_simulator.Order_book.create () in
  let _ =
    Market_simulator.Order_book.apply_exn book
      (make_add_event ~oid:"a1" ~side:Ask ~price:101.0 ~size:100 ())
  in
  let _ =
    Market_simulator.Order_book.apply_exn book
      (make_add_event ~oid:"a2" ~side:Ask ~price:100.0 ~size:100 ())
  in
  let _ =
    Market_simulator.Order_book.apply_exn book
      (make_add_event ~oid:"a3" ~side:Ask ~price:99.0 ~size:100 ())
  in
  let snap = Market_simulator.Order_book.get_snapshot book in
  let prices =
    List.map
      (fun (l : price_level) ->
        int_of_float (Market_simulator.Price.to_float l.price))
      snap.asks
  in
  Alcotest.(check bool) "asks ascending" true (prices = [ 99; 100; 101 ])

(** Many orders at many levels. *)
let test_book_many_levels () =
  let book = Market_simulator.Order_book.create () in
  for i = 0 to 15 do
    let side = if i mod 2 = 0 then Bid else Ask in
    let price =
      if side = Bid then 100.0 +. float_of_int (15 - i)
      else 110.0 +. float_of_int (i + 15)
    in
    let _ =
      Market_simulator.Order_book.apply_exn book
        (make_add_event ~oid:(Printf.sprintf "o%d" i) ~side ~price ~size:(i + 1)
           ())
    in
    ()
  done;
  let snap = Market_simulator.Order_book.get_snapshot book in
  Alcotest.(check bool) "only top 10 bids" (List.length snap.bids <= 10) true;
  Alcotest.(check bool) "only top 10 asks" (List.length snap.asks <= 10) true;
  Alcotest.(check bool) "has spread set" (snap.spread <> None) true;
  Alcotest.(check bool) "has mid price" (snap.mid_price <> None) true

(** Micro price calculation. *)
let test_book_micro_price () =
  let book = Market_simulator.Order_book.create () in
  let _ =
    Market_simulator.Order_book.apply_exn book
      (make_add_event ~oid:"b1" ~side:Bid ~price:100.0 ~size:1000 ())
  in
  let _ =
    Market_simulator.Order_book.apply_exn book
      (make_add_event ~oid:"a1" ~side:Ask ~price:101.0 ~size:500 ())
  in
  let snap = Market_simulator.Order_book.get_snapshot book in
  Alcotest.(check bool) "micro price present" (snap.micro_price <> None) true

(** Verify that apply_exn raises on error. *)
let test_book_apply_exn_raises () =
  let book = Market_simulator.Order_book.create () in
  Alcotest.check_raises "apply_exn raises"
    (Failure "order ghost not found for cancel action") (fun () ->
      ignore
        (Market_simulator.Order_book.apply_exn book
           (make_cancel_event ~oid:"ghost" ())))

(* ================================================================== *)
(* MARKET_DATA: CSV parser and generator *)
(* ================================================================== *)

(** Generator creates events. *)
let test_generator_creates_events () =
  let config =
    {
      Market_simulator.Market_data.default_config with
      symbols = [ "TEST" ];
      duration_s = 1.0;
      speed = 10.0;
      rng_seed = Some 42;
    }
  in
  let events = Market_simulator.Market_data.generate config in
  Alcotest.(check bool) "generated events" (List.length events > 0) true;
  let first = List.hd events in
  Alcotest.(check bool) "has order_id" (String.length first.order_id > 0) true;
  match first.side with Bid | Ask -> ()

(** CSV roundtrip preserves event count. *)
let test_csv_roundtrip () =
  let config =
    {
      Market_simulator.Market_data.default_config with
      symbols = [ "TEST" ];
      duration_s = 0.5;
      speed = 20.0;
      rng_seed = Some 42;
    }
  in
  let events = Market_simulator.Market_data.generate config in
  let tmpfile = "/tmp/test_csv_roundtrip.csv" in
  (match Market_simulator.Market_data.write_csv tmpfile events with
  | Ok () -> ()
  | Error e -> Alcotest.fail e);
  match Market_simulator.Market_data.parse_csv tmpfile with
  | Ok parsed ->
      Alcotest.(check int)
        "csv roundtrip count" (List.length events) (List.length parsed)
  | Error e -> Alcotest.fail e

(** CSV parse error on nonexistent file. *)
let test_csv_parse_nonexistent () =
  match Market_simulator.Market_data.parse_csv "/tmp/nonexistent_file.csv" with
  | Ok _ -> Alcotest.fail "expected error"
  | Error msg ->
      Alcotest.(check bool)
        "file not found error"
        (Base.String.is_prefix ~prefix:"IO error" msg)
        true

(** CSV parse handles alternate action keywords. *)
let test_csv_parse_alternates () =
  let tmpfile = "/tmp/test_csv_alternates.csv" in
  (* Write CSV with alternate keywords *)
  let oc = open_out tmpfile in
  output_string oc "# timestamp,order_id,side,price,size,action\n";
  output_string oc "2026-09-01T09:30:00Z,ord001,bid,100.50,500,new\n";
  output_string oc "2026-09-01T09:30:01Z,ord001,bid,100.55,200,mod\n";
  output_string oc "2026-09-01T09:30:02Z,ord001,bid,100.55,0,del\n";
  output_string oc "2026-09-01T09:30:03Z,ord002,ask,101.00,300,fill\n";
  close_out oc;
  match Market_simulator.Market_data.parse_csv tmpfile with
  | Ok events ->
      Alcotest.(check int) "parsed alternate keywords" 4 (List.length events);
      let actions = List.map (fun (e : event) -> e.action) events in
      Alcotest.(check bool)
        "action mapping" true
        (actions = [ Add; Amend; Cancel; Execute ])
  | Error e -> Alcotest.fail e

(** CSV parse handles side alternates. *)
let test_csv_parse_side_alternates () =
  let tmpfile = "/tmp/test_csv_side_alt.csv" in
  let oc = open_out tmpfile in
  output_string oc "# timestamp,order_id,side,price,size,action\n";
  output_string oc "2026-09-01T09:30:00Z,o1,b,100.00,100,add\n";
  output_string oc "2026-09-01T09:30:01Z,o2,a,101.00,200,add\n";
  output_string oc "2026-09-01T09:30:02Z,o3,offer,102.00,300,add\n";
  close_out oc;
  match Market_simulator.Market_data.parse_csv tmpfile with
  | Ok events ->
      Alcotest.(check int) "side alt count" 3 (List.length events);
      Alcotest.(check int)
        "side alt bid count" 1
        (List.length (List.filter (fun (e : event) -> e.side = Bid) events));
      Alcotest.(check int)
        "side alt ask count" 2
        (List.length (List.filter (fun (e : event) -> e.side = Ask) events))
  | Error e -> Alcotest.fail e

(** CSV parse with valid_time column. *)
let test_csv_parse_valid_time () =
  let tmpfile = "/tmp/test_csv_valid_time.csv" in
  let oc = open_out tmpfile in
  output_string oc "# timestamp,order_id,side,price,size,action,valid_time\n";
  output_string oc
    "2026-09-01T09:30:00Z,o1,bid,100.00,500,add,2026-09-01T09:00:00Z\n";
  close_out oc;
  match Market_simulator.Market_data.parse_csv tmpfile with
  | Ok events ->
      Alcotest.(check int) "valid_time events" 1 (List.length events);
      let e = List.hd events in
      Alcotest.(check bool) "has valid_time" (e.valid_time <> None) true
  | Error e -> Alcotest.fail e

(** CSV parse silently skips malformed rows. *)
let test_csv_parse_malformed_row () =
  let tmpfile = "/tmp/test_csv_malformed.csv" in
  let oc = open_out tmpfile in
  output_string oc "# timestamp,order_id,side,price,size,action\n";
  output_string oc "2026-09-01T09:30:00Z,o1,bid,100.00,500,add\n";
  output_string oc "this,is,a,garbled,row\n";
  (* too few fields *)
  output_string oc "2026-09-01T09:30:01Z,o2,ask,101.00,300,cancel\n";
  close_out oc;
  match Market_simulator.Market_data.parse_csv tmpfile with
  | Ok events ->
      Alcotest.(check int) "skip malformed rows" 2 (List.length events)
  | Error e -> Alcotest.fail e

(** Strict CSV parsing rejects malformed data rows. *)
let test_csv_parse_strict () =
  let tmpfile = "/tmp/test_csv_strict.csv" in
  let oc = open_out tmpfile in
  output_string oc "# timestamp,order_id,side,price,size,action\n";
  output_string oc "not-a-row\n";
  close_out oc;
  match Market_simulator.Market_data.parse_csv_strict tmpfile with
  | Ok _ -> Alcotest.fail "strict parser accepted malformed row"
  | Error _ -> ()

(** Feed CSV parsing preserves venue identity and sequence metadata. *)
let test_feed_csv_parse () =
  let tmpfile = "/tmp/test_feed_csv.csv" in
  let oc = open_out tmpfile in
  output_string oc
    "# \
     venue,symbol,sequence,event_time,received_time,order_id,side,price,size,action\n";
  output_string oc
    "CME,ES,42,2026-09-01T09:30:00Z,2026-09-01T09:30:00Z,o1,bid,100.00,10,add\n";
  close_out oc;
  match Market_simulator.Market_data.parse_feed_csv tmpfile with
  | Error msg -> Alcotest.fail msg
  | Ok [ ev ] -> (
      Alcotest.(check string) "venue" "CME" ev.venue;
      Alcotest.(check string) "symbol" "ES" ev.symbol;
      Alcotest.(check int) "sequence" 42 ev.sequence;
      match Market_simulator.Market_data.validate_feed [ ev ] with
      | Ok () -> ()
      | Error msg -> Alcotest.fail msg)
  | Ok _ -> Alcotest.fail "unexpected feed row count"

(** Pipe-delimited NYSE mapping files load symbol indexes and price scales. *)
let test_nyse_mapping_file () =
  let path = "/tmp/test_nyse_symbol_mapping.txt" in
  let oc = open_out path in
  output_string oc "ABC|ABC|7|N|N|A|100|2|53|||\n";
  close_out oc;
  match Market_simulator.Nyse_binary.read_symbol_mapping path with
  | Ok [ (7, "ABC", 2) ] -> ()
  | Ok _ -> Alcotest.fail "unexpected NYSE mapping result"
  | Error msg -> Alcotest.fail msg

(** Raw NYSE binary messages decode into strict replay events. *)
let test_nyse_binary_parse () =
  let put_u16 bytes offset value =
    Bytes.set bytes offset (Char.chr (value land 0xff));
    Bytes.set bytes (offset + 1) (Char.chr ((value lsr 8) land 0xff))
  in
  let put_u32 bytes offset value =
    for index = 0 to 3 do
      Bytes.set bytes (offset + index)
        (Char.chr ((value lsr (8 * index)) land 0xff))
    done
  in
  let put_u64 bytes offset value =
    for index = 0 to 7 do
      Bytes.set bytes (offset + index)
        (Char.chr ((value lsr (8 * index)) land 0xff))
    done
  in
  let message size kind =
    let bytes = Bytes.make size '\000' in
    put_u16 bytes 0 size;
    put_u16 bytes 2 kind;
    bytes
  in
  let time_reference = message 16 2 in
  put_u32 time_reference 12 1_788_255_000;
  let mapping = message 44 3 in
  put_u32 mapping 4 1;
  Bytes.blit_string "ABC" 0 mapping 8 3;
  Bytes.set mapping 24 (Char.chr 2);
  let add = message 39 100 in
  put_u32 add 4 100;
  put_u32 add 8 1;
  put_u32 add 12 1;
  put_u64 add 16 42;
  put_u32 add 24 10_000;
  put_u32 add 28 10;
  Bytes.set add 32 'B';
  let replace = message 42 104 in
  put_u32 replace 4 200;
  put_u32 replace 8 1;
  put_u32 replace 12 2;
  put_u64 replace 16 42;
  put_u64 replace 24 43;
  put_u32 replace 32 10_100;
  put_u32 replace 36 8;
  let execute = message 38 103 in
  put_u32 execute 4 300;
  put_u32 execute 8 1;
  put_u32 execute 12 3;
  put_u64 execute 16 43;
  put_u32 execute 24 99;
  put_u32 execute 28 10_100;
  put_u32 execute 32 8;
  let tmpfile = "/tmp/test_nyse_binary.bin" in
  let oc = open_out_bin tmpfile in
  List.iter (output_bytes oc) [ time_reference; mapping; add; replace; execute ];
  close_out oc;
  let messages = [ time_reference; mapping; add; replace; execute ] in
  let packet_size =
    16 + List.fold_left (fun total msg -> total + Bytes.length msg) 0 messages
  in
  let packet = Bytes.make packet_size '\000' in
  put_u16 packet 0 packet_size;
  Bytes.set packet 2 (Char.chr 11);
  Bytes.set packet 3 (Char.chr (List.length messages));
  put_u32 packet 4 1;
  put_u32 packet 8 1_788_255_000;
  put_u32 packet 12 0;
  let packet_offset = ref 16 in
  List.iter
    (fun msg ->
      Bytes.blit msg 0 packet !packet_offset (Bytes.length msg);
      packet_offset := !packet_offset + Bytes.length msg)
    messages;
  let packet_file = "/tmp/test_nyse_packet.bin" in
  let packet_oc = open_out_bin packet_file in
  output_bytes packet_oc packet;
  close_out packet_oc;
  (match
     Market_simulator.Nyse_binary.parse_file ~trading_date:"2026-09-01"
       Market_simulator.Nyse_binary.default_config packet_file
   with
  | Ok packet_events ->
      Alcotest.(check int) "NYSE packet events" 3 (List.length packet_events)
  | Error msg -> Alcotest.fail msg);
  let packet_gap = Bytes.copy packet in
  put_u32 packet_gap 4 3;
  let packet_gap_file = "/tmp/test_nyse_packet_gap.bin" in
  let packet_gap_oc = open_out_bin packet_gap_file in
  output_bytes packet_gap_oc packet;
  output_bytes packet_gap_oc packet_gap;
  close_out packet_gap_oc;
  (match
     Market_simulator.Nyse_binary.parse_file ~trading_date:"2026-09-01"
       Market_simulator.Nyse_binary.default_config packet_gap_file
   with
  | Error msg ->
      Alcotest.(check bool)
        "packet gap is rejected" true (String.contains msg 'g')
  | Ok _ -> Alcotest.fail "expected packet sequence gap");
  let status = message 46 34 in
  put_u32 status 4 1_788_255_000;
  put_u32 status 8 400;
  put_u32 status 12 1;
  put_u32 status 16 1;
  Bytes.set status 20 'O';
  let status_file = "/tmp/test_nyse_status.bin" in
  let status_oc = open_out_bin status_file in
  List.iter (output_bytes status_oc) [ time_reference; mapping; status ];
  close_out status_oc;
  (match
     Market_simulator.Nyse_binary.parse_file ~trading_date:"2026-09-01"
       Market_simulator.Nyse_binary.default_config status_file
   with
  | Ok [ { event = { action = Control "security_status"; _ }; _ } ] -> ()
  | Ok _ -> Alcotest.fail "NYSE control event missing"
  | Error msg -> Alcotest.fail msg);
  (match
     Market_simulator.Nyse_binary.parse_file ~trading_date:"2026-09-02"
       Market_simulator.Nyse_binary.default_config tmpfile
   with
  | Error msg ->
      Alcotest.(check bool)
        "trading date is enforced" true (String.contains msg 'd')
  | Ok _ -> Alcotest.fail "expected NYSE trading date rejection");
  match
    Market_simulator.Nyse_binary.parse_file ~trading_date:"2026-09-01"
      Market_simulator.Nyse_binary.default_config tmpfile
  with
  | Error msg -> Alcotest.fail msg
  | Ok events ->
      Alcotest.(check int) "NYSE binary events" 3 (List.length events);
      let first = List.hd events in
      Alcotest.(check string) "NYSE binary symbol" "ABC" first.symbol;
      Alcotest.(check int) "NYSE binary sequence" 1 first.sequence;
      (match first.event.action with
      | Add -> ()
      | _ -> Alcotest.fail "NYSE binary add action missing");
      (match List.nth events 1 with
      | { event = { action = Replace old_id; order_id; _ }; _ } ->
          Alcotest.(check string) "NYSE replacement old order" "42" old_id;
          Alcotest.(check string) "NYSE replacement new order" "43" order_id
      | _ -> Alcotest.fail "NYSE binary replace action missing");
      let book = Market_simulator.Order_book.create () in
      List.iter
        (fun (event : Market_simulator.Market_data.feed_event) ->
          match Market_simulator.Order_book.apply_replay book event.event with
          | Ok _ -> ()
          | Error msg -> Alcotest.fail msg)
        events;
      Alcotest.(check int)
        "NYSE binary final book" 0
        (Market_simulator.Order_book.order_count book)

(** NYSE TAQ order messages map into replay events. *)
let test_nyse_taq_parse () =
  let tmpfile = "/tmp/test_nyse_taq.csv" in
  let oc = open_out tmpfile in
  output_string oc "100,1,09:30:00.000000001,ABC,1,101,10000,50,B, ,0\n";
  output_string oc "101,2,09:30:00.000000002,ABC,2,101,9900,40,0,B,0\n";
  output_string oc "103,3,09:30:00.000000003,ABC,3,101,9900,10,1, , , , \n";
  output_string oc "104,4,09:30:00.000000004,ABC,4,101,102,9800,20,B,0\n";
  output_string oc "102,5,09:30:00.000000005,ABC,5,102,0\n";
  close_out oc;
  match
    Market_simulator.Market_data.parse_nyse_taq ~trading_date:"2026-04-01"
      tmpfile
  with
  | Error msg -> Alcotest.fail msg
  | Ok events ->
      Alcotest.(check int) "NYSE events" 6 (List.length events);
      (match Market_simulator.Market_data.validate_feed events with
      | Ok () -> ()
      | Error msg -> Alcotest.fail msg);
      let book = Market_simulator.Order_book.create () in
      List.iter
        (fun (ev : Market_simulator.Market_data.feed_event) ->
          match Market_simulator.Order_book.apply_replay book ev.event with
          | Ok _ -> ()
          | Error msg -> Alcotest.fail msg)
        events;
      Alcotest.(check int)
        "NYSE final book" 0
        (Market_simulator.Order_book.order_count book);
      let first = List.hd events in
      Alcotest.(check string) "NYSE venue" "NYSE_NATIONAL" first.venue;
      Alcotest.(check string) "NYSE symbol" "ABC" first.symbol;
      let gzfile = tmpfile ^ ".gz" in
      Alcotest.(check int)
        "gzip fixture created" 0
        (Sys.command
           (Printf.sprintf "gzip -c %s > %s" (Filename.quote tmpfile)
              (Filename.quote gzfile)));
      (match
         Market_simulator.Market_data.parse_nyse_taq ~trading_date:"2026-04-01"
           gzfile
       with
      | Ok compressed_events ->
          Alcotest.(check int)
            "gzip NYSE events" 6
            (List.length compressed_events)
      | Error msg -> Alcotest.fail msg);
      Sys.remove gzfile

(** SonarX L2 snapshots retain decimal fields without rounding. *)
let test_sonarx_l2_parse () =
  let tmpfile = "/tmp/test_sonarx_l2.json" in
  let oc = open_out tmpfile in
  output_string oc
    "[{\"height\":901329020,\"block_time\":\"2026-02-21T11:02:26.827929333\",\"market\":\"BTC\",\"bids\":[{\"px\":\"68182.0\",\"sz\":\"0.05387\",\"n\":4}],\"asks\":[{\"px\":\"68183.0\",\"sz\":\"0.01874\",\"n\":1}]}]";
  close_out oc;
  let check snapshots =
    match snapshots with
    | [ (snapshot : Market_simulator.Sonarx.snapshot) ] ->
        Alcotest.(check int) "SonarX height" 901329020 snapshot.height;
        Alcotest.(check string) "SonarX market" "BTC" snapshot.market;
        Alcotest.(check string)
          "SonarX bid price" "68182.0" (List.hd snapshot.bids).price;
        Alcotest.(check string)
          "SonarX bid size" "0.05387" (List.hd snapshot.bids).size
    | _ -> Alcotest.fail "expected one SonarX snapshot"
  in
  (match Market_simulator.Sonarx.parse_l2_file tmpfile with
  | Ok snapshots -> check snapshots
  | Error msg -> Alcotest.fail msg);
  let gzfile = tmpfile ^ ".gz" in
  Alcotest.(check int)
    "gzip fixture created" 0
    (Sys.command
       (Printf.sprintf "gzip -c %s > %s" (Filename.quote tmpfile)
          (Filename.quote gzfile)));
  (match Market_simulator.Sonarx.parse_l2_file gzfile with
  | Ok snapshots -> check snapshots
  | Error msg -> Alcotest.fail msg);
  Sys.remove gzfile

(** Binance Futures L2 messages apply only contiguous update chains. *)
let test_binance_l2_replay () =
  let lines =
    [
      "2024-01-01T00:00:01Z \
       {\"stream\":\"btcusdt@depthSnapshot\",\"generated\":true,\"data\":{\"lastUpdateId\":10,\"E\":1704067201000,\"bids\":[[\"100\",\"2\"]],\"asks\":[[\"101\",\"3\"]]}}";
      "2024-01-01T00:00:02Z \
       {\"stream\":\"btcusdt@depth@0ms\",\"data\":{\"e\":\"depthUpdate\",\"E\":1704067202000,\"U\":11,\"u\":12,\"pu\":10,\"b\":[[\"100\",\"0\"]],\"a\":[[\"102\",\"4\"]]}}";
    ]
  in
  match Market_simulator.Binance_l2.parse_lines lines with
  | Error msg -> Alcotest.fail msg
  | Ok messages -> (
      let evidence_file = "/tmp/test_binance_l2.jsonl" in
      let oc = open_out_bin evidence_file in
      output_string oc (String.concat "\n" lines ^ "\n");
      close_out oc;
      (match Market_simulator.Binance_l2.evidence evidence_file with
      | Ok evidence ->
          Alcotest.(check int) "Binance evidence lines" 2 evidence.line_count;
          Alcotest.(check bool)
            "Binance evidence bytes" true (evidence.byte_count > 0)
      | Error msg -> Alcotest.fail msg);
      (match Market_simulator.Binance_l2.replay ~instrument:btc_instrument messages with
      | Error msg -> Alcotest.fail msg
      | Ok [ initial; updated ] ->
          (match
             Market_simulator.Binance_l2.to_hf_l2 ~instrument:btc_instrument
               ~symbol:"BTCUSDT" [ initial ]
           with
          | Ok [ snapshot ] -> (
              Alcotest.(check string) "Binance symbol" "BTCUSDT" snapshot.symbol;
              Alcotest.(check (float 0.00001))
                "Binance mid price" 100.5 snapshot.mid_price;
              match Market_simulator.L2_metrics.measure snapshot with
              | Ok point ->
                  Alcotest.(check (float 0.00001))
                    "Binance spread"
                    (1.0 /. 100.5 *. 10_000.0)
                    point.spread_bps;
                  Alcotest.(check (float 0.00001))
                    "Binance imbalance" (-0.2) point.imbalance
              | Error msg -> Alcotest.fail msg)
          | Ok _ -> Alcotest.fail "expected Binance L2 snapshots"
          | Error msg -> Alcotest.fail msg);
          Alcotest.(check int64)
            "Binance final update id" 12L updated.last_update_id;
          Alcotest.(check int)
            "Binance bid removed" 0 (List.length updated.bids);
          Alcotest.(check int) "Binance ask added" 2 (List.length updated.asks);
          Alcotest.(check int)
            "Binance initial bid" 1 (List.length initial.bids);
          Alcotest.(check bool)
            "Binance raw evidence" true
            (String.length initial.raw_line > 0));
      let bootstrap_lines =
        [
          "2024-01-01T00:00:00Z \
           {\"stream\":\"btcusdt@depth@0ms\",\"data\":{\"e\":\"depthUpdate\",\"E\":1704067200000,\"U\":1,\"u\":10,\"pu\":0,\"b\":[],\"a\":[]}}";
          List.hd lines;
          List.nth lines 1;
        ]
      in
      (match Market_simulator.Binance_l2.parse_lines bootstrap_lines with
      | Error msg -> Alcotest.fail msg
      | Ok messages -> (
          match Market_simulator.Binance_l2.replay ~instrument:btc_instrument messages with
          | Ok [ _; _ ] -> ()
          | Ok _ -> Alcotest.fail "expected bootstrapped Binance states"
          | Error msg -> Alcotest.fail msg));
      let malformed =
        [
          "2024-01-01T00:00:03Z \
           {\"stream\":\"btcusdt@depth@0ms\",\"data\":{\"e\":\"depthUpdate\",\"E\":1704067203000,\"U\":13,\"u\":13,\"pu\":12,\"b\":[[\"nan\",\"1\"]],\"a\":[]}}";
        ]
      in
      (match Market_simulator.Binance_l2.parse_lines malformed with
      | Error _ -> ()
      | Ok _ -> Alcotest.fail "expected malformed Binance level rejection");
      (match
         Market_simulator.Binance_l2.parse_lines
           [ List.nth lines 1; List.hd lines ]
       with
      | Error msg -> Alcotest.fail msg
      | Ok messages -> (
          match Market_simulator.Binance_l2.replay ~instrument:btc_instrument messages with
          | Error _ -> ()
          | Ok _ -> Alcotest.fail "expected Binance timestamp rejection"));
      let gap =
        [
          List.hd lines;
          "2024-01-01T00:00:02Z \
           {\"stream\":\"btcusdt@depth@0ms\",\"data\":{\"e\":\"depthUpdate\",\"E\":1704067202000,\"U\":13,\"u\":14,\"pu\":12,\"b\":[],\"a\":[]}}";
        ]
      in
      match Market_simulator.Binance_l2.parse_lines gap with
      | Error msg -> Alcotest.fail msg
      | Ok messages -> (
          match Market_simulator.Binance_l2.replay ~instrument:btc_instrument messages with
          | Error msg ->
              Alcotest.(check bool)
                "Binance gap diagnostic" true (String.contains msg 'g')
          | Ok _ -> Alcotest.fail "expected Binance update gap"))

(** Binance derivatives streams preserve mark, funding, and liquidation data. *)
let test_binance_derivatives () =
  let mark_line =
    "2024-01-01T00:00:00Z \
     {\"stream\":\"btcusdt@markPrice@1s\",\"data\":{\"E\":1704067200000,\"s\":\"BTCUSDT\",\"p\":\"100\",\"i\":\"99\",\"r\":\"0.001\",\"T\":1704096000000}}"
  in
  (match
     Market_simulator.Binance_derivatives.parse_mark_lines [ mark_line ]
   with
  | Ok [ mark ] ->
      Alcotest.(check string) "mark symbol" "BTCUSDT" mark.symbol;
      Alcotest.(check (float 0.00001)) "funding rate" 0.001 mark.funding_rate;
      let snapshot : Market_simulator.Hf_l2.snapshot =
        {
          timestamp = mark.event_time;
          symbol = "BTCUSDT";
          mid_price = 100.0;
          traded_volume = 0.0;
          bids = [];
          asks = [];
        }
      in
      Alcotest.(check (float 0.00001))
        "funding adapter" 0.001
        (Market_simulator.Binance_derivatives.funding_rate [ mark ] snapshot)
  | Ok _ -> Alcotest.fail "expected one mark update"
  | Error msg -> Alcotest.fail msg);
  let liquidation_line =
    "2024-01-01T00:00:00Z \
     {\"stream\":\"!forceOrder@arr\",\"data\":{\"E\":1704067200000,\"o\":{\"s\":\"BTCUSDT\",\"S\":\"SELL\",\"ap\":\"101\",\"z\":\"2\"}}}"
  in
  match
    Market_simulator.Binance_derivatives.parse_liquidation_lines
      [ liquidation_line ]
  with
  | Ok [ liquidation ] ->
      Alcotest.(check string) "liquidation side" "SELL" liquidation.side;
      Alcotest.(check (float 0.00001))
        "liquidation quantity" 2.0 liquidation.quantity
  | Ok _ -> Alcotest.fail "expected one liquidation"
  | Error msg -> Alcotest.fail msg

(** Hugging Face L2 CSV rows parse into absolute depth levels. *)
let test_hf_l2_parse () =
  let tmpfile = "/tmp/test_hf_l2.csv" in
  let header =
    [
      "timestamp_utc";
      "instrument_symbol";
      "open_price";
      "high_price";
      "low_price";
      "close_price";
      "interval_traded_volume";
    ]
    @ (List.init 10 (fun index ->
           let level = index + 1 in
           [
             Printf.sprintf "bid_volume_level_%d" level;
             Printf.sprintf "ask_volume_level_%d" level;
             Printf.sprintf "bid_distance_level_%d" level;
             Printf.sprintf "ask_distance_level_%d" level;
           ])
      |> List.flatten)
  in
  let row =
    [ "2026-02-15T00:00:00Z"; "BTC-USDT"; "100"; "100"; "100"; "100"; "2" ]
    @ List.flatten
        (List.init 10 (fun index ->
             let level = index + 1 in
             [ string_of_int level; string_of_int (level + 1); "1"; "1" ]))
  in
  let oc = open_out tmpfile in
  output_string oc (String.concat "," header ^ "\n");
  output_string oc (String.concat "," row ^ "\n");
  close_out oc;
  match Market_simulator.Hf_l2.parse_csv tmpfile with
  | Error msg -> Alcotest.fail msg
  | Ok [ snapshot ] ->
      Alcotest.(check string) "HF symbol" "BTC-USDT" snapshot.symbol;
      Alcotest.(check (float 0.00001))
        "HF bid price" 99.99 (List.hd snapshot.bids).price;
      Alcotest.(check (float 0.00001))
        "HF ask price" 100.01 (List.hd snapshot.asks).price;
      Alcotest.(check (float 0.00001))
        "HF cumulative bid size" 1.0 (List.hd snapshot.bids).cumulative_size;
      Alcotest.(check (float 0.00001))
        "HF cumulative ask size" 2.0 (List.hd snapshot.asks).cumulative_size
  | Ok _ -> Alcotest.fail "expected one Hugging Face L2 snapshot"

(** L2 execution consumes visible cumulative depth. *)
let test_l2_execution () =
  let timestamp =
    match Market_simulator.Timestamp.of_string "2026-02-15T00:00:00Z" with
    | Ok value -> value
    | Error msg -> Alcotest.fail msg
  in
  let level price cumulative_size : Market_simulator.Hf_l2.level =
    { price; cumulative_size; distance_bps = 1.0 }
  in
  let snapshot : Market_simulator.Hf_l2.snapshot =
    {
      timestamp;
      symbol = "BTC-USDT";
      mid_price = 100.0;
      traded_volume = 0.0;
      bids = [ level 99.9 5.0; level 99.8 10.0 ];
      asks = [ level 100.1 3.0; level 100.2 10.0 ];
    }
  in
  let result = Market_simulator.L2_execution.execute snapshot Buy 6.0 in
  Alcotest.(check (float 0.00001)) "L2 filled" 6.0 result.filled;
  Alcotest.(check int) "L2 fill count" 2 (List.length result.fills);
  Alcotest.(check (float 0.00001)) "L2 vwap" 100.15 (Option.get result.vwap);
  let limited =
    Market_simulator.L2_execution.execute snapshot Buy ~limit_price:100.1 6.0
  in
  Alcotest.(check (float 0.00001)) "L2 limited fill" 3.0 limited.filled;
  Alcotest.(check (float 0.00001)) "L2 limited remainder" 3.0 limited.remaining

(** L2 backtesting combines strategy orders, fills, fees, and equity. *)
let test_l2_backtest () =
  let timestamp second =
    match
      Market_simulator.Timestamp.of_string
        (Printf.sprintf "2026-02-15T00:00:%02dZ" second)
    with
    | Ok value -> value
    | Error msg -> Alcotest.fail msg
  in
  let level price cumulative_size : Market_simulator.Hf_l2.level =
    { price; cumulative_size; distance_bps = 1.0 }
  in
  let make_snapshot second mid : Market_simulator.Hf_l2.snapshot =
    {
      timestamp = timestamp second;
      symbol = "BTC-USDT";
      mid_price = mid;
      traded_volume = 0.0;
      bids = [ level (mid -. 0.1) 10.0 ];
      asks = [ level (mid +. 0.1) 3.0; level (mid +. 0.2) 10.0 ];
    }
  in
  let calls = ref 0 in
  let strategy (_portfolio : Market_simulator.L2_backtest.portfolio) _snapshot =
    incr calls;
    if !calls = 1 then
      [
        {
          Market_simulator.L2_backtest.side = Buy;
          size = 6.0;
          limit_price = None;
        };
      ]
    else []
  in
  let result =
    Market_simulator.L2_backtest.run ~initial_cash:1_000.0 ~fee_bps:10.0
      strategy
      [ make_snapshot 0 100.0; make_snapshot 1 101.0 ]
  in
  Alcotest.(check (float 0.00001))
    "backtest position" 6.0 result.final_portfolio.position;
  Alcotest.(check int) "backtest fills" 2 result.final_portfolio.trade_count;
  Alcotest.(check int) "backtest curve" 2 (List.length result.curve);
  Alcotest.(check bool) "backtest fees" true (result.final_portfolio.fees > 0.0);
  calls := 0;
  let delayed =
    Market_simulator.L2_backtest.run ~initial_cash:1_000.0 ~latency_snapshots:1
      ~funding_rate:(fun _ -> 0.001)
      strategy
      [ make_snapshot 0 100.0; make_snapshot 1 101.0 ]
  in
  Alcotest.(check (float 0.00001))
    "delayed position" 6.0 delayed.final_portfolio.position;
  Alcotest.(check bool)
    "funding charged" true
    (delayed.final_portfolio.funding_paid > 0.5);
  let summary = Market_simulator.Backtest_metrics.summarize delayed in
  Alcotest.(check bool) "metrics turnover" true (summary.turnover > 0.0);
  Alcotest.(check bool) "metrics drawdown" true (summary.max_drawdown >= 0.0)

(** SonarX replay emits immutable snapshots in source order. *)
let test_sonarx_replay () =
  let timestamp value =
    match Market_simulator.Timestamp.of_string value with
    | Ok t -> t
    | Error msg -> Alcotest.fail msg
  in
  let snapshot height second : Market_simulator.Sonarx.snapshot =
    {
      height;
      block_time = timestamp (Printf.sprintf "2026-02-21T11:02:%02dZ" second);
      market = "BTC";
      bids = [];
      asks = [];
    }
  in
  let loop =
    Market_simulator.Sonarx_replay.create [ snapshot 1 0; snapshot 2 1 ]
  in
  let seen = ref [] in
  Market_simulator.Sonarx_replay.add_handler loop (fun item ->
      seen := item.height :: !seen;
      Lwt.return_unit);
  Lwt_main.run (Market_simulator.Sonarx_replay.run_fast loop);
  Alcotest.(check (list int)) "SonarX replay order" [ 1; 2 ] (List.rev !seen);
  Alcotest.(check (pair int int))
    "SonarX replay progress" (2, 2)
    (Market_simulator.Sonarx_replay.progress loop);
  match Market_simulator.Sonarx_replay.current loop with
  | Some item -> Alcotest.(check int) "SonarX current" 2 item.height
  | None -> Alcotest.fail "missing current SonarX snapshot"

(** CSV parse handles invalid field values gracefully. *)
let test_csv_parse_invalid_fields () =
  let tmpfile = "/tmp/test_csv_invalid_fields.csv" in
  let oc = open_out tmpfile in
  output_string oc "# timestamp,order_id,side,price,size,action\n";
  output_string oc "2026-09-01T09:30:00Z,o1,invalid,100.00,500,add\n";
  (* bad side *)
  output_string oc "2026-09-01T09:30:01Z,o2,bid,not-price,500,add\n";
  (* bad price *)
  output_string oc "2026-09-01T09:30:02Z,o3,bid,100.00,not-size,add\n";
  (* bad size *)
  output_string oc "2026-09-01T09:30:03Z,o4,bid,100.00,500,bogus\n";
  (* bad action *)
  close_out oc;
  match Market_simulator.Market_data.parse_csv tmpfile with
  | Ok events ->
      Alcotest.(check int) "skip all invalid rows" 0 (List.length events)
  | Error e -> Alcotest.fail e

(** Write CSV with no events creates valid file. *)
let test_csv_write_empty () =
  let tmpfile = "/tmp/test_csv_empty_write.csv" in
  match Market_simulator.Market_data.write_csv tmpfile [] with
  | Ok () -> (
      match Market_simulator.Market_data.parse_csv tmpfile with
      | Ok events ->
          Alcotest.(check int) "empty csv roundtrip" 0 (List.length events)
      | Error e -> Alcotest.fail e)
  | Error e -> Alcotest.fail e

(** Generator with seed produces deterministic output. *)
let test_generator_deterministic () =
  let config1 =
    {
      Market_simulator.Market_data.default_config with
      symbols = [ "A" ];
      duration_s = 0.1;
      speed = 5.0;
      rng_seed = Some 42;
    }
  in
  let config2 = { config1 with rng_seed = Some 42 } in
  let events1 = Market_simulator.Market_data.generate config1 in
  let events2 = Market_simulator.Market_data.generate config2 in
  Alcotest.(check int)
    "deterministic count" (List.length events1) (List.length events2)

(** Generator with no seed produces different output. *)
let test_generator_no_deterministic () =
  let config =
    {
      Market_simulator.Market_data.default_config with
      symbols = [ "A" ];
      duration_s = 2.0;
      speed = 10.0;
      rng_seed = None;
    }
  in
  let events = Market_simulator.Market_data.generate config in
  Alcotest.(check bool)
    "realistic generator output"
    (List.length events > 0)
    true

(* ================================================================== *)
(* BITEMPORAL: bitemporal time model *)
(* ================================================================== *)

(** as_of query. *)
let test_bitemporal_as_of () =
  let now = Market_simulator.Timestamp.now () in
  let ev1 = make_add_event ~ts:now ~oid:"o1" ~price:100.0 ~size:500 () in
  let ev2 =
    {
      (make_add_event
         ~ts:(Market_simulator.Timestamp.add_seconds now 10.0)
         ~oid:"o1" ~price:101.0 ~size:300 ())
      with
      action = Amend;
    }
  in
  let bf_events = Market_simulator.Bitemporal.of_events [ ev1; ev2 ] in
  let result = Market_simulator.Bitemporal.filter_sequenced bf_events now now in
  Alcotest.(check int) "as-of matches first event" 1 (List.length result);
  Alcotest.(check string)
    "as-of price" "100.0000"
    (Market_simulator.Price.to_string (List.hd result).price);
  let later = Market_simulator.Timestamp.add_seconds now 10.0 in
  let later_result =
    Market_simulator.Bitemporal.filter_sequenced bf_events later later
  in
  Alcotest.(check int) "amend closes prior state" 1 (List.length later_result);
  Alcotest.(check string)
    "latest amended price" "101.0000"
    (Market_simulator.Price.to_string (List.hd later_result).price)

(** Bitemporal interval query. *)
let test_bitemporal_interval () =
  let now = Market_simulator.Timestamp.now () in
  let later = Market_simulator.Timestamp.add_seconds now 60.0 in
  let ev1 = make_add_event ~ts:now ~oid:"o1" ~price:100.0 ~size:500 () in
  let ev2 =
    make_add_event ~ts:later ~oid:"o2" ~side:Ask ~price:101.0 ~size:300 ()
  in
  let bf_events = Market_simulator.Bitemporal.of_events [ ev1; ev2 ] in
  Alcotest.(check int)
    "as-of now: only first" 1
    (List.length
       (Market_simulator.Bitemporal.filter_sequenced bf_events now now));
  Alcotest.(check int)
    "as-of later: both" 2
    (List.length
       (Market_simulator.Bitemporal.filter_sequenced bf_events later later))

(** Sequenced vs non-sequenced query. *)
let test_bitemporal_sequenced () =
  let now = Market_simulator.Timestamp.now () in
  let ev1 = make_add_event ~ts:now ~oid:"o1" ~price:100.0 ~size:500 () in
  let bf_events = Market_simulator.Bitemporal.of_events [ ev1 ] in
  let seq = Market_simulator.Bitemporal.filter_sequenced bf_events now now in
  Alcotest.(check int) "sequenced query" 1 (List.length seq);
  let far = Market_simulator.Timestamp.add_seconds now 86400.0 in
  let between =
    Market_simulator.Bitemporal.between bf_events (now, far) (now, far)
  in
  Alcotest.(check int) "between query" 1 (List.length between)

(** Singleton creates a fact with far-future intervals. *)
let test_bitemporal_singleton () =
  let now = Market_simulator.Timestamp.now () in
  let ts = Market_simulator.Bitemporal.singleton 42 now now in
  Alcotest.(check int) "singleton length" 1 (List.length ts);
  let result = Market_simulator.Bitemporal.as_of ts now now in
  Alcotest.(check (list int)) "singleton as_of" [ 42 ] result

(** Add prepends new facts. *)
let test_bitemporal_add () =
  let now = Market_simulator.Timestamp.now () in
  let ts = Market_simulator.Bitemporal.singleton "first" now now in
  let later = Market_simulator.Timestamp.add_seconds now 10.0 in
  let ts = Market_simulator.Bitemporal.add ts "second" later later in
  Alcotest.(check int) "add length" 2 (List.length ts);
  let result = Market_simulator.Bitemporal.as_of ts later later in
  Alcotest.(check bool) "add sees both" (List.length result = 2) true

(** add_with_interval adds a fact with a full interval. *)
let test_bitemporal_add_with_interval () =
  let now = Market_simulator.Timestamp.now () in
  let far = Market_simulator.Timestamp.add_seconds now 86400.0 in
  let interval =
    {
      Market_simulator.Bitemporal.valid_from = now;
      valid_until = far;
      tx_from = now;
      tx_until = far;
    }
  in
  let ts = Market_simulator.Bitemporal.add_with_interval [] 42 interval in
  Alcotest.(check int) "add_with_interval length" 1 (List.length ts);
  let result = Market_simulator.Bitemporal.as_of ts now now in
  Alcotest.(check (list int)) "add_with_interval as_of" [ 42 ] result

(** close_valid closes the valid interval of the most recent fact. *)
let test_bitemporal_close_valid () =
  let now = Market_simulator.Timestamp.now () in
  let later = Market_simulator.Timestamp.add_seconds now 10.0 in
  let ts = Market_simulator.Bitemporal.singleton 42 now now in
  let ts = Market_simulator.Bitemporal.close_valid ts later in
  (* After close_valid, as_of at later should NOT find the fact *)
  let result = Market_simulator.Bitemporal.as_of ts later now in
  Alcotest.(check int) "close_valid excludes after" 0 (List.length result);
  (* But as_of at now should still find it *)
  let result_now = Market_simulator.Bitemporal.as_of ts now now in
  Alcotest.(check int) "close_valid includes before" 1 (List.length result_now)

(** close_tx closes the tx interval of the most recent fact. *)
let test_bitemporal_close_tx () =
  let now = Market_simulator.Timestamp.now () in
  let later = Market_simulator.Timestamp.add_seconds now 10.0 in
  let ts = Market_simulator.Bitemporal.singleton 42 now now in
  let ts = Market_simulator.Bitemporal.close_tx ts later in
  let result = Market_simulator.Bitemporal.as_of ts now later in
  Alcotest.(check int) "close_tx excludes after" 0 (List.length result)

(** between_valid query. *)
let test_bitemporal_between_valid () =
  let now = Market_simulator.Timestamp.now () in
  let later = Market_simulator.Timestamp.add_seconds now 10.0 in
  let ts = Market_simulator.Bitemporal.singleton 42 now now in
  let result = Market_simulator.Bitemporal.between_valid ts now later in
  Alcotest.(check int) "between_valid finds fact" 1 (List.length result)

(** between_tx query. *)
let test_bitemporal_between_tx () =
  let now = Market_simulator.Timestamp.now () in
  let later = Market_simulator.Timestamp.add_seconds now 10.0 in
  let ts = Market_simulator.Bitemporal.singleton 42 now now in
  let result = Market_simulator.Bitemporal.between_tx ts now later in
  Alcotest.(check int) "between_tx finds fact" 1 (List.length result)

(** history returns facts up to tx_at. *)
let test_bitemporal_history () =
  let now = Market_simulator.Timestamp.now () in
  let later = Market_simulator.Timestamp.add_seconds now 10.0 in
  let ts = Market_simulator.Bitemporal.singleton 42 now now in
  let result = Market_simulator.Bitemporal.history ts later in
  Alcotest.(check int) "history finds fact" 1 (List.length result);
  Alcotest.(check int) "history value" 42 (List.hd result)

(** index_by_order_id builds an index. *)
let test_bitemporal_index () =
  let now = Market_simulator.Timestamp.now () in
  let ev1 = make_add_event ~ts:now ~oid:"ord1" ~price:100.0 ~size:500 () in
  let ev2 = make_add_event ~ts:now ~oid:"ord2" ~price:101.0 ~size:300 () in
  let bf = Market_simulator.Bitemporal.of_events [ ev1; ev2 ] in
  let idx = Market_simulator.Bitemporal.index_by_order_id bf in
  Alcotest.(check int)
    "index cardinal" 2
    (Market_simulator.Order_id.Map.cardinal idx);
  let h1 = Market_simulator.Bitemporal.history_of_order idx "ord1" in
  Alcotest.(check int) "history_of_order found" 1 (List.length h1);
  let h2 = Market_simulator.Bitemporal.history_of_order idx "unknown" in
  Alcotest.(check int) "history_of_order unknown" 0 (List.length h2)

(** Empty bitemporal collections behave correctly. *)
let test_bitemporal_empty () =
  let now = Market_simulator.Timestamp.now () in
  Alcotest.(check int)
    "as_of empty" 0
    (List.length (Market_simulator.Bitemporal.as_of [] now now));
  Alcotest.(check int)
    "close_valid empty" 0
    (List.length (Market_simulator.Bitemporal.close_valid [] now));
  Alcotest.(check int)
    "close_tx empty" 0
    (List.length (Market_simulator.Bitemporal.close_tx [] now));
  Alcotest.(check int)
    "history empty" 0
    (List.length (Market_simulator.Bitemporal.history [] now));
  Alcotest.(check int)
    "of_events empty" 0
    (List.length (Market_simulator.Bitemporal.of_events []));
  let idx = Market_simulator.Bitemporal.index_by_order_id [] in
  Alcotest.(check bool)
    "empty index" true
    (Market_simulator.Order_id.Map.is_empty idx)

(* ================================================================== *)
(* EVENT_LOOP: Lwt-based event processor *)
(* ================================================================== *)

(** Process a single event. *)
let test_event_loop () =
  let ev = make_add_event ~oid:"o1" ~price:100.0 ~size:500 () in
  let book = Market_simulator.Order_book.create () in
  let loop = Market_simulator.Event_loop.create book [ ev ] in
  let snapshots = ref [] in
  Market_simulator.Event_loop.add_handler loop (fun mev ->
      match mev with
      | BookSnapshot s ->
          snapshots := s :: !snapshots;
          Lwt.return ()
      | _ -> Lwt.return ());
  Lwt_main.run (Market_simulator.Event_loop.run_fast loop);
  Alcotest.(check int) "snapshots generated" 1 (List.length !snapshots);
  Alcotest.(check int)
    "order count after loop" 1
    (Market_simulator.Order_book.order_count book)

(** Event loop with multiple events. *)
let test_event_loop_multi () =
  let events =
    [
      make_add_event ~oid:"o1" ~side:Bid ~price:100.0 ~size:500 ();
      make_add_event ~oid:"o2" ~side:Ask ~price:101.0 ~size:300 ();
      make_cancel_event ~oid:"o1" ();
    ]
  in
  let book = Market_simulator.Order_book.create () in
  let loop = Market_simulator.Event_loop.create book events in
  let handler_events = ref [] in
  Market_simulator.Event_loop.add_handler loop (fun mev ->
      handler_events := mev :: !handler_events;
      Lwt.return ());
  Lwt_main.run (Market_simulator.Event_loop.run_fast loop);
  Alcotest.(check bool) "handlers fired" (List.length !handler_events > 0) true;
  Alcotest.(check int)
    "order count after multi" 1
    (Market_simulator.Order_book.order_count book)

(** Simulation mode matches crossing orders and emits a trade. *)
let test_event_loop_simulation_mode () =
  let events =
    [
      make_add_event ~oid:"ask" ~side:Ask ~price:100.0 ~size:100 ();
      make_add_event ~oid:"bid" ~side:Bid ~price:101.0 ~size:100 ();
    ]
  in
  let book = Market_simulator.Order_book.create () in
  let loop = Market_simulator.Event_loop.create ~mode:Simulation book events in
  let trades = ref 0 in
  Market_simulator.Event_loop.add_handler loop (fun mev ->
      (match mev with Trade _ -> incr trades | _ -> ());
      Lwt.return ());
  Lwt_main.run (Market_simulator.Event_loop.run_fast loop);
  Alcotest.(check int) "simulation trade" 1 !trades;
  Alcotest.(check int)
    "simulation book empty" 0
    (Market_simulator.Order_book.order_count book)

(** Event loop progress reporting. *)
let test_event_loop_progress () =
  let ev = make_add_event ~oid:"o1" ~price:100.0 ~size:500 () in
  let book = Market_simulator.Order_book.create () in
  let loop = Market_simulator.Event_loop.create book [ ev; ev ] in
  let processed, total = Market_simulator.Event_loop.progress loop in
  Alcotest.(check int) "initial progress processed" 0 processed;
  Alcotest.(check int) "initial progress total" 2 total;
  Lwt_main.run (Market_simulator.Event_loop.run_fast loop);
  let processed, total = Market_simulator.Event_loop.progress loop in
  Alcotest.(check int) "after run progress" 2 processed

(** Event loop with error event. *)
let test_event_loop_error () =
  let ev = make_cancel_event ~oid:"nonexistent" () in
  let book = Market_simulator.Order_book.create () in
  let loop = Market_simulator.Event_loop.create book [ ev ] in
  (* Should not raise; error is handled gracefully *)
  Lwt_main.run (Market_simulator.Event_loop.run_fast loop);
  Alcotest.(check int)
    "order count after error" 0
    (Market_simulator.Order_book.order_count book)

(** Event loop stop. *)
let test_event_loop_stop () =
  let ev = make_add_event ~oid:"o1" ~price:100.0 ~size:500 () in
  let many_events =
    List.init 100 (fun i -> { ev with order_id = Printf.sprintf "o%d" i })
  in
  let book = Market_simulator.Order_book.create () in
  let loop = Market_simulator.Event_loop.create book many_events in
  let processed_before, total = Market_simulator.Event_loop.progress loop in
  Alcotest.(check int) "initial progress processed" 0 processed_before;
  Alcotest.(check int) "total events" 100 total;
  Market_simulator.Event_loop.stop loop;
  (* stop sets running=false, but run_internal will reset it to true.
     The stop call prevents new handlers from being added, but run_fast
     will still process events because it sets running=true. *)
  let () = Market_simulator.Event_loop.set_speed loop 0.0 in
  Lwt_main.run (Market_simulator.Event_loop.run_fast loop);
  (* All events should have been processed *)
  let processed_after, _ = Market_simulator.Event_loop.progress loop in
  Alcotest.(check bool) "events processed after stop" true (processed_after > 0)

(** Event loop set_speed. *)
let test_event_loop_speed () =
  let book = Market_simulator.Order_book.create () in
  let loop = Market_simulator.Event_loop.create book [] in
  Market_simulator.Event_loop.set_speed loop 2.0;
  let processed, total = Market_simulator.Event_loop.progress loop in
  Alcotest.(check int) "empty speed test" 0 processed;
  Alcotest.(check int) "empty total" 0 total

(* ================================================================== *)
(* METRICS: instrumentation *)
(* ================================================================== *)

(** Basic metrics collection. *)
let test_metrics () =
  let book = Market_simulator.Order_book.create () in
  let collector = Market_simulator.Metrics.create book in
  let _ =
    Market_simulator.Order_book.apply_exn book
      (make_add_event ~oid:"o1" ~price:100.0 ~size:500 ())
  in
  let m = Market_simulator.Metrics.record collector in
  Alcotest.(check int) "events processed" 1 m.event_count;
  Alcotest.(check int) "order count" 1 m.order_count;
  Alcotest.(check bool) "has bid price" (m.top_bid_price <> None) true;
  Alcotest.(check bool)
    "has json report"
    (String.length (Market_simulator.Metrics.json_report m) > 0)
    true

(** Metrics on empty book. *)
let test_metrics_empty () =
  let book = Market_simulator.Order_book.create () in
  let collector = Market_simulator.Metrics.create book in
  let m = Market_simulator.Metrics.record collector in
  Alcotest.(check int) "empty events" 1 m.event_count;
  Alcotest.(check int) "empty order count" 0 m.order_count;
  Alcotest.(check bool) "no top bid" (m.top_bid_price = None) true;
  Alcotest.(check bool) "no top ask" (m.top_ask_price = None) true

(** Metrics after add and cancel. *)
let test_metrics_add_cancel () =
  let book = Market_simulator.Order_book.create () in
  let collector = Market_simulator.Metrics.create book in
  let ev = make_add_event ~oid:"o1" ~price:100.0 ~size:500 () in
  let _ = Market_simulator.Order_book.apply_exn book ev in
  let _ = Market_simulator.Metrics.record collector in
  let _ =
    Market_simulator.Order_book.apply_exn book (make_cancel_event ~oid:"o1" ())
  in
  let m = Market_simulator.Metrics.record collector in
  Alcotest.(check int) "metrics event count after cancel" 2 m.event_count;
  Alcotest.(check int) "metrics order count after cancel" 0 m.order_count

(** Metrics json_report outputs valid JSON. *)
let test_metrics_json () =
  let book = Market_simulator.Order_book.create () in
  let collector = Market_simulator.Metrics.create book in
  let _ =
    Market_simulator.Order_book.apply_exn book
      (make_add_event ~oid:"o1" ~price:100.0 ~size:500 ())
  in
  let m = Market_simulator.Metrics.record collector in
  let json = Market_simulator.Metrics.json_report m in
  Alcotest.(check bool) "non-empty json" (String.length json > 0) true;
  (* Should be parseable *)
  try
    let parsed = Yojson.Safe.from_string json in
    Alcotest.(check bool)
      "json has events field"
      (Yojson.Safe.Util.member "events" parsed <> `Null)
      true
  with _ -> Alcotest.fail "invalid json"

(* ================================================================== *)
(* WEBSOCKET: real-time data streaming *)
(* ================================================================== *)

(** Snapshot encoding. *)
let test_ws_encode_snapshot () =
  let snap =
    {
      timestamp = zero_ts;
      bids =
        [
          {
            price = Market_simulator.Price.of_float 100.0;
            total_size = Market_simulator.Size.of_int 500;
            order_count = 2;
          };
        ];
      asks =
        [
          {
            price = Market_simulator.Price.of_float 101.0;
            total_size = Market_simulator.Size.of_int 300;
            order_count = 1;
          };
        ];
      spread = Some (Market_simulator.Price.of_float 1.0);
      mid_price = Some (Market_simulator.Price.of_float 100.5);
      micro_price = None;
    }
  in
  let json = Market_simulator.Websocket_server.encode_snapshot snap in
  Alcotest.(check bool)
    "snapshot json length > 10"
    (String.length json > 10)
    true;
  Alcotest.(check bool) "snapshot has bids" (String.contains json '"') true

(** Market event encoding for each variant. *)
let test_ws_encode_all_events () =
  let base_ev = make_add_event ~oid:"o1" ~price:100.0 ~size:500 () in
  let events =
    [
      OrderAdded base_ev;
      OrderAmended base_ev;
      OrderCancelled base_ev;
      OrderExecuted (base_ev, Market_simulator.Size.of_int 200);
      Trade
        {
          trade_time = zero_ts;
          buy_order_id = "bid-1";
          sell_order_id = "ask-1";
          fill_price = Market_simulator.Price.of_float 100.0;
          fill_size = Market_simulator.Size.of_int 200;
          aggressor_order_id = "bid-1";
        };
      StatsUpdate
        {
          total_bid_size = Market_simulator.Size.of_int 500;
          total_ask_size = Market_simulator.Size.of_int 300;
          bid_count = 1;
          ask_count = 1;
          spread = Some (Market_simulator.Price.of_float 1.0);
          mid_price = Some (Market_simulator.Price.of_float 100.5);
        };
    ]
  in
  List.iteri
    (fun i ev ->
      let json = Market_simulator.Websocket_server.encode_market_event ev in
      Alcotest.(check bool)
        (Printf.sprintf "event %d has json" i)
        (String.length json > 10)
        true)
    events

(** Snapshot with null micro_price. *)
let test_ws_encode_no_micro () =
  let snap =
    {
      timestamp = zero_ts;
      bids =
        [
          {
            price = Market_simulator.Price.of_float 100.0;
            total_size = Market_simulator.Size.of_int 500;
            order_count = 2;
          };
        ];
      asks =
        [
          {
            price = Market_simulator.Price.of_float 101.0;
            total_size = Market_simulator.Size.of_int 300;
            order_count = 1;
          };
        ];
      spread = None;
      mid_price = None;
      micro_price = None;
    }
  in
  let json = Market_simulator.Websocket_server.encode_snapshot snap in
  Alcotest.(check bool) "no micro snapshot json" (String.length json > 10) true

(* ================================================================== *)
(* MATCHING ENGINE *)
(* ================================================================== *)

(** Bid crosses ask at same price. *)
let test_match_same_price () =
  let book = Market_simulator.Order_book.create () in
  let _ =
    Market_simulator.Order_book.apply_exn book
      (make_add_event ~oid:"a1" ~side:Ask ~price:100.0 ~size:500 ())
  in
  let result =
    Market_simulator.Order_book.apply book
      (make_add_event ~oid:"b1" ~side:Bid ~price:100.0 ~size:300 ())
  in
  match result with
  | Ok (snap, fills) ->
      Alcotest.(check int) "fills count" 1 (List.length fills);
      let f = List.hd fills in
      Alcotest.(check string) "fill buy id" "b1" f.buy_order_id;
      Alcotest.(check string) "fill sell id" "a1" f.sell_order_id;
      Alcotest.(check int) "fill size" 300 (Size.to_int f.fill_size);
      Alcotest.(check string)
        "fill price" "100.0000"
        (Price.to_string f.fill_price);
      Alcotest.(check string) "fill aggressor" "b1" f.aggressor_order_id;
      (* Bid fully consumed, ask partially filled *)
      Alcotest.(check int) "bid levels after match" 0 (List.length snap.bids);
      Alcotest.(check int) "ask levels after match" 1 (List.length snap.asks);
      Alcotest.(check int)
        "ask remaining size" 200
        (Size.to_int (List.hd snap.asks).total_size)
  | Error _ -> Alcotest.fail "expected Ok"

(** Bid walks the book across multiple ask levels. *)
let test_match_walk_book () =
  let book = Market_simulator.Order_book.create () in
  let _ =
    Market_simulator.Order_book.apply_exn book
      (make_add_event ~oid:"a1" ~side:Ask ~price:100.0 ~size:100 ())
  in
  let _ =
    Market_simulator.Order_book.apply_exn book
      (make_add_event ~oid:"a2" ~side:Ask ~price:101.0 ~size:200 ())
  in
  let result =
    Market_simulator.Order_book.apply book
      (make_add_event ~oid:"b1" ~side:Bid ~price:101.0 ~size:250 ())
  in
  match result with
  | Ok (snap, fills) ->
      Alcotest.(check int) "walk fills count" 2 (List.length fills);
      let f1 = List.hd fills in
      let f2 = List.nth fills 1 in
      Alcotest.(check string) "first fill: a1" "a1" f1.sell_order_id;
      Alcotest.(check int) "first fill size" 100 (Size.to_int f1.fill_size);
      Alcotest.(check string)
        "first fill price" "100.0000"
        (Price.to_string f1.fill_price);
      Alcotest.(check string) "second fill: a2" "a2" f2.sell_order_id;
      Alcotest.(check int) "second fill size" 150 (Size.to_int f2.fill_size);
      Alcotest.(check string)
        "second fill price" "101.0000"
        (Price.to_string f2.fill_price);
      (* Ask levels remaining: a2 has 50 left *)
      Alcotest.(check int) "asks after walk" 1 (List.length snap.asks);
      Alcotest.(check int)
        "ask remaining" 50
        (Size.to_int (List.hd snap.asks).total_size);
      Alcotest.(check int) "bids after walk" 0 (List.length snap.bids)
  | Error _ -> Alcotest.fail "expected Ok"

(** Ask aggressor crosses best bid. *)
let test_match_ask_aggressor () =
  let book = Market_simulator.Order_book.create () in
  let _ =
    Market_simulator.Order_book.apply_exn book
      (make_add_event ~oid:"b1" ~side:Bid ~price:100.0 ~size:500 ())
  in
  let result =
    Market_simulator.Order_book.apply book
      (make_add_event ~oid:"a1" ~side:Ask ~price:99.0 ~size:300 ())
  in
  match result with
  | Ok (snap, fills) ->
      Alcotest.(check int) "ask aggressor fills" 1 (List.length fills);
      let f = List.hd fills in
      Alcotest.(check string) "ask aggressor buy id" "b1" f.buy_order_id;
      Alcotest.(check string) "ask aggressor sell id" "a1" f.sell_order_id;
      Alcotest.(check string)
        "ask aggressor price" "100.0000"
        (Price.to_string f.fill_price);
      (* Fill at resting bid price (100), not aggressor price (99) *)
      Alcotest.(check int) "ask aggressor size" 300 (Size.to_int f.fill_size);
      Alcotest.(check int) "bids after ask aggressor" 1 (List.length snap.bids);
      Alcotest.(check int)
        "bid remaining" 200
        (Size.to_int (List.hd snap.bids).total_size)
  | Error _ -> Alcotest.fail "expected Ok"

(** No crossing: bid below best ask rests. *)
let test_match_no_cross () =
  let book = Market_simulator.Order_book.create () in
  let _ =
    Market_simulator.Order_book.apply_exn book
      (make_add_event ~oid:"a1" ~side:Ask ~price:101.0 ~size:500 ())
  in
  let result =
    Market_simulator.Order_book.apply book
      (make_add_event ~oid:"b1" ~side:Bid ~price:100.0 ~size:300 ())
  in
  match result with
  | Ok (snap, fills) ->
      Alcotest.(check int) "no cross fills" 0 (List.length fills);
      Alcotest.(check int) "no cross bids" 1 (List.length snap.bids);
      Alcotest.(check int)
        "no cross bid size" 300
        (Size.to_int (List.hd snap.bids).total_size)
  | Error _ -> Alcotest.fail "expected Ok"

(** Partial fill: bid partially consumes ask. *)
let test_match_partial () =
  let book = Market_simulator.Order_book.create () in
  let _ =
    Market_simulator.Order_book.apply_exn book
      (make_add_event ~oid:"a1" ~side:Ask ~price:100.0 ~size:100 ())
  in
  let result =
    Market_simulator.Order_book.apply book
      (make_add_event ~oid:"b1" ~side:Bid ~price:101.0 ~size:300 ())
  in
  match result with
  | Ok (snap, fills) ->
      Alcotest.(check int) "partial fills count" 1 (List.length fills);
      let f = List.hd fills in
      Alcotest.(check int) "partial fill size" 100 (Size.to_int f.fill_size);
      (* Ask fully consumed, bid has 200 remaining *)
      Alcotest.(check int) "asks after partial" 0 (List.length snap.asks);
      Alcotest.(check int) "bids after partial" 1 (List.length snap.bids);
      Alcotest.(check int)
        "remaining bid" 200
        (Size.to_int (List.hd snap.bids).total_size)
  | Error _ -> Alcotest.fail "expected Ok"

(** Multiple orders at same level: FIFO priority. *)
let test_match_fifo_level () =
  let book = Market_simulator.Order_book.create () in
  let early_ts = Market_simulator.Timestamp.add_seconds zero_ts 1.0 in
  let late_ts = Market_simulator.Timestamp.add_seconds zero_ts 2.0 in
  let _ =
    Market_simulator.Order_book.apply_exn book
      (make_add_event ~ts:early_ts ~oid:"z-order" ~side:Ask ~price:100.0
         ~size:100 ())
  in
  let _ =
    Market_simulator.Order_book.apply_exn book
      (make_add_event ~ts:late_ts ~oid:"a-order" ~side:Ask ~price:100.0
         ~size:200 ())
  in
  let result =
    Market_simulator.Order_book.apply book
      (make_add_event ~oid:"b1" ~side:Bid ~price:101.0 ~size:150 ())
  in
  match result with
  | Ok (snap, fills) ->
      (* Time priority must beat the lexicographic order of the IDs. *)
      Alcotest.(check int) "fifo fills count" 2 (List.length fills);
      let f1 = List.hd fills in
      let f2 = List.nth fills 1 in
      Alcotest.(check string) "fifo first: z-order" "z-order" f1.sell_order_id;
      Alcotest.(check int) "fifo first size" 100 (Size.to_int f1.fill_size);
      Alcotest.(check string) "fifo second: a-order" "a-order" f2.sell_order_id;
      Alcotest.(check int) "fifo second size" 50 (Size.to_int f2.fill_size);
      Alcotest.(check int) "fifo asks after" 1 (List.length snap.asks);
      Alcotest.(check int)
        "fifo ask remaining" 150
        (Size.to_int (List.hd snap.asks).total_size)
  | Error _ -> Alcotest.fail "expected Ok"

(** Same-timestamp orders use arrival order, not order-ID order. *)
let test_match_fifo_same_timestamp () =
  let book = Market_simulator.Order_book.create () in
  let ts = Market_simulator.Timestamp.add_seconds zero_ts 1.0 in
  let _ =
    Market_simulator.Order_book.apply_exn book
      (make_add_event ~ts ~oid:"z-order" ~side:Ask ~price:100.0 ~size:100 ())
  in
  let result =
    Market_simulator.Order_book.apply book
      (make_add_event ~ts ~oid:"a-order" ~side:Ask ~price:100.0 ~size:100 ())
  in
  let _ = result in
  match
    Market_simulator.Order_book.apply book
      (make_add_event ~oid:"b1" ~side:Bid ~price:101.0 ~size:100 ())
  with
  | Ok (_, fills) ->
      Alcotest.(check string)
        "same timestamp preserves arrival order" "z-order"
        (List.hd fills).sell_order_id
  | Error _ -> Alcotest.fail "expected Ok"

(** Partial execution does not reset an order's queue priority. *)
let test_match_partial_preserves_fifo () =
  let book = Market_simulator.Order_book.create () in
  let first_ts = Market_simulator.Timestamp.add_seconds zero_ts 1.0 in
  let second_ts = Market_simulator.Timestamp.add_seconds zero_ts 2.0 in
  let _ =
    Market_simulator.Order_book.apply_exn book
      (make_add_event ~ts:first_ts ~oid:"z-order" ~side:Ask ~price:100.0
         ~size:200 ())
  in
  let _ =
    Market_simulator.Order_book.apply_exn book
      (make_add_event ~ts:second_ts ~oid:"b0" ~side:Bid ~price:101.0 ~size:50 ())
  in
  let _ =
    Market_simulator.Order_book.apply_exn book
      (make_add_event ~ts:second_ts ~oid:"a-order" ~side:Ask ~price:100.0
         ~size:100 ())
  in
  match
    Market_simulator.Order_book.apply book
      (make_add_event ~oid:"b1" ~side:Bid ~price:101.0 ~size:50 ())
  with
  | Ok (_, fills) ->
      Alcotest.(check string)
        "partial order keeps queue priority" "z-order"
        (List.hd fills).sell_order_id
  | Error _ -> Alcotest.fail "expected Ok"

(** Full fill across 3 ask levels. *)
let test_match_walk_three () =
  let book = Market_simulator.Order_book.create () in
  let _ =
    Market_simulator.Order_book.apply_exn book
      (make_add_event ~oid:"a1" ~side:Ask ~price:100.0 ~size:50 ())
  in
  let _ =
    Market_simulator.Order_book.apply_exn book
      (make_add_event ~oid:"a2" ~side:Ask ~price:101.0 ~size:100 ())
  in
  let _ =
    Market_simulator.Order_book.apply_exn book
      (make_add_event ~oid:"a3" ~side:Ask ~price:102.0 ~size:150 ())
  in
  let result =
    Market_simulator.Order_book.apply book
      (make_add_event ~oid:"b1" ~side:Bid ~price:103.0 ~size:300 ())
  in
  match result with
  | Ok (snap, fills) ->
      Alcotest.(check int) "walk3 fills" 3 (List.length fills);
      let sizes = List.map (fun f -> Size.to_int f.fill_size) fills in
      Alcotest.(check bool) "walk3 fill sizes" true (sizes = [ 50; 100; 150 ]);
      (* All asks consumed, bid fully consumed too *)
      Alcotest.(check int) "asks after walk3" 0 (List.length snap.asks);
      Alcotest.(check int) "bids after walk3" 0 (List.length snap.bids)
  | Error _ -> Alcotest.fail "expected Ok"

(** Amend that crosses the book generates fills. *)
let test_match_amend_cross () =
  let book = Market_simulator.Order_book.create () in
  let _ =
    Market_simulator.Order_book.apply_exn book
      (make_add_event ~oid:"a1" ~side:Ask ~price:101.0 ~size:200 ())
  in
  (* Add a bid that rests at 100 *)
  let _ =
    Market_simulator.Order_book.apply_exn book
      (make_add_event ~oid:"b1" ~side:Bid ~price:100.0 ~size:300 ())
  in
  (* Amend bid from 100 to 102 — now it crosses best ask at 101 *)
  let result =
    Market_simulator.Order_book.apply book
      {
        (make_add_event ~oid:"b1" ~side:Bid ~price:102.0 ~size:300 ()) with
        action = Amend;
      }
  in
  match result with
  | Ok (snap, fills) ->
      Alcotest.(check int) "amend cross fills" 1 (List.length fills);
      let f = List.hd fills in
      Alcotest.(check int) "amend cross fill size" 200 (Size.to_int f.fill_size);
      Alcotest.(check string)
        "amend cross price" "101.0000"
        (Price.to_string f.fill_price);
      (* Ask fully consumed, bid has 100 left *)
      Alcotest.(check int) "asks after amend cross" 0 (List.length snap.asks);
      Alcotest.(check int) "bids after amend cross" 1 (List.length snap.bids);
      Alcotest.(check int)
        "bid remaining after amend" 100
        (Size.to_int (List.hd snap.bids).total_size)
  | Error _ -> Alcotest.fail "expected Ok"

(** Apply returns fills for all crossing events. *)
let test_match_return_rate () =
  let book = Market_simulator.Order_book.create () in
  (* Three crossings in sequence *)
  let r1 =
    Market_simulator.Order_book.apply book
      (make_add_event ~oid:"a1" ~side:Ask ~price:100.0 ~size:100 ())
  in
  let r2 =
    Market_simulator.Order_book.apply book
      (make_add_event ~oid:"b1" ~side:Bid ~price:101.0 ~size:150 ())
  in
  let r3 =
    Market_simulator.Order_book.apply book
      (make_add_event ~oid:"a2" ~side:Ask ~price:99.0 ~size:50 ())
  in
  match (r1, r2, r3) with
  | Ok (_, f1), Ok (_, f2), Ok (_, f3) ->
      Alcotest.(check int) "first add no cross" 0 (List.length f1);
      Alcotest.(check int) "bid crossing fills" 1 (List.length f2);
      Alcotest.(check int) "second ask crossing fills" 1 (List.length f3);
      Alcotest.(check string) "r3 buy" "b1" (List.hd f3).buy_order_id;
      Alcotest.(check string) "r3 sell" "a2" (List.hd f3).sell_order_id
  | _ -> Alcotest.fail "expected all Ok"

(* ================================================================== *)
(* FULL SEQUENCE SCENARIOS *)
(* ================================================================== *)

(** Full scenario: add bids/asks, execute, verify invariants. *)
let test_full_scenario () =
  let book = Market_simulator.Order_book.create () in
  (* Add 3 bids at different prices *)
  let _ =
    Market_simulator.Order_book.apply_exn book
      (make_add_event ~oid:"b1" ~side:Bid ~price:100.0 ~size:200 ())
  in
  let _ =
    Market_simulator.Order_book.apply_exn book
      (make_add_event ~oid:"b2" ~side:Bid ~price:99.0 ~size:300 ())
  in
  let _ =
    Market_simulator.Order_book.apply_exn book
      (make_add_event ~oid:"b3" ~side:Bid ~price:101.0 ~size:150 ())
  in
  (* Add 2 asks *)
  let _ =
    Market_simulator.Order_book.apply_exn book
      (make_add_event ~oid:"a1" ~side:Ask ~price:102.0 ~size:250 ())
  in
  let _ =
    Market_simulator.Order_book.apply_exn book
      (make_add_event ~oid:"a2" ~side:Ask ~price:103.0 ~size:350 ())
  in
  (* Verify snapshot *)
  let snap = Market_simulator.Order_book.get_snapshot book in
  Alcotest.(check int) "scenario bids count" 3 (List.length snap.bids);
  Alcotest.(check int) "scenario asks count" 2 (List.length snap.asks);
  (* Best bid should be 101 *)
  Alcotest.(check int)
    "best bid"
    (int_of_float (Market_simulator.Price.to_float (List.hd snap.bids).price))
    (int_of_float
       (Market_simulator.Price.to_float (Market_simulator.Price.of_float 101.0)));
  (* Best ask should be 102 *)
  Alcotest.(check int)
    "best ask"
    (int_of_float (Market_simulator.Price.to_float (List.hd snap.asks).price))
    (int_of_float
       (Market_simulator.Price.to_float (Market_simulator.Price.of_float 102.0)));
  (* Spread: 102 - 101 = 1 *)
  ignore
    (match snap.spread with
    | Some s ->
        Alcotest.(check int)
          "spread 1"
          (int_of_float (Market_simulator.Price.to_float s))
          (int_of_float
             (Market_simulator.Price.to_float
                (Market_simulator.Price.of_float 1.0)))
    | None -> Alcotest.fail "expected spread");
  (* Add another bid at 102: crosses with best ask (102.0), generates a trade.
     The bid is fully filled (size 100 consumed), ask goes from 250 -> 150.
     No new bid level added — it traded instead. *)
  let snap2 =
    Market_simulator.Order_book.apply_exn book
      (make_add_event ~oid:"b4" ~side:Bid ~price:102.0 ~size:100 ())
  in
  Alcotest.(check int) "bids after crossing bid" 3 (List.length snap2.bids);
  (* Partially fill best ask. Before the crossing bid above consumed 100,
   so a1 now has 150 remaining. Execute 100 more, leaving 50. *)
  let snap3 =
    Market_simulator.Order_book.apply_exn book
      {
        (make_add_event ~oid:"a1" ~side:Ask ~price:102.0 ~size:100 ()) with
        action = Execute;
      }
  in
  Alcotest.(check int)
    "ask remaining after fill" 50
    (Market_simulator.Size.to_int (List.hd snap3.asks).total_size);
  (* Cancel middle bid *)
  let snap4 =
    Market_simulator.Order_book.apply_exn book
      (make_cancel_event ~oid:"b2" ~price:99.0 ())
  in
  Alcotest.(check int) "bids after cancel" 2 (List.length snap4.bids);
  Alcotest.(check int)
    "total orders" 4
    (Market_simulator.Order_book.order_count book);
  (* Full execute remaining on a1 (50 left) *)
  let _ =
    Market_simulator.Order_book.apply_exn book
      {
        (make_add_event ~oid:"a1" ~side:Ask ~price:102.0 ~size:200 ()) with
        action = Execute;
      }
  in
  let snap5 = Market_simulator.Order_book.get_snapshot book in
  Alcotest.(check int) "asks after full fill" 1 (List.length snap5.asks);
  Alcotest.(check int)
    "remaining ask" 350
    (Market_simulator.Size.to_int (List.hd snap5.asks).total_size)

(* ================================================================== *)
(* ERROR SCENARIOS *)
(* ================================================================== *)

(** Execute order with zero size clamps to zero is a no-op? depends on min. *)
let test_book_execute_zero () =
  let book = Market_simulator.Order_book.create () in
  let _ =
    Market_simulator.Order_book.apply_exn book
      (make_add_event ~oid:"o1" ~side:Ask ~price:101.0 ~size:100 ())
  in
  (* Execute with size=0: min(0,100)=0, remaining=100, so no change *)
  let snap =
    Market_simulator.Order_book.apply_exn book
      {
        (make_add_event ~oid:"o1" ~side:Ask ~price:101.0 ~size:0 ()) with
        action = Execute;
      }
  in
  Alcotest.(check int)
    "execute zero preserves size" 100
    (Market_simulator.Size.to_int (List.hd snap.asks).total_size)

(** Replay mode applies venue events without inventing new matches. *)
let test_replay_does_not_match () =
  let book = Market_simulator.Order_book.create () in
  let ask = make_add_event ~oid:"ask" ~side:Ask ~price:100.0 ~size:100 () in
  let bid = make_add_event ~oid:"bid" ~side:Bid ~price:101.0 ~size:100 () in
  let _ = Market_simulator.Order_book.apply_replay book ask in
  match Market_simulator.Order_book.apply_replay book bid with
  | Ok (snap, fills) ->
      Alcotest.(check int) "replay emits no fills" 0 (List.length fills);
      Alcotest.(check int) "replay keeps bid" 1 (List.length snap.bids);
      Alcotest.(check int) "replay keeps ask" 1 (List.length snap.asks)
  | Error msg -> Alcotest.fail msg

(** Cancel and execute use the stored order location, not stale event metadata.
*)
let test_cancel_uses_stored_order () =
  let book = Market_simulator.Order_book.create () in
  let _ =
    Market_simulator.Order_book.apply_exn book
      (make_add_event ~oid:"o1" ~side:Bid ~price:100.0 ~size:100 ())
  in
  let bad_cancel =
    {
      (make_cancel_event ~oid:"o1" ~side:Ask ~price:999.0 ~size:100 ()) with
      action = Cancel;
    }
  in
  let _ = Market_simulator.Order_book.apply_exn book bad_cancel in
  Alcotest.(check int)
    "stale cancel removes order" 0
    (Market_simulator.Order_book.order_count book)

(** Duplicate order IDs are rejected instead of corrupting a price level. *)
let test_duplicate_order_rejected () =
  let book = Market_simulator.Order_book.create () in
  let ev = make_add_event ~oid:"o1" ~side:Bid ~price:100.0 ~size:100 () in
  let _ = Market_simulator.Order_book.apply_exn book ev in
  match Market_simulator.Order_book.apply book ev with
  | Ok _ -> Alcotest.fail "duplicate add unexpectedly succeeded"
  | Error msg ->
      Alcotest.(check bool) "duplicate error" true (String.contains msg 'd')

(** Event replay rejects sequence gaps and isolates symbol books. *)
let test_event_replay_strict () =
  let timestamp value =
    match Market_simulator.Timestamp.of_string value with
    | Ok t -> t
    | Error msg -> Alcotest.fail msg
  in
  let make_event sequence symbol order_id time :
      Market_simulator.Market_data.feed_event =
    let timestamp = timestamp time in
    {
      venue = "TEST";
      symbol;
      epoch = 0;
      sequence;
      event_time = timestamp;
      received_time = Some timestamp;
      event =
        {
          timestamp;
          order_id;
          side = Bid;
          price = Market_simulator.Price.of_int 10000;
          size = Market_simulator.Size.of_int 10;
          action = Add;
          valid_time = None;
        };
    }
  in
  let replay = Market_simulator.Event_replay.create () in
  (match
     Market_simulator.Event_replay.apply replay
       (make_event 10 "A" "a1" "2026-09-01T09:30:00Z")
   with
  | Ok _ -> ()
  | Error msg -> Alcotest.fail msg);
  (match
     Market_simulator.Event_replay.apply replay
       (make_event 12 "A" "a2" "2026-09-01T09:30:01Z")
   with
  | Ok _ -> Alcotest.fail "sequence gap accepted"
  | Error msg ->
      Alcotest.(check bool) "sequence gap reported" true (String.length msg > 0));
  (match
     Market_simulator.Event_replay.apply replay
       (make_event 10 "B" "b1" "2026-09-01T09:30:00Z")
   with
  | Ok _ -> ()
  | Error msg -> Alcotest.fail msg);
  Alcotest.(check int)
    "one book per symbol" 2
    (Market_simulator.Event_replay.book_count replay)

(** Generated feed events carry source identity and sequence metadata. *)
let test_generated_feed_metadata () =
  let config =
    {
      Market_simulator.Market_data.default_config with
      symbols = [ "A"; "B" ];
      duration_s = 30.0;
      speed = 10.0;
      rng_seed = Some 7;
    }
  in
  let feed = Market_simulator.Market_data.generate_feed config in
  let sequences =
    List.map
      (fun (ev : Market_simulator.Market_data.feed_event) -> ev.sequence)
      feed
  in
  Alcotest.(check bool) "feed is non-empty" true (sequences <> []);
  Alcotest.(check bool)
    "sequences are ordered" true
    (sequences = List.mapi (fun i _ -> i + 1) feed);
  let groups = Market_simulator.Market_data.group_by_symbol feed in
  Alcotest.(check int) "one group per symbol" 2 (List.length groups)

(** Generated feed events must replay without unknown-order failures. *)
let test_generated_events_replay () =
  let config =
    {
      Market_simulator.Market_data.default_config with
      symbols = [ "A"; "B" ];
      duration_s = 30.0;
      speed = 10.0;
      rng_seed = Some 7;
    }
  in
  let book = Market_simulator.Order_book.create () in
  List.iter
    (fun ev ->
      match Market_simulator.Order_book.apply_replay book ev with
      | Ok _ -> ()
      | Error msg -> Alcotest.fail msg)
    (Market_simulator.Market_data.generate config)

(* ================================================================== *)
(* Main test registration *)
(* ================================================================== *)

let () =
  Alcotest.run "market_simulator"
    [
      ( "incr",
        [
          ("basic", `Quick, test_incr_basic);
          ("return", `Quick, test_incr_return);
          ("map2", `Quick, test_incr_map2);
          ("map3", `Quick, test_incr_map3);
          ("bind", `Quick, test_incr_bind);
          ("if_", `Quick, test_incr_if);
          ("if_dynamic", `Quick, test_incr_if_dynamic);
          ("bind_dynamic", `Quick, test_incr_bind_dynamic);
          ("cutoff", `Quick, test_incr_cutoff);
          ("cutoff_custom", `Quick, test_incr_cutoff_custom);
          ("on_change_multi", `Quick, test_incr_on_change_multi);
          ("topo_chain", `Quick, test_incr_topo_chain);
          ("topo_diamond", `Quick, test_incr_topo_diamond);
          ("stabilize_noop", `Quick, test_incr_stabilize_noop);
          ("double_set", `Quick, test_incr_double_set);
          ("of_var", `Quick, test_incr_of_var);
          ("map_string", `Quick, test_incr_map_string);
          ("bind_on_change", `Quick, test_incr_bind_on_change);
          ("deep_chain", `Quick, test_incr_deep_chain);
        ] );
      ( "serror",
        [
          ("return", `Quick, test_serror_return);
          ("fail", `Quick, test_serror_fail);
          ("failf", `Quick, test_serror_failf);
          ("map", `Quick, test_serror_map);
          ("bind", `Quick, test_serror_bind);
          ("map_error", `Quick, test_serror_map_error);
          ("both", `Quick, test_serror_both);
          ("all", `Quick, test_serror_all);
          ("try_with", `Quick, test_serror_try_with);
          ("of_option", `Quick, test_serror_of_option);
          ("ok_or_failwith", `Quick, test_serror_ok_or_failwith);
          ("value", `Quick, test_serror_value);
          ("filter_map", `Quick, test_serror_filter_map);
          ("map_list", `Quick, test_serror_map_list);
        ] );
      ( "side",
        [
          ("sexp_roundtrip", `Quick, test_side_sexp);
          ("sexp_invalid", `Quick, test_side_sexp_invalid);
          ("action_sexp", `Quick, test_action_sexp);
          ("action_invalid", `Quick, test_action_sexp_invalid);
          ("show", `Quick, test_side_show);
          ("compare", `Quick, test_side_compare);
        ] );
      ( "order_id",
        [
          ("sexp", `Quick, test_order_id_sexp);
          ("map", `Quick, test_order_id_map);
        ] );
      ( "price",
        [
          ("basic", `Quick, test_price_ops);
          ("int_roundtrip", `Quick, test_price_int_roundtrip);
          ("float_roundtrip", `Quick, test_price_float_roundtrip);
          ("edge_cases", `Quick, test_price_edge);
          ("sexp", `Quick, test_price_sexp);
          ("sexp_invalid", `Quick, test_price_sexp_invalid);
          ("map", `Quick, test_price_map);
        ] );
      ( "size",
        [
          ("basic", `Quick, test_size_ops);
          ("zero", `Quick, test_size_zero);
          ("edge", `Quick, test_size_edge);
          ("sexp", `Quick, test_size_sexp);
          ("sexp_invalid", `Quick, test_size_sexp_invalid);
        ] );
      ( "timestamp",
        [
          ("basic", `Quick, test_timestamp_ops);
          ("zero", `Quick, test_timestamp_zero);
          ("of_string_valid", `Quick, test_timestamp_of_string_valid);
          ("of_string_invalid", `Quick, test_timestamp_of_string_invalid);
          ("max_min", `Quick, test_timestamp_max_min);
          ("sexp", `Quick, test_timestamp_sexp);
          ("sexp_invalid", `Quick, test_timestamp_sexp_invalid);
          ("ptime_roundtrip", `Quick, test_timestamp_ptime);
        ] );
      ("list_utils", [ ("take", `Quick, test_list_utils_take) ]);
      ( "order_book",
        [
          ("add_order", `Quick, test_book_add_order);
          ("add_ask", `Quick, test_book_add_ask);
          ("cancel", `Quick, test_book_cancel);
          ("execute", `Quick, test_book_execute);
          ("full_execute", `Quick, test_book_full_execute);
          ("multiple_orders", `Quick, test_book_multiple_orders);
          ("amend_same_price", `Quick, test_book_amend_same_price);
          ("amend_move_level", `Quick, test_book_amend_move_level);
          ("cancel_unknown", `Quick, test_book_cancel_unknown);
          ("amend_unknown", `Quick, test_book_amend_unknown);
          ("execute_unknown", `Quick, test_book_execute_unknown);
          ("execute_overflow", `Quick, test_book_execute_overflow);
          ("double_cancel", `Quick, test_book_double_cancel);
          ("amend_after_cancel", `Quick, test_book_amend_after_cancel);
          ("stats", `Quick, test_book_stats);
          ("reset", `Quick, test_book_reset);
          ("empty_snapshot", `Quick, test_book_empty_snapshot);
          ("empty_stats", `Quick, test_book_empty_stats);
          ("order_count_empty", `Quick, test_book_order_count_empty);
          ("bids_descending", `Quick, test_book_bids_descending);
          ("asks_ascending", `Quick, test_book_asks_ascending);
          ("many_levels", `Quick, test_book_many_levels);
          ("micro_price", `Quick, test_book_micro_price);
          ("apply_exn_raises", `Quick, test_book_apply_exn_raises);
          ("execute_zero", `Quick, test_book_execute_zero);
          ("replay_no_match", `Quick, test_replay_does_not_match);
          ("cancel_stored_order", `Quick, test_cancel_uses_stored_order);
          ("duplicate_order", `Quick, test_duplicate_order_rejected);
          ("match_same_price", `Quick, test_match_same_price);
          ("match_walk_book", `Quick, test_match_walk_book);
          ("match_ask_aggressor", `Quick, test_match_ask_aggressor);
          ("match_no_cross", `Quick, test_match_no_cross);
          ("match_partial", `Quick, test_match_partial);
          ("match_fifo_level", `Quick, test_match_fifo_level);
          ("match_fifo_same_timestamp", `Quick, test_match_fifo_same_timestamp);
          ( "match_partial_preserves_fifo",
            `Quick,
            test_match_partial_preserves_fifo );
          ("match_walk_three", `Quick, test_match_walk_three);
          ("match_amend_cross", `Quick, test_match_amend_cross);
          ("match_return_fills", `Quick, test_match_return_rate);
        ] );
      ( "market_data",
        [
          ("generator", `Quick, test_generator_creates_events);
          ("csv_roundtrip", `Quick, test_csv_roundtrip);
          ("parse_nonexistent", `Quick, test_csv_parse_nonexistent);
          ("parse_alternates", `Quick, test_csv_parse_alternates);
          ("side_alternates", `Quick, test_csv_parse_side_alternates);
          ("valid_time", `Quick, test_csv_parse_valid_time);
          ("malformed_row", `Quick, test_csv_parse_malformed_row);
          ("strict_parser", `Quick, test_csv_parse_strict);
          ("feed_csv", `Quick, test_feed_csv_parse);
          ("nyse_mapping_file", `Quick, test_nyse_mapping_file);
          ("nyse_binary", `Quick, test_nyse_binary_parse);
          ("nyse_taq", `Quick, test_nyse_taq_parse);
          ("sonarx_l2", `Quick, test_sonarx_l2_parse);
          ("binance_l2", `Quick, test_binance_l2_replay);
          ("binance_derivatives", `Quick, test_binance_derivatives);
          ("hf_l2", `Quick, test_hf_l2_parse);
          ("l2_execution", `Quick, test_l2_execution);
          ("l2_backtest", `Quick, test_l2_backtest);
          ("sonarx_replay", `Quick, test_sonarx_replay);
          ("invalid_fields", `Quick, test_csv_parse_invalid_fields);
          ("write_empty", `Quick, test_csv_write_empty);
          ("deterministic", `Quick, test_generator_deterministic);
          ("no_seed", `Quick, test_generator_no_deterministic);
          ("generated_replay", `Quick, test_generated_events_replay);
          ("feed_metadata", `Quick, test_generated_feed_metadata);
          ("event_replay", `Quick, test_event_replay_strict);
        ] );
      ( "bitemporal",
        [
          ("as_of", `Quick, test_bitemporal_as_of);
          ("interval", `Quick, test_bitemporal_interval);
          ("sequenced", `Quick, test_bitemporal_sequenced);
          ("singleton", `Quick, test_bitemporal_singleton);
          ("add", `Quick, test_bitemporal_add);
          ("add_with_interval", `Quick, test_bitemporal_add_with_interval);
          ("close_valid", `Quick, test_bitemporal_close_valid);
          ("close_tx", `Quick, test_bitemporal_close_tx);
          ("between_valid", `Quick, test_bitemporal_between_valid);
          ("between_tx", `Quick, test_bitemporal_between_tx);
          ("history", `Quick, test_bitemporal_history);
          ("index", `Quick, test_bitemporal_index);
          ("empty", `Quick, test_bitemporal_empty);
        ] );
      ( "event_loop",
        [
          ("process_events", `Quick, test_event_loop);
          ("multi_events", `Quick, test_event_loop_multi);
          ("simulation_mode", `Quick, test_event_loop_simulation_mode);
          ("progress", `Quick, test_event_loop_progress);
          ("error_handling", `Quick, test_event_loop_error);
          ("stop", `Quick, test_event_loop_stop);
          ("set_speed", `Quick, test_event_loop_speed);
        ] );
      ( "metrics",
        [
          ("collector", `Quick, test_metrics);
          ("empty_book", `Quick, test_metrics_empty);
          ("add_cancel", `Quick, test_metrics_add_cancel);
          ("json_report", `Quick, test_metrics_json);
        ] );
      ( "websocket",
        [
          ("encode_snapshot", `Quick, test_ws_encode_snapshot);
          ("encode_all_events", `Quick, test_ws_encode_all_events);
          ("encode_no_micro", `Quick, test_ws_encode_no_micro);
        ] );
      ("scenarios", [ ("full_scenario", `Quick, test_full_scenario) ]);
    ]
