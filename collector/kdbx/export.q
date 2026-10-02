/ Export validated Binance normalized rows as JSONL for OCaml replay.
/ Run: q export.q DB_DIRECTORY [SYMBOL]

args:.z.x
if[0=count args; '"usage: q export.q DB_DIRECTORY [SYMBOL]"]
root:first args
path:`$":" ,root , "/depth_events.bin"
t:-9!read1 path
if[1<count args; t:select from t where symbol=`$args 1]
t:update event_time_ms:"j"$event_time_ms,
  last_update_id:"j"$last_update_id,
  first_update_id:"j"$first_update_id,
  final_update_id:"j"$final_update_id,
  previous_update_id:"j"$previous_update_id from t
t:`received_time xasc t
-1 .j.j each t
