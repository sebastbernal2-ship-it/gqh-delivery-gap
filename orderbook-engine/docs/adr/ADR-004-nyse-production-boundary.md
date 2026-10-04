# ADR-004: NYSE production replay boundary

## Decision

Keep pcap extraction, UDP channel grouping, XDP packet framing, message decoding, and order-book replay as separate stages.

The pcap stage preserves capture metadata and exact UDP payloads.

The XDP stage validates packet lengths, message counts, delivery flags, and channel sequence continuity.

The message stage validates symbol mappings, source timestamps, message lengths, and symbol sequence continuity.

The replay stage applies only validated semantic events.

Any missing mapping, unsupported message, packet gap, or symbol gap fails closed.

## Evidence

The NYSE National Pillar sample PCAP contains 59,131 UDP datagrams across 26 channels.

Its observed message types are 2, 34, 100, 101, 102, 103, 104, 105, 110, 111, 140, 220, and 223.

The capture does not contain Symbol Index Mapping messages.

The public FTP no longer exposes the February 23, 2022 National mapping file.

A Wayback copy of the generic May 2022 mapping file does not contain observed indexes 48869 or 59083.

The capture contains a shared packet gap on redundant order channels from sequence 54596 to 54990.

The decoder therefore cannot claim a continuous production book from this capture.

## Consequences

A complete replay needs the matching channel mapping source and a loss-free channel or an official retransmission or refresh result.

A packet gap invalidates the affected book until recovery or refresh data establishes a new trusted boundary.

Synthetic symbol mappings may test binary layouts, but they cannot prove symbol identity or price-scale correctness.
