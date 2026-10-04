/ KDB-X schema for validated Binance depth events.

depth_events:([]
  kind:`symbol$();
  segment:`long$();
  symbol:`symbol$();
  received_time:`timestamp$();
  event_time_ms:`long$();
  source_path:`symbol$();
  source_sha256:`symbol$();
  applied:`boolean$();
  last_update_id:`long$();
  first_update_id:`long$();
  final_update_id:`long$();
  previous_update_id:`long$();
  bids:();
  asks:())

trade_events:([])
  received_time:`timestamp$();
  event_time_ms:`long$();
  trade_time_ms:`long$();
  source_path:`symbol$();
  source_sha256:`symbol$();
  symbol:`symbol$();
  trade_id:`long$();
  price:`symbol$();
  quantity:`symbol$();
  buyer_is_maker:`boolean$())
