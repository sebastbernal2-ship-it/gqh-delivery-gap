/ Load one validated Binance trade-event JSONL file into KDB-X.
/ Run from this directory:
/   q trade_load.q NORMALIZED_JSONL DB_DIRECTORY

file:first .z.x
root:.z.x 1
data:flip .j.k each read0 `$file
rows:([]
  received_time:raze ("P"$) each data`received_time;
  event_time_ms:data`event_time_ms;
  trade_time_ms:data`trade_time_ms;
  source_path:data`source_path;
  source_sha256:data`source_sha256;
  symbol:data`symbol;
  trade_id:data`trade_id;
  price:data`price;
  quantity:data`quantity;
  buyer_is_maker:data`buyer_is_maker)
system "mkdir -p ",root
savepath:`$":" ,root,"/trade_events.bin"
if[0N<>@[hcount;savepath;{0N}]; rows:(-9!read1 savepath),rows]
system "rm -f ",root,"/trade_events.bin"
h:hopen savepath
h -8!rows
hclose h
-1 "loaded ",(string count rows)," trade rows"
