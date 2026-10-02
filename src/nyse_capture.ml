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

type endian = Little | Big

let ( let* ) result f = Result.bind result f
let failf fmt = Serror.failf fmt

let check bytes offset width =
  if offset < 0 || width < 0 || offset > Bytes.length bytes - width then
    failf "truncated pcap at offset %d" offset
  else Ok ()

let u16 endian bytes offset =
  let* () = check bytes offset 2 in
  let a = Char.code (Bytes.get bytes offset) in
  let b = Char.code (Bytes.get bytes (offset + 1)) in
  Ok (match endian with Little -> a lor (b lsl 8) | Big -> (a lsl 8) lor b)

let u32 endian bytes offset =
  let* () = check bytes offset 4 in
  let byte_at index = Char.code (Bytes.get bytes (offset + index)) in
  let value = ref 0L in
  for index = 0 to 3 do
    let shift =
      match endian with Little -> 8 * index | Big -> 8 * (3 - index)
    in
    value :=
      Int64.logor !value (Int64.shift_left (Int64.of_int (byte_at index)) shift)
  done;
  Ok !value

let ipv4 bytes offset =
  let* () = check bytes offset 4 in
  Ok
    (Printf.sprintf "%d.%d.%d.%d"
       (Char.code (Bytes.get bytes offset))
       (Char.code (Bytes.get bytes (offset + 1)))
       (Char.code (Bytes.get bytes (offset + 2)))
       (Char.code (Bytes.get bytes (offset + 3))))

let pcap_endian bytes =
  let* () = check bytes 0 4 in
  let magic =
    ( Char.code (Bytes.get bytes 0),
      Char.code (Bytes.get bytes 1),
      Char.code (Bytes.get bytes 2),
      Char.code (Bytes.get bytes 3) )
  in
  match magic with
  | 0xd4, 0xc3, 0xb2, 0xa1 -> Ok (Little, false)
  | 0x4d, 0x3c, 0xb2, 0xa1 -> Ok (Little, true)
  | 0xa1, 0xb2, 0xc3, 0xd4 -> Ok (Big, false)
  | 0xa1, 0xb2, 0x3c, 0x4d -> Ok (Big, true)
  | _ -> failf "unsupported pcap magic"

let read_file path =
  try
    let ic = open_in_bin path in
    let length = in_channel_length ic in
    let bytes = Bytes.create length in
    really_input ic bytes 0 length;
    close_in ic;
    Ok bytes
  with
  | Sys_error message -> Serror.fail ("IO error: " ^ message)
  | End_of_file -> Serror.fail "truncated pcap file"

let parse_frame ~network ~seconds ~fraction frame =
  if network <> 1 then Ok None
  else
    let* () = check frame 0 14 in
    let rec ethernet offset ether_type remaining =
      if ether_type = 0x8100 || ether_type = 0x88a8 then
        if remaining = 0 then failf "too many VLAN tags"
        else
          let* () = check frame offset 4 in
          let* next_type = u16 Big frame (offset + 2) in
          ethernet (offset + 4) next_type (remaining - 1)
      else Ok (offset, ether_type)
    in
    let* ether_type = u16 Big frame 12 in
    let* ip_offset, ether_type = ethernet 14 ether_type 2 in
    if ether_type <> 0x0800 then Ok None
    else
      let* () = check frame ip_offset 20 in
      let version_ihl = Char.code (Bytes.get frame ip_offset) in
      if version_ihl lsr 4 <> 4 then Ok None
      else
        let ihl = version_ihl land 0x0f * 4 in
        let* () = check frame ip_offset ihl in
        let* flags_fragment = u16 Big frame (ip_offset + 6) in
        if flags_fragment land 0x1fff <> 0 || flags_fragment land 0x2000 <> 0
        then failf "fragmented IPv4 packet is unsupported"
        else if Char.code (Bytes.get frame (ip_offset + 9)) <> 17 then Ok None
        else
          let udp_offset = ip_offset + ihl in
          let* () = check frame udp_offset 8 in
          let* source_port = u16 Big frame udp_offset in
          let* destination_port = u16 Big frame (udp_offset + 2) in
          let* udp_length = u16 Big frame (udp_offset + 4) in
          if udp_length < 8 then failf "invalid UDP length"
          else
            let payload_length = udp_length - 8 in
            let payload_offset = udp_offset + 8 in
            let* () = check frame payload_offset payload_length in
            let* source = ipv4 frame (ip_offset + 12) in
            let* destination = ipv4 frame (ip_offset + 16) in
            Ok
              (Some
                 {
                   capture_seconds = seconds;
                   capture_fraction = fraction;
                   source;
                   destination;
                   source_port;
                   destination_port;
                   payload = Bytes.sub frame payload_offset payload_length;
                 })

let read_pcap path : datagram list Serror.t =
  let* bytes = read_file path in
  let* endian, _nanosecond_timestamps = pcap_endian bytes in
  let* () = check bytes 0 24 in
  let* network = u32 endian bytes 20 in
  let network = Int64.to_int network in
  let rec packets offset acc =
    if offset = Bytes.length bytes then Ok (List.rev acc)
    else
      let* () = check bytes offset 16 in
      let* seconds = u32 endian bytes offset in
      let* fraction = u32 endian bytes (offset + 4) in
      let* captured_length = u32 endian bytes (offset + 8) in
      let* original_length = u32 endian bytes (offset + 12) in
      let captured_length = Int64.to_int captured_length in
      let original_length = Int64.to_int original_length in
      if captured_length < 0 || original_length < captured_length then
        failf "invalid pcap packet lengths at offset %d" offset
      else
        let payload_offset = offset + 16 in
        let* () = check bytes payload_offset captured_length in
        let frame = Bytes.sub bytes payload_offset captured_length in
        let* datagram = parse_frame ~network ~seconds ~fraction frame in
        let acc =
          match datagram with Some value -> value :: acc | None -> acc
        in
        packets (payload_offset + captured_length) acc
  in
  packets 24 []

let group_udp_channels datagrams =
  let add (datagram : datagram) (channels : channel list) =
    let key =
      ( datagram.source,
        datagram.destination,
        datagram.source_port,
        datagram.destination_port )
    in
    let rec insert = function
      | [] ->
          [
            {
              source = datagram.source;
              destination = datagram.destination;
              source_port = datagram.source_port;
              destination_port = datagram.destination_port;
              datagrams = [ datagram ];
            };
          ]
      | channel :: rest
        when ( channel.source,
               channel.destination,
               channel.source_port,
               channel.destination_port )
             = key ->
          { channel with datagrams = datagram :: channel.datagrams } :: rest
      | channel :: rest -> channel :: insert rest
    in
    insert channels
  in
  List.fold_left (fun channels datagram -> add datagram channels) [] datagrams
  |> List.map (fun channel ->
      { channel with datagrams = List.rev channel.datagrams })
