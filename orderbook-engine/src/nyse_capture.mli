(** Strict extraction of IPv4 UDP payloads from libpcap captures. *)

type datagram = {
  capture_seconds : int64;
  capture_fraction : int64;
  source : string;
  destination : string;
  source_port : int;
  destination_port : int;
  payload : bytes;
}

type channel = {
  source : string;
  destination : string;
  source_port : int;
  destination_port : int;
  datagrams : datagram list;
}

val read_pcap : string -> datagram list Serror.t
val group_udp_channels : datagram list -> channel list
