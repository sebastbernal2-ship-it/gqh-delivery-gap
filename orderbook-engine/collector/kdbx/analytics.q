/ Read-only analytics over validated KDB-X capture tables.
/ Run: q analytics.q DB_DIRECTORY METRIC [SYMBOL]
/ METRIC is spread, depth, volatility, or trade_flow.

args:.z.x
if[2>count args; '"usage: q analytics.q DB_DIRECTORY METRIC [SYMBOL]"]
root:first args
metric:args 1
depth_path:`$":" ,root , "/depth_events.bin"

level_prices:{[levels] $[0=count levels;0f;"f"$first each levels]}
level_sizes:{[levels] $[0=count levels;0f;sum "f"$second each levels]}
best_bid:{[levels] first level_prices levels}
best_ask:{[levels] first level_prices levels}
with_book:{[table]
  update best_bid:best_bid each bids,
    best_ask:best_ask each asks,
    bid_depth:level_sizes each bids,
    ask_depth:level_sizes each asks from table}

if[metric in `spread`depth`volatility;
  depth:-9!read1 depth_path;
  if[2<count args; depth:select from depth where symbol=`$args 2];
  book:with_book depth;
  if[metric=`spread;
    result:select symbol,received_time,event_time_ms,best_bid,best_ask,
      spread:best_ask-best_bid,
      spread_bps:10000*(best_ask-best_bid)%((best_ask+best_bid)%2f)
      from book where applied=1b,best_bid>0f,best_ask>0f];
  if[metric=`depth;
    result:select symbol,received_time,event_time_ms,bid_depth,ask_depth,
      total_depth:bid_depth+ask_depth,
      imbalance:(bid_depth-ask_depth)%((bid_depth+ask_depth)%2f)
      from book where applied=1b];
  if[metric=`volatility;
    mid:select symbol,received_time,event_time_ms,
      mid:(best_bid+best_ask)%2f from book
      where applied=1b,best_bid>0f,best_ask>0f;
    mid:update log_return:log mid%prev mid by symbol from mid;
    result:select symbol,received_time,event_time_ms,mid,log_return from mid];
  -1 .j.j each result];

if[metric=`trade_flow;
  trade_path:`$":" ,root , "/trade_events.bin";
  trades:-9!read1 trade_path;
  if[2<count args; trades:select from trades where symbol=`$args 2];
  result:select symbol,received_time,event_time_ms,trade_time_ms,trade_id,
    price,quantity,buyer_is_maker,
    signed_quantity:("f"$quantity)*(1f-2f*"f"$buyer_is_maker)
    from trades;
  -1 .j.j each result];

if[not metric in `spread`depth`volatility`trade_flow;
  '"metric must be spread, depth, volatility, or trade_flow"]
