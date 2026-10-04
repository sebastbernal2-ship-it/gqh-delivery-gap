/ Export validated Binance trade events as JSONL.
/ Run: q trade_export.q DB_DIRECTORY [SYMBOL]

args:.z.x
if[0=count args; '"usage: q trade_export.q DB_DIRECTORY [SYMBOL]"]
root:first args
path:`$":" ,root , "/trade_events.bin"
t:-9!read1 path
if[1<count args; t:select from t where symbol=`$args 1]
t:update event_time_ms:"j"$event_time_ms,
  trade_time_ms:"j"$trade_time_ms,
  trade_id:"j"$trade_id from t
t:`received_time xasc t
-1 .j.j each t
