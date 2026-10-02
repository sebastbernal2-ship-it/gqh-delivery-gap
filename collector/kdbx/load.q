/ Load one validated normalized JSONL file into KDB-X.
/ Run from this directory:
/   q load.q NORMALIZED_JSONL DB_DIRECTORY

file:first .z.x
root:.z.x 1
data:flip .j.k each read0 `$file
rows:([]
  kind:data`kind;
  segment:data`segment;
  symbol:data`symbol;
  received_time:raze ("P"$) each data`received_time;
  event_time_ms:data`event_time_ms;
  source_path:data`source_path;
  source_sha256:data`source_sha256;
  applied:data`applied;
  last_update_id:data`last_update_id;
  first_update_id:data`first_update_id;
  final_update_id:data`final_update_id;
  previous_update_id:data`previous_update_id;
  bids:data`bids;
  asks:data`asks)
system "mkdir -p ",root
savepath:`$":" ,root,"/depth_events.bin"
append_rows:{[old;new] old,:new; old}
depth_events:rows
if[0N<>@[hcount;savepath;{0N}]; depth_events:append_rows[-9!read1 savepath;rows]]
system "rm -f ",root,"/depth_events.bin"
h:hopen savepath
h -8!depth_events
hclose h
-1 "loaded ",(string count rows)," rows"
