(** WebSocket server for real-time market data streaming.

    Uses [Websocket.b64_encoded_sha1sum] for the HTTP upgrade handshake and raw
    Lwt_unix TCP for frame I/O. Delivers the full event stream to connected
    clients. *)

open Market_types
open Side
open Lwt.Infix

type client = { fd : Lwt_unix.file_descr; mutable alive : bool; id : int }
(** A connected WebSocket client. *)

type t = {
  mutable port : int;
  mutable running : bool;
  mutable server_fd : Lwt_unix.file_descr option;
  clients : client list ref;
  mutable next_client_id : int;
}
(** WebSocket server state. *)

let create () : t =
  {
    port = 8080;
    running = false;
    server_fd = None;
    clients = ref [];
    next_client_id = 1;
  }

(* ------------------------------------------------------------------ *)
(* WebSocket handshake *)
(* ------------------------------------------------------------------ *)

let read_http_request (fd : Lwt_unix.file_descr) : string Lwt.t =
  let buf = Bytes.create 4096 in
  let rec loop acc =
    Lwt_unix.read fd buf 0 4096 >>= fun nread ->
    if nread <= 0 then Lwt.return acc
    else
      let chunk = Bytes.sub_string buf 0 nread in
      let combined = acc ^ chunk in
      if
        String.contains combined '\r'
        && String.length combined >= 4
        && String.sub combined (String.length combined - 4) 4 = "\r\n\r\n"
      then Lwt.return combined
      else if String.length combined > 8192 then Lwt.return combined
      else loop combined
  in
  loop ""

(** Perform the WebSocket upgrade handshake. Returns [true] on success. *)
let handshake (fd : Lwt_unix.file_descr) : bool Lwt.t =
  read_http_request fd >>= fun req ->
  let lines = String.split_on_char '\n' req in
  let ws_key =
    List.find_opt
      (fun line ->
        let trimmed = String.trim line in
        String.lowercase_ascii trimmed
        |> String.starts_with ~prefix:"sec-websocket-key")
      lines
  in
  match ws_key with
  | None -> Lwt.return false
  | Some key_line ->
      let key =
        String.trim
          (String.sub key_line
             (String.index key_line ':' + 1)
             (String.length key_line - String.index key_line ':' - 1))
      in
      let accept = Websocket.b64_encoded_sha1sum key in
      let response =
        Printf.sprintf
          "HTTP/1.1 101 Switching Protocols\r\n\
           Upgrade: websocket\r\n\
           Connection: Upgrade\r\n\
           Sec-WebSocket-Accept: %s\r\n\
           \r\n"
          accept
      in
      let resp_buf = Bytes.of_string response in
      Lwt_unix.write fd resp_buf 0 (Bytes.length resp_buf) >>= fun _ ->
      Lwt.return true

(* ------------------------------------------------------------------ *)
(* WebSocket frame encoding *)
(* ------------------------------------------------------------------ *)

let opcode_text = 0x1
let opcode_close = 0x8
let opcode_ping = 0x9

let encode_frame (opcode : int) (payload : string) : string =
  let len = String.length payload in
  let buf = Buffer.create (len + 14) in
  (* FIN + opcode *)
  Buffer.add_char buf (Char.chr (0x80 lor opcode));
  (* Mask bit (0 = server-to-client) + length *)
  if len < 126 then Buffer.add_char buf (Char.chr len)
  else if len < 65536 then (
    Buffer.add_char buf (Char.chr 126);
    Buffer.add_char buf (Char.chr (len lsr 8));
    Buffer.add_char buf (Char.chr (len land 0xFF)))
  else (
    Buffer.add_char buf (Char.chr 127);
    for i = 56 downto 0 do
      Buffer.add_char buf (Char.chr ((len lsr i) land 0xFF))
    done);
  Buffer.add_string buf payload;
  Buffer.contents buf

let send_frame (fd : Lwt_unix.file_descr) (opcode : int) (payload : string) :
    unit Lwt.t =
  let frame = encode_frame opcode payload in
  let buf = Bytes.of_string frame in
  Lwt_unix.write fd buf 0 (Bytes.length buf) >>= fun _ -> Lwt.return ()

let send_text (fd : Lwt_unix.file_descr) (text : string) : unit Lwt.t =
  send_frame fd opcode_text text

let send_close (fd : Lwt_unix.file_descr) : unit Lwt.t =
  send_frame fd opcode_close ""

(* ------------------------------------------------------------------ *)
(* JSON encoding *)
(* ------------------------------------------------------------------ *)

let encode_price_level (level : price_level) : Yojson.Safe.t =
  `Assoc
    [
      ("price", `String (Price.to_string level.price));
      ("size", `Int (Size.to_int level.total_size));
      ("count", `Int level.order_count);
    ]

let encode_snapshot (snap : book_snapshot) : string =
  let bids = `List (List.map encode_price_level snap.bids) in
  let asks = `List (List.map encode_price_level snap.asks) in
  let spread =
    match snap.spread with
    | Some s -> `String (Price.to_string s)
    | None -> `Null
  in
  let mid =
    match snap.mid_price with
    | Some m -> `String (Price.to_string m)
    | None -> `Null
  in
  let mp =
    match snap.micro_price with
    | Some m -> `String (Price.to_string m)
    | None -> `Null
  in
  let json =
    `Assoc
      [
        ("type", `String "snapshot");
        ("ts", `String (Timestamp.to_string snap.timestamp));
        ("bids", bids);
        ("asks", asks);
        ("spread", spread);
        ("mid", mid);
        ("micro", mp);
      ]
  in
  Yojson.Safe.to_string json

let encode_market_event (ev : market_event) : string =
  let event_json ?old_order_id action (e : event) sz =
    let side_str = match e.side with Bid -> "bid" | Ask -> "ask" in
    let size_v =
      match sz with Some s -> `Int (Size.to_int s) | None -> `Null
    in
    let old_order_field =
      match old_order_id with
      | Some id -> [ ("old_order_id", `String id) ]
      | None -> []
    in
    let json =
      `Assoc
        ([
           ("type", `String "event");
           ("action", `String action);
           ("ts", `String (Timestamp.to_string e.timestamp));
           ("order_id", `String e.order_id);
           ("side", `String side_str);
           ("price", `String (Price.to_string e.price));
           ("size", size_v);
         ]
        @ old_order_field)
    in
    Yojson.Safe.to_string json
  in
  match ev with
  | OrderAdded e -> event_json "add" e None
  | OrderAmended e -> event_json "amend" e None
  | OrderCancelled e -> event_json "cancel" e None
  | OrderExecuted (e, sz) -> event_json "execute" e (Some sz)
  | OrderReplaced (e, old_id) ->
      event_json ~old_order_id:old_id "replace" e None
  | ControlEvent e -> event_json "control" e None
  | BookSnapshot snap -> encode_snapshot snap
  | Trade f ->
      let json =
        `Assoc
          [
            ("type", `String "trade");
            ("trade_time", `String (Timestamp.to_string f.trade_time));
            ("buy_order_id", `String f.buy_order_id);
            ("sell_order_id", `String f.sell_order_id);
            ("price", `String (Price.to_string f.fill_price));
            ("size", `Int (Size.to_int f.fill_size));
            ("aggressor", `String f.aggressor_order_id);
          ]
      in
      Yojson.Safe.to_string json
  | StatsUpdate stats ->
      let spread =
        match stats.spread with
        | Some s -> `String (Price.to_string s)
        | None -> `Null
      in
      let mid =
        match stats.mid_price with
        | Some m -> `String (Price.to_string m)
        | None -> `Null
      in
      let json =
        `Assoc
          [
            ("type", `String "stats");
            ("bid_size", `Int (Size.to_int stats.total_bid_size));
            ("ask_size", `Int (Size.to_int stats.total_ask_size));
            ("bid_count", `Int stats.bid_count);
            ("ask_count", `Int stats.ask_count);
            ("spread", spread);
            ("mid", mid);
          ]
      in
      Yojson.Safe.to_string json

(* ------------------------------------------------------------------ *)
(* Server operations *)
(* ------------------------------------------------------------------ *)

let broadcast (server : t) (json : string) : unit Lwt.t =
  let alive = ref [] in
  Lwt_list.iter_p
    (fun client ->
      Lwt.catch
        (fun () ->
          send_text client.fd json >>= fun () ->
          alive := client :: !alive;
          Lwt.return ())
        (fun _ ->
          client.alive <- false;
          Lwt.catch
            (fun () -> Lwt_unix.close client.fd)
            (fun _ -> Lwt.return ())))
    !(server.clients)
  >>= fun () ->
  server.clients := !alive;
  Lwt.return ()

(** [client_reader server client] reads frames from a client to detect
    disconnection. *)
let client_reader (server : t) (client : client) : unit Lwt.t =
  let buf = Bytes.create 2 in
  let rec loop () =
    Lwt.catch
      (fun () ->
        Lwt_unix.read client.fd buf 0 2 >>= fun n ->
        if n <= 0 then (
          client.alive <- false;
          server.clients :=
            List.filter (fun c -> c.id <> client.id) !(server.clients);
          Lwt_unix.close client.fd)
        else
          let first_byte = Char.code (Bytes.get buf 0) in
          let opcode = first_byte land 0x0F in
          if opcode = opcode_close then (
            client.alive <- false;
            server.clients :=
              List.filter (fun c -> c.id <> client.id) !(server.clients);
            Lwt_unix.close client.fd)
          else loop ())
      (fun _ ->
        client.alive <- false;
        server.clients :=
          List.filter (fun c -> c.id <> client.id) !(server.clients);
        Lwt.catch (fun () -> Lwt_unix.close client.fd) (fun _ -> Lwt.return ()))
  in
  loop ()

let rec accept_loop (server : t) (listen_fd : Lwt_unix.file_descr) : unit Lwt.t
    =
  Lwt_unix.accept listen_fd >>= fun (client_fd, _addr) ->
  handshake client_fd >>= fun ok ->
  if ok then (
    let client = { fd = client_fd; alive = true; id = server.next_client_id } in
    server.next_client_id <- server.next_client_id + 1;
    server.clients := client :: !(server.clients);
    Logs.info (fun m ->
        m "WS client #%d connected (total %d)" client.id
          (List.length !(server.clients)));
    Lwt.async (fun () -> client_reader server client);
    accept_loop server listen_fd)
  else Lwt_unix.close client_fd >>= fun () -> accept_loop server listen_fd

(** [start server port] starts the WebSocket server. *)
let start (server : t) (port : int) : unit Lwt.t =
  server.port <- port;
  server.running <- true;
  let sockaddr = Lwt_unix.ADDR_INET (Unix.inet_addr_any, port) in
  let listen_fd = Lwt_unix.socket Unix.PF_INET Unix.SOCK_STREAM 0 in
  Lwt_unix.setsockopt listen_fd Lwt_unix.SO_REUSEADDR true;
  Lwt_unix.bind listen_fd sockaddr >>= fun () ->
  Lwt_unix.listen listen_fd 10;
  server.server_fd <- Some listen_fd;
  Logs.info (fun m -> m "WebSocket server listening on port %d" port);
  Lwt.async (fun () -> accept_loop server listen_fd);
  Lwt.return ()

(** [stop server] stops the WebSocket server. *)
let stop (server : t) : unit Lwt.t =
  server.running <- false;
  Lwt_list.iter_p
    (fun client ->
      Lwt.catch
        (fun () -> send_close client.fd >>= fun () -> Lwt_unix.close client.fd)
        (fun _ -> Lwt.return ()))
    !(server.clients)
  >>= fun () ->
  server.clients := [];
  match server.server_fd with
  | Some fd -> Lwt_unix.close fd
  | None -> Lwt.return ()

(** Create an event handler that broadcasts to all WebSocket clients. *)
let make_broadcast_handler (server : t) : Event_loop.event_handler =
 fun ev ->
  let json = encode_market_event ev in
  if !(server.clients) <> [] then broadcast server json else Lwt.return ()
