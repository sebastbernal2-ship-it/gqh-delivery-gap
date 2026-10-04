(** WebSocket server for real-time market data streaming.

    Uses raw Lwt_unix TCP with the WebSocket protocol for frame I/O and delivers
    the full event stream to connected clients. *)

open Lwt

type t
(** Opaque handle to the WebSocket server. *)

val create : unit -> t

val start : t -> int -> unit Lwt.t
(** [start server port] begins accepting WebSocket connections on the given TCP
    port. Returns immediately; accepts in a background fiber. *)

val stop : t -> unit Lwt.t
(** [stop server] gracefully closes all client connections and stops accepting
    new ones. *)

val broadcast : t -> string -> unit Lwt.t
(** [broadcast server json] sends a text frame to all connected clients,
    silently removing clients that have disconnected. *)

val encode_snapshot : Market_types.book_snapshot -> string
(** [encode_snapshot snap] returns a JSON string for a book snapshot. *)

val encode_market_event : Market_types.market_event -> string
(** [encode_market_event ev] returns a JSON string for a market event. *)

val make_broadcast_handler : t -> Event_loop.event_handler
(** [make_broadcast_handler server] returns an event-loop handler that
    broadcasts all incoming events to every connected WebSocket client. *)
